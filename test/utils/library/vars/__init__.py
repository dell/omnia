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

"""Utils domain variables package."""

from .common_vars import (
    DOMAIN_NAME,
    PLAYBOOK_COLLECT,
    PLAYBOOK_INSTALL_OS,
    PLAYBOOK_WORKDIR,
    COLLECT_PLAYBOOK_TAGS,
    INSTALL_OS_TAGS,
    SHARED_PATH,
    CMDS,
    FUNCTIONAL_GROUPS,
    COLLECT_PXE_FILE,
    INSTALL_OS_CONFIG_FILE,
    INSTALL_OS_CREDENTIALS_FILE,
    LOG_BUNDLE_PATTERN,
    METADATA_FILE,
    INSTALL_OS_OUTPUT_DIR,
    INSTALL_OS_STATUS_FILE,
    CUSTOM_ISO_PATTERN,
    KICKSTART_FILE,
    REQUIRED_CONFIG_FIELDS,
    REQUIRED_DATASET_FILES,
    REQUIRED_SRC_FILES,
    MODULE_ROOT,
    TEST_ROOT,
    MONOREPO_ROOT,
    SRC_INPUT_DIR,
)

from .test_case_vars import TEST_CASES

__all__ = [
    "DOMAIN_NAME",
    "PLAYBOOK_COLLECT",
    "PLAYBOOK_INSTALL_OS",
    "PLAYBOOK_WORKDIR",
    "COLLECT_PLAYBOOK_TAGS",
    "INSTALL_OS_TAGS",
    "SHARED_PATH",
    "CMDS",
    "FUNCTIONAL_GROUPS",
    "COLLECT_PXE_FILE",
    "INSTALL_OS_CONFIG_FILE",
    "INSTALL_OS_CREDENTIALS_FILE",
    "LOG_BUNDLE_PATTERN",
    "METADATA_FILE",
    "INSTALL_OS_OUTPUT_DIR",
    "INSTALL_OS_STATUS_FILE",
    "CUSTOM_ISO_PATTERN",
    "KICKSTART_FILE",
    "REQUIRED_CONFIG_FIELDS",
    "REQUIRED_DATASET_FILES",
    "REQUIRED_SRC_FILES",
    "MODULE_ROOT",
    "TEST_ROOT",
    "MONOREPO_ROOT",
    "SRC_INPUT_DIR",
    "TEST_CASES",
]
