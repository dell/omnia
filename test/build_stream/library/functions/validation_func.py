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
Build Stream — Config Validation Functions.

Validates test_config.yml and test_creds.yml before test execution.
"""

from typing import Any, Dict

from omnia_auto import load_test_config


class ConfigValidationError(Exception):
    """Raised when test configuration is invalid."""


def validate_test_config() -> Dict[str, Any]:
    """Validate test_config.yml has all required fields.

    Returns:
        Dict with keys: valid, warnings, errors.
    """
    config = load_test_config()

    result = {
        "valid": True,
        "warnings": [],
        "errors": [],
    }

    if not config.get("clone_path"):
        result["errors"].append("clone_path is required")
        result["valid"] = False

    if not config.get("project_name"):
        result["warnings"].append(
            "project_name not set, using default 'project_default'"
        )

    oim_ip = config.get("oim_server_ip", "")
    if not oim_ip:
        result["warnings"].append(
            "oim_server_ip is empty, will run in local mode"
        )

    return result


def validate_all() -> Dict[str, Any]:
    """Run all config validations.

    Returns:
        Dict with keys: warnings.

    Raises:
        ConfigValidationError: If critical validation fails.
    """
    config_result = validate_test_config()

    if not config_result["valid"]:
        raise ConfigValidationError(
            f"Config validation failed: {config_result['errors']}"
        )

    return {"warnings": config_result["warnings"]}
