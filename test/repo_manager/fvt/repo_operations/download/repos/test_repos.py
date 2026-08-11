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
Repo Operations — Download — Repository Verification Tests.

Validates repository state after ``--tags download``.
References: src/repo_manager/roles/parse_and_download/
            src/repo_manager/playbooks/repo_operations/download.yml

  TC_DL_002: Verify software_config.json is valid
  TC_DL_003: Verify repos are synced in Pulp
  TC_DL_004: Verify repo_status.yml generated after download
"""

import pytest

from library.functions import (
    TestLogger,
    check_software_config_valid,
    check_repos_synced,
    check_repo_status_file,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_software_config_valid(host):
    """TC_DL_002: Verify software_config.json is valid."""
    tc = TC["software_config_valid"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_software_config_valid(host)

    if result["success"]:
        tl.passed(LOG["software_config_valid_ok"], result["details"])
    else:
        tl.failed(LOG["software_config_invalid"], result.get("error", ""))

    assert result["success"], result.get("error", result["details"])


@pytest.mark.functional
@pytest.mark.order(2)
def test_repos_synced(host):
    """TC_DL_003: Verify repos are synced in Pulp after download."""
    tc = TC["dl_repos_synced"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_repos_synced(host)

    if result["success"]:
        tl.passed(
            LOG["repos_synced_ok"].format(count=result["count"]),
            result["details"],
        )
    else:
        tl.failed(
            LOG["repos_missing"].format(count=result["count"]),
            result.get("error", ""),
        )

    assert result["success"], result.get("error", result["details"])


@pytest.mark.sanity
@pytest.mark.order(3)
def test_repo_status_generated(host):
    """TC_DL_004: Verify repo_status.yml generated after download."""
    tc = TC["dl_repo_status_generated"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_repo_status_file(host)

    if result["success"]:
        tl.passed(LOG["repo_status_ok"], result["details"])
    else:
        if result.get("not_found"):
            tl.failed(LOG["repo_status_not_found"], result.get("error", ""))
        else:
            tl.failed(LOG["repo_status_failed"], result.get("error", ""))

    assert result["success"], ASSERT["repo_status_failed"].format(
        error=result.get("error", ""),
        status_path=result.get("status_path", ""),
    )
