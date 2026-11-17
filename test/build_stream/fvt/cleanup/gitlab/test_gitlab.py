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
Cleanup GitLab — GitLab removed by build_stream.yml --tags cleanup.

Packages, the gitlab-runner container, quadlet and services, the GitLab URL,
directories, gitlab-ctl services and the HTTPS port. Every checked item is
printed on its own line with a check mark.
"""

import pytest

from library.functions import (
    TestLogger,
    check_gitlab_directories_removed,
    check_gitlab_packages_removed,
    check_gitlab_port_free,
    check_gitlab_runner_container_removed,
    check_gitlab_runner_quadlet_removed,
    check_gitlab_runner_services_stopped,
    check_gitlab_services_stopped,
    check_gitlab_url_not_accessible,
    report_check,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_ASSERT_MSGS as ASSERT


@pytest.mark.sanity
@pytest.mark.order(90101)
def test_gitlab_packages_removed(host):
    """Verify GitLab packages removed after cleanup."""
    tc = TC["gitlab_packages_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_packages_removed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="GitLab packages", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90102)
def test_gitlab_runner_container_removed(host):
    """Verify gitlab-runner container removed after cleanup."""
    tc = TC["gitlab_runner_container_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_container_removed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="gitlab-runner container", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90103)
def test_gitlab_runner_quadlet_removed(host):
    """Verify gitlab-runner quadlet file removed after cleanup."""
    tc = TC["gitlab_runner_quadlet_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_quadlet_removed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="gitlab-runner quadlet", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90104)
def test_gitlab_runner_services_stopped(host):
    """Verify GitLab runner services stopped after cleanup."""
    tc = TC["gitlab_runner_services_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_services_stopped(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="GitLab runner services", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90105)
def test_gitlab_url_not_accessible(host):
    """Verify GitLab URL not accessible after cleanup."""
    tc = TC["gitlab_url_not_accessible"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_url_not_accessible(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="GitLab URL", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90106)
def test_gitlab_directories_removed(host):
    """Verify GitLab directories removed after cleanup."""
    tc = TC["gitlab_directories_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_directories_removed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="GitLab directories", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90107)
def test_gitlab_services_stopped(host):
    """Verify all GitLab services stopped after cleanup."""
    tc = TC["gitlab_services_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_services_stopped(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="GitLab services", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90108)
def test_gitlab_port_free(host):
    """Verify GitLab HTTPS port is free after cleanup."""
    tc = TC["gitlab_port_free"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_port_free(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="GitLab HTTPS port", error=result["error"],
    )
