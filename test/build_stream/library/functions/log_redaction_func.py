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

"""Write-time redaction of stage logs on disk (ER-BSM-003 TC-FVT-019).

The watcher captures playbook stdout/stderr, redacts every line (Tier 1
only) and writes the sanitized stream to ``/var/log/omnia/<domain>/``; the
published copy under ``<OMNIA_DATA_PATH>/build_stream/log/<job_id>/`` is
mode 0644 with its directory's SELinux label. For every stage log of the
target job, both copies are read on the OIM and scanned in this process:

- no Tier 1 secret pattern is left (``LOG_SECRET_DETECTORS``);
- no value of build_stream_credentials.yml or of the secret GitLab CI/CD
  variables occurs (values stay in memory; only key names are reported);
- no Tier 2 marker (``<REDACTED_IP>``) appears: identifiers stay verbatim;
- no line carries Ansible's own ``log_path`` prefix (capture replaced it);
- Ansible stage logs keep their ``TASK [`` lines.

Findings report the detector name and line number, never the matched text.
"""

import posixpath
from typing import Any, Callable, Dict, List, Tuple

from . import gitlab_api_func
from .bsm_api_func import read_bsm_credentials
from .execute_probe_func import run_cmd
from .log_query_func import SESSION, add_check, blocked_result, finish, new_result, target
from ..messages.execute_msgs import STEP_MSGS
from ..vars.execute_vars import (
    LOG_ANSIBLE_PREFIX_RE,
    LOG_ANSIBLE_STAGES,
    LOG_CI_SECRET_VARIABLES,
    LOG_KNOWN_SECRET_KEY_RE,
    LOG_KNOWN_SECRET_MIN_LENGTH,
    LOG_PUBLISHED_MODE,
    LOG_REDACTION_SUPPRESSED,
    LOG_SECRET_DETECTORS,
    LOG_TASK_MARKER,
    LOG_TIER2_MARKERS,
    PLAYBOOK_LOG_BASE_DIR,
)

Emit = Callable[[str], None]


Secret = Tuple[str, str]
_MAX_REPORTED_LINES = 5


def _secret_leaves(data: Any, key: str = "") -> List[Secret]:
    """Return ``(key name, value)`` for secret-named keys in a nested mapping."""
    if isinstance(data, dict):
        return [pair for name, item in data.items()
                for pair in _secret_leaves(item, str(name))]
    if isinstance(data, list):
        return [pair for item in data for pair in _secret_leaves(item, key)]
    if (isinstance(data, str) and LOG_KNOWN_SECRET_KEY_RE.search(key)
            and len(data) >= LOG_KNOWN_SECRET_MIN_LENGTH):
        return [(key, data)]
    return []


def known_secrets(host: Any, api: Dict[str, Any]) -> Dict[str, Any]:
    """Collect the credential values that must never reach a log.

    Each value keeps the name it is known by (the credential key or the CI/CD
    variable name), so a finding can say which credential leaked without
    printing it. Values are kept in memory only.

    Returns:
        Dict with keys: success, values (list of (name, value)), error.
    """
    context = api["context"]
    try:
        pairs = _secret_leaves(read_bsm_credentials(host, context["input_dir"]))
    except RuntimeError as exc:
        return {"success": False, "values": [], "error": str(exc)}
    for key in LOG_CI_SECRET_VARIABLES:
        variable = gitlab_api_func.ci_variable_value(context, key)
        if variable["success"] and len(variable["value"]) >= LOG_KNOWN_SECRET_MIN_LENGTH:
            pairs.append((key, variable["value"]))
    unique = {value: name for name, value in sorted(pairs, key=lambda pair: pair[0])}
    return {"success": True, "values": [(name, value) for value, name in unique.items()],
            "error": ""}


