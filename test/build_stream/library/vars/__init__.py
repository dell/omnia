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
Build Stream — Variables

Common constants, paths, container names, and command templates.
"""

from .common_vars import (
    MODULE_ROOT,
    REPO_ROOT,
    SHARED_PATH,
    BSM_CONTAINER,
    POSTGRES_CONTAINER,
    GITLAB_CONTAINER,
    GITLAB_RUNNER_CONTAINER,
    BSM_API_PORT,
    GITLAB_HTTP_PORT,
    POSTGRES_PORT,
    POSTGRES_DB,
    EXPECTED_POSTGRES_TABLES,
    LISTENING_PORTS,
    PLAYBOOK_TAGS,
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
)
