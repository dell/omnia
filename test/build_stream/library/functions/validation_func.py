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

"""Fail-closed configuration validation for Build Stream automation."""

import os
import re
from typing import Any, Dict, List

import yaml

from ..vars.common_vars import (
    IPV4_PATTERN,
    MODULE_ROOT,
    REQUIRED_CONFIG_FIELDS,
    REQUIRED_DATASET_FILES,
    REQUIRED_SRC_FILES,
    SRC_INPUT_DIR,
)


class ConfigValidationError(Exception):
    """Raised when test configuration is invalid."""


def _validate_dataset(dataset: str) -> List[str]:
    """Validate the selected dataset, or the canonical source input."""
    errors: List[str] = []
    if not dataset:
        for relative_file in REQUIRED_SRC_FILES:
            path = os.path.join(SRC_INPUT_DIR, relative_file)
            if not os.path.isfile(path):
                errors.append(f"Required src file missing: {path}")
        return errors

    if (
        not isinstance(dataset, str)
        or dataset in {".", "..", "generator"}
        or os.path.isabs(dataset)
        or os.path.basename(dataset) != dataset
        or "\x00" in dataset
    ):
        return [f"Unsafe dataset name: {dataset!r}"]

    dataset_root = os.path.realpath(os.path.join(MODULE_ROOT, "datasets"))
    dataset_path = os.path.join(dataset_root, dataset)
    if os.path.islink(dataset_path) or not os.path.isdir(dataset_path):
        return [f"Dataset directory not found: datasets/{dataset}/"]
    if os.path.dirname(os.path.realpath(dataset_path)) != dataset_root:
        return [f"Dataset escapes datasets directory: {dataset!r}"]

    for relative_file in REQUIRED_DATASET_FILES:
        path = os.path.join(dataset_path, relative_file)
        if not os.path.isfile(path) or os.path.islink(path):
            errors.append(
                f"Required file missing: datasets/{dataset}/{relative_file}"
            )
    return errors


def validate_test_config() -> Dict[str, Any]:
    """Validate required settings, paths, formats, and dataset files."""
    config_path = os.path.join(MODULE_ROOT, "test_config.yml")
    errors: List[str] = []
    warnings: List[str] = []

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
    except (OSError, yaml.YAMLError) as exc:
        return {
            "valid": False,
            "errors": [f"Unable to read test_config.yml: {exc}"],
            "warnings": [],
        }

    if not isinstance(config, dict):
        return {
            "valid": False,
            "errors": ["test_config.yml root must be a mapping"],
            "warnings": [],
        }

    for field in REQUIRED_CONFIG_FIELDS:
        if field not in config or config[field] is None:
            errors.append(f"Required field missing in test_config.yml: {field}")
    if "oim_server_ip" not in config:
        errors.append(
            'Required field missing: oim_server_ip (set to "" for local mode)'
        )
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    oim_ip = config["oim_server_ip"]
    if oim_ip and not IPV4_PATTERN.fullmatch(str(oim_ip)):
        errors.append(f"oim_server_ip: invalid IPv4 format {oim_ip!r}")

    project_name = config["project_name"]
    if (
        not isinstance(project_name, str)
        or not re.fullmatch(r"[A-Za-z0-9._-]+", project_name)
        or project_name in {".", ".."}
    ):
        errors.append("project_name must be a safe non-empty directory name")

    for field in ("sync_build_stream_input", "allow_pipeline_cancel"):
        if field in config and not isinstance(config[field], bool):
            errors.append(f"{field} must be true or false (without quotes)")

    dataset = os.environ.get("OMNIA_DATASET_OVERRIDE", "") or config["dataset"]
    errors.extend(_validate_dataset(dataset))

    if " " in str(config["report_path"]):
        errors.append("report_path must not contain spaces")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(config["report_name"])):
        errors.append(
            "report_name must contain only letters, numbers, underscores, hyphens"
        )

    if oim_ip:
        clone_path = config.get("clone_path")
        if not isinstance(clone_path, str) or not clone_path.strip():
            errors.append("clone_path required for remote execution")
        elif not os.path.isabs(clone_path.strip()):
            errors.append(f"clone_path must be absolute: {clone_path}")
        if not config.get("oim_ssh_user"):
            errors.append("oim_ssh_user required when oim_server_ip is set")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


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

    return config_result
