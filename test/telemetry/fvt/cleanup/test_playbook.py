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
Telemetry Cleanup — Playbook Deployment Test.

Test case:
    TC_CL_001: Deploy telemetry (cleanup)
    Runs: ansible-playbook telemetry.yml --tags cleanup
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
@pytest.mark.order(50)
def test_deploy_cleanup(host):
    """TC_CL_001: Run telemetry cleanup playbook.

    Executes ``ansible-playbook telemetry.yml --tags cleanup`` which removes
    all telemetry sources, sinks, and associated K8s resources from the
    telemetry namespace.
    """
    tc = TC["deploy_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Running telemetry cleanup playbook (--tags cleanup)")
    result = run_playbook(
        host=host,
        playbook=PLAYBOOK_ENTRY_POINT,
        workdir=PLAYBOOK_WORKDIR,
        tag="cleanup",
    )

    if result["rc"] == 0:
        tl.passed(
            LOG_MSGS["cleanup_passed"],
            f"Exit code: {result['rc']}\n"
            f"Duration: {result.get('duration', 'N/A')}s",
        )
    else:
        output_lines = result.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-30:])
        tl.failed(
            LOG_MSGS["cleanup_failed"],
            f"Exit code: {result['rc']}\n"
            f"Last output:\n{tail}",
        )

    assert result["rc"] == 0, ASSERT_MSGS["cleanup_failed"].format(
        rc=result["rc"],
    )
