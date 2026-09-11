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
GitLab Cleanup — Comprehensive Verification.

Validates that --tags gitlab_cleanup removed all GitLab artifacts:
  GitLab packages uninstalled (gitlab-ce)
  gitlab-runner container removed
  gitlab-runner quadlet file removed
  GitLab runner services stopped
  GitLab URL not accessible
  GitLab directories removed (/etc/gitlab, /var/opt/gitlab, etc.)
  All GitLab services stopped
  GitLab HTTPS port free
"""

import pytest

from library.functions import (
    TestLogger,
    check_gitlab_packages_removed,
    check_gitlab_runner_container_removed,
    check_gitlab_runner_quadlet_removed,
    check_gitlab_runner_services_stopped,
    check_gitlab_url_not_accessible,
    check_gitlab_directories_removed,
    check_gitlab_services_stopped,
    check_gitlab_port_free,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_gitlab_packages_removed(host):
    """Verify GitLab packages removed after cleanup."""
    tc = TC["gitlab_packages_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_packages_removed(host)

    if result["success"]:
        tl.passed(
            LOG["packages_removed"].format(
                packages=", ".join(result["removed"]),
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["packages_still_present"].format(
                packages=", ".join(result["still_installed"]),
            ),
            result["details"],
        )

    assert result["success"], ASSERT["packages_still_present"].format(
        packages=", ".join(result["still_installed"]),
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_gitlab_runner_container_removed(host):
    """Verify gitlab-runner container removed after cleanup."""
    tc = TC["gitlab_runner_container_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_container_removed(host)

    if result["success"]:
        tl.passed(LOG["runner_container_removed"], result["details"])
    else:
        tl.failed(
            LOG["runner_container_still_exists"],
            result.get("error", ""),
        )

    assert result["success"], ASSERT["runner_container_still_exists"]


@pytest.mark.sanity
@pytest.mark.order(3)
def test_gitlab_runner_quadlet_removed(host):
    """Verify gitlab-runner quadlet file removed after cleanup."""
    tc = TC["gitlab_runner_quadlet_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_quadlet_removed(host)

    if result["success"]:
        tl.passed(
            LOG["quadlet_removed"].format(path=result["path"]),
            result["details"],
        )
    else:
        tl.failed(
            LOG["quadlet_still_exists"].format(path=result["path"]),
            result.get("error", ""),
        )

    assert result["success"], result.get("error", "Quadlet not removed")


@pytest.mark.sanity
@pytest.mark.order(4)
def test_gitlab_runner_services_stopped(host):
    """Verify GitLab runner services stopped after cleanup."""
    tc = TC["gitlab_runner_services_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_services_stopped(host)

    lines = []
    for svc in result["results"]:
        status = (
            "active (FAIL)" if svc["is_active"] else "inactive (OK)"
        )
        lines.append(f"  {svc['name']}: {status}")
    details = "\n".join(lines)

    if result["success"]:
        tl.passed(result["details"], details)
    else:
        active = [
            s["name"] for s in result["results"] if s["is_active"]
        ]
        tl.failed(
            LOG["runner_services_still_active"].format(
                active=", ".join(active),
            ),
            details,
        )

    assert result["success"], result.get(
        "error", "Runner services still active"
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_gitlab_url_not_accessible(host):
    """Verify GitLab URL not accessible after cleanup."""
    tc = TC["gitlab_url_not_accessible"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_url_not_accessible(host)

    if result["success"]:
        tl.passed(LOG["url_not_accessible_ok"], result["details"])
    else:
        tl.failed(
            LOG["url_still_accessible"].format(
                url=result["url"], code=result["http_code"],
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["gitlab_url_still_accessible"].format(
        url=result.get("url", "unknown"),
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_gitlab_directories_removed(host):
    """Verify GitLab directories removed after cleanup."""
    tc = TC["gitlab_directories_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_directories_removed(host)

    if result["success"]:
        tl.passed(
            LOG["directories_removed"].format(
                count=len(result["removed"]),
                total=len(result["removed"]),
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["directories_still_exist"].format(
                dirs=", ".join(result["still_exist"]),
            ),
            result["details"],
        )

    assert result["success"], ASSERT["gitlab_dirs_still_exist"].format(
        dirs=", ".join(result.get("still_exist", [])),
    )


@pytest.mark.sanity
@pytest.mark.order(7)
def test_gitlab_services_stopped(host):
    """Verify all GitLab services stopped after cleanup."""
    tc = TC["gitlab_services_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_services_stopped(host)

    if result["success"]:
        tl.passed(LOG["services_stopped"], result["details"])
    else:
        tl.failed(
            LOG["services_still_running"].format(
                services=", ".join(result["still_running"]),
            ),
            result["details"],
        )

    assert result["success"], result.get(
        "error", "GitLab services still running"
    )


@pytest.mark.sanity
@pytest.mark.order(8)
def test_gitlab_port_free(host):
    """Verify GitLab HTTPS port is free after cleanup."""
    tc = TC["gitlab_port_free"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_port_free(host)

    if result["success"]:
        tl.passed(
            LOG["port_free"].format(port=result["port"]),
            result["details"],
        )
    else:
        tl.failed(
            LOG["port_in_use"].format(port=result["port"]),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["gitlab_port_in_use"].format(
        port=result.get("port", "unknown"),
    )
