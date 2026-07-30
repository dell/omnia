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
Validation Module

Centralized configuration validation for test_config.yml and datasets.
All validation logic, constants, and messages live here — no inline
validation elsewhere.

Structure:
    functions/   - Validation functions (validate_all, etc.)
    vars/        - Allowed values, regex patterns, field rules
    messages/    - Error and success messages
"""

from .functions import (
    validate_test_config,
    validate_storage_params,
    validate_report_config,
    validate_dataset_config,
    validate_all,
    ConfigValidationError,
)

from .vars import (
    VALID_SHARE_OPTIONS,
    VALID_NFS_TYPES,
    VALID_DATASETS,
    VALID_COMMANDS,
    REQUIRED_CONFIG_KEYS,
    IPV4_PATTERN,
    UNIX_PATH_PATTERN,
)

from .messages import (
    VALIDATION_MSGS,
)
