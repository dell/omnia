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

"""Constants for the playbook runner.

Runner-specific constants only. For container names, input paths, and
credential file names, import from ``automation_library.core.vars``.
"""

from automation_library.core.vars import (
    OMNIA_CORE_CONTAINER,
    INPUT_BASE_PATH,
    OMNIA_CREDENTIALS_FILE,
    OMNIA_CREDENTIALS_KEY_PATH,
)

# Re-export core vars under runner-friendly aliases
DEFAULT_CONTAINER: str = OMNIA_CORE_CONTAINER
CONTAINER_INPUT_PATH: str = INPUT_BASE_PATH
CREDENTIALS_FILE: str = OMNIA_CREDENTIALS_FILE
CREDENTIALS_KEY_FILE: str = OMNIA_CREDENTIALS_KEY_PATH.rsplit("/", 1)[-1]

# Ansible settings
DEFAULT_VERBOSITY: int = 1
DEFAULT_TIMEOUT: int = 7200  # 2 hours max for a playbook run

# Output formatting
LINE_WIDTH: int = 160  # Max visible chars per │ line before folding

# Container SSH port (mapped from OIM host to omnia_core container)
CONTAINER_SSH_PORT: int = 2222

# SSH options for remote execution
SSH_OPTIONS: list = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=10",
]
