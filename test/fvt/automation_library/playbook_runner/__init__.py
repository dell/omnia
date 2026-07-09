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
Playbook Runner Module

Provides a pytest-native runner for executing Ansible playbooks inside
the omnia_core container with live streaming output.

Key Features:
- Live line-by-line output streaming (like running in a terminal)
- Supports local and remote (SSH) execution modes
- Proper subprocess lifecycle management
- Returns structured results for pytest assertions

Usage:
    from automation_library.playbook_runner import PlaybookRunner

    runner = PlaybookRunner()
    result = runner.run("/omnia/src/playbooks/prepare_oim/prepare_oim.yml")
    assert result["success"], f"Playbook failed (rc={result['rc']})"
"""

from .functions import PlaybookRunner, run_playbook

from .vars import (
    DEFAULT_CONTAINER,
    DEFAULT_VERBOSITY,
    DEFAULT_TIMEOUT,
    LINE_WIDTH,
)

from .messages import (
    RUNNER_LOG_MSGS,
    RUNNER_ASSERT_MSGS,
)

__all__ = [
    "PlaybookRunner",
    "run_playbook",
    "DEFAULT_CONTAINER",
    "DEFAULT_VERBOSITY",
    "DEFAULT_TIMEOUT",
    "LINE_WIDTH",
    "RUNNER_LOG_MSGS",
    "RUNNER_ASSERT_MSGS",
]
