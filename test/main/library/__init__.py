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
Test Automation Library for omnia main (omnia.sh / omnia-cli).

Common utilities (formatting, host, report, runner) come from
the ``omnia_auto`` package.  Module-specific functions (omnia_main,
validation) remain here.

Structure:
    functions/   - Module-specific verification + re-exports from omnia_auto
    vars/        - Module-specific constants, commands, paths
    messages/    - Test names, log/assert messages
"""

# Common (from omnia_auto via functions/__init__.py re-exports)
from .functions import (
    get_testinfra_host,
    is_local_execution,
    load_test_config,
    load_test_credentials,
    TestLogger,
    TestReport,
    get_current_report,
    set_current_report,
    get_test_output,
    validate_all,
    ConfigValidationError,
)

__all__ = [
    "get_testinfra_host",
    "is_local_execution",
    "load_test_config",
    "load_test_credentials",
    "TestLogger",
    "TestReport",
    "get_current_report",
    "set_current_report",
    "get_test_output",
    "validate_all",
    "ConfigValidationError",
]
