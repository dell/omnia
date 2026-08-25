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
Telemetry Deploy — Playbook Execution.

Test cases:
    TC_DP_001: Deploy telemetry (full stack, no tags)
    TC_DP_002: Deploy telemetry (--tags deploy)
"""

import os

import pytest

from library.functions import TestLogger, run_playbook
from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)


def _get_deploy_tag():
    """Get deploy tag from OMNIA_DEPLOY_TAG env var.

    When run_validation.sh executes with a specific tag (e.g. deploy),
    it sets OMNIA_DEPLOY_TAG so the test knows which ansible tag to use.
    When empty, the playbook runs without tags (full stack).
    """
    return os.environ.get("OMNIA_DEPLOY_TAG", "")


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_telemetry(host):
    """Deploy telemetry playbook with the configured tag."""
    tag = _get_deploy_tag()
    if tag:
        tc = TC["deploy_deploy"]
        tl = TestLogger(tc["title"], tc["id"])
        tl.check(f"Running telemetry playbook --tags {tag}")
        result = run_playbook(tag=tag)
        tag_label = tag
    else:
        tc = TC["deploy_telemetry"]
        tl = TestLogger(tc["title"], tc["id"])
        tl.check("Running telemetry playbook (full stack)")
        result = run_playbook()
        tag_label = "(none)"

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
        tag=tag_label,
        rc=result["rc"],
    )
