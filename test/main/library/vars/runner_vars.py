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

"""Constants for the playbook/shell runner."""

from .common_vars import OMNIA_CORE_CONTAINER, CONTAINER_SSH_PORT, SSH_OPTS

# Re-export under runner-friendly aliases
DEFAULT_CONTAINER: str = OMNIA_CORE_CONTAINER

# Ansible settings
DEFAULT_VERBOSITY: int = 1
DEFAULT_TIMEOUT: int = 7200  # 2 hours max

# Output formatting
LINE_WIDTH: int = 160  # Max visible chars per | line before folding

# SSH options for remote execution (list form for subprocess calls)
SSH_OPTIONS: list = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=10",
]
