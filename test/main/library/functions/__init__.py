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
Omnia Main — Functions

Common utilities come from the omnia_auto package.
Module-specific functions remain here.
"""

# --- Common (from omnia_auto package) ---
from omnia_auto import (
    Colors,
    Symbols,
    log,
    set_debug_mode,
    TestLogger,
    get_test_output,
    get_testinfra_host,
    load_test_config,
    load_test_credentials,
    get_module_root,
    run_on_host,
    is_local_execution,
    TestReport,
    get_current_report,
    set_current_report,
)

# --- Omnia Main verification ---
from .omnia_main_func import (
    run_omnia_cmd,
    run_omnia_cmd_expect_error,
    check_env_file_installed,
    check_profile_drop_in,
    check_env_vars_loaded,
    check_venv_created,
    check_ansible_available,
    check_base_dirs_created,
    check_activate_helper,
    check_domain_log_dirs,
    check_domain_input_staged,
    check_help_output,
    check_error_contains,
)

# --- Validation ---
from .validation_func import (
    validate_test_config,
    validate_all,
    ConfigValidationError,
)

__all__ = [
    "Colors",
    "Symbols",
    "log",
    "set_debug_mode",
    "TestLogger",
    "get_test_output",
    "get_testinfra_host",
    "load_test_config",
    "load_test_credentials",
    "get_module_root",
    "run_on_host",
    "is_local_execution",
    "TestReport",
    "get_current_report",
    "set_current_report",
    "run_omnia_cmd",
    "run_omnia_cmd_expect_error",
    "check_env_file_installed",
    "check_profile_drop_in",
    "check_env_vars_loaded",
    "check_venv_created",
    "check_ansible_available",
    "check_base_dirs_created",
    "check_activate_helper",
    "check_domain_log_dirs",
    "check_domain_input_staged",
    "check_help_output",
    "check_error_contains",
    "validate_test_config",
    "validate_all",
    "ConfigValidationError",
]
