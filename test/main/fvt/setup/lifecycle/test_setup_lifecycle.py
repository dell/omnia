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

"""Omnia Main extended setup execution and postcondition verification."""

import pytest

from library.functions import TestLogger, resolve_runtime_paths, run_on_host
from library.functions.omnia_main_func import (
    check_ansible_available,
    check_env_file_installed,
    check_profile_drop_in,
    check_venv_created,
    is_running_from_omnia_venv,
    run_omnia_cmd,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT
from library.messages import TEST_LOG_MSGS as LOG
from library.vars import CMDS
from library.vars import TEST_CASES as TC
from library.vars.common_vars import PROFILE_DROP_IN, SYSTEM_ENV_FILE

_SKIP_VENV_MSG = (
    "Skipped: running from omnia production venv — "
    "cannot replace the active interpreter"
)


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(1)
def test_deploy_setup_deps_only(host):
    """Run the extended dependency-only setup workflow."""
    tc = TC["deploy_setup_deps_only"]
    tl = TestLogger(tc["title"], tc["id"])

    if is_running_from_omnia_venv(host):
        tl.passed(_SKIP_VENV_MSG)
        pytest.skip(_SKIP_VENV_MSG)

    venv_path = resolve_runtime_paths(host)["venv_path"]
    venv_check = run_on_host(
        host,
        CMDS["dir_exists"].format(path=f"{venv_path}/bin")
    )
    if "exists" in venv_check.stdout:
        message = f"Venv already exists at {venv_path} — setup rerun not required"
        tl.passed(message)
        pytest.skip(message)

    result = run_omnia_cmd(host, "omnia_sh_setup_venv")
    tl.bind_result(result)
    if result["success"]:
        tl.passed(LOG["exec_setup_ok"].format(
            rc=result["rc"], duration=result["duration"]
        ))
    else:
        tl.failed(LOG["exec_setup_failed"].format(
            rc=result["rc"], duration=result["duration"]
        ))
    assert result["success"], ASSERT["exec_setup_failed"].format(rc=result["rc"])


@pytest.mark.functional
@pytest.mark.order(11)
def test_verify_venv_exists(host):
    """Verify the extended setup workflow created a venv with Ansible."""
    tc = TC["verify_venv_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    venv_path = resolve_runtime_paths(host)["venv_path"]
    result = check_venv_created(host)
    ansible_result = check_ansible_available(host)
    fields = {
        "Virtual environment": venv_path,
        "Venv status": result.get("details", result.get("error", "unknown")),
        "Ansible": ansible_result.get(
            "details", ansible_result.get("error", "missing")
        ),
    }
    if result["success"] and ansible_result["success"]:
        tl.passed_fields("Venv and Ansible are available after setup", fields)
    else:
        tl.failed_fields("Venv or Ansible verification failed after setup", fields)
    assert result["success"], ASSERT["venv_missing"]
    assert ansible_result["success"], ASSERT["ansible_missing"]


@pytest.mark.functional
@pytest.mark.order(12)
def test_verify_env_installed(host):
    """Verify the extended setup workflow installed system environment files."""
    tc = TC["verify_env_installed"]
    tl = TestLogger(tc["title"], tc["id"])
    env_result = check_env_file_installed(host)
    profile_result = check_profile_drop_in(host)
    fields = {
        "Environment file": (
            f"{SYSTEM_ENV_FILE} (present)" if env_result["success"]
            else env_result.get("error", "missing")
        ),
        "Profile drop-in": (
            f"{PROFILE_DROP_IN} (present)" if profile_result["success"]
            else profile_result.get("error", "missing")
        ),
    }
    if env_result["success"] and profile_result["success"]:
        tl.passed_fields("Required environment files are installed", fields)
    else:
        tl.failed_fields("Required environment files are not installed", fields)
    assert env_result["success"], ASSERT["env_file_missing"]
    assert profile_result["success"], ASSERT["profile_missing"]