def scan_log(content: str, stage: str, secrets: List[Secret]) -> Dict[str, Any]:
    """Scan one log text; return findings without any matched content.

    A leaked credential is reported by its key name and the line numbers it
    appears on (the first few), never by its value.

    Returns:
        Dict with keys: lines, problems (list of text), suppressed.
    """
    problems: List[str] = []
    hits: Dict[str, int] = {}
    prefixed = 0
    lines = content.splitlines()
    for number, line in enumerate(lines, start=1):
        for name, pattern in LOG_SECRET_DETECTORS.items():
            if name not in hits and pattern.search(line):
                hits[name] = number
        if LOG_ANSIBLE_PREFIX_RE.match(line):
            prefixed += 1
    problems.extend(f"{name} pattern left at line {number}" for name, number in hits.items())
    for name, value in secrets:
        found = [number for number, line in enumerate(lines, start=1) if value in line]
        if found:
            shown = ", ".join(str(number) for number in found[:_MAX_REPORTED_LINES])
            more = f" (+{len(found) - _MAX_REPORTED_LINES} more)" \
                if len(found) > _MAX_REPORTED_LINES else ""
            problems.append(f"credential {name} found in clear text at line(s) {shown}{more}")
    problems.extend(f"Tier 2 marker {marker} present (identifiers must stay verbatim)"
                    for marker in LOG_TIER2_MARKERS if marker in content)
    if prefixed:
        problems.append(f"{prefixed} line(s) carry Ansible's log_path prefix "
                        "(output not captured by the watcher)")
    if stage in LOG_ANSIBLE_STAGES and LOG_TASK_MARKER not in content:
        problems.append(f"no '{LOG_TASK_MARKER}' line (task output not preserved)")
    return {"lines": len(lines), "problems": problems,
            "suppressed": content.count(LOG_REDACTION_SUPPRESSED)}


def mode_and_label(host: Any, path: str) -> Dict[str, Any]:
    """Check a log is 0644 and labelled like its directory (what publish_stage_log sets).

    Returns:
        Dict with keys: ok, state.
    """
    file_stat = run_cmd(host, "log_stat", path=path)
    dir_stat = run_cmd(host, "log_stat", path=posixpath.dirname(path))
    if file_stat.rc != 0 or dir_stat.rc != 0:
        return {"ok": False, "state": f"stat failed (rc={file_stat.rc}/{dir_stat.rc})"}
    mode, _, label = file_stat.stdout.strip().partition("|")
    dir_label = dir_stat.stdout.strip().partition("|")[2]
    ok = mode == LOG_PUBLISHED_MODE and label == dir_label
    return {"ok": ok, "state": f"mode {mode}, label {label or '-'} (directory {dir_label or '-'})"}


def _scan_file(host: Any, result: Dict[str, Any], item: Tuple[str, str, str],
               secrets: List[Secret]) -> None:
    """Read one log ``(label, path, stage)`` on the OIM and record its scan."""
    label, path, stage = item
    read = run_cmd(host, "cat_file", path=path)
    if not add_check(result, read.rc == 0, label, path, f"{label}: cannot read {path} "
                     f"(rc={read.rc})"):
        return
    scan = scan_log(read.stdout, stage, secrets)
    state = (f"{scan['lines']} lines, {len(secrets)} credential values not found"
             if not scan["problems"] else "; ".join(scan["problems"]))
    if scan["suppressed"]:
        state = f"{state}; {scan['suppressed']} line(s) withheld by redaction"
    add_check(result, not scan["problems"], f"{label} redaction", state,
              f"{label} ({posixpath.basename(path)}): {'; '.join(scan['problems'])}")


def verify_write_time_redaction(host: Any, settings: Dict[str, Any],
                                emit: Emit) -> Dict[str, Any]:
    """TC-FVT-019: published and domain stage logs hold only sanitized output."""
    del settings
    job = target()
    api = SESSION.get("client")
    if not job or not api:
        return blocked_result(STEP_MSGS["log_no_target"])
    result = new_result()
    secrets = known_secrets(host, api)
    if not add_check(result, secrets["success"], "Credential values to look for",
                     f"{len(secrets['values'])} (values are not shown)",
                     f"cannot read the credential values: {secrets['error']}"):
        return finish(result)
    stored = {s.get("stage_name"): s.get("log_file_path") or "" for s in job["stages"]}
    for stage in sorted(job["logged"]):
        path = stored.get(stage, "")
        if not add_check(result, bool(path) and not path.startswith(f"{PLAYBOOK_LOG_BASE_DIR}/"),
                         f"{stage}: published copy", path or "no log_file_path"):
            continue
        emit(f"scanning {stage} logs of job {job['job_id']}")
        _scan_file(host, result, (f"{stage}: published", path, stage), secrets["values"])
        permissions = mode_and_label(host, path)
        add_check(result, permissions["ok"], f"{stage}: published mode/label",
                  permissions["state"])
        copies = run_cmd(host, "log_domain_copies", base=PLAYBOOK_LOG_BASE_DIR,
                         name=posixpath.basename(path)).stdout.split()
        if not copies:
            result["fields"].append((f"  {stage}: domain log", "not on disk (rotated or "
                                     "removed); only the published copy is scanned"))
        for copy in copies:
            _scan_file(host, result, (f"{stage}: domain", copy, stage), secrets["values"])
    return finish(result)
