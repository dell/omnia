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
Discovery — Test Configuration Validation

Validates test_config.yml and test_creds.yml before test execution.
"""

import os
import re
from typing import Any, Dict, List

from omnia_auto import load_test_config, get_module_root
from ..vars.common_vars import SRC_INPUT_DIR


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
    for field in ("report_path", "report_name"):
        val = config.get(field, "")
        if not val or not str(val).strip():
            errors.append(f"'{field}' is required and cannot be empty")

    # clone_path is required for remote execution
    server_ip = config.get("oim_server_ip", "")
    if server_ip:
        clone_path = config.get("clone_path", "")
        if not clone_path or not str(clone_path).strip():
            errors.append("clone_path is required for remote execution")
        elif not os.path.isabs(clone_path.strip()):
            errors.append(f"clone_path must be absolute: {clone_path.strip()}")
    else:
        warnings.append(
            "oim_server_ip is empty — running in local mode"
        )

    # Dataset directory must exist locally (if dataset is set)
    dataset = config.get("dataset", "")
    if dataset:
        module_root = get_module_root()
        dataset_dir = os.path.join(module_root, "datasets", dataset)
        if not os.path.isdir(dataset_dir):
            errors.append(
                f"Dataset directory not found: {dataset_dir}"
            )
    else:
        # When dataset is empty, src/ input directory must exist
        if not os.path.isdir(SRC_INPUT_DIR):
            errors.append(
                f"src/ input directory not found: {SRC_INPUT_DIR}"
            )

    # Report path should not contain spaces
    report_path = str(config.get("report_path", ""))
    if " " in report_path:
        errors.append("report_path must not contain spaces")

    # Report name must contain only letters, numbers, underscores, hyphens
    report_name = str(config.get("report_name", ""))
    if not re.match(r'^[a-zA-Z0-9_-]+$', report_name):
        errors.append(
            "report_name must contain only letters, numbers, underscores, hyphens"
        )

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
