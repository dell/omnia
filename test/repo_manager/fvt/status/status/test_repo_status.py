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
Repo Manager Status — Verification Tests.

Validates repo_status.yml generation after ``--tags status``.
References: src/repo_manager/playbooks/repo_operations/generate_repo_status.yml

  TC_ST_002: Verify Pulp container running (prerequisite)
  TC_ST_003: Verify repo_status.yml exists
  TC_ST_004: Verify repo_status.yml reports success with expected content
"""

import pytest

from library.functions import (
    TestLogger,
    check_pulp_container_running,
    check_repo_status_file,
)
from library.vars.common_vars import PULP_CONTAINER
from library.messages import TEST_NAMES, LOG_MSGS, ASSERT_MSGS


@pytest.mark.sanity
@pytest.mark.order(1)
def test_pulp_running_for_status(host):
    """TC_ST_002: Verify Pulp running (prerequisite for status)."""
    tl = TestLogger(TEST_NAMES["pulp_container_running"], "TC_ST_002")
    result = check_pulp_container_running(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["container_running"].format(container=PULP_CONTAINER),
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["container_not_running"].format(container=PULP_CONTAINER),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["container_not_running"].format(
        container=PULP_CONTAINER, status=result.get("status", "unknown"),
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_repo_status_exists(host):
    """TC_ST_003: Verify repo_status.yml exists."""
    tl = TestLogger(TEST_NAMES["repo_status_generated"], "TC_ST_003")
    result = check_repo_status_file(host)

    if result["success"]:
        tl.passed(LOG_MSGS["repo_status_ok"], result["details"])
    elif result.get("not_found"):
        tl.failed(LOG_MSGS["repo_status_not_found"], result.get("error", ""))
    else:
        tl.failed(LOG_MSGS["repo_status_failed"], result.get("error", ""))

    assert result["success"], ASSERT_MSGS["repo_status_failed"].format(
        error=result.get("error", ""),
        status_path=result.get("status_path", ""),
    )


@pytest.mark.functional
@pytest.mark.order(3)
def test_repo_status_content(host):
    """TC_ST_004: Verify repo_status.yml has expected content."""
    tl = TestLogger(TEST_NAMES["repo_status_success"], "TC_ST_004")
    result = check_repo_status_file(host)

    if not result["success"]:
        tl.failed(LOG_MSGS["repo_status_failed"], result.get("error", ""))
        assert False, ASSERT_MSGS["repo_status_check_failed"].format(
            error=result.get("error", ""),
        )

    data = result.get("data", {})

    # Validate expected keys from generate_local_repo_access.py
    expected_keys = [
        "cluster_os_type",
        "cluster_os_version",
    ]
    missing = [k for k in expected_keys if k not in data]

    details = result["details"]
    if missing:
        details += f"\n  Missing keys: {', '.join(missing)}"
        tl.failed(LOG_MSGS["repo_status_failed"], details)
        assert False, ASSERT_MSGS["repo_status_missing_keys"].format(
            missing_keys=", ".join(missing),
        )

    tl.passed(LOG_MSGS["repo_status_ok"], details)
