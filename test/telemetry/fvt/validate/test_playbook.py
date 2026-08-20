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
Telemetry Validate — Playbook Deployment Test.

Test case:
    TC_VL_001: Deploy telemetry (validate)
    Runs: ansible-playbook telemetry.yml --tags validate
"""

import pytest

from omnia_auto import TestLogger, run_playbook

from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(10)
def test_deploy_validate(host):
    """TC_VL_001: Run telemetry validation playbook.

    Executes ``ansible-playbook telemetry.yml --tags validate`` on the
    target host and verifies it exits with rc=0.

    This runs L1 (JSON schema) and L2 (cross-field logic) validation
    for all three telemetry input files:
    - telemetry_config.yml
    - telemetry_storage_config.yml
    - telemetry_packages.yml
    """
    tc = TC["deploy_validate"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Running telemetry validation playbook")
    result = run_playbook(
        host=host,
        playbook=PLAYBOOK_ENTRY_POINT,
        workdir=PLAYBOOK_WORKDIR,
        tag="validate",
    )

    if result["rc"] == 0:
        tl.passed(
            LOG_MSGS["validate_passed"],
            f"Exit code: {result['rc']}\n"
            f"Duration: {result.get('duration', 'N/A')}s\n"
            f"All input files validated (L1 + L2)",
        )
    else:
        output_lines = result.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-20:])
        tl.failed(
            LOG_MSGS["validate_failed"],
            f"Exit code: {result['rc']}\n"
            f"Last output:\n{tail}",
        )

    assert result["rc"] == 0, ASSERT_MSGS["validate_failed"].format(
        rc=result["rc"],
    )
