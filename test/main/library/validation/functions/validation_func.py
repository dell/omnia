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
Validation Functions

Centralized validation for test_config.yml, dataset configs, and
report settings. Called once before any test execution via conftest.py.

Usage:
    from main.library.validation import validate_all, ConfigValidationError

    try:
        validate_all()
    except ConfigValidationError as e:
        pytest.exit(str(e))
"""

import os
from typing import Any, Dict, List, Optional

import yaml

from ..vars.validation_vars import (
    IPV4_PATTERN,
    UNIX_PATH_PATTERN,
    REPORT_ID_PATTERN,
    USERNAME_PATTERN,
    VALID_DATASETS,
    NFS_EXTERNAL_REQUIRED,
    NFS_INTERNAL_REQUIRED,
    LOCAL_REQUIRED,
    ENUM_VALUES,
    FIELD_RULES,
    MIN_PORT,
    MAX_PORT,
)

from ..messages.validation_msgs import VALIDATION_MSGS


# =============================================================================
# MODULE ROOT (inlined to avoid circular imports)
# =============================================================================

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# functions/ -> validation/ -> library/ -> main/
_MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_DIR)))


# =============================================================================
# CUSTOM EXCEPTION
# =============================================================================

class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, errors: List[str], source: str = "test_config.yml"):
        self.errors = errors
        self.source = source
        count = len(errors)
        header = VALIDATION_MSGS["config_invalid"].format(count=count)
        detail = "\n".join(f"  [{i+1}] {e}" for i, e in enumerate(errors))
        super().__init__(f"\n{header}\n{detail}")


# =============================================================================
# FIELD VALIDATORS
# =============================================================================

def _validate_ipv4(value: str, field: str) -> Optional[str]:
    """Validate IPv4 address format."""
    if not IPV4_PATTERN.match(value):
        return VALIDATION_MSGS["invalid_ipv4"].format(field=field, value=value)
    return None


def _validate_ipv4_or_localhost(value: str, field: str) -> Optional[str]:
    """Validate IPv4, 'localhost', or empty string."""
    if not value:
        return None
    if value.lower() == "localhost":
        return None
    if IPV4_PATTERN.match(value):
        return None
    return VALIDATION_MSGS["invalid_ipv4_or_localhost"].format(field=field, value=value)


def _validate_unix_path(value: str, field: str) -> Optional[str]:
    """Validate Unix absolute path (starts with /, no spaces)."""
    if not UNIX_PATH_PATTERN.match(value):
        return VALIDATION_MSGS["invalid_unix_path"].format(field=field, value=value)
    return None


def _validate_report_path(value: str, _field: str) -> Optional[str]:
    """Validate report path — absolute path or folder name, no spaces."""
    if not value:
        return None
    if " " in value:
        return VALIDATION_MSGS["invalid_report_path"].format(value=value)
    if value.startswith("/") and not UNIX_PATH_PATTERN.match(value):
        return VALIDATION_MSGS["invalid_report_path"].format(value=value)
    return None


def _validate_report_id(value: str, _field: str) -> Optional[str]:
    """Validate report ID — alphanumeric, underscores, hyphens only."""
    if not value:
        return None
    if not REPORT_ID_PATTERN.match(value):
        return VALIDATION_MSGS["invalid_report_id"].format(value=value)
    return None


def _validate_username(value: str, field: str) -> Optional[str]:
    """Validate Linux username format."""
    if not USERNAME_PATTERN.match(value):
        return VALIDATION_MSGS["invalid_username"].format(field=field, value=value)
    return None


def _validate_port(value: Any, field: str) -> Optional[str]:
    """Validate port number (1-65535)."""
    try:
        port = int(value)
        if port < MIN_PORT or port > MAX_PORT:
            raise ValueError
    except (ValueError, TypeError):
        return VALIDATION_MSGS["invalid_port"].format(field=field, value=value)
    return None


def _validate_enum(value: str, field: str) -> Optional[str]:
    """Validate against allowed enum values."""
    allowed = ENUM_VALUES.get(field, set())
    if value not in allowed:
        return VALIDATION_MSGS["invalid_enum"].format(
            field=field, value=value, allowed=", ".join(sorted(allowed))
        )
    return None


def _validate_bool(value: Any, field: str) -> Optional[str]:
    """Validate boolean value."""
    if not isinstance(value, bool):
        return VALIDATION_MSGS["invalid_bool"].format(field=field, value=value)
    return None


# Dispatcher
_VALIDATORS = {
    "ipv4": _validate_ipv4,
    "ipv4_or_localhost": _validate_ipv4_or_localhost,
    "unix_path": _validate_unix_path,
    "report_path": _validate_report_path,
    "report_id": _validate_report_id,
    "username": _validate_username,
    "port": _validate_port,
    "enum": _validate_enum,
    "bool": _validate_bool,
}


def _validate_field(field: str, value: Any) -> Optional[str]:
    """Validate a single field using FIELD_RULES."""
    rule = FIELD_RULES.get(field)
    if not rule:
        return None

    vtype, _allow_empty, _desc = rule
    str_val = str(value).strip() if value is not None else ""

    if not str_val:
        return None

    validator = _VALIDATORS.get(vtype)
    if not validator:
        return None
    if vtype in ("bool", "port"):
        return validator(value, field)
    return validator(str_val, field)


# =============================================================================
# PUBLIC VALIDATION FUNCTIONS
# =============================================================================

def validate_test_config(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """Validate test_config.yml fields.

    Args:
        config: Pre-loaded config dict, or None to load from disk.

    Returns:
        List of error message strings. Empty list = valid.
    """
    if config is None:
        config = _load_config()

    errors: List[str] = []

    # Validate each present field against its rule
    for field, value in config.items():
        if field.startswith("_"):
            continue
        err = _validate_field(field, value)
        if err:
            errors.append(err)

    return errors


def _validate_nfs_storage(
    storage: Dict[str, Any], source: str
) -> List[str]:
    """Validate NFS-specific storage parameters."""
    errors: List[str] = []
    nfs_type = str(storage.get("nfs_type", "")).strip()
    if not nfs_type:
        errors.append(VALIDATION_MSGS["missing_required"].format(
            field="nfs_type", source=source, context="NFS storage"
        ))
        return errors

    if nfs_type.lower() == "external":
        required, msg_key = NFS_EXTERNAL_REQUIRED, "nfs_external_missing"
    else:
        required, msg_key = NFS_INTERNAL_REQUIRED, "nfs_internal_missing"

    for param in required:
        if not str(storage.get(param, "")).strip():
            errors.append(VALIDATION_MSGS[msg_key].format(
                field=param, source=source
            ))

    nfs_ip = str(storage.get("nfs_server_ip", "")).strip()
    if nfs_ip:
        err = _validate_ipv4(nfs_ip, "nfs_server_ip")
        if err:
            errors.append(err)

    errors.extend(_validate_storage_paths(storage))
    return errors


def _validate_local_storage(
    storage: Dict[str, Any], source: str
) -> List[str]:
    """Validate Local storage parameters."""
    errors: List[str] = []
    for param in LOCAL_REQUIRED:
        if not str(storage.get(param, "")).strip():
            errors.append(VALIDATION_MSGS["local_missing"].format(
                field=param, source=source
            ))
    errors.extend(_validate_storage_paths(storage))
    return errors


def _validate_storage_paths(storage: Dict[str, Any]) -> List[str]:
    """Validate path fields in storage config."""
    errors: List[str] = []
    for path_field in ("nfs_server_share_path", "omnia_shared_path"):
        path_val = str(storage.get(path_field, "")).strip()
        if path_val:
            err = _validate_unix_path(path_val, path_field)
            if err:
                errors.append(err)
    return errors


def validate_storage_params(
    storage: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Validate storage parameters based on share_option.

    Args:
        storage: Pre-loaded storage dict with resolved values.
        config: Pre-loaded config dict (used if storage is None).

    Returns:
        List of error message strings. Empty list = valid.
    """
    if storage is None and config is None:
        config = _load_config()
    if storage is None:
        storage = config or {}

    source = storage.get("_source", "test_config.yml")
    share_option = str(storage.get("share_option", "")).strip()

    if not share_option:
        return [VALIDATION_MSGS["missing_required"].format(
            field="share_option", source=source,
            context="storage configuration"
        )]

    if share_option.upper() == "NFS":
        return _validate_nfs_storage(storage, source)
    if share_option.upper() == "LOCAL":
        return _validate_local_storage(storage, source)
    return []


