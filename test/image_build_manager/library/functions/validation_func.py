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
Config validation for image_build_manager test framework.

Validates test_config.yml fields: IP format, paths, dataset existence.
"""

import os
import re
from typing import Dict, Any, List

import yaml

IPV4_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
    r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
)

# Module root: functions/ -> library/ -> test/
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MODULE_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))


class ConfigValidationError(Exception):
    """Raised when config validation fails."""


def _validate_ip(value: str, field: str) -> List[str]:
    """Validate IPv4 address format."""
    errors = []
    if value and not IPV4_PATTERN.match(value):
        errors.append(f"{field}: invalid IPv4 format '{value}'")
    return errors


REQUIRED_FIELDS = [
    "dataset",
    "project_name",
    "clone_path",
    "shared_path",
    "report_path",
    "report_name",
]

REQUIRED_DATASET_FILES = [
    "input/config.yml",
    "input/image_build_config.yml",
    "input/image_build_credentials.yml",
]


def validate_test_config() -> Dict[str, Any]:
    """Validate test_config.yml.

    Checks:
    - File exists and is valid YAML
    - All required fields are present (no fallback defaults)
    - OIM IP format (if set)
    - Dataset directory and required files exist
    - Paths are absolute where required
    - report_path/report_name format

    Returns:
        Dict with 'valid', 'errors', 'warnings'.
    """
    config_path = os.path.join(_MODULE_ROOT, "test_config.yml")
    errors: List[str] = []
    warnings: List[str] = []

    if not os.path.exists(config_path):
        return {
            "valid": False,
            "errors": ["test_config.yml not found"],
            "warnings": [],
        }

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # --- Required fields ---
    for field in REQUIRED_FIELDS:
        if field not in config or config[field] is None:
            errors.append(
                f"Required field missing in test_config.yml: {field}"
            )

    # oim_server_ip must be present (empty string is valid = local)
    if "oim_server_ip" not in config:
        errors.append(
            "Required field missing: oim_server_ip "
            "(set to \"\" for local mode)"
        )

    # Stop early if required fields are missing
    if errors:
        return {
            "valid": False, "errors": errors, "warnings": warnings,
        }

    # --- OIM IP format ---
    oim_ip = config["oim_server_ip"]
    if oim_ip:
        errors.extend(_validate_ip(str(oim_ip), "oim_server_ip"))

    # --- Dataset validation ---
    dataset = config["dataset"]
    dataset_path = os.path.join(_MODULE_ROOT, "datasets", dataset)
    if not os.path.isdir(dataset_path):
        errors.append(
            f"Dataset directory not found: datasets/{dataset}/"
        )
    else:
        for rel_file in REQUIRED_DATASET_FILES:
            full = os.path.join(dataset_path, rel_file)
            if not os.path.isfile(full):
                errors.append(
                    f"Required file missing: datasets/{dataset}/"
                    f"{rel_file}"
                )

    # --- Clone path ---
    clone_path = config["clone_path"]
    if not os.path.isabs(clone_path):
        errors.append(
            f"clone_path must be absolute: {clone_path}"
        )

    # --- Shared path ---
    shared_path = config["shared_path"]
    if not os.path.isabs(shared_path):
        errors.append(
            f"shared_path must be absolute: {shared_path}"
        )

    # --- Report path ---
    report_path = config["report_path"]
    if " " in str(report_path):
        errors.append("report_path must not contain spaces")

    # --- Report name ---
    report_name = config["report_name"]
    if not re.match(r'^[a-zA-Z0-9_-]+$', str(report_name)):
        errors.append(
            "report_name must contain only letters, numbers, "
            "underscores, hyphens"
        )

    # --- Remote mode checks ---
    if oim_ip:
        if "oim_ssh_user" not in config:
            errors.append(
                "oim_ssh_user required when oim_server_ip is set"
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def validate_all() -> Dict[str, Any]:
    """Run all validation checks.

    Returns:
        Dict with 'valid', 'errors', 'warnings'.

    Raises:
        ConfigValidationError if validation fails.
    """
    result = validate_test_config()

    if not result["valid"]:
        errors = "\n".join(f"  - {err}" for err in result["errors"])
        msg = f"Config validation failed:\n{errors}"
        raise ConfigValidationError(msg)

    return result
