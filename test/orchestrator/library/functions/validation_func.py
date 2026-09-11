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

"""Fail-closed validation for Orchestrator test configuration and datasets."""

import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List

from jsonschema import Draft7Validator
import yaml

from omnia_auto import load_test_config
from ..vars.common_vars import (
    DATASET_NAME_PATTERN,
    DATASETS_DIR,
    REQUIRED_IMAGE_BUILD_OUTPUT_FILES,
    REQUIRED_DATASET_INPUT_FILES,
    REQUIRED_REPO_OUTPUT_FILES,
    SCHEMA_DIR,
    SRC_IMAGE_BUILD_OUTPUT_DIR,
    SRC_INPUT_DIR,
    SRC_REPO_OUTPUT_DIR,
)


class ConfigValidationError(Exception):
    """Raised when test configuration is invalid."""


def _selected_dataset(config: Dict[str, Any]) -> str:
    """Return the environment override or configured dataset name."""
    value = os.environ.get("OMNIA_DATASET_OVERRIDE", "") or config.get(
        "dataset", ""
    )
    if not isinstance(value, str):
        raise ValueError("dataset must be a directory name string")
    return value.strip()


def _boolean_override(name: str):
    """Parse an optional boolean environment override without guessing."""
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return None
    if value not in {"true", "false"}:
        raise ValueError(f"{name} must be 'true' or 'false'")
    return value == "true"


def _dataset_root(dataset: str) -> Path:
    """Resolve a named dataset without permitting traversal or symlinks."""
    if (
        not DATASET_NAME_PATTERN.fullmatch(dataset)
        or dataset in {".", "..", "generator"}
    ):
        raise ValueError(f"Unsafe dataset name: {dataset!r}")
    datasets_root = Path(DATASETS_DIR).resolve()
    candidate = datasets_root / dataset
    if candidate.is_symlink():
        raise ValueError(f"Dataset symlinks are not allowed: {dataset}")
    resolved = candidate.resolve(strict=False)
    if resolved.parent != datasets_root:
        raise ValueError(f"Dataset escapes datasets directory: {dataset!r}")
    return resolved


def _reject_nested_symlinks(directory: Path) -> List[str]:
    errors = []
    if not directory.is_dir():
        return errors
    for path in directory.rglob("*"):
        if path.is_symlink():
            errors.append(f"Dataset symlink is not allowed: {path}")
    return errors


def _required_files(directory: Path, names: List[str], label: str) -> List[str]:
    errors = []
    if not directory.is_dir():
        return [f"Required {label} directory not found: {directory}"]
    for name in names:
        path = directory / name
        if not path.is_file() or path.is_symlink():
            errors.append(f"Required {label} file missing or unsafe: {path}")
    return errors


def _validate_yaml_schema(data_path: Path, schema_name: str) -> List[str]:
    """Validate one YAML input against its source JSON schema."""
    schema_path = Path(SCHEMA_DIR) / schema_name
    try:
        data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError, json.JSONDecodeError) as exc:
        return [f"Unable to parse dataset contract '{data_path}': {exc}"]
    errors = sorted(
        Draft7Validator(schema).iter_errors(data),
        key=lambda item: list(item.absolute_path),
    )
    return [
        f"{data_path}: {'/'.join(map(str, error.absolute_path)) or '<root>'}: "
        f"{error.message}"
        for error in errors
    ]


def _validate_repo_status(path: Path) -> List[str]:
    """Validate the core Repo Manager handoff needed by Orchestrator."""
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return [f"Unable to parse Repo Manager output '{path}': {exc}"]
    if not isinstance(value, dict):
        return [f"Repo Manager output must be a mapping: {path}"]
    errors = []
    if value.get("overall_status") != "success":
        errors.append(f"Repo Manager output is not successful: {path}")
    if not value.get("cluster_os_type"):
        errors.append(f"cluster_os_type is missing from {path}")
    if not isinstance(value.get("repositories"), dict):
        errors.append(f"repositories must be a mapping in {path}")
    repo_manager = value.get("repo_manager", {})
    if not isinstance(repo_manager, dict):
        errors.append(f"repo_manager must be a mapping in {path}")
        repo_manager = {}
    certificates = repo_manager.get("certificates", {})
    if not isinstance(certificates, dict) or not certificates.get("server_crt"):
        errors.append(f"repo_manager.certificates.server_crt is missing from {path}")
    return errors


def _validate_build_status(path: Path) -> List[str]:
    """Validate the image-builder handoff consumed during provisioning."""
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return [f"Unable to parse Image Build Manager output '{path}': {exc}"]
    if not isinstance(value, dict):
        return [f"Image Build Manager output must be a mapping: {path}"]
    errors = []
    if value.get("overall_status") != "success":
        errors.append(f"Image Build Manager output is not successful: {path}")
    s3_configurations = value.get("s3_configurations")
    if not isinstance(s3_configurations, dict):
        errors.append(f"s3_configurations must be a mapping in {path}")
    else:
        for field in ("endpoint_url", "bucket"):
            if not s3_configurations.get(field):
                errors.append(f"s3_configurations.{field} is missing from {path}")
    images = value.get("functional_group_images")
    if not isinstance(images, list) or not images:
        errors.append(f"functional_group_images must be a non-empty list in {path}")
    return errors


