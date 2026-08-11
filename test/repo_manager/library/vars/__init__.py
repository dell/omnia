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
Repo Manager — Variables

Common constants, paths, container names, and command templates.
"""

from .common_vars import (
    MODULE_ROOT,
    MONOREPO_ROOT,
    REPO_ROOT,
    SRC_INPUT_DIR,
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    SHARED_PATH,
    PULP_CONTAINER,
    PULP_PORT,
    PLAYBOOK_TAGS,
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
    CONFIG_FILE,
    CREDENTIALS_FILE_NAME,
    CREDENTIALS_KEY_NAME,
    ENDPOINT_CONFIG_FILE,
    SOFTWARE_CONFIG_FILE,
    LISTENING_PORTS,
    SYSTEMD_SERVICES,
    PULP_CONFIG_DIR,
    REPO_STATUS_PATH,
    CMDS,
    IPV4_PATTERN,
    REQUIRED_CONFIG_FIELDS,
    REQUIRED_DATASET_FILES,
    REQUIRED_SRC_FILES,
)

from .test_case_vars import TEST_CASES
