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
Config validation for telemetry test framework.

Validates test_config.yml fields: IP format, paths, dataset existence.
"""

import os
import re


import yaml

from ..vars.common_vars import (
    IPV4_PATTERN,
    REQUIRED_CONFIG_FIELDS,
    REQUIRED_SRC_FILES,
    MODULE_ROOT,
    SRC_INPUT_DIR,
)
from ..vars.sfm_vars import (
    SFM_CONFIG_KEYS,
    SFM_MAX_NETWORK_PORT,
    SFM_PORT_DEFAULTS,
    SFM_REQUIRED_ENDPOINT_SETTINGS,
)

_MODULE_ROOT = MODULE_ROOT


class ConfigValidationError(Exception):
    """Raised when config validation fails."""


def _validate_ip(value, field):
    """Validate IPv4 address format."""
    errors = []
    if value and not IPV4_PATTERN.match(str(value)):
        errors.append(f"{field}: invalid IPv4 format '{value}'")
    return errors


def _validate_positive_int(value, field, maximum=None):
    """Validate an integer configuration field against optional bounds."""
    valid = (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
        and (maximum is None or value <= maximum)
    )
    if valid:
        return []
    if maximum is None:
        return [f"{field}: must be a positive integer"]
    return [f"{field}: must be between 1 and {maximum}"]


def _validate_sfm_config(config):
    """Validate settings required by the opt-in SFM integration."""
    errors = []
    enabled_field = SFM_CONFIG_KEYS["enabled"]
    enabled = config.get(enabled_field, False)
    if not isinstance(enabled, bool):
        return [f"{enabled_field}: must be true or false"]
    if not enabled:
        return errors

    for setting in SFM_REQUIRED_ENDPOINT_SETTINGS:
        field = SFM_CONFIG_KEYS[setting]
        value = str(config.get(field, "")).strip()
        if not value:
            errors.append(f"{field} required when {enabled_field} is true")
        else:
            errors.extend(_validate_ip(value, field))
    for setting, default in SFM_PORT_DEFAULTS.items():
        field = SFM_CONFIG_KEYS[setting]
        errors.extend(_validate_positive_int(
            config.get(field, default), field, SFM_MAX_NETWORK_PORT,
        ))
    force_field = SFM_CONFIG_KEYS["force_export"]
    if not isinstance(config.get(force_field, False), bool):
        errors.append(f"{force_field}: must be true or false")
    return errors


def _validate_dataset(dataset):
    """Validate dataset directory or src/ files."""
    errors = []
    if not dataset:
        # Default mode - validate src/ files exist
        if not os.path.isdir(SRC_INPUT_DIR):
            errors.append(f"src/ input directory not found: {SRC_INPUT_DIR}")
            return errors
        for rel_file in REQUIRED_SRC_FILES:
            if not os.path.isfile(os.path.join(SRC_INPUT_DIR, rel_file)):
                errors.append(f"Required src file missing: {rel_file}")
        return errors

    dataset_path = os.path.join(_MODULE_ROOT, "datasets", dataset)
    if not os.path.isdir(dataset_path):
        available = [
            d for d in os.listdir(os.path.join(_MODULE_ROOT, "datasets"))
            if os.path.isdir(os.path.join(_MODULE_ROOT, "datasets", d))
        ]
        errors.append(
            f"Dataset directory not found: datasets/{dataset}/. "
            f"Available: {', '.join(sorted(available))}"
        )
    return errors


def validate_test_config():
    """Validate test_config.yml.

    Checks:
    - File exists and is valid YAML
    - All required fields are present
    - OIM IP format (if set)
    - Dataset directory and required files exist
    - Paths are absolute where required
    - report_path/report_name format

    Returns:
        Dict with 'valid', 'errors', 'warnings'.
    """
    config_path = os.path.join(_MODULE_ROOT, "test_config.yml")
    errors = []
    warnings = []

    if not os.path.exists(config_path):
        return {
            "valid": False,
            "errors": ["test_config.yml not found"],
            "warnings": [],
        }

    with open(config_path, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}

    # --- Required fields ---
    for field in REQUIRED_CONFIG_FIELDS:
        if field not in config or config[field] is None:
            errors.append(
                f"Required field missing in test_config.yml: {field}"
            )

    # oim_server_ip must be present (empty string is valid = local)
    if "oim_server_ip" not in config:
        errors.append(
            'Required field missing: oim_server_ip '
            '(set to "" for local mode)'
        )

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    # --- OIM IP format ---
    oim_ip = config["oim_server_ip"]
    if oim_ip:
        errors.extend(_validate_ip(str(oim_ip), "oim_server_ip"))

    # --- Dataset validation ---
    dataset = (
        os.environ.get("OMNIA_DATASET_OVERRIDE", "")
        or config.get("dataset", "")
    )
    errors.extend(_validate_dataset(dataset))

    # --- Clone path ---
    clone_path = config["clone_path"]
    if not os.path.isabs(str(clone_path)):
        errors.append(f"clone_path must be absolute: {clone_path}")

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

    # --- Opt-in SFM integration checks ---
    errors.extend(_validate_sfm_config(config))

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def validate_all():
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
