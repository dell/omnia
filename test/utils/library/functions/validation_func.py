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
Utils Domain — Configuration Validation Functions.

Validates test_config.yml and dataset files at session startup.
"""

import os
from typing import Dict, Any, List

from omnia_auto import load_test_config

from ..vars.common_vars import (
    MODULE_ROOT,
    SRC_INPUT_DIR,
    REQUIRED_CONFIG_FIELDS,
    REQUIRED_DATASET_FILES,
    REQUIRED_SRC_FILES,
)


class ConfigValidationError(Exception):
    """Raised when test configuration validation fails."""
    pass


def validate_required_fields(config: Dict[str, Any]) -> List[str]:
    """Validate required fields are present in config.

    Args:
        config: Test configuration dict.

    Returns:
        List of missing field names.
    """
    missing = []
    for field in REQUIRED_CONFIG_FIELDS:
        if not config.get(field):
            missing.append(field)
    return missing


def validate_dataset_files(dataset: str) -> List[str]:
    """Validate required files exist in dataset directory.

    Args:
        dataset: Dataset name.

    Returns:
        List of missing file paths.
    """
    if not dataset:
        return []

    dataset_dir = os.path.join(MODULE_ROOT, "datasets", dataset)
    if not os.path.isdir(dataset_dir):
        return [f"Dataset directory not found: {dataset_dir}"]

    missing = []
    for rel_path in REQUIRED_DATASET_FILES:
        full_path = os.path.join(dataset_dir, rel_path)
        if not os.path.isfile(full_path):
            missing.append(rel_path)

    return missing


def validate_src_files() -> List[str]:
    """Validate required files exist in src/utils/input/.

    Returns:
        List of missing file paths.
    """
    missing = []
    for rel_path in REQUIRED_SRC_FILES:
        full_path = os.path.join(SRC_INPUT_DIR, rel_path)
        if not os.path.isfile(full_path):
            missing.append(rel_path)

    return missing


def validate_clone_path(clone_path: str) -> bool:
    """Validate clone_path is an absolute path.

    Args:
        clone_path: The clone path from config.

    Returns:
        True if valid, False otherwise.
    """
    return clone_path.startswith("/")


def validate_all() -> Dict[str, Any]:
    """Run all configuration validations.

    Returns:
        dict: {"valid": bool, "warnings": list, "errors": list}

    Raises:
        ConfigValidationError: If critical validation fails.
    """
    config = load_test_config()
    warnings = []
    errors = []

    # Validate required fields
    missing_fields = validate_required_fields(config)
    if missing_fields:
        errors.append(f"Missing required fields in test_config.yml: {missing_fields}")

    # Validate clone_path
    clone_path = config.get("clone_path", "")
    if clone_path and not validate_clone_path(clone_path):
        errors.append(f"clone_path must be an absolute path: {clone_path}")

    # Validate dataset or src files
    dataset = config.get("dataset", "")
    if dataset:
        missing_dataset = validate_dataset_files(dataset)
        if missing_dataset:
            errors.append(f"Missing dataset files: {missing_dataset}")
    else:
        # When dataset is empty, check src files
        missing_src = validate_src_files()
        if missing_src:
            warnings.append(f"Missing src input files (will be created by domain-init.sh): {missing_src}")

    # Validate oim_server_ip (empty = local mode)
    oim_ip = config.get("oim_server_ip", "")
    if not oim_ip:
        warnings.append("oim_server_ip is empty — running in local mode")

    if errors:
        raise ConfigValidationError("\n".join(errors))

    return {
        "valid": True,
        "warnings": warnings,
        "errors": [],
    }
