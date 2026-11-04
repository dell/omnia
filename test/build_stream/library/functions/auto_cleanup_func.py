# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""BuildStream automated cleanup (retention): facts, one pass, verification.

The AutoCleanupScheduler in the
omnia_build_stream container calls ``cleanup_cron.main()`` every
``retention.evaluation_interval_hours`` while
``retention.auto_cleanup_enabled`` is true. This module runs that same entry
point once, with a stdout log handler so every line can be followed.

Eligibility mirrors the source exactly:

FAILED phase (``list_by_status_all(FAILED)``)
    every image group in FAILED is submitted for cleanup.
Retention phase (``list_eligible_for_retention``), evaluated after the
FAILED phase moved those groups to CLEANING
    not protected, deploy_count = 0, created before now - retention_age_days,
    status not CLEANED/CLEANING; oldest first, and only while the group's
    catalog_identifier keeps more than min_keep_count active image groups.
    Groups without a catalog_identifier are never retention candidates.
    Candidates in DEPLOYING/RESTARTING/VALIDATING are refused (counted as
    errors by cleanup_cron).

A submitted group moves to CLEANING; the playbook watcher runs
``image_build_manager.yml --tags cleanup_images`` (log
``/var/log/omnia/image_build_manager/cleanup_*.log``, streamed with
debug_mode) and the result poller then moves it to CLEANED (job tombstoned,
JOB_CLEANED) or CLEANUP_FAILED.
"""

import re
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

from omnia_auto import read_remote_yaml

from .db_func import db_now_epoch, query
from .log_func import LogFollower, find_stage_log
from .execute_probe_func import (
    Probe,
    data_path,
    domain_input_path,
    path_exists,
    run_cmd,
    summarize,
)
from .probe_func import container_running, unit_active
from ..messages.execute_msgs import PROGRESS_MSGS as PROGRESS
from ..vars.execute_vars import (
    AUDIT_CLEANED,
    AUDIT_CLEANUP_FAILED,
    AUDIT_CLEANUP_SUBMITTED,
    AUDIT_RETENTION_DELETED,
    AUTO_CLEANUP_BORDERLINE_SECONDS,
    AUTO_CLEANUP_FATAL_RC,
    AUTO_CLEANUP_LOG_RE,
    AUTO_CLEANUP_TRIGGER_CODE,
    BSM_CONFIG_FILE,
    BSM_CONTAINER,
    BSM_DOMAIN,
    BSM_PLAYBOOK_WATCHER_SERVICE,
    CLEANUP_LOG_STAGE,
    IMAGE_GROUP_ACTIVE,
    IMAGE_GROUP_CLEANED,
    IMAGE_GROUP_CLEANING,
    IMAGE_GROUP_CLEANUP_FAILED,
    IMAGE_GROUP_FAILED,
    IMAGE_GROUP_NOT_COUNTED,
    NFS_ARTIFACTS_DIR,
    RETENTION_DEFAULTS,
    RETENTION_MINIMUMS,
    RETENTION_SECTION,
    S3CMD_CONFIG,
    SECONDS_PER_DAY,
    SQL,
    UNKNOWN_CATALOG_IDENTIFIER,
    UUID_RE,
)
from ..vars.common_vars import S3_BOOT_IMAGES_BUCKET

Emit = Callable[[str], None]
_GROUP_FIELDS = ("id", "job_id", "status", "deploy_count", "is_protected",
                 "catalog_identifier", "created_epoch")


def retention_settings(host: Any) -> Dict[str, Any]:
    """Read and validate ``retention`` from the project build_stream_config.yml.

    Validation follows retention_config.py: an invalid value makes the
    scheduler keep its previous settings, so it is reported as an error.

    Returns:
        Dict with keys: success, config (effective settings), path, error.
    """
    path = BSM_CONFIG_FILE
    try:
        path = f"{domain_input_path(host, BSM_DOMAIN)}/{BSM_CONFIG_FILE}"
        section = (read_remote_yaml(host, path) or {}).get(RETENTION_SECTION) or {}
    except (RuntimeError, ValueError, AttributeError) as exc:
        return {"success": False, "config": {}, "path": path, "error": str(exc)}
    if not isinstance(section, dict):
        return {"success": False, "config": {}, "path": path,
                "error": f"{RETENTION_SECTION} is not a mapping"}

    unknown = sorted(set(section) - set(RETENTION_DEFAULTS))
    config = {**RETENTION_DEFAULTS, **section}
    errors = [f"unknown keys {unknown}"] if unknown else []
    if not isinstance(config["auto_cleanup_enabled"], bool):
        errors.append(f"auto_cleanup_enabled={config['auto_cleanup_enabled']!r}")
    for key, minimum in RETENTION_MINIMUMS.items():
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            errors.append(f"{key}={value!r} (integer >= {minimum})")
    if errors:
        return {"success": False, "config": config, "path": path,
                "error": f"invalid {RETENTION_SECTION} in {path}: {'; '.join(errors)}"}
    return {"success": True, "config": config, "path": path, "error": ""}


def precheck_auto_cleanup(host: Any) -> Dict[str, Any]:
    """Check that one automated cleanup pass can run and be finalized.

    Verifies the ``retention`` settings (as the scheduler validates them),
    the omnia_build_stream container (runs the pass) and playbook-watcher
    (runs the cleanup playbook that finalizes CLEANING groups).

    Returns:
        Dict with keys: name, success, fields, failures, config (effective
        retention settings), path (build_stream_config.yml), enabled.
    """
    settings = retention_settings(host)
    probes = [(f"retention in {settings['path']}",
               "valid" if settings["success"] else settings["error"], settings["success"]),
              container_running(host, BSM_CONTAINER),
              unit_active(host, BSM_PLAYBOOK_WATCHER_SERVICE)]
    result = summarize("precheck_auto_cleanup", probes)
    result.update(config=settings["config"], path=settings["path"],
                  enabled=bool(settings["config"].get("auto_cleanup_enabled")))
    return result


def _groups(host: Any) -> List[Dict[str, Any]]:
    """Return every image group with the cleanup_cron eligibility inputs."""
    result = query(host, SQL["auto_cleanup_groups"])
    if not result["success"]:
        raise RuntimeError(f"cannot read image_groups: {result['error']}")
    groups = []
    for row in result["rows"]:
        if len(row) < len(_GROUP_FIELDS):
            continue
        group = dict(zip(_GROUP_FIELDS, row))
        group["deploy_count"] = int(group["deploy_count"] or 0)
        group["is_protected"] = group["is_protected"] == "t"
        group["created_epoch"] = int(group["created_epoch"])
        groups.append(group)
    return groups


def s3_keys(host: Any) -> List[str]:
    """Return every object key in the boot-images bucket.

    Raises:
        RuntimeError: When the bucket cannot be listed.
    """
    result = run_cmd(host, "s3_list_recursive", config=S3CMD_CONFIG,
                     bucket=S3_BOOT_IMAGES_BUCKET)
    if result.rc != 0:
        raise RuntimeError(
            f"s3cmd ls -r {S3_BOOT_IMAGES_BUCKET} failed (rc={result.rc}): "
            f"{(result.stderr or result.stdout).strip()}")
    return [f"s3://{line.split('s3://', 1)[1]}" for line in result.stdout.splitlines()
            if "s3://" in line]


def snapshot_state(host: Any) -> Dict[str, Any]:
    """Capture image groups, DB time and boot-images objects.

    Returns:
        Dict with keys: success, now_epoch, groups, s3_keys, error.
    """
    try:
        return {"success": True, "now_epoch": db_now_epoch(host), "groups": _groups(host),
                "s3_keys": s3_keys(host), "error": ""}
    except RuntimeError as exc:
        return {"success": False, "now_epoch": 0, "groups": [], "s3_keys": [],
                "error": str(exc)}


def expected_candidates(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply the cleanup_cron.py rules to a snapshot.

    Returns:
        Dict with keys: failed (FAILED-phase group IDs), retention (retention
        group IDs), refused (retention IDs in an active status, expected to
        error), borderline (IDs whose age is within the clock tolerance of the
        cutoff), reasons ({group_id: why it is or is not a candidate}).
    """
    groups = state["groups"]
    cutoff = state["now_epoch"] - config["retention_age_days"] * SECONDS_PER_DAY
    min_keep = config["min_keep_count"]
    failed = [g["id"] for g in groups if g["status"] == IMAGE_GROUP_FAILED]

    # The retention query runs after the FAILED phase moved those to CLEANING.
    status = {g["id"]: (IMAGE_GROUP_CLEANING if g["id"] in failed else g["status"])
              for g in groups}
    active = [g for g in groups if status[g["id"]] not in IMAGE_GROUP_NOT_COUNTED]
    counts: Dict[str, int] = {}
    for group in active:
        counts[group["catalog_identifier"]] = counts.get(group["catalog_identifier"], 0) + 1

    reasons = {gid: "FAILED phase" for gid in failed}
    candidates = []
    for group in sorted(active, key=lambda item: item["created_epoch"]):
        why = ("protected" if group["is_protected"] else
               f"deploy_count={group['deploy_count']}" if group["deploy_count"] else
               "younger than retention_age_days" if group["created_epoch"] >= cutoff else "")
        if why:
            reasons[group["id"]] = f"kept: {why}"
        else:
            candidates.append(group)

    retention = _retention_phase(candidates, counts, min_keep, reasons)

    return {
        "failed": failed,
        "retention": retention,
        "refused": [g["id"] for g in groups
                    if g["id"] in retention and g["status"] in IMAGE_GROUP_ACTIVE],
        "borderline": [g["id"] for g in groups
                       if abs(g["created_epoch"] - cutoff) <= AUTO_CLEANUP_BORDERLINE_SECONDS],
        "reasons": reasons,
    }


