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
Orchestrator — Test Configuration Validation

Validates test_config.yml and test_creds.yml before test execution.
"""

import os
from typing import Any, Dict, List

from omnia_auto import load_test_config, get_module_root


class ConfigValidationError(Exception):
    """Raised when test configuration is invalid."""


def validate_test_config() -> Dict[str, Any]:
    """Validate test_config.yml fields.

    Returns:
        Dict with keys: valid (bool), errors (list), warnings (list).
    """
    config = load_test_config()
    errors: List[str] = []
    warnings: List[str] = []

    # Required string fields
    for field in ("clone_path", "dataset", "project_name"):
        val = config.get(field, "")
        if not val or not str(val).strip():
            errors.append(f"'{field}' is required and cannot be empty")

    # Dataset directory must exist locally
    module_root = get_module_root()
    dataset = config.get("dataset", "data_set_01")
    dataset_dir = os.path.join(module_root, "datasets", dataset)
    if not os.path.isdir(dataset_dir):
        errors.append(
            f"Dataset directory not found: {dataset_dir}"
        )

    # Optional: oim_server_ip
    server_ip = config.get("oim_server_ip", "")
    if not server_ip:
        warnings.append(
            "oim_server_ip is empty — running in local mode"
        )

    # Report path should not contain spaces
    report_path = str(config.get("report_path", ""))
    if " " in report_path:
        errors.append("report_path must not contain spaces")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def validate_all() -> Dict[str, Any]:
    """Run all validation checks and raise on error.

    Returns:
        Dict with warnings list.

    Raises:
        ConfigValidationError: If any validation fails.
    """
    result = validate_test_config()
    if not result["valid"]:
        msg = "Test configuration errors:\n" + "\n".join(
            f"  - {e}" for e in result["errors"]
        )
        raise ConfigValidationError(msg)
    return {"warnings": result["warnings"]}
