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
Build Stream — Cleanup Verification Tests.

TC_CL_002: Verify all build_stream containers removed
TC_CL_003: Verify service ports closed
TC_CL_004: Verify GitLab containers removed
"""

import pytest

from library.functions import (
    TestLogger,
    check_containers_removed,
    check_ports_closed,
    check_gitlab_container,
    check_gitlab_runner_container,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
)


# =============================================================================
# TC_CL_002: CONTAINERS REMOVED
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(1)
def test_containers_removed(host):
    """TC_CL_002: Verify all build_stream containers removed after cleanup."""
    tl = TestLogger(TEST_NAMES["containers_removed"], "TC_CL_002")
    result = check_containers_removed(host)

    if result["success"]:
        tl.passed(LOG["containers_removed_ok"], result.get("details", ""))
    else:
        tl.failed(
            LOG["containers_still_running"].format(
                count=len(result.get("still_running", []))
            ),
            f"Still running: {result.get('still_running', [])}",
        )

    assert result["success"], (
        f"Containers still running: {result.get('still_running', [])}"
    )


# =============================================================================
# TC_CL_003: PORTS CLOSED
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(2)
def test_ports_closed(host):
    """TC_CL_003: Verify service ports closed after cleanup."""
    tl = TestLogger(TEST_NAMES["ports_closed"], "TC_CL_003")
    result = check_ports_closed(host)

    if result["success"]:
        tl.passed(LOG["ports_closed_ok"], result.get("details", ""))
    else:
        tl.failed(
            LOG["ports_still_open"].format(
                count=len(result.get("still_open", []))
            ),
            f"Still open: {result.get('still_open', [])}",
        )

    assert result["success"], (
        f"Ports still open: {result.get('still_open', [])}"
    )


# =============================================================================
# TC_CL_004: GITLAB CONTAINERS REMOVED
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(3)
def test_gitlab_removed(host):
    """TC_CL_004: Verify GitLab containers removed after cleanup."""
    tl = TestLogger(TEST_NAMES["gitlab_removed"], "TC_CL_004")

    gitlab_result = check_gitlab_container(host)
    runner_result = check_gitlab_runner_container(host)

    still_running = []
    if gitlab_result["success"]:
        still_running.append("gitlab")
    if runner_result["success"]:
        still_running.append("gitlab-runner")

    if not still_running:
        tl.passed("All GitLab containers removed")
    else:
        tl.failed(
            f"{len(still_running)} GitLab container(s) still running",
            f"Still running: {still_running}",
        )

    assert not still_running, (
        f"GitLab containers still running: {still_running}"
    )
