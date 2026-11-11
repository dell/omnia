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
Repo Manager Execute — Artifact Verification.

Validates that --tags execute synced and published all expected artifacts:
  Software download status per architecture
  Per-software package status
  All RPM repositories synced
  All RPM distributions published
  All container repositories synced
  All file repositories synced
  RPM content reachable via HTTPS
  Software packages present in Pulp
"""

import pytest

from library.functions import (
    TestLogger,
    check_software_download_status,
    check_per_software_package_status,
    check_pulp_repositories_synced,
    check_pulp_distributions_published,
    check_container_repos_synced,
    check_file_repos_synced,
    check_pulp_content_accessible,
    check_software_packages_in_pulp,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(7)
def test_software_download_status(host):
    """Verify software.csv download status per architecture."""
    tc = TC["software_download_status"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_software_download_status(host)

    if result["success"]:
        tl.passed(LOG["software_download_ok"], result["details"])
    else:
        tl.failed(LOG["software_download_failed"], result["details"])

    assert result["success"], ASSERT["software_download_failed"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(8)
def test_per_software_package_status(host):
    """Verify per-software status.csv for individual package download results."""
    tc = TC["per_software_package_status"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_per_software_package_status(host)

    if result["success"]:
        tl.passed(LOG["per_software_pkg_ok"], result["details"])
    else:
        tl.failed(LOG["per_software_pkg_failed"], result["details"])

    assert result["success"], ASSERT["per_software_pkg_failed"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(9)
def test_pulp_repositories_synced(host):
    """Verify all RPM repositories have latest_version_href (sync indicator)."""
    tc = TC["pulp_repositories_synced"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_repositories_synced(host)

    if result["success"]:
        tl.passed(LOG["pulp_repos_synced"], result["details"])
    else:
        tl.failed(LOG["pulp_repos_not_synced"], result["details"])

    assert result["success"], ASSERT["pulp_repos_not_synced"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(10)
def test_pulp_distributions_published(host):
    """Verify all RPM distributions are published with repository attachment."""
    tc = TC["pulp_distributions_published"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_distributions_published(host)

    if result["success"]:
        tl.passed(LOG["pulp_distributions_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_distributions_missing"], result["details"])

    assert result["success"], ASSERT["pulp_distributions_missing"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(11)
def test_container_repos_synced(host):
    """Verify all container image repositories are synced."""
    tc = TC["container_repos_synced"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_container_repos_synced(host)

    if result["success"]:
        tl.passed(LOG["container_repos_synced"], result["details"])
    else:
        tl.failed(LOG["container_repos_not_synced"], result["details"])

    assert result["success"], ASSERT["container_repos_not_synced"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(12)
def test_file_repos_synced(host):
    """Verify all file repositories (tarball, git, etc.) are synced."""
    tc = TC["file_repos_synced"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_file_repos_synced(host)

    if result["success"]:
        tl.passed(LOG["file_repos_synced"], result["details"])
    else:
        tl.failed(LOG["file_repos_not_synced"], result["details"])

    assert result["success"], ASSERT["file_repos_not_synced"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(13)
def test_pulp_content_accessible(host):
    """Verify RPM content is reachable via HTTPS (repomd.xml check)."""
    tc = TC["pulp_content_accessible"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_content_accessible(host)

    if result["success"]:
        tl.passed(LOG["pulp_content_accessible"], result["details"])
    else:
        tl.failed(LOG["pulp_content_not_accessible"], result["details"])

    assert result["success"], ASSERT["pulp_content_not_accessible"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(14)
def test_software_packages_in_pulp(host):
    """Verify all RPM packages from software_config.json are present in Pulp."""
    tc = TC["software_packages_in_pulp"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_software_packages_in_pulp(host)

    if result["success"]:
        tl.passed(LOG["software_packages_ok"], result["details"])
    else:
        tl.failed(LOG["software_packages_missing"], result["details"])

    assert result["success"], ASSERT["software_packages_missing"]
