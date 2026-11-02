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

"""Domain cleanup: orchestrator, image_build_manager, repo_manager (and main).

Exec (``run_domain_cleanups``) cleans the enabled domains in DOMAIN_CLEANUP_ORDER
(the reverse of --prepare-base) and, right before each one, records which
to-be-preserved paths exist so a path that never existed is not reported as
deleted. Verify (``verify_domain_cleanup``) checks one domain's postconditions
against the flags its command received; the record of each domain is the
exec -> verify hand-off (see state_func). The ``main`` block runs
``./omnia.sh --cleanup``, removes the setup and is disabled by default.
"""

import posixpath
from typing import Any, Callable, Dict, List, Tuple

from omnia_auto import read_remote_env

from .cleanup_func import container_probes, unit_stopped
from .command_func import repository_path, run_ansible_playbook, run_omnia_sh
from .config_func import domain_cleanup_fail_fast, domain_cleanup_plan
from .execute_probe_func import data_path, path_exists, summarize
from .probe_func import (
    Probe,
    domain_data_path,
    domain_input_path,
    env_var_set,
    file_present,
    port_closed,
)
from ..vars.common_vars import (
    CLEANUP_STATUS_DISABLED,
    CLEANUP_STATUS_FAILED,
    CLEANUP_STATUS_NOT_RUN,
    CLEANUP_STATUS_RAN,
    ENV_OMNIA_PROJECT_NAME,
    ENV_OMNIA_VENV_PATH,
    IBM_BUILD_STATUS,
    IBM_CONTAINERS,
    IBM_CREDENTIAL_FILES,
    IBM_DATA_DIRS,
    IBM_PORTS,
    IBM_SERVICES,
    OMNIA_SH_CLEANUP_ALL_ARG,
    OMNIA_SH_CLEANUP_ARGS,
    OMNIA_SYSTEM_ENV_FILES,
    ORCH_CREDENTIAL_FILES,
    ORCH_OPENCHAMI_CONTAINERS,
    ORCH_OPENCHAMI_INIT_CONTAINER,
    ORCH_OPENCHAMI_TIMER,
    ORCH_OPENCHAMI_UNITS,
    ORCH_OPENLDAP_CONTAINER,
    ORCH_OPENLDAP_SERVICE,
    RM_CREDENTIAL_FILES,
    RM_LOG_DIRS,
    RM_PULP_CONTAINER,
    RM_PULP_DIRS,
    RM_PULP_QUADLET,
)

Emit = Callable[[str], None]


# =============================================================================
# PROBES
# =============================================================================

def _removed(host: Any, path: str) -> Probe:
    """Probe that a file or directory no longer exists."""
    gone = not path_exists(host, path)
    return f"Path {path}", "removed" if gone else "STILL EXISTS", gone


def _kept_or_removed(host: Any, paths: List[str], remove: bool,
                     baseline: Dict[str, bool]) -> List[Probe]:
    """Probe each path: removed when ``remove``, else kept when it existed before."""
    probes: List[Probe] = []
    for path in paths:
        if remove:
            probes.append(_removed(host, path))
        elif not baseline.get(path, False):
            probes.append((f"Preserved {path}", "did not exist before cleanup", True))
        else:
            kept = path_exists(host, path)
            probes.append((f"Preserved {path}", "kept" if kept else "DELETED", kept))
    return probes


def _credentials(host: Any, domain: str, files: List[str]) -> List[str]:
    """Return the credential file paths of a domain."""
    return [posixpath.join(domain_input_path(host, domain), name) for name in files]


# =============================================================================
# PER-DOMAIN PRE-CLEANUP AND VERIFICATION
# =============================================================================

def _pre_orchestrator(host: Any, flags: Dict[str, Any]) -> Dict[str, Any]:
    keep = [] if flags["cleanup_credentials"] else \
        _credentials(host, "orchestrator", ORCH_CREDENTIAL_FILES)
    return {"preserve": keep, "facts": {}}


def _verify_orchestrator(host: Any, flags: Dict[str, Any], baseline: Dict[str, bool],
                         facts: Dict[str, Any]) -> Dict[str, Any]:
    del facts
    containers = [*ORCH_OPENCHAMI_CONTAINERS, ORCH_OPENCHAMI_INIT_CONTAINER,
                  ORCH_OPENLDAP_CONTAINER]
    units = [*ORCH_OPENCHAMI_UNITS, ORCH_OPENCHAMI_TIMER, ORCH_OPENLDAP_SERVICE]
    probes: List[Probe] = []
    for name in containers:
        probes.extend(container_probes(host, name, True))
    probes.extend(unit_stopped(host, unit) for unit in units)
    probes.extend(_kept_or_removed(
        host, _credentials(host, "orchestrator", ORCH_CREDENTIAL_FILES),
        flags["cleanup_credentials"], baseline))
    return summarize("orchestrator", probes, [
        ("cleanup_credentials", str(flags["cleanup_credentials"]).lower()),
        ("cleanup_slurm / cleanup_k8s",
         f"{str(flags['cleanup_slurm']).lower()} / {str(flags['cleanup_k8s']).lower()}"),
    ])