def _retention_phase(candidates: List[Dict[str, Any]], counts: Dict[str, int],
                     min_keep: int, reasons: Dict[str, str]) -> List[str]:
    """Return the retention-phase group IDs, oldest first, honouring min_keep_count.

    Records the decision for every candidate in ``reasons``.
    """
    retention, pending = [], {}
    for group in candidates:
        key = group["catalog_identifier"] or UNKNOWN_CATALOG_IDENTIFIER
        if min_keep <= 0 or counts.get(key, 0) - pending.get(key, 0) > min_keep:
            retention.append(group["id"])
            pending[key] = pending.get(key, 0) + 1
            reasons[group["id"]] = "retention phase"
        else:
            reasons[group["id"]] = (
                f"kept: catalog '{group['catalog_identifier'] or 'none'}' "
                f"at min_keep_count={min_keep}")
    return retention


def _parse_pass(stdout: str) -> Dict[str, Any]:
    """Extract submitted groups, phase summaries and errors from the pass log."""
    parsed: Dict[str, Any] = {"submitted": [], "retention_deleted": [], "errors": []}
    for line in stdout.splitlines():
        for key, pattern in AUTO_CLEANUP_LOG_RE.items():
            match = pattern.search(line)
            if not match:
                continue
            if key in ("submitted", "retention_deleted"):
                parsed[key].append(match.group(1))
            elif key == "error":
                parsed["errors"].append(match.group(1).strip())
            else:
                parsed[key] = tuple(int(value) for value in match.groups())
            break
    return parsed


