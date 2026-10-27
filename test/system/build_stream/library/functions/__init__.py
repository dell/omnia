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

"""BuildStream system test — public function API for test files.

Test files import only from here (never from omnia_auto directly). Each
scenario exposes a precheck, its entry point (exec) and its verifiers.
"""

from omnia_auto import TestLogger, load_test_config, log

from .auto_cleanup_func import retention_settings, run_auto_cleanup, verify_auto_cleanup
from .cleanup_func import CLEANUP_VERIFIERS, run_full_cleanup, verify_domain_cleanup
from .command_func import run_omnia_sh
from .config_func import (
    ConfigValidationError,
    cleanup_plan,
    installation_settings,
    validate_test_config,
)
from .cadence_func import (
    is_cadence_enabled,
    verify_cadence_disable_live,
    verify_cadence_reenable_live,
)
from .log_func import failure_fields, mark, skip_test
from .installation_func import (
    failure_summary,
    run_build_pipeline,
    run_build_stream_installation,
    run_cadence_pipeline,
    run_deploy_pipeline,
    verify_build_stream_services,
    verify_gitlab_repository,
)
from .precheck_func import (
    precheck_auto_cleanup,
    precheck_cleanup,
    precheck_installation,
    precheck_prepare_base,
)
from .readiness_func import (
    verify_image_build_manager_ready,
    verify_orchestrator_ready,
    verify_repo_manager_ready,
)
from .state_func import clear_run_state, load_run_state, save_run_state

__all__ = [
    "CLEANUP_VERIFIERS",
    "ConfigValidationError",
    "TestLogger",
    "cleanup_plan",
    "clear_run_state",
    "failure_fields",
    "failure_summary",
    "installation_settings",
    "is_cadence_enabled",
    "load_run_state",
    "load_test_config",
    "log",
    "mark",
    "precheck_auto_cleanup",
    "precheck_cleanup",
    "precheck_installation",
    "precheck_prepare_base",
    "retention_settings",
    "run_auto_cleanup",
    "run_build_pipeline",
    "run_build_stream_installation",
    "run_cadence_pipeline",
    "run_deploy_pipeline",
    "run_full_cleanup",
    "run_omnia_sh",
    "save_run_state",
    "skip_test",
    "validate_test_config",
    "verify_auto_cleanup",
    "verify_build_stream_services",
    "verify_cadence_disable_live",
    "verify_cadence_reenable_live",
    "verify_domain_cleanup",
    "verify_gitlab_repository",
    "verify_image_build_manager_ready",
    "verify_orchestrator_ready",
    "verify_repo_manager_ready",
]
