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

"""Full cleanup: run every enabled domain cleanup, then verify each domain.

Exec (``run_full_cleanup``) cleans the enabled domains in CLEANUP_ORDER and,
right before each playbook, records which to-be-preserved paths exist so a
path that never existed is not reported as deleted. Verify
(``verify_domain_cleanup``) checks one domain's postconditions against the
flags its playbook received. The record of each domain is the exec -> verify
hand-off (see state_func).
"""

from typing import Any, Callable, Dict, List, Tuple

from . import (
    build_stream_cleanup_func,
    image_build_manager_cleanup_func,
    orchestrator_cleanup_func,
    repo_manager_cleanup_func,
)
from .command_func import cleanup_command, run_domain_cleanup
from .config_func import cleanup_fail_fast, cleanup_plan
from .probe_func import capture_baseline
from ..messages.system_test_msgs import TEST_LOG_MSGS as LOG
from ..vars.common_vars import (
    CLEANUP_STATUS_DISABLED,
    CLEANUP_STATUS_FAILED,
    CLEANUP_STATUS_NOT_RUN,
    CLEANUP_STATUS_RAN,
)

Emit = Callable[[str], None]

# Cleanup block -> (pre_cleanup, verify). Both receive the block's effective
# flags so verification always matches what the playbook was asked to do.
CLEANUP_VERIFIERS = {
    "cleanup_build_stream": (
        build_stream_cleanup_func.pre_cleanup,
        build_stream_cleanup_func.verify_build_stream_cleanup,
    ),
    "cleanup_orchestrator": (
        orchestrator_cleanup_func.pre_cleanup,
        orchestrator_cleanup_func.verify_orchestrator_cleanup,
    ),
    "cleanup_image_build_manager": (
        image_build_manager_cleanup_func.pre_cleanup,
        image_build_manager_cleanup_func.verify_image_build_manager_cleanup,
    ),
    "cleanup_repo_manager": (
        repo_manager_cleanup_func.pre_cleanup,
        repo_manager_cleanup_func.verify_repo_manager_cleanup,
    ),
}


def _clean_domain(host: Any, entry: Dict[str, Any],
                  emit: Emit) -> Tuple[Dict[str, Any], List[Tuple[str, Any]]]:
    """Record the preserve baseline, run one domain cleanup; return (record, fields)."""
    name = entry["name"]
    command = cleanup_command(entry)
    emit(LOG["cleanup_start"].format(name=name, command=command))
    pre = CLEANUP_VERIFIERS[name][0](host, entry["effective_vars"])
    baseline = capture_baseline(host, pre["preserve"])
    result = run_domain_cleanup(entry)
    record = {
        "status": CLEANUP_STATUS_RAN if result["success"] else CLEANUP_STATUS_FAILED,
        "command": command, "rc": result["rc"], "duration": result["duration"],
        "effective_vars": entry["effective_vars"], "baseline": baseline,
        "facts": pre["facts"],
    }
    fields: List[Tuple[str, Any]] = [
        (f"{name} command", command),
        (f"{name} return code", result["rc"]),
        (f"{name} duration seconds", f"{result['duration']:.1f}"),
    ]
    if result["success"]:
        emit(LOG["cleanup_playbook_ok"].format(name=name, duration=result["duration"]))
    else:
        emit(LOG["cleanup_playbook_failed"].format(name=name, rc=result["rc"]))
        fields.append((f"{name} error", result.get("error") or "See playbook output"))
    return record, fields


def run_full_cleanup(host: Any, config: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Run every enabled domain cleanup in CLEANUP_ORDER (the cleanup entry point).

    ``cleanup.fail_fast`` stops at the first failed playbook; the remaining
    domains are recorded as not run.

    Returns:
        Dict with keys: success, fields, failures (failed domain names) and
        state ({"domains": {block_name: record}}) for the verify tests.
    """
    fail_fast = cleanup_fail_fast(config)
    plan = cleanup_plan(config)
    fields: List[Tuple[str, Any]] = [
        ("fail_fast", str(fail_fast).lower()),
        ("order", " -> ".join(entry["name"] for entry in plan)),
    ]
    failures: List[str] = []
    domains: Dict[str, Dict[str, Any]] = {}
    for entry in plan:
        name = entry["name"]
        if not entry["enabled"]:
            domains[name] = {"status": CLEANUP_STATUS_DISABLED}
            fields.append((name, LOG["cleanup_skipped"].format(name=name)))
        elif failures and fail_fast:
            domains[name] = {"status": CLEANUP_STATUS_NOT_RUN}
            fields.append((name, LOG["cleanup_not_run"].format(name=name)))
        else:
            domains[name], domain_fields = _clean_domain(host, entry, emit)
            fields.extend(domain_fields)
            if domains[name]["status"] == CLEANUP_STATUS_FAILED:
                failures.append(name)
    return {"success": not failures, "fields": fields, "failures": failures,
            "state": {"domains": domains}}


def verify_domain_cleanup(host: Any, name: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Verify one domain's cleanup postconditions from its exec record.

    Returns:
        Dict with keys: name, success, fields, failures, skipped (true when
        the domain was disabled or its cleanup did not run).
    """
    status = record.get("status", CLEANUP_STATUS_NOT_RUN)
    if status not in (CLEANUP_STATUS_RAN, CLEANUP_STATUS_FAILED):
        return {"name": name, "success": True, "skipped": True, "fields": [],
                "failures": [], "status": status}
    verify = CLEANUP_VERIFIERS[name][1]
    result = verify(host, record["effective_vars"], record["baseline"], record["facts"])
    result["fields"] = [("command", record["command"]), ("return code", record["rc"]),
                        *result["fields"]]
    result.update(skipped=False, status=status)
    return result
