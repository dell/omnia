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

"""
Utils Domain — Slurm Config Util Verification Functions.

Functions specific to the slurm_config_util backup/cleanup/rollback metadata
schema and directory layout. Generic helpers (check_dir_exists,
validate_yaml_file, read_remote_file) are reused as-is from utils_func.py.
"""

import json
from typing import Any, Dict, List

from .utils_func import read_remote_file, check_dir_exists
from ..vars.common_vars import SLURM_CONFIG_BACKUP_DIRECTORIES


def find_latest_backup_run_dir(host, output_dir: str) -> Dict[str, Any]:
    """Find the most recently modified backup run directory.

    Args:
        host: Testinfra host object.
        output_dir: Path to the slurm_config_util backup workspace.

    Returns:
        dict: {"success": bool, "run_dir": str, "error": str}
    """
    check_result = check_dir_exists(host, output_dir)
    if not check_result["success"]:
        return {
            "success": False,
            "run_dir": "",
            "error": f"Backup workspace not found: {output_dir}",
        }

    cmd = f"find {output_dir} -mindepth 1 -maxdepth 1 -type d 2>/dev/null | xargs -r ls -dt 2>/dev/null | head -1"
    result = host.run(cmd)

    if result.rc == 0 and result.stdout.strip():
        return {"success": True, "run_dir": result.stdout.strip(), "error": ""}

    return {
        "success": False,
        "run_dir": "",
        "error": f"No backup run directory found under {output_dir}",
    }


def validate_slurm_backup_metadata_file(host, path: str) -> Dict[str, Any]:
    """Validate a slurm_config_backup metadata.json file structure.

    Args:
        host: Testinfra host object.
        path: Absolute path to metadata.json.

    Returns:
        dict: {"success": bool, "data": dict, "has_checksums": bool, "error": str}
    """
    file_result = read_remote_file(host, path)
    if not file_result["success"]:
        return {
            "success": False,
            "data": {},
            "has_checksums": False,
            "error": file_result["error"],
        }

    try:
        data = json.loads(file_result["content"])
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "data": {},
            "has_checksums": False,
            "error": f"Invalid JSON: {exc}",
        }

    required_fields = ["backup_id", "controller_hostname", "directories_included"]
    missing = [f for f in required_fields if f not in data]

    return {
        "success": len(missing) == 0,
        "data": data,
        "has_checksums": bool(data.get("file_checksums_sha256")),
        "error": f"Missing required fields: {missing}" if missing else "",
    }


def check_backup_directories_present(host, backup_run_dir: str, controller_hostname: str) -> Dict[str, Any]:
    """Verify a backup run directory contains the expected config subdirectories.

    Args:
        host: Testinfra host object.
        backup_run_dir: Path to a single timestamped backup run directory.
        controller_hostname: Controller hostname subdirectory to check under.

    Returns:
        dict: {"success": bool, "found": list, "missing": list, "error": str}
    """
    found: List[str] = []
    missing: List[str] = []

    for directory in SLURM_CONFIG_BACKUP_DIRECTORIES:
        result = check_dir_exists(host, f"{backup_run_dir}/{controller_hostname}/{directory}")
        (found if result["success"] else missing).append(directory)

    return {
        "success": len(missing) == 0,
        "found": found,
        "missing": missing,
        "error": f"Missing directories: {missing}" if missing else "",
    }


def check_slurm_config_dir_removed(host, slurm_config_path: str) -> Dict[str, Any]:
    """Check that the active Slurm config directory no longer exists.

    Args:
        host: Testinfra host object.
        slurm_config_path: Resolved active Slurm config path.

    Returns:
        dict: {"success": bool, "error": str}
    """
    result = check_dir_exists(host, slurm_config_path)
    if result["success"]:
        return {
            "success": False,
            "error": f"Slurm config directory still present: {slurm_config_path}",
        }
    return {"success": True, "error": ""}


def check_backup_workspace_run_dirs_removed(host, backup_path: str) -> Dict[str, Any]:
    """Check that no backup run directories remain under the workspace.

    Args:
        host: Testinfra host object.
        backup_path: Path to the slurm_config_util backup workspace.

    Returns:
        dict: {"success": bool, "remaining": list, "error": str}
    """
    cmd = f"find {backup_path} -mindepth 1 -maxdepth 1 -type d 2>/dev/null"
    result = host.run(cmd)

    if result.rc != 0:
        # Missing workspace directory counts as "cleaned".
        return {"success": True, "remaining": [], "error": ""}

    remaining = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    return {
        "success": len(remaining) == 0,
        "remaining": remaining,
        "error": f"Backup run directories still present: {remaining}" if remaining else "",
    }
