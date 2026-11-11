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

"""Restart node coverage: every PXE-mapped node has one restart result.

The expected nodes are the BMC_IP column of the GitLab PXE mapping (the
deploy trigger only reorders its rows). A restart retry, or a later deploy
of the same job, PXE-boots only the nodes not booted yet
(pxe_buildstream_manager generate_effective_csv.yml), so nodes that the
job's restart_state.json lists as booted count as covered.
"""

import csv
import io
import json
from typing import Any, Dict, List, Set

from . import gitlab_api_func
from .execute_probe_func import data_path, run_cmd
from .log_func import mark
from ..vars.execute_vars import (
    GITLAB_PXE_MAPPING_FILE,
    PXE_BMC_IP_COLUMN,
    RESTART_STATE_DIR,
    RESTART_STATE_FILE,
)


def check_node_coverage(host: Any, context: Dict[str, Any], job_id: str,
                        data: Dict[str, Any]) -> Dict[str, List[Any]]:
    """Compare the node_results.json content of a job with the PXE mapping.

    Returns:
        Dict with keys: fields (marked label/value pairs), failures.
    """
    nodes = [item for item in data.get("nodes", []) if isinstance(item, dict)]
    actual = [str(item.get("bmc_ip") or "").strip() for item in nodes]
    mapping = gitlab_api_func.get_file(context, GITLAB_PXE_MAPPING_FILE)
    if not mapping["success"]:
        return {"fields": [(mark(False, "PXE node coverage"), mapping["error"])],
                "failures": [f"cannot read {GITLAB_PXE_MAPPING_FILE}: {mapping['error']}"]}
    expected = [str(row.get(PXE_BMC_IP_COLUMN) or "").strip()
                for row in csv.DictReader(io.StringIO(mapping["content"]))]
    booted = booted_earlier(host, job_id)
    problems = []
    if not expected or not all(expected):
        problems.append(f"{GITLAB_PXE_MAPPING_FILE} has no nodes or an empty {PXE_BMC_IP_COLUMN}")
    duplicates = sorted({ip for ip in actual if actual.count(ip) > 1})
    if not all(actual) or duplicates:
        problems.append(f"node-results has empty or duplicate nodes: {duplicates}")
    missing = sorted(set(expected) - set(actual) - booted)
    unexpected = sorted(set(actual) - set(expected))
    if missing or unexpected:
        problems.append(f"node coverage mismatch: missing={missing}, unexpected={unexpected}")
    problems.extend(_count_problems(data, nodes))
    covered = len(set(expected) & (set(actual) | booted))
    text = f"{covered}/{len(expected)} mapped node(s)"
    if booted:
        text += f", {len(booted)} booted by earlier attempts"
    return {"fields": [(mark(not problems, "PXE node coverage"), text)], "failures": problems}


def _count_problems(data: Dict[str, Any], nodes: List[Dict[str, Any]]) -> List[str]:
    """Return a problem when the node_results summary counts differ from its node list."""
    counts = {"total_nodes": len(nodes),
              "success_count": sum(item.get("status") == "success" for item in nodes),
              "failure_count": sum(item.get("status") == "failed" for item in nodes)}
    wrong = {key: data.get(key) for key, value in counts.items()
             if str(data.get(key)) != str(value)}
    return [f"node-results counts {wrong} do not match its node list {counts}"] if wrong else []


def booted_earlier(host: Any, job_id: str) -> Set[str]:
    """Return the BMC IPs restart_state.json records as booted for the job (empty if none)."""
    path = f"{data_path(host)}/{RESTART_STATE_DIR}/{job_id}/{RESTART_STATE_FILE}"
    read = run_cmd(host, "cat_file", path=path)
    if read.rc != 0:
        return set()
    try:
        booted = json.loads(read.stdout).get("booted_nodes") or []
    except (json.JSONDecodeError, AttributeError):
        return set()
    return {str(item.get("bmc_ip")).strip() for item in booted
            if isinstance(item, dict) and item.get("bmc_ip")}
