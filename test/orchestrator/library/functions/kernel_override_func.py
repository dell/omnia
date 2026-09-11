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

"""Kernel-version override verification helpers for orchestrator FVT."""

import csv
import io
import os
import re
import shlex
from typing import Any, Dict, List

import yaml

from omnia_auto import run_on_host

ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"

KERNEL_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-.+$")
_ARCH_SUFFIXES = (".x86_64", ".aarch64", ".ppc64le", ".s390x")


def _project_path() -> str:
    project = os.environ.get(ENV_OMNIA_PROJECT_NAME, "project_default")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", project):
        raise ValueError(f"Invalid project name: {project!r}")
    data_path = os.environ.get(ENV_OMNIA_DATA_PATH, "/opt/omnia")
    return f"{data_path}/orchestrator/input/{project}"


def _strip_arch(version: str) -> str:
    return next((version[:-len(s)] for s in _ARCH_SUFFIXES if version.endswith(s)), version)


def get_kernel_version_override(host) -> Dict[str, Any]:
    path = f"{_project_path()}/orchestrator_config.yml"
    result = run_on_host(host, f"cat {shlex.quote(path)} 2>/dev/null")
    if result.rc != 0:
        return {"success": False, "kernel_version_override": "", "is_configured": False,
                "error": result.stderr or result.stdout}
    try:
        config = yaml.safe_load(result.stdout) or {}
        value = str(config.get("kernel_version_override", "") or "").strip()
    except (TypeError, yaml.YAMLError) as exc:
        return {"success": False, "kernel_version_override": "", "is_configured": False,
                "error": str(exc)}
    return {"success": True, "kernel_version_override": value,
            "is_configured": bool(value), "error": ""}


def validate_kernel_version_override_format(host) -> Dict[str, Any]:
    result = get_kernel_version_override(host)
    value = result["kernel_version_override"]
    return {**result, "is_empty": not value,
            "is_valid_format": bool(KERNEL_VERSION_PATTERN.fullmatch(value)) if value else True}


def _nodes(host) -> List[Dict[str, str]]:
    result = run_on_host(host, f"cat {shlex.quote(_project_path() + '/pxe_mapping_file.csv')} 2>/dev/null")
    if result.rc != 0:
        return []
    return [{str(k).lower(): str(v or "").strip() for k, v in row.items()}
            for row in csv.DictReader(io.StringIO(result.stdout))]




def _node_kernels(host) -> List[Dict[str, str]]:
    results = []
    for node in _nodes(host):
        ip = node.get("admin_ip", "")
        if not ip:
            continue
        command = f"ssh -o BatchMode=yes -o ConnectTimeout=10 root@{shlex.quote(ip)} uname -r 2>/dev/null"
        response = run_on_host(host, command)
        results.append({"hostname": node.get("hostname", ip), "admin_ip": ip,
                        "running_kernel": response.stdout.strip() if response.rc == 0 else ""})
    return results


def verify_all_nodes_kernel_version(host) -> Dict[str, Any]:
    config = get_kernel_version_override(host)
    value = config["kernel_version_override"]
    if not config["success"] or not value:
        return {**config, "not_configured": not value, "nodes_checked": 0,
                "nodes_matched": [], "nodes_mismatched": []}
    nodes = _node_kernels(host)
    matched = [n for n in nodes if _strip_arch(n["running_kernel"]) == _strip_arch(value)]
    mismatched = [n for n in nodes if n not in matched]
    return {"success": bool(nodes) and not mismatched, "kernel_version_override": value,
            "not_configured": False, "nodes_checked": len(nodes),
            "nodes_matched": matched, "nodes_mismatched": mismatched,
            "details": "\n".join(f"{n['hostname']} : {n['running_kernel'] or 'UNREACHABLE'}" for n in nodes)}


def verify_kernel_consistency(host) -> Dict[str, Any]:
    config = get_kernel_version_override(host)
    nodes = _node_kernels(host)
    versions = sorted({n["running_kernel"] for n in nodes if n["running_kernel"]})
    value = config["kernel_version_override"]
    if value:
        mismatched = [n for n in nodes if _strip_arch(n["running_kernel"]) != _strip_arch(value)]
        success = bool(nodes) and not mismatched
    else:
        mismatched = []
        success = bool(nodes) and len(versions) == 1
    return {"success": success, "nodes": nodes, "unique_versions": versions,
            "kernel_version_override": value, "is_configured": bool(value),
            "mismatched": mismatched, "details": "\n".join(
                f"{n['hostname']} : {n['running_kernel'] or 'UNREACHABLE'}" for n in nodes)}