def validate_report_config(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """Validate report-related configuration.

    Checks:
      - report_path: absolute path or folder name, no spaces
      - report_name: alphanumeric + underscore/hyphen, no spaces
      - report_id: alphanumeric + underscore/hyphen, no spaces (optional)

    Args:
        config: Pre-loaded config dict, or None to load from disk.

    Returns:
        List of error message strings. Empty list = valid.
    """
    if config is None:
        config = _load_config()

    errors: List[str] = []

    # report_path
    report_path = str(config.get("report_path", "")).strip()
    if report_path:
        err = _validate_report_path(report_path, "report_path")
        if err:
            errors.append(err)

    # report_name
    report_name = str(config.get("report_name", "")).strip()
    if report_name:
        err = _validate_report_id(report_name, "report_name")
        if err:
            errors.append(err)

    # report_id (custom user-provided ID)
    report_id = str(config.get("report_id", "")).strip()
    if report_id:
        err = _validate_report_id(report_id, "report_id")
        if err:
            errors.append(err)

    return errors


def validate_dataset_config(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """Validate dataset configuration when use_dataset is true.

    Checks:
      - Dataset folder exists
      - install_config.yml exists in dataset folder
      - Fields in install_config.yml are valid (IP format, paths, etc.)

    Args:
        config: Pre-loaded config dict, or None to load from disk.

    Returns:
        List of error message strings. Empty list = valid.
    """
    if config is None:
        config = _load_config()

    if not config.get("use_dataset", False):
        return []

    dataset_name = str(config.get("dataset", "")).strip()
    if not dataset_name:
        return [VALIDATION_MSGS["missing_required"].format(
            field="dataset", source="test_config.yml",
            context="dataset override (use_dataset: true)"
        )]

    errors: List[str] = []
    if dataset_name not in VALID_DATASETS:
        errors.append(VALIDATION_MSGS["invalid_enum"].format(
            field="dataset", value=dataset_name,
            allowed=", ".join(sorted(VALID_DATASETS))
        ))

    dataset_dir = os.path.join(_MODULE_ROOT, "datasets", dataset_name)
    if not os.path.isdir(dataset_dir):
        return errors + [VALIDATION_MSGS["dataset_not_found"].format(
            path=dataset_dir, available=_list_datasets()
        )]

    config_file = os.path.join(dataset_dir, "install_config.yml")
    if not os.path.isfile(config_file):
        return errors + [VALIDATION_MSGS["dataset_config_missing"].format(
            path=config_file
        )]

    ds_config = _load_dataset_file(config_file, errors)
    if ds_config is None:
        return errors

    errors.extend(_validate_dataset_fields(ds_config, dataset_name))
    return errors


def _list_datasets() -> str:
    """List available dataset directories."""
    datasets_dir = os.path.join(_MODULE_ROOT, "datasets")
    if not os.path.isdir(datasets_dir):
        return "none"
    return ", ".join(sorted(
        d for d in os.listdir(datasets_dir)
        if os.path.isdir(os.path.join(datasets_dir, d))
    ))


def _load_dataset_file(
    config_file: str, errors: List[str]
) -> Optional[Dict[str, Any]]:
    """Load and parse a dataset install_config.yml."""
    try:
        with open(config_file, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except (yaml.YAMLError, OSError) as exc:
        errors.append(
            f"Failed to parse dataset config: {config_file}: {exc}"
        )
        return None


def _validate_dataset_fields(
    ds_config: Dict[str, Any], dataset_name: str
) -> List[str]:
    """Validate IP and path fields inside a dataset config."""
    errors: List[str] = []
    field_validators = [
        (("admin_nic_ip", "nfs_server_ip"), _validate_ipv4),
        (("nfs_server_share_path", "omnia_shared_path"), _validate_unix_path),
    ]
    for fields, validator in field_validators:
        for fld in fields:
            val = str(ds_config.get(fld, "")).strip()
            if val:
                err = validator(val, fld)
                if err:
                    errors.append(VALIDATION_MSGS["dataset_field_invalid"].format(
                        dataset=dataset_name, field=fld, value=val, detail=err
                    ))
    return errors


def validate_all(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """Run all validations on test_config.yml.

    Combines: field validation, storage params, report config, and dataset.
    Returns all errors. Raises ConfigValidationError if any.

    Args:
        config: Pre-loaded config dict, or None to load from disk.

    Returns:
        Empty list if valid.

    Raises:
        ConfigValidationError if validation fails.
    """
    if config is None:
        config = _load_config()

    errors: List[str] = []
    errors.extend(validate_test_config(config))
    errors.extend(validate_report_config(config))
    errors.extend(validate_storage_params(config=config))
    errors.extend(validate_dataset_config(config))

    if errors:
        # Deduplicate (same error from storage + field check)
        seen = set()
        unique = []
        for e in errors:
            if e not in seen:
                seen.add(e)
                unique.append(e)
        raise ConfigValidationError(unique, source="test_config.yml")

    return []


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _load_config() -> Dict[str, Any]:
    """Load test_config.yml from module root."""
    config_path = os.path.join(_MODULE_ROOT, "test_config.yml")
    if not os.path.exists(config_path):
        raise ConfigValidationError(
            [VALIDATION_MSGS["config_file_missing"].format(
                path=config_path, filename="test_config.yml"
            )],
            source="test_config.yml",
        )
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not data:
        raise ConfigValidationError(
            [VALIDATION_MSGS["config_file_empty"].format(
                path=config_path, filename="test_config.yml"
            )],
            source="test_config.yml",
        )
    return data
