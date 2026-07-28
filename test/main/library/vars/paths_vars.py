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
Container and OIM paths for the main module.

All paths inside the omnia_core container are defined here.
"""

# =============================================================================
# OMNIA BASE PATHS (inside omnia_core container)
# =============================================================================

OIM_SHARED_PATH = "/opt/omnia"
OMNIA_DATA_PATH = f"{OIM_SHARED_PATH}/.data"
OMNIA_AUTH_PATH = f"{OIM_SHARED_PATH}/auth"
OMNIA_LOG_PATH = f"{OIM_SHARED_PATH}/log"

# =============================================================================
# INPUT BASE PATH (inside omnia_core container)
# =============================================================================

INPUT_BASE_PATH = f"{OIM_SHARED_PATH}/input/project_default"

# =============================================================================
# OMNIA DATA PATHS (inside omnia_core container under .data/)
# =============================================================================

OIM_METADATA_PATH = f"{OMNIA_DATA_PATH}/oim_metadata.yml"

# =============================================================================
# CREDENTIALS FILE NAMES (inside container at INPUT_BASE_PATH)
# =============================================================================

OMNIA_CREDENTIALS_FILE = "omnia_config_credentials.yml"
OMNIA_CREDENTIALS_KEY_PATH = f"{INPUT_BASE_PATH}/.omnia_config_credentials_key"