def _validate_dataset(config: Dict[str, Any]) -> List[str]:
    """Validate source fallbacks or the selected generated dataset."""
    errors: List[str] = []
    try:
        dataset = _selected_dataset(config)
        dataset_root = _dataset_root(dataset) if dataset else None
    except ValueError as exc:
        return [str(exc)]

    try:
        _boolean_override("OMNIA_SYNC_INPUT_OVERRIDE")
        output_override = _boolean_override("OMNIA_SYNC_OUTPUT_OVERRIDE")
        image_output_override = _boolean_override(
            "OMNIA_SYNC_IMAGE_OUTPUT_OVERRIDE"
        )
    except ValueError as exc:
        return [str(exc)]

    input_dir = (
        dataset_root / "input" if dataset_root is not None else Path(SRC_INPUT_DIR)
    )
    output_dir = (
        dataset_root / "repo_manager_output"
        if dataset_root is not None
        else Path(SRC_REPO_OUTPUT_DIR)
    )
    image_output_dir = (
        dataset_root / "image_build_manager_output"
        if dataset_root is not None
        else Path(SRC_IMAGE_BUILD_OUTPUT_DIR)
    )
    if dataset_root is not None and not dataset_root.is_dir():
        return [f"Dataset directory not found: {dataset_root}"]

    errors.extend(
        _required_files(
            input_dir,
            REQUIRED_DATASET_INPUT_FILES,
            "dataset input",
        )
    )
    errors.extend(_reject_nested_symlinks(input_dir))
    if not errors:
        errors.extend(
            _validate_yaml_schema(
                input_dir / "orchestrator_config.yml",
                "orchestrator_config.json",
            )
        )
        errors.extend(
            _validate_yaml_schema(
                input_dir / "network_spec.yml", "network_spec.json"
            )
        )

    output_requested = (
        output_override
        if output_override is not None
        else bool(config.get("sync_repo_manager_output", False))
    )
    if output_requested:
        output_errors = _required_files(
            output_dir,
            REQUIRED_REPO_OUTPUT_FILES,
            "Repo Manager output",
        )
        errors.extend(output_errors)
        errors.extend(_reject_nested_symlinks(output_dir))
        if not output_errors:
            errors.extend(_validate_repo_status(output_dir / "repo_status.yml"))

    image_output_requested = (
        image_output_override
        if image_output_override is not None
        else bool(config.get("sync_image_build_manager_output", False))
    )
    if image_output_requested:
        image_errors = _required_files(
            image_output_dir,
            REQUIRED_IMAGE_BUILD_OUTPUT_FILES,
            "Image Build Manager output",
        )
        errors.extend(image_errors)
        errors.extend(_reject_nested_symlinks(image_output_dir))
        if not image_errors:
            errors.extend(
                _validate_build_status(image_output_dir / "build_status.yml")
            )
    return errors


def validate_test_config() -> Dict[str, Any]:
    """Validate runner configuration and selected dataset contracts."""
    config = load_test_config()
    errors: List[str] = []
    warnings: List[str] = []

    for field in ("clone_path", "project_name", "report_path", "report_name"):
        value = config.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"'{field}' is required and cannot be empty")

    clone_path = str(config.get("clone_path", ""))
    if clone_path and not os.path.isabs(clone_path):
        errors.append(f"clone_path must be absolute: {clone_path}")

    report_path = str(config.get("report_path", ""))
    if " " in report_path:
        errors.append("report_path must not contain spaces")
    report_name = str(config.get("report_name", ""))
    if report_name and not re.fullmatch(r"[A-Za-z0-9_-]+", report_name):
        errors.append(
            "report_name must contain only letters, numbers, underscores, or hyphens"
        )

    for field in (
        "sync_orchestrator_input",
        "sync_repo_manager_output",
        "sync_image_build_manager_output",
    ):
        if field in config and not isinstance(config[field], bool):
            errors.append(f"'{field}' must be true or false")

    errors.extend(_validate_dataset(config))

    server_ip = config.get("oim_server_ip", "")
    if not server_ip:
        warnings.append("oim_server_ip is empty — running in local mode")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def validate_all() -> Dict[str, Any]:
    """Validate all contracts and raise a consolidated error on failure."""
    result = validate_test_config()
    if not result["valid"]:
        message = "Test configuration errors:\n" + "\n".join(
            f"  - {error}" for error in result["errors"]
        )
        raise ConfigValidationError(message)
    return {"warnings": result["warnings"]}
