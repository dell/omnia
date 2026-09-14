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
Omnia Main Setup — Deploy.

MAIN_FVT_SETUP_E001: Deploy omnia.sh --setup-venv --deps-only
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    resolve_runtime_paths,
    run_omnia_cmd,
)
from library.vars import CMDS
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_setup_venv(host):
    """MAIN_FVT_SETUP_E001: Deploy omnia.sh --setup-venv --deps-only."""
    venv_path = resolve_runtime_paths(host)["venv_path"]

    # Check if venv already exists - skip deploy if it does
    venv_exists_cmd = CMDS["dir_exists"].format(path=f"{venv_path}/bin")
    venv_check = host.run(venv_exists_cmd)

    tc = TC["deploy_setup_venv"]
    tl = TestLogger(tc["title"], tc["id"])

    if "exists" in venv_check.stdout:
        tl.skipped_fields("Setup execution is not required", {
            "Virtual environment": venv_path,
            "Reason": "already exists",
        })
        pytest.skip(f"Venv already exists at {venv_path} - skipping deploy")

    result = run_omnia_cmd(host, "omnia_sh_setup_venv")
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["setup_success"].format(
            duration=result["duration"]
        ), {
            "Command": "omnia.sh --setup-venv --deps-only",
            "Virtual environment": venv_path,
            "Return code": result["rc"],
            "Duration": f"{result['duration']:.1f}s",
        })
    else:
        tl.failed_fields(LOG["setup_failed"].format(
            rc=result["rc"], duration=result["duration"]
        ), {
            "Command": "omnia.sh --setup-venv --deps-only",
            "Return code": result["rc"],
            "Error": result.get("error", "See command output"),
        })

    assert result["success"], ASSERT["setup_failed"].format(
        rc=result["rc"],
        duration=result["duration"],
    )