def _pre_image_build_manager(host: Any, flags: Dict[str, Any]) -> Dict[str, Any]:
    keep = [] if flags["cleanup_credentials"] else \
        _credentials(host, "image_build_manager", IBM_CREDENTIAL_FILES)
    return {"preserve": keep, "facts": {}}


def _verify_image_build_manager(host: Any, flags: Dict[str, Any], baseline: Dict[str, bool],
                                facts: Dict[str, Any]) -> Dict[str, Any]:
    del facts
    root = domain_data_path(host, "image_build_manager")
    status = IBM_BUILD_STATUS.format(project=read_remote_env(host, ENV_OMNIA_PROJECT_NAME))
    probes: List[Probe] = []
    for name in IBM_CONTAINERS:
        probes.extend(container_probes(host, name, True))
    probes.extend(unit_stopped(host, unit) for unit in IBM_SERVICES)
    probes.extend(port_closed(host, port) for port in IBM_PORTS)
    probes.append(_removed(host, f"{root}/{status}"))
    probes.extend(_removed(host, f"{root}/{rel}") for rel in IBM_DATA_DIRS)
    probes.extend(_kept_or_removed(
        host, _credentials(host, "image_build_manager", IBM_CREDENTIAL_FILES),
        flags["cleanup_credentials"], baseline))
    return summarize("image_build_manager", probes,
                     [("cleanup_credentials", str(flags["cleanup_credentials"]).lower())])


def _repo_logs(host: Any) -> List[str]:
    root = domain_data_path(host, "repo_manager")
    return [f"{root}/{rel}" for rel in RM_LOG_DIRS]


def _pre_repo_manager(host: Any, flags: Dict[str, Any]) -> Dict[str, Any]:
    keep = [*([] if flags["cleanup_logs"] else _repo_logs(host)),
            *([] if flags["cleanup_credentials"] else
              _credentials(host, "repo_manager", RM_CREDENTIAL_FILES))]
    return {"preserve": keep, "facts": {}}


def _verify_repo_manager(host: Any, flags: Dict[str, Any], baseline: Dict[str, bool],
                         facts: Dict[str, Any]) -> Dict[str, Any]:
    del facts
    root = domain_data_path(host, "repo_manager")
    probes: List[Probe] = [*container_probes(host, RM_PULP_CONTAINER, True),
                           _removed(host, RM_PULP_QUADLET)]
    probes.extend(_removed(host, f"{root}/{rel}") for rel in RM_PULP_DIRS)
    probes.extend(_kept_or_removed(host, _repo_logs(host), flags["cleanup_logs"], baseline))
    probes.extend(_kept_or_removed(
        host, _credentials(host, "repo_manager", RM_CREDENTIAL_FILES),
        flags["cleanup_credentials"], baseline))
    return summarize("repo_manager", probes, [
        ("cleanup_logs", str(flags["cleanup_logs"]).lower()),
        ("cleanup_credentials", str(flags["cleanup_credentials"]).lower()),
    ])


def _pre_main(host: Any, flags: Dict[str, Any]) -> Dict[str, Any]:
    """Record the venv and data paths (omnia.env is removed by the cleanup itself)."""
    try:
        venv = read_remote_env(host, ENV_OMNIA_VENV_PATH).rstrip("/")
    except ValueError:
        venv = ""
    data = data_path(host)
    return {"preserve": [] if flags["full_reset"] else [data],
            "facts": {"venv": venv, "data": data}}


def _verify_main(host: Any, flags: Dict[str, Any], baseline: Dict[str, bool],
                 facts: Dict[str, Any]) -> Dict[str, Any]:
    probes = [_removed(host, facts["venv"])] if facts.get("venv") else []
    probes.extend(_removed(host, path) for path in OMNIA_SYSTEM_ENV_FILES)
    probes.extend(_kept_or_removed(host, [facts["data"]], flags["full_reset"], baseline))
    return summarize("main", probes, [("full_reset", str(flags["full_reset"]).lower())])


# Cleanup block -> (pre_cleanup, verify); both receive the block's effective flags.
VERIFIERS = {
    "cleanup_orchestrator": (_pre_orchestrator, _verify_orchestrator),
    "cleanup_image_build_manager": (_pre_image_build_manager, _verify_image_build_manager),
    "cleanup_repo_manager": (_pre_repo_manager, _verify_repo_manager),
    "cleanup_main": (_pre_main, _verify_main),
}


# =============================================================================
# EXEC
# =============================================================================

def cleanup_command(entry: Dict[str, Any]) -> str:
    """Return a readable command for a plan entry."""
    spec = entry["spec"]
    if spec["kind"] == "omnia_sh":
        extra = f" {OMNIA_SH_CLEANUP_ALL_ARG}" if entry["effective_vars"]["full_reset"] else ""
        return f"./omnia.sh {OMNIA_SH_CLEANUP_ARGS}{extra}"
    parts = [f"--tags={spec['tag']}"]
    if entry["skip_tags"]:
        parts.append(f"--skip-tags={','.join(entry['skip_tags'])}")
    parts.extend(f"-e {key}={str(value).lower() if isinstance(value, bool) else value}"
                 for key, value in entry["extra_vars"].items())
    return " ".join(["ansible-playbook", spec["playbook"], *parts])


