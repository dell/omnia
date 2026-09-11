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

Runs cleanup/cleanup_gitlab.yml with -e standalone_mode=true to remove
GitLab from the target host.  No --tags filter is applied so that all
plays execute.

The standalone_mode=true flag tells the playbook to use local paths
instead of requiring container-based paths.
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_gitlab_cleanup(host):
    """Run cleanup/cleanup_gitlab.yml -e standalone_mode=true."""
    tc = TC["deploy_gitlab_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(
        playbook="cleanup/cleanup_gitlab.yml",
        timeout=1800,
        extra_vars={"standalone_mode": True},
    )

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
        playbook="cleanup_gitlab.yml",
        tag="all",
        rc=result["rc"],
        duration=result["duration"],
    )
