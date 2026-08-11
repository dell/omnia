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
Repo Manager — Repo Status Verification Tests.

Validates repository status after full end-to-end deployment:
  TC_RM_009: Verify repo_status.yml exists and reports success
  TC_RM_010: Verify repositories are synced in Pulp
"""

import pytest

from library.functions import (
    TestLogger,
    check_repo_status_file,
    check_repos_synced,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(8)
def test_repo_status_file(host):
    """TC_RM_009: Verify repo_status.yml exists and reports success."""
    tc = TC["rm_repo_status_file"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_repo_status_file(host)

    if result.get("not_found"):
        tl.skipped(LOG["repo_status_not_found"])
        pytest.skip(LOG["repo_status_not_found"])

    if result["success"]:
        tl.passed(LOG["repo_status_ok"], result["details"])
    else:
        tl.failed(LOG["repo_status_failed"], result.get("error", ""))

    assert result["success"], ASSERT["repo_status_failed"].format(
        error=result.get("error", ""),
        status_path=result.get("status_path", ""),
    )


@pytest.mark.sanity
@pytest.mark.order(9)
def test_repos_synced(host):
    """TC_RM_010: Verify repositories are synced in Pulp."""
    tc = TC["rm_repos_synced"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_repos_synced(host)

    if result["success"]:
        tl.passed(
            LOG["repos_synced_ok"].format(count=result.get("count", 0)),
            result["details"],
        )
    else:
        tl.failed(
            LOG["repos_missing"].format(count=0),
            result.get("error", ""),
        )

    assert result["success"], result.get("error", result["details"])
