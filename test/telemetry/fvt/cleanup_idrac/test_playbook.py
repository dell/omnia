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
Telemetry Cleanup iDRAC --- Playbook Execution.

Covers the ``cleanup_idrac`` Ansible tag which removes iDRAC telemetry
resources without affecting sinks or other sources.

Test cases:
    TEL_FVT_CLEANUP_IDRAC_E001: Cleanup iDRAC (--tags cleanup_idrac)
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
@pytest.mark.deploy
@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_cleanup_idrac(host):
    """TEL_FVT_CLEANUP_IDRAC_E001: Run ``telemetry.yml --tags cleanup_idrac``."""
    tc = TC["deploy_cleanup_idrac"]
    tl = TestLogger(tc["title"], tc["id"])
    tl.check("Running telemetry playbook --tags cleanup_idrac")

    result = run_playbook(tag="cleanup_idrac")

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
        playbook="telemetry.yml", tag="cleanup_idrac", rc=result["rc"],
    )