def run_cleanup_pass(host: Any, emit: Emit) -> Dict[str, Any]:
    """Run one ``cleanup_cron.main()`` pass in omnia_build_stream.

    Returns:
        Dict with keys: rc (0 ok, 1 some groups failed, 2 fatal), started_epoch,
        submitted, retention_deleted, errors, and the parsed summary tuples
        failed_phase, retention_started, retention_eligible (when logged).
    """
    started = db_now_epoch(host)
    result = run_cmd(host, "container_python", container=BSM_CONTAINER,
                     code=AUTO_CLEANUP_TRIGGER_CODE)
    for line in result.stdout.splitlines():
        emit(line)
    parsed = _parse_pass(result.stdout)
    if result.stderr.strip():
        parsed["errors"].extend(line for line in result.stderr.splitlines() if line.strip())
    return {"rc": result.rc, "started_epoch": started, **parsed}


def follow_cleanup_log(host: Any, since_epoch: int, follower: Optional[LogFollower],
                       shown: Dict[str, str], emit: Emit) -> None:
    """Stream (debug_mode) or point to the newest cleanup playbook log.

    The playbook watcher writes ``cleanup_image_build_manager.yml_<ts>_attempt<N>.log``
    under /var/log/omnia/image_build_manager/ for every cleanup request.
    """
    path = find_stage_log(host, CLEANUP_LOG_STAGE, since_epoch)
    if not path or shown.get("path") == path:
        return
    shown["path"] = path
    if follower is not None:
        follower.follow(path)
        emit(PROGRESS["cleanup_log_streaming"].format(path=path))
    else:
        emit(PROGRESS["cleanup_log_follow"].format(path=path))


