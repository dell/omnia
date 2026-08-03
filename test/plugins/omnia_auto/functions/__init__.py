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

"""omnia-auto — Functions"""

# --- Formatting ---
from .formatting_func import (
    Colors,
    Symbols,
    log,
    set_debug_mode,
    TestLogger,
    get_test_output,
    add_session_result,
    get_session_results,
    clear_session_results,
    print_summary_table,
)

# --- Host / Config ---
from .host_func import (
    get_testinfra_host,
    load_test_config,
    load_test_credentials,
    run_on_host,
    is_local_execution,
    encrypt_test_credentials,
    connection_params,
    read_remote_env,
    ensure_remote_dir,
    resolve_domain_input_path,
)

# --- Report ---
from .report_func import (
    TestReport,
    get_current_report,
    set_current_report,
)

# --- Runner ---
from .runner_func import run_playbook

# --- Sync ---
from .sync_func import clone_repo, sync_files