def _run_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Run one plan entry (omnia.sh for main, else its playbook)."""
    spec = entry["spec"]
    if spec["kind"] == "omnia_sh":
        extra = f" {OMNIA_SH_CLEANUP_ALL_ARG}" if entry["effective_vars"]["full_reset"] else ""
        return run_omnia_sh(f"{OMNIA_SH_CLEANUP_ARGS}{extra}")
    return run_ansible_playbook(spec["playbook"], spec["workdir"], tag=spec["tag"],
                                extra_vars=entry["extra_vars"], skip_tags=entry["skip_tags"])


def _clean_domain(host: Any, entry: Dict[str, Any],
                  emit: Emit) -> Tuple[Dict[str, Any], List[Tuple[str, Any]]]:
    """Record the preserve baseline, run one cleanup; return (record, report fields)."""
    name, command = entry["name"], cleanup_command(entry)
    emit(f"cleaning {name}: {command}")
    pre = VERIFIERS[name][0](host, entry["effective_vars"])
    baseline = {path: path_exists(host, path) for path in pre["preserve"]}
    result = _run_entry(entry)
    record = {"status": CLEANUP_STATUS_RAN if result["success"] else CLEANUP_STATUS_FAILED,
              "command": command, "rc": result["rc"], "duration": result["duration"],
              "effective_vars": entry["effective_vars"], "baseline": baseline,
              "facts": pre["facts"]}
    fields: List[Tuple[str, Any]] = [(f"{name} command", command),
                                     (f"{name} return code", result["rc"]),
                                     (f"{name} duration seconds", f"{result['duration']:.1f}")]
    if not result["success"]:
        fields.append((f"{name} error", result.get("error") or "See playbook output"))
    return record, fields


def run_domain_cleanups(host: Any, config: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Run every enabled domain cleanup in DOMAIN_CLEANUP_ORDER (the exec entry point).

    ``domain_cleanup.fail_fast`` stops at the first failed domain; the rest are
    recorded as not run.

    Returns:
        Dict with keys: success, fields, failures (failed block names) and
        state ({"domains": {block: record}}) for the verify tests.
    """
    fail_fast = domain_cleanup_fail_fast(config)
    plan = domain_cleanup_plan(config)
    fields: List[Tuple[str, Any]] = [
        ("fail_fast", str(fail_fast).lower()),
        ("order", " -> ".join(entry["name"] for entry in plan if entry["enabled"]) or "none"),
    ]
    failures: List[str] = []
    domains: Dict[str, Dict[str, Any]] = {}
    for entry in plan:
        name = entry["name"]
        if not entry["enabled"]:
            domains[name] = {"status": CLEANUP_STATUS_DISABLED}
            fields.append((name, "disabled in test_config.yml"))
        elif failures and fail_fast:
            domains[name] = {"status": CLEANUP_STATUS_NOT_RUN}
            fields.append((name, "not run: an earlier cleanup failed (fail_fast)"))
        else:
            domains[name], domain_fields = _clean_domain(host, entry, emit)
            fields.extend(domain_fields)
            if domains[name]["status"] == CLEANUP_STATUS_FAILED:
                failures.append(name)
    return {"success": not failures, "fields": fields, "failures": failures,
            "state": {"domains": domains}}


def precheck_domain_cleanup(host: Any, config: Dict[str, Any]) -> Dict[str, Any]:
    """Check that the enabled cleanups can run (changes nothing).

    At least one block is enabled, the omnia.env variables verification resolves
    paths from are set, and each enabled playbook (or omnia.sh) exists in the checkout.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    plan = domain_cleanup_plan(config)
    enabled = [entry for entry in plan if entry["enabled"]]
    probes: List[Probe] = [("Enabled blocks",
                            ", ".join(entry["name"] for entry in enabled) or "NONE",
                            bool(enabled))]
    probes.extend(env_var_set(host, name) for name in (ENV_OMNIA_PROJECT_NAME,
                                                       ENV_OMNIA_VENV_PATH))
    for entry in enabled:
        spec = entry["spec"]
        probes.append(file_present(
            host, posixpath.join(repository_path(spec["workdir"]), spec["playbook"])))
    return summarize("precheck_domain_cleanup", probes)


# =============================================================================
# VERIFY
# =============================================================================

def verify_domain_cleanup(host: Any, name: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Verify one block's postconditions from its exec record.

    Returns:
        Dict with keys: name, success, fields, failures, skipped (true when the
        block was disabled or did not run), status.
    """
    status = record.get("status", CLEANUP_STATUS_NOT_RUN)
    if status not in (CLEANUP_STATUS_RAN, CLEANUP_STATUS_FAILED):
        return {"name": name, "success": True, "skipped": True, "fields": [],
                "failures": [], "status": status}
    result = VERIFIERS[name][1](host, record["effective_vars"], record["baseline"],
                                record["facts"])
    result["fields"] = [("command", record["command"]), ("return code", record["rc"]),
                        *result["fields"]]
    result.update(skipped=False, status=status)
    return result