def wait_for_finalization(host: Any, cleanup_pass: Dict[str, Any], poll: int, emit: Emit,
                          debug_mode: bool = True) -> Dict[str, str]:
    """Poll until no submitted group is CLEANING; return {group_id: status}.

    ``cleanup_pass`` is the ``run_cleanup_pass`` result: its ``submitted``
    groups are followed and the cleanup playbook log is looked up from its
    ``started_epoch``.

    No timeout, like the rest of the suite: the cleanup playbook runs until
    it finishes and the result poller always leaves CLEANING. The cleanup
    playbook log is streamed live with ``debug_mode``, otherwise its
    ``tail -f`` command is printed with a status line on every change.
    """
    group_ids: Sequence[str] = cleanup_pass["submitted"]
    since_epoch = cleanup_pass["started_epoch"]
    statuses: Dict[str, str] = {}
    follower = LogFollower(host) if debug_mode else None
    shown: Dict[str, str] = {}
    started = time.time()
    try:
        while True:
            follow_cleanup_log(host, since_epoch, follower, shown, emit)
            rows = query(host, SQL["auto_cleanup_statuses"])
            current = {row[0]: row[1] for row in rows["rows"] if len(row) >= 2}
            latest = {gid: current.get(gid, "NOT FOUND") for gid in group_ids}
            described = ", ".join(f"{gid}={state}" for gid, state in latest.items())
            if latest != statuses:
                statuses = latest
                emit(PROGRESS["cleanup_statuses"].format(statuses=described))
            elif follower is None:
                emit(PROGRESS["cleanup_still_running"].format(
                    elapsed=int(time.time() - started), statuses=described))
            if rows["success"] and IMAGE_GROUP_CLEANING not in statuses.values():
                return statuses
            time.sleep(poll)
    finally:
        if follower is not None:
            follower.drain(final=True)


def _audit(host: Any, epoch: int) -> List[Dict[str, str]]:
    """Return cleanup audit events recorded since ``epoch``."""
    result = query(host, SQL["auto_cleanup_audit_since"].format(epoch=int(epoch)))
    return [{"event_type": row[0], "job_id": row[1], "image_group_id": row[2]}
            for row in result["rows"] if len(row) >= 3]


def _tombstoned(host: Any, job_ids: Sequence[str]) -> Dict[str, bool]:
    """Return ``{job_id: tombstoned}`` for valid job UUIDs."""
    valid = [job_id for job_id in job_ids if UUID_RE.fullmatch(job_id)]
    if not valid:
        return {}
    result = query(host, SQL["jobs_tombstoned"].format(
        job_ids=", ".join(f"'{job_id}'" for job_id in valid)))
    return {row[0]: row[1] == "t" for row in result["rows"] if len(row) >= 2}


def group_pattern(group_id: str) -> "re.Pattern[str]":
    """Match ``group_id`` in an artifact name without matching a longer version.

    ``...-v1.2`` must not match ``...-v1.20`` (artifact names continue with
    ``-imgth``), so the ID may not be followed by a digit or a dot.
    """
    return re.compile(re.escape(group_id) + r"(?![0-9.])")


def matching(keys: Sequence[str], group_id: str) -> List[str]:
    """Return the keys that belong to ``group_id``."""
    pattern = group_pattern(group_id)
    return [key for key in keys if pattern.search(key)]


def _pass_probes(expected: Dict[str, Any], cleanup_pass: Dict[str, Any],
                 config: Dict[str, Any]) -> List[Probe]:
    """Compare the pass log with the expected candidates."""
    want = set(expected["failed"]) | set(expected["retention"])
    got = set(cleanup_pass["submitted"])
    tolerated = set(expected["borderline"]) | set(expected["refused"])
    probes = [("cleanup_cron exit code", str(cleanup_pass["rc"]),
               cleanup_pass["rc"] == (1 if expected["refused"] else 0))]

    logged = cleanup_pass.get("retention_started")
    probes.append(("Retention settings used by the pass",
                   f"retention_age_days={logged[0]}, min_keep_count={logged[1]}"
                   if logged else "NOT LOGGED",
                   bool(logged) and tuple(logged) == (config["retention_age_days"],
                                                      config["min_keep_count"])))

    failed_phase = cleanup_pass.get("failed_phase")
    probes.append(("FAILED phase total/cleaned/errors",
                   "/".join(map(str, failed_phase)) if failed_phase else "NOT LOGGED",
                   bool(failed_phase) and failed_phase[0] == len(expected["failed"])
                   and failed_phase[2] == 0))

    eligible = (cleanup_pass.get("retention_eligible") or (None,))[0]
    probes.append(("Retention eligible (logged / expected)",
                   f"{eligible} / {len(expected['retention'])}",
                   eligible is not None and (
                       eligible == len(expected["retention"])
                       or bool(set(expected["borderline"])))))

    missing, unexpected = sorted(want - got - tolerated), sorted(got - want - tolerated)
    probes.append(("Groups submitted for cleanup", ", ".join(sorted(got)) or "none",
                   not missing and not unexpected))
    probes.extend((f"Expected candidate {gid}", "NOT SUBMITTED", False) for gid in missing)
    probes.extend((f"Unexpected cleanup {gid}", "SUBMITTED although not eligible", False)
                  for gid in unexpected)
    unexpected_errors = [] if expected["refused"] else cleanup_pass["errors"]
    probes.extend((f"Pass error {index + 1}", error, False)
                  for index, error in enumerate(unexpected_errors))
    return probes


