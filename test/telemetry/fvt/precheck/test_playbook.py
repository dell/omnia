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
Telemetry Precheck — Playbook Execution.

Test cases:
    TC_PC_001: Deploy telemetry (--tags precheck)
"""

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions import run_playbook


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_precheck(host):
    """TC_PC_001: Deploy telemetry (--tags precheck)."""
    tc = TC["deploy_precheck"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Running telemetry playbook --tags precheck")
    result = run_playbook(tag="precheck")

    if result["success"]:
        tl.passed(
            LOG_MSGS["playbook_success"].format(
                duration=f"{result['duration']:.1f}s",
            ),
            f"rc={result['rc']}",
        )
    else:
        tl.failed(
            LOG_MSGS["playbook_failed"].format(
                rc=result["rc"],
                duration=f"{result['duration']:.1f}s",
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["playbook_failed"].format(
        playbook="telemetry.yml",
        tag="precheck",
        rc=result["rc"],
    )
