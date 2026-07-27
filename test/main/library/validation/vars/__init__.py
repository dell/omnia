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

"""Validation Variables — patterns, enums, field rules."""

from .validation_vars import (
    VALID_SHARE_OPTIONS,
    VALID_NFS_TYPES,
    VALID_DATASETS,
    VALID_COMMANDS,
    REQUIRED_CONFIG_KEYS,
    IPV4_PATTERN,
    UNIX_PATH_PATTERN,
    REPORT_ID_PATTERN,
    USERNAME_PATTERN,
    NFS_EXTERNAL_REQUIRED,
    NFS_INTERNAL_REQUIRED,
    LOCAL_REQUIRED,
    FIELD_RULES,
    ENUM_VALUES,
    MIN_PORT,
    MAX_PORT,
)
