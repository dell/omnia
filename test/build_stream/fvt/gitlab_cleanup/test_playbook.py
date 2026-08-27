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
Build Stream GitLab Cleanup — Playbook Deployment.

Deploys build_stream.yml --tags gitlab_cleanup and verifies the
playbook completes successfully. Used in regression runs to execute
the cleanup before verifying results.
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.vars import TEST_CASES as TC
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.regression
@pytest.mark.order(0)
def test_deploy_gitlab_cleanup(host):
    """Deploy build_stream playbook with --tags gitlab_cleanup."""
    tc = TC["deploy_gitlab_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(tag="gitlab_cleanup", timeout=1800)

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=result["duration"],
        ))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See playbook output above"),
        )

    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="gitlab_cleanup",
        rc=result["rc"],
        duration=result["duration"],
    )
