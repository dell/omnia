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
Omnia Main — Configuration Validation

Validates test_config.yml fields before any tests run.
Raises ConfigValidationError on fatal misconfigurations.
"""

from typing import Any, Dict, List

from omnia_auto import load_test_config


class ConfigValidationError(Exception):
    """Raised when test configuration is invalid."""


def validate_test_config() -> Dict[str, Any]:
    """Validate test_config.yml for the main module.

    Returns:
        Dict with keys: valid (bool), errors (list), warnings (list).
    """
    config = load_test_config()
    errors: List[str] = []
    warnings: List[str] = []

    # clone_path: required for remote mode, ignored in local mode
    clone_path = config.get("clone_path", "")
    server_ip = config.get("oim_server_ip", "")
    if not clone_path:
        if server_ip:
            # Remote mode: clone_path is required
            errors.append(
                "clone_path is required for remote mode (path to omnia repo on target)"
            )
        # Local mode: clone_path is not needed (resolved from source tree)
    elif not clone_path.startswith("/"):
        errors.append(
            f"clone_path must be absolute: '{clone_path}'"
        )

    # oim_server_ip: warn if empty (local mode)
    if not server_ip:
        warnings.append(
            "oim_server_ip is empty — running in local mode"
        )

    # omnia_data_path must start with /
    data_path = config.get("omnia_data_path", "/opt/omnia")
    if not data_path.startswith("/"):
        errors.append(
            f"omnia_data_path must be absolute: '{data_path}'"
        )

    # venv_path must start with /
    venv_path = config.get("venv_path", "/opt/omnia/venv")
    if not venv_path.startswith("/"):
        errors.append(
            f"venv_path must be absolute: '{venv_path}'"
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def validate_all() -> Dict[str, Any]:
    """Run all validations and raise on fatal errors.

    Returns:
        Dict with warnings list.

    Raises:
        ConfigValidationError: If any validation error found.
    """
    result = validate_test_config()

    if not result["valid"]:
        msg = "Configuration errors:\n" + "\n".join(
            f"  - {e}" for e in result["errors"]
        )
        raise ConfigValidationError(msg)

    return {"warnings": result["warnings"]}
