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
Orchestrator Rollback -- Deploy (reserved placeholder).

TC_RB_000: Verify orchestrator.yml --tags rollback fails with
           'not supported' message (rollback is reserved for future use).
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_rollback_not_supported(host):
    """TC_RB_000: Verify rollback tag fails with 'not supported' message."""
    tl = TestLogger(
        TEST_NAMES["deploy_rollback"], "TC_RB_000"
    )
    result = run_playbook(tag="rollback")

    # Rollback is expected to FAIL — it is a reserved placeholder.
    # The playbook should exit non-zero with "ROLLBACK NOT SUPPORTED".
    if not result["success"]:
        output = result.get("output", "") + result.get("error", "")
        if "ROLLBACK NOT SUPPORTED" in output:
            tl.passed(LOG["rollback_not_supported"])
            return
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"],
            ),
            "Rollback failed but without the expected 'ROLLBACK NOT SUPPORTED' message",
        )
        pytest.fail(
            "Rollback failed but did not produce the expected "
            "'ROLLBACK NOT SUPPORTED' message. Got: " + output[:500]
        )

    # If it succeeds, that is unexpected — rollback should always fail.
    tl.failed(
        LOG["playbook_success"].format(duration=result["duration"]),
        "Rollback should fail with 'ROLLBACK NOT SUPPORTED' but succeeded",
    )
    pytest.fail(
        "Rollback tag should fail with 'ROLLBACK NOT SUPPORTED' "
        "but the playbook succeeded (rc=0). Rollback is not supported "
        "in this release."
    )