def _summary_fields(before: Dict[str, Any], expected: Dict[str, Any],
                    config: Dict[str, Any]) -> List[tuple]:
    """Return the pass context shown above the probes."""
    return [("retention_age_days", config["retention_age_days"]),
            ("min_keep_count", config["min_keep_count"]),
            ("Image groups before", len(before["groups"])),
            ("Expected FAILED phase", ", ".join(expected["failed"]) or "none"),
            ("Expected retention phase", ", ".join(expected["retention"]) or "none")]


def verify_auto_cleanup_db(host: Any, state: Dict[str, Any]) -> Dict[str, Any]:
    """Verify the recorded pass in build_stream_db.

    The pass submitted exactly the expected candidates; each one is CLEANED,
    its job tombstoned and its audit trail complete (JOB_CLEANUP_SUBMITTED,
    JOB_CLEANED, RETENTION_DELETED for retention, never JOB_CLEANUP_FAILED);
    every other image group kept its status.

    Returns:
        Dict with keys: name, success, fields, failures (see ``summarize``).
    """
    before, expected, cleanup_pass = state["before"], state["expected"], state["cleanup_pass"]
    config = state["config"]
    probes = _pass_probes(expected, cleanup_pass, config)
    after_status = {g["id"]: g["status"] for g in _groups(host)}
    groups = {g["id"]: g for g in before["groups"]}
    submitted = [gid for gid in cleanup_pass["submitted"] if gid in groups]
    probes += _submitted_probes(host, state, groups, submitted)
    probes += _kept_probes(expected, groups, submitted, after_status)
    return summarize("auto_cleanup_db", probes, _summary_fields(before, expected, config))


def _submitted_probes(host: Any, state: Dict[str, Any], groups: Dict[str, Dict[str, Any]],
                      submitted: Sequence[str]) -> List[Probe]:
    """Probe status, job tombstone and audit trail of every submitted group."""
    expected, final = state["expected"], state["final"]
    audit = _audit(host, state["cleanup_pass"]["started_epoch"])
    tombstoned = _tombstoned(host, [groups[gid]["job_id"] for gid in submitted])
    probes: List[Probe] = []
    for gid in submitted:
        job_id = groups[gid]["job_id"]
        events = {e["event_type"] for e in audit if e["job_id"] == job_id}
        probes += [
            (f"{gid} status", f"{groups[gid]['status']} -> {final.get(gid, 'NOT FOUND')}",
             final.get(gid) == IMAGE_GROUP_CLEANED),
            (f"{gid} job {job_id} tombstoned", str(tombstoned.get(job_id, False)).lower(),
             tombstoned.get(job_id, False)),
            (f"{gid} audit", ", ".join(sorted(events)) or "none",
             {AUDIT_CLEANUP_SUBMITTED, AUDIT_CLEANED} <= events
             and AUDIT_CLEANUP_FAILED not in events
             and (gid not in expected["retention"] or AUDIT_RETENTION_DELETED in events)),
        ]
    return probes


def _kept_probes(expected: Dict[str, Any], groups: Dict[str, Dict[str, Any]],
                 submitted: Sequence[str], after_status: Dict[str, str]) -> List[Probe]:
    """Probe that every image group not submitted kept its status."""
    probes: List[Probe] = []
    for gid, group in groups.items():
        if gid in submitted:
            continue
        status = after_status.get(gid, "NOT FOUND")
        cleaned = status in (IMAGE_GROUP_CLEANING, IMAGE_GROUP_CLEANED,
                             IMAGE_GROUP_CLEANUP_FAILED, "NOT FOUND")
        probes.append((f"{gid} kept ({expected['reasons'].get(gid, 'not eligible')})",
                       f"{group['status']} -> {status}",
                       not cleaned or group["status"] in IMAGE_GROUP_NOT_COUNTED
                       or group["status"] == IMAGE_GROUP_CLEANUP_FAILED))
    return probes


