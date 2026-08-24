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
Telemetry Deploy — Playbook Deployment Test.

Test case:
    TC_DP_001: Deploy telemetry (execute/deploy)
    Runs: ansible-playbook telemetry.yml --tags execute
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
@pytest.mark.order(20)
def test_deploy_telemetry(host):
    """TC_DP_001: Run telemetry deploy playbook.

    Executes ``ansible-playbook telemetry.yml --tags execute`` which deploys
    all enabled sinks (Kafka, VictoriaMetrics, VictoriaLogs) and sources
    (iDRAC, LDMS, OME, etc.) based on telemetry_config.yml.
    """
    tc = TC["deploy_telemetry"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Running telemetry deploy playbook (--tags execute)")
    result = run_playbook(
        host=host,
        playbook=PLAYBOOK_ENTRY_POINT,
        workdir=PLAYBOOK_WORKDIR,
        tag="execute",
    )

    if result["rc"] == 0:
        tl.passed(
            LOG_MSGS["deploy_passed"],
            f"Exit code: {result['rc']}\n"
            f"Duration: {result.get('duration', 'N/A')}s",
        )
    else:
        output_lines = result.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-30:])
        tl.failed(
            LOG_MSGS["deploy_failed"],
            f"Exit code: {result['rc']}\n"
            f"Last output:\n{tail}",
        )

    assert result["rc"] == 0, ASSERT_MSGS["deploy_failed"].format(
        rc=result["rc"],
    )
