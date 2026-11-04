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
Execute GitLab Server — GitLab CE on the GitLab host.

Packages, reachability, URL, services, resources and tuning that
build_stream.yml --tags execute deploys.
"""

import pytest

from library.functions import (
    TestLogger,
    check_gitlab_packages_installed,
    check_gitlab_resources,
    check_gitlab_server_reachable,
    check_gitlab_services_running,
    check_gitlab_url_accessible,
    check_puma_workers,
    check_sidekiq_concurrency,
    report_check,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_ASSERT_MSGS as ASSERT


@pytest.mark.sanity
@pytest.mark.order(40101)
def test_gitlab_packages_installed(host):
    """Verify GitLab packages installed on GitLab server."""
    tc = TC["gitlab_packages_installed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_packages_installed(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["packages_missing"].format(
            packages=", ".join(result["missing"]),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40102)
def test_gitlab_server_reachable(host):
    """Verify GitLab server reachable from OIM host."""
    tc = TC["gitlab_server_reachable"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_server_reachable(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["server_unreachable"].format(
            host=result.get("gitlab_host", "unknown"),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40103)
def test_gitlab_url_accessible(host):
    """Verify GitLab URL accessible from OIM server."""
    tc = TC["gitlab_url_accessible"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_url_accessible(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["url_not_accessible"].format(
            url=result.get("url", "unknown"),
            code=result.get("http_code", 0),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40104)
def test_gitlab_server_running(host):
    """Verify GitLab server is running and accessible."""
    tc = TC["gitlab_server_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_url_accessible(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["url_not_accessible"].format(
            url=result.get("url", "unknown"),
            code=result.get("http_code", 0),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40105)
def test_gitlab_services_running(host):
    """Verify all GitLab services running via gitlab-ctl status."""
    tc = TC["gitlab_services_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_services_running(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["services_not_running"].format(
            services=", ".join(result.get("not_running", [])),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40106)
def test_gitlab_resources(host):
    """Verify GitLab server meets minimum resource requirements."""
    tc = TC["gitlab_resources"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_resources(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["resources_insufficient"].format(
            failed=result.get("error", ""),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40107)
def test_puma_workers(host):
    """Verify puma workers configured correctly in gitlab.rb."""
    tc = TC["puma_workers"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_puma_workers(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["puma_workers_mismatch"].format(
            expected=result["expected"], actual=result["actual"],
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40108)
def test_sidekiq_concurrency(host):
    """Verify sidekiq concurrency configured correctly in gitlab.rb."""
    tc = TC["sidekiq_concurrency"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_sidekiq_concurrency(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["sidekiq_mismatch"].format(
            expected=result["expected"], actual=result["actual"],
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )
