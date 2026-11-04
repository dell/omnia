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
Execute GitLab Runner — gitlab-runner container, quadlet and services.
"""

import pytest

from library.functions import (
    TestLogger,
    check_gitlab_runner_container,
    check_gitlab_runner_quadlet,
    check_gitlab_runner_services,
    report_check,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_ASSERT_MSGS as ASSERT


@pytest.mark.sanity
@pytest.mark.order(40201)
def test_gitlab_runner_container(host):
    """Verify gitlab-runner container running on GitLab server."""
    tc = TC["gitlab_runner_container"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_container(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["runner_container_missing"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40202)
def test_gitlab_runner_quadlet_exists(host):
    """Verify gitlab-runner quadlet file exists on GitLab server."""
    tc = TC["gitlab_runner_quadlet_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_quadlet(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["quadlet_missing"].format(path=result["path"])
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40203)
def test_gitlab_runner_services_status(host):
    """Verify GitLab runner services running on GitLab server."""
    tc = TC["gitlab_runner_services_status"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_services(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["runner_services_failed"].format(
            failed=result.get("error", ""),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40204)
def test_gitlab_runner_running(host):
    """Verify GitLab runner container is running."""
    tc = TC["gitlab_runner_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_container(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["runner_container_missing"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )
