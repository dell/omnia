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
Utils Domain — OIM Log Backup Verification Functions.

Functions specific to the backup_oim_logs metadata schema and config file.
Generic helpers (find_log_bundle, validate_tar_contents, validate_yaml_file,
check_dir_exists) already cover archive discovery and content checks and are
reused as-is from utils_func.py.
"""

import json
from typing import Any, Dict, List

from ..vars.common_vars import BACKUP_ALL_DOMAINS
from .utils_func import read_remote_file, validate_yaml_file


def validate_backup_config(host, path: str) -> Dict[str, Any]:
    """Validate backup_oim_logs_config.yml structure and domain names.

    Args:
        host: Testinfra host object.
        path: Absolute path to backup_oim_logs_config.yml.

    Returns:
        dict: {"success": bool, "domains": list, "invalid_domains": list, "error": str}
    """
    yaml_result = validate_yaml_file(host, path)
    if not yaml_result["success"]:
        return {
            "success": False,
            "domains": [],
            "invalid_domains": [],
            "error": yaml_result["error"],
        }

    domains = yaml_result["data"].get("domains") or []
    invalid_domains = [d for d in domains if d not in BACKUP_ALL_DOMAINS]

    return {
        "success": len(invalid_domains) == 0,
        "domains": domains,
        "invalid_domains": invalid_domains,
        "error": f"Invalid domains: {invalid_domains}" if invalid_domains else "",
    }


def validate_backup_metadata_file(host, path: str) -> Dict[str, Any]:
    """Validate a backup_oim_logs metadata.json file structure.

    Args:
        host: Testinfra host object.
        path: Absolute path to metadata.json.

    Returns:
        dict: {"success": bool, "data": dict, "has_sha256": bool, "error": str}
    """
    file_result = read_remote_file(host, path)
    if not file_result["success"]:
        return {
            "success": False,
            "data": {},
            "has_sha256": False,
            "error": file_result["error"],
        }

    try:
        data = json.loads(file_result["content"])
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "data": {},
            "has_sha256": False,
            "error": f"Invalid JSON: {exc}",
        }

    required_fields = ["backup_name", "domains_included"]
    missing = [f for f in required_fields if f not in data]

    return {
        "success": len(missing) == 0,
        "data": data,
        "has_sha256": bool(data.get("archive_sha256")),
        "error": f"Missing required fields: {missing}" if missing else "",
    }


def check_backup_workspace_removed(host, backup_path: str) -> Dict[str, Any]:
    """Check that no omnia_oim_logs_* run directories remain.

    Args:
        host: Testinfra host object.
        backup_path: Path to the backup workspace (resolved backup_path).

    Returns:
        dict: {"success": bool, "remaining": list, "error": str}
    """
    cmd = f"find {backup_path} -maxdepth 1 -type d -name 'omnia_oim_logs_*' 2>/dev/null"
    result = host.run(cmd)

    if result.rc != 0:
        # Missing workspace directory counts as "cleaned".
        return {"success": True, "remaining": [], "error": ""}

    lines = result.stdout.strip().split("\n")
    remaining: List[str] = [line.strip() for line in lines if line.strip()]
    return {
        "success": len(remaining) == 0,
        "remaining": remaining,
        "error": f"Backup run directories still present: {remaining}" if remaining else "",
    }
