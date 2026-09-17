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

"""Fail-closed validation for Repo Manager test configuration and datasets."""

import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

import yaml

from omnia_auto import load_test_config
from ..vars.common_vars import (
    DATASET_NAME_PATTERN,
    DATASETS_DIR,
    REQUIRED_DATASET_INPUT_FILES,
    SRC_INPUT_DIR,
)


_SENSITIVE_FILE_PARTS = (
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


class ConfigValidationError(Exception):
    """Raised when Repo Manager test configuration is invalid."""


def _selected_dataset(config: Dict[str, Any]) -> str:
    """Return the environment override or configured dataset name."""
    value = os.environ.get("OMNIA_DATASET_OVERRIDE", "") or config.get(
        "dataset", ""
    )
    if not isinstance(value, str):
        raise ValueError("dataset must be a directory name string")
    return value.strip()


def _boolean_override(name: str) -> Optional[bool]:
    """Parse an optional boolean environment override without guessing."""
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return None
    if value not in {"true", "false"}:
        raise ValueError(f"{name} must be 'true' or 'false'")
    return value == "true"


def _dataset_root(dataset: str) -> Path:
    """Resolve one named dataset without permitting traversal or symlinks."""
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
    """Return errors for links that could escape the selected input tree."""
    errors: List[str] = []
    if not directory.is_dir():
        return errors
    for path in directory.rglob("*"):
        if path.is_symlink():
            errors.append(f"Dataset symlink is not allowed: {path}")
    return errors


def _required_files(directory: Path) -> List[str]:
    """Require the complete public Repo Manager input contract."""
    if not directory.is_dir():
        return [f"Required dataset input directory not found: {directory}"]

    errors: List[str] = []
    for name in REQUIRED_DATASET_INPUT_FILES:
        path = directory / name
        if not path.is_file() or path.is_symlink():
            errors.append(f"Required dataset input file missing or unsafe: {path}")
    return errors


def _validate_public_input(directory: Path) -> List[str]:
    """Validate YAML inputs and reject credential-like dataset files."""
    errors: List[str] = []
    if not directory.is_dir():
        return errors

    for path in directory.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        normalized_name = path.name.lower().replace("-", "_")
        if any(part in normalized_name for part in _SENSITIVE_FILE_PARTS):
            errors.append(
                "Credential-like files are forbidden in Repo Manager "
                f"datasets: {path}"
            )

    for name in REQUIRED_DATASET_INPUT_FILES:
        path = directory / name
        if not path.is_file() or path.is_symlink():
            continue
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            errors.append(f"Unable to parse dataset YAML '{path}': {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"Dataset YAML must contain a mapping: {path}")
    return errors


def _validate_dataset(config: Dict[str, Any]) -> List[str]:
    """Validate the selected dataset or canonical source-input fallback."""
    try:
        _boolean_override("OMNIA_SYNC_INPUT_OVERRIDE")
        dataset = _selected_dataset(config)
        dataset_root = _dataset_root(dataset) if dataset else None
    except ValueError as exc:
        return [str(exc)]

    input_dir = (
        dataset_root / "input"
        if dataset_root is not None
        else Path(SRC_INPUT_DIR)
    )
    if dataset_root is not None and not dataset_root.is_dir():
        return [f"Dataset directory not found: {dataset_root}"]

    errors = _required_files(input_dir)
    errors.extend(_reject_nested_symlinks(input_dir))
    if not errors:
        errors.extend(_validate_public_input(input_dir))
    return errors


def validate_test_config(
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate runner configuration and selected dataset contracts."""
    if config is None:
        config = load_test_config()

    if not isinstance(config, dict):
        return {
            "valid": False,
            "errors": ["test_config.yml root must be a mapping"],
            "warnings": [],
        }

    errors: List[str] = []
    warnings: List[str] = []

    for field in (
        "clone_path",
        "project_name",
        "report_path",
        "report_name",
    ):
        value = config.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"'{field}' is required and cannot be empty")

    if "oim_server_ip" not in config:
        errors.append("'oim_server_ip' is required (use an empty string locally)")
    elif not isinstance(config.get("oim_server_ip"), str):
        errors.append("'oim_server_ip' must be a string")

    clone_path = str(config.get("clone_path", ""))
    if clone_path and not os.path.isabs(clone_path):
        errors.append(f"clone_path must be absolute: {clone_path}")

    project_name = str(config.get("project_name", ""))
    if project_name and (
        not re.fullmatch(r"[A-Za-z0-9._-]+", project_name)
        or project_name in {".", ".."}
    ):
        errors.append("project_name must be a safe directory name")

    report_path = str(config.get("report_path", ""))
    if " " in report_path:
        errors.append("report_path must not contain spaces")
    report_name = str(config.get("report_name", ""))
    if report_name and not re.fullmatch(r"[A-Za-z0-9_-]+", report_name):
        errors.append(
            "report_name must contain only letters, numbers, underscores, "
            "or hyphens"
        )

    if "dataset" not in config:
        errors.append("'dataset' is required (use an empty string for source mode)")
    if not isinstance(config.get("sync_repo_manager_input"), bool):
        errors.append("'sync_repo_manager_input' must be true or false")

    errors.extend(_validate_dataset(config))

    if not config.get("oim_server_ip", ""):
        warnings.append("oim_server_ip is empty — running in local mode")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def validate_all(
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate all contracts and raise one actionable startup error."""
    result = validate_test_config(config)
    if not result["valid"]:
        message = "Repo Manager test configuration errors:\n" + "\n".join(
            f"  - {error}" for error in result["errors"]
        )
        raise ConfigValidationError(message)
    return {"warnings": result["warnings"]}
