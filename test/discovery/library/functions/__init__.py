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
Discovery — Functions

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
    run_playbook as _run_playbook,
)
from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

# --- Discovery verification ---
from .discovery_func import (
    check_input_config_exists,
    check_network_spec_exists,
    check_credentials_present,
    check_output_dir_exists,
    check_pxe_mapping_created,
    check_pxe_mapping_columns,
    check_pxe_mapping_has_rows,
    check_discovery_report_created,
    check_pxe_mapping_symlink,
    check_clone_status,
)

# --- Validation ---
from .validation_func import (
    validate_test_config,
    validate_all,
    ConfigValidationError,
)


def run_playbook(extra_vars=None, **kwargs):
    """Wrapper that injects module-specific playbook and workdir."""
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        extra_vars=extra_vars,
        **kwargs,
    )
