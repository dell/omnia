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
Telemetry Precheck — Playbook Deployment Test.

Test case:
    TC_PC_001: Deploy telemetry (precheck)
    Runs: ansible-playbook telemetry.yml --tags precheck
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
@pytest.mark.order(1)
def test_deploy_precheck(host):
    """TC_PC_001: Run telemetry precheck playbook.

    Executes ``ansible-playbook telemetry.yml --tags precheck`` on the
    target host and verifies it exits with rc=0.
    """
    tc = TC["deploy_precheck"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Running telemetry precheck playbook")
    result = run_playbook(
        host=host,
        playbook=PLAYBOOK_ENTRY_POINT,
        workdir=PLAYBOOK_WORKDIR,
        tag="precheck",
    )

    if result["rc"] == 0:
        tl.passed(
            LOG_MSGS["precheck_passed"],
            f"Exit code: {result['rc']}\n"
            f"Duration: {result.get('duration', 'N/A')}s",
        )
    else:
        # Extract last 20 lines for failure context
        output_lines = result.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-20:])
        tl.failed(
            LOG_MSGS["precheck_failed"],
            f"Exit code: {result['rc']}\n"
            f"Last output:\n{tail}",
        )

    assert result["rc"] == 0, ASSERT_MSGS["precheck_failed"].format(
        rc=result["rc"],
    )
