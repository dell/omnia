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
omnia-auto — Shared Test Automation Utilities for Omnia.

Provides formatting, host connectivity, playbook execution,
file synchronisation, and test reporting utilities.

Usage::

    import omnia_auto

    omnia_auto.configure(
        module_root  = os.path.dirname(__file__),
        config_file  = "test_config.yml",
        default_timeout = 3600,
    )

    from omnia_auto import TestLogger, TestReport, get_testinfra_host
"""

__version__ = "1.0.0"

# --- Central config ---
from .vars.common_vars import (
    configure,
    get_setting,
    init_module_root,
    get_module_root,
)

# --- Formatting ---
from .functions.formatting_func import (
    Colors,
    Symbols,
    log,
    set_debug_mode,
    set_verbose_mode,
    TestLogger,
    get_test_output,
    get_last_tc_id,
    add_session_result,
    get_session_results,
    clear_session_results,
    print_summary_table,
)

# --- Host / Config ---
from .functions.host_func import (
    get_testinfra_host,
    load_test_config,
    load_test_credentials,
    run_on_host,
    is_local_execution,
    encrypt_test_credentials,
    connection_params,
    read_remote_env,
    ensure_remote_dir,
    read_remote_yaml,
    read_yaml_key,
    resolve_domain_input_path,
)

# --- Report ---
from .functions.report_func import (
    TestReport,
    get_current_report,
    set_current_report,
)

# --- Runner ---
from .functions.runner_func import run_playbook

# --- Sync ---
from .functions.sync_func import clone_repo, sync_files

# --- Validation Runner ---
from .functions.validation_runner import ValidationRunner

__all__ = [
    "__version__",
    # Config
    "configure",
    "get_setting",
    "init_module_root",
    "get_module_root",
    # Formatting
    "Colors",
    "Symbols",
    "log",
    "set_debug_mode",
    "set_verbose_mode",
    "TestLogger",
    "get_test_output",
    "get_last_tc_id",
    "add_session_result",
    "get_session_results",
    "clear_session_results",
    "print_summary_table",
    # Host
    "get_testinfra_host",
    "load_test_config",
    "load_test_credentials",
    "run_on_host",
    "is_local_execution",
    "encrypt_test_credentials",
    "connection_params",
    "read_remote_env",
    "ensure_remote_dir",
    "read_remote_yaml",
    "read_yaml_key",
    "resolve_domain_input_path",
    # Report
    "TestReport",
    "get_current_report",
    "set_current_report",
    # Runner
    "run_playbook",
    # Sync
    "clone_repo",
    "sync_files",
    # Validation Runner
    "ValidationRunner",
]
