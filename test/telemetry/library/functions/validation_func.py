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
Telemetry — Config Validation Functions.

Validates test_config.yml and test_creds.yml before test execution.
"""

import os

from omnia_auto import load_test_config, load_test_credentials, log

from library.vars.common_vars import (
    IPV4_PATTERN,
    MODULE_ROOT,
    REQUIRED_CONFIG_FIELDS,
    REQUIRED_DATASET_FILES,
    REQUIRED_SRC_FILES,
    SRC_INPUT_DIR,
)


class ConfigValidationError(Exception):
    """Raised when test configuration validation fails."""


def validate_all():
    """Validate test_config.yml and test_creds.yml.

    Checks:
        1. Required fields present in test_config.yml
        2. target_host is a valid IPv4 address
        3. Dataset files exist (if dataset is set)
        4. src/ input files exist (if dataset is empty)
        5. Credentials file loadable

    Raises:
        ConfigValidationError: with list of validation errors.
    """
    errors = []
    config = load_test_config()

    # 1. Required fields
    for field in REQUIRED_CONFIG_FIELDS:
        if not config.get(field):
            errors.append(f"Missing required field: '{field}' in test_config.yml")

    # 2. target_host validation
    target_host = config.get("target_host", "")
    if target_host and not IPV4_PATTERN.match(target_host):
        errors.append(
            f"target_host '{target_host}' is not a valid IPv4 address"
        )

    # 3. Dataset validation
    dataset = config.get("dataset", "")
    if dataset:
        dataset_dir = os.path.join(MODULE_ROOT, "datasets", dataset)
        if not os.path.isdir(dataset_dir):
            errors.append(f"Dataset directory not found: {dataset_dir}")
        else:
            for req_file in REQUIRED_DATASET_FILES:
                full_path = os.path.join(dataset_dir, req_file)
                if not os.path.isfile(full_path):
                    errors.append(
                        f"Required dataset file missing: {req_file}"
                    )
    else:
        # 4. src/ input files
        for req_file in REQUIRED_SRC_FILES:
            full_path = os.path.join(SRC_INPUT_DIR, req_file)
            if not os.path.isfile(full_path):
                errors.append(
                    f"Required src input file missing: {req_file} "
                    f"(looked in {SRC_INPUT_DIR})"
                )

    # 5. Credentials
    try:
        load_test_credentials()
    except Exception as exc:
        errors.append(f"Failed to load test_creds.yml: {exc}")

    if errors:
        raise ConfigValidationError(
            "Test configuration validation failed:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    log("Test configuration validated successfully", "INFO")