def verify_auto_cleanup_artifacts(host: Any, state: Dict[str, Any]) -> Dict[str, Any]:
    """Verify the recorded pass in S3 and on the NFS share.

    Every cleaned group's boot-images objects and NFS artifact directory are
    gone; no object of a kept group was deleted.

    Returns:
        Dict with keys: name, success, fields, failures (see ``summarize``).
    """
    before, cleanup_pass = state["before"], state["cleanup_pass"]
    groups = {g["id"]: g for g in before["groups"]}
    submitted = [gid for gid in cleanup_pass["submitted"] if gid in groups]
    try:
        after_keys = s3_keys(host)
    except RuntimeError as exc:
        return summarize("auto_cleanup_artifacts", [("boot-images listing", str(exc), False)])
    artifacts = f"{data_path(host)}/{NFS_ARTIFACTS_DIR}"
    probes: List[Probe] = []
    for gid in submitted:
        job_dir = f"{artifacts}/{groups[gid]['job_id']}"
        leftover = matching(after_keys, gid)
        probes += [
            (f"{gid} S3 objects", f"{len(matching(before['s3_keys'], gid))} -> {len(leftover)}",
             not leftover),
            (f"{gid} NFS artifacts {job_dir}",
             "STILL EXISTS" if path_exists(host, job_dir) else "removed",
             not path_exists(host, job_dir)),
        ]
    removed_keys = [key for key in set(before["s3_keys"]) - set(after_keys)
                    if not any(matching([key], gid) for gid in submitted)]
    probes.append(("S3 objects of kept groups", f"{len(removed_keys)} deleted",
                   not removed_keys))
    probes.extend(("Unexpected S3 deletion", key, False) for key in sorted(removed_keys))
    return summarize("auto_cleanup_artifacts", probes, [
        ("Groups cleaned by the pass", ", ".join(submitted) or "none"),
        ("boot-images objects before / after", f"{len(before['s3_keys'])} / {len(after_keys)}"),
    ])


def run_auto_cleanup(host: Any, config: Dict[str, Any], poll: int, emit: Emit,
                     debug_mode: bool = True) -> Dict[str, Any]:
    """Run one automated cleanup pass end to end.

    Snapshots every image group and boot-images object, computes the
    expected candidates, runs one ``cleanup_cron.main()`` pass and waits
    until no submitted group is CLEANING (cleanup playbook log streamed
    with ``debug_mode``).

    Returns:
        Dict with keys: success (the pass ran without a fatal error), error,
        state (before, expected, cleanup_pass, final, config — everything
        the verification functions need).
    """
    before = snapshot_state(host)
    if not before["success"]:
        return {"success": False, "error": before["error"], "state": {}}
    expected = expected_candidates(before, config)
    for line in describe_candidates(before, expected):
        emit(line)
    cleanup_pass = run_cleanup_pass(host, emit)
    final = (wait_for_finalization(host, cleanup_pass, poll, emit, debug_mode)
             if cleanup_pass["submitted"] else {})
    fatal = cleanup_pass["rc"] == AUTO_CLEANUP_FATAL_RC
    return {
        "success": not fatal,
        "error": (f"cleanup_cron exit code {cleanup_pass['rc']}: "
                  f"{'; '.join(cleanup_pass['errors']) or 'see output'}") if fatal else "",
        "state": {"before": before, "expected": expected, "cleanup_pass": cleanup_pass,
                  "final": final, "config": config},
    }


def describe_candidates(state: Dict[str, Any], expected: Dict[str, Any]) -> List[str]:
    """Return one line per image group explaining the expected decision."""
    now = state["now_epoch"]
    return [f"{g['id']}: status={g['status']}, "
            f"age={(now - g['created_epoch']) / SECONDS_PER_DAY:.2f}d, "
            f"deploy_count={g['deploy_count']}, protected={str(g['is_protected']).lower()}, "
            f"catalog={g['catalog_identifier'] or 'none'} -> "
            f"{expected['reasons'].get(g['id'], 'kept: already cleaned')}"
            for g in state["groups"]]
