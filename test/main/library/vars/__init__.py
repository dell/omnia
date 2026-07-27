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
Main Module — Variables

All constants and configuration variables for the main module.
"""

# --- Common constants ---
from .common_vars import (
    MODULE_ROOT,
    REPO_ROOT,
    OMNIA_SH_PATH,
    OMNIA_CORE_CONTAINER,
    CONTAINER_SSH_PORT,
    PODMAN_EXEC_PREFIX,
    SSH_OPTS,
    SSH_KEY_PRIV,
    SSH_KEY_PUB,
    SSH_CONFIG_PATH,
    AUTHORIZED_KEYS_PATH,
    KNOWN_HOSTS_PATH,
    KNOWN_HOSTS_PATTERN,
    TEST_CONFIG_FILE,
    TEST_CREDENTIALS_FILE,
    TEST_CREDENTIALS_KEY,
    CMDS,
)

# --- Container paths ---
from .paths_vars import (
    OIM_SHARED_PATH,
    OMNIA_DATA_PATH,
    INPUT_BASE_PATH,
    OIM_METADATA_PATH,
)

# --- Runner constants ---
from .runner_vars import (
    DEFAULT_CONTAINER,
    DEFAULT_VERBOSITY,
    DEFAULT_TIMEOUT,
    LINE_WIDTH,
    SSH_OPTIONS,
)

# --- Omnia.sh test variables ---
from .omnia_sh_vars import OMNIA_SH_VARS, TEST_VARS, validate_current_dataset
