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

"""Verification of Python and Ansible dependencies installed by omnia.sh."""

import json
from typing import Any, Dict, List, Tuple

from omnia_auto import run_on_host
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from ..vars.common_vars import CMDS, DOMAINS_WITH_INIT
from .omnia_main_func import _resolve_clone_path, resolve_runtime_paths

CORE_PACKAGES = ("pip", "setuptools", "wheel")


def _read_domain_requirements(host) -> Tuple[Dict[str, List[Requirement]], List[str], List[str]]:
    """Read and merge applicable requirements from every initialized domain."""
    requirement_map: Dict[str, List[Requirement]] = {}
    missing_files: List[str] = []
    invalid_requirements: List[str] = []
    clone_path = _resolve_clone_path()

    for domain in DOMAINS_WITH_INIT:
        path = f"{clone_path}/src/{domain}/requirements.txt"
        result = run_on_host(host, CMDS["cat_file"].format(path=path))
        if result.rc != 0:
            missing_files.append(path)
            continue
        for raw_line in result.stdout.splitlines():
            text = raw_line.split("#", 1)[0].strip()
            if not text:
                continue
            try:
                requirement = Requirement(text)
            except InvalidRequirement:
                invalid_requirements.append(f"{path}: {text}")
                continue
            if requirement.marker and not requirement.marker.evaluate():
                continue
            name = canonicalize_name(requirement.name)
            requirement_map.setdefault(name, []).append(requirement)

    return requirement_map, missing_files, invalid_requirements


def _read_installed_packages(host, venv_path: str) -> Tuple[Dict[str, str], str]:
    """Return normalized package/version pairs from the target venv."""
    command = CMDS["venv_pip_list"].format(venv_path=venv_path)
    result = run_on_host(host, command)
    if result.rc != 0:
        return {}, result.stderr.strip() or "pip list failed"
    try:
        rows = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        return {}, f"pip list returned invalid JSON: {exc}"
    installed = {
        canonicalize_name(row["name"]): str(row["version"])
        for row in rows
        if row.get("name") and row.get("version")
    }
    return installed, ""


def _find_version_mismatches(
    requirements: Dict[str, List[Requirement]], installed: Dict[str, str]
) -> List[str]:
    """Return installed versions that violate any declared constraint."""
    mismatches = []
    for name, declarations in requirements.items():
        installed_version = installed.get(name)
        if not installed_version:
            continue
        try:
            version = Version(installed_version)
        except InvalidVersion:
            mismatches.append(f"{name} {installed_version} has an invalid version")
            continue
        failed = sorted({
            str(declaration.specifier)
            for declaration in declarations
            if declaration.specifier and version not in declaration.specifier
        })
        if failed:
            mismatches.append(
                f"{name} {installed_version} requires {', '.join(failed)}"
            )
    return mismatches


def _domain_inventory(
    requirements: Dict[str, List[Requirement]], installed: Dict[str, str]
) -> List[str]:
    """Format installed domain packages with their merged constraints."""
    inventory = []
    for name in sorted(requirements):
        if name not in installed:
            continue
        constraints = sorted({
            str(declaration.specifier)
            for declaration in requirements[name]
            if declaration.specifier
        })
        required = ", ".join(constraints) or "any version"
        inventory.append(f"{name} {installed[name]} (required: {required})")
    return inventory


def check_pip_packages(host) -> Dict[str, Any]:
    """Verify core tooling and all declared domain requirements in the venv."""
    venv_path = resolve_runtime_paths(host)["venv_path"]
    requirements, missing_files, invalid = _read_domain_requirements(host)
    installed, query_error = _read_installed_packages(host, venv_path)
    missing = [name for name in CORE_PACKAGES if name not in installed]
    missing.extend(name for name in requirements if name not in installed)
    mismatches = _find_version_mismatches(requirements, installed)
    failures = missing_files + invalid + missing + mismatches
    if query_error:
        failures.append(query_error)

    required_count = len(CORE_PACKAGES) + len(requirements)
    installed_count = required_count - len(missing)
    return {
        "success": not failures,
        "details": f"{installed_count}/{required_count} required packages installed",
        "error": "; ".join(failures),
        "missing": missing,
        "missing_files": missing_files,
        "invalid_requirements": invalid,
        "version_mismatches": mismatches,
        "requirement_file_count": len(DOMAINS_WITH_INIT) - len(missing_files),
        "required_file_count": len(DOMAINS_WITH_INIT),
        "required_count": required_count,
        "installed_count": installed_count,
        "core_packages": [
            f"{name} {installed[name]}" for name in CORE_PACKAGES if name in installed
        ],
        "domain_packages": _domain_inventory(requirements, installed),
    }


def check_galaxy_collections(host) -> Dict[str, Any]:
    """List installed Ansible Galaxy collections and their versions."""
    venv_path = resolve_runtime_paths(host)["venv_path"]
    command = CMDS["venv_galaxy_list"].format(venv_path=venv_path)
    result = run_on_host(host, command)
    collections = []
    for line in result.stdout.splitlines():
        columns = line.split()
        if len(columns) >= 2 and "." in columns[0] and not line.startswith("#"):
            collections.append(f"{columns[0]} {columns[1]}")
    return {
        "success": bool(collections),
        "details": f"{len(collections)} collection(s)" if collections else "",
        "error": "" if collections else "No Galaxy collections found",
        "collections": collections,
    }
