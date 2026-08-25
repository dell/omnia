# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Download scenario verification tests.

TC_RM_DL_000: Deploy repo_manager --tags download
TC_RM_DL_001: Verify repo_status.yml generated
TC_RM_DL_002: Verify overall_status is success
TC_RM_DL_003: Verify slurm_custom repo present
TC_RM_DL_004: Verify epel repo present
TC_RM_DL_005: Verify x86_64 repositories present
TC_RM_DL_006: Verify file repos present
TC_RM_DL_007: Verify software.csv download status per architecture
TC_RM_DL_008: Verify per-software status.csv for individual package download results
TC_RM_DL_009: Verify all RPM repositories have latest_version_href (sync indicator)
TC_RM_DL_010: Verify all RPM distributions are published with repository attachment
TC_RM_DL_011: Verify all container image repositories are synced
TC_RM_DL_012: Verify all file repositories (tarball, git, etc.) are synced
TC_RM_DL_013: Verify RPM content is reachable via HTTPS (repomd.xml check)
TC_RM_DL_014: Verify all RPM packages from software_config.json are present in Pulp
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_repo_status_exists,
    check_repo_status_success,
    check_repo_status_has_repo,
    check_repo_status_has_file_repo,
    check_software_download_status,
    check_per_software_package_status,
    check_pulp_repositories_synced,
    check_pulp_distributions_published,
    check_container_repos_synced,
    check_file_repos_synced,
    check_pulp_content_accessible,
    check_software_packages_in_pulp,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_download(host):
    """TC_RM_DL_000: Deploy repo_manager --tags download."""
    tl = TestLogger(TEST_NAMES["repo_status_exists"], "TC_RM_DL_000")
    result = run_playbook(tag="download")

    if result["success"]:
        tl.passed("repo_manager --tags download completed", result.get("details", ""))
    else:
        tl.failed("repo_manager --tags download failed", result.get("error", ""))

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_repo_status_exists(host):
    """TC_RM_DL_001: Verify repo_status.yml generated."""
    tl = TestLogger(TEST_NAMES["repo_status_exists"], "TC_RM_DL_001")
    result = check_repo_status_exists(host)

    if result["success"]:
        tl.passed(LOG["repo_status_exists"], result["details"])
    else:
        tl.failed(LOG["repo_status_missing"], result["details"])

    assert result["success"], ASSERT["repo_status_missing"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_repo_status_success(host):
    """TC_RM_DL_002: Verify overall_status is success."""
    tl = TestLogger(TEST_NAMES["repo_status_success"], "TC_RM_DL_002")
    result = check_repo_status_success(host)

    if result["success"]:
        tl.passed(LOG["repo_status_success"], result["details"])
    else:
        tl.failed(LOG["repo_status_failed"], result["details"])

    assert result["success"], ASSERT["repo_status_not_success"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(3)
def test_slurm_custom_repo_present(host):
    """TC_RM_DL_003: Verify slurm_custom repo present."""
    tl = TestLogger(TEST_NAMES["slurm_custom_repo_present"], "TC_RM_DL_003")
    result = check_repo_status_has_repo(host, "slurm_custom", arch="x86_64")

    if result["success"]:
        tl.passed(LOG["repo_present"].format(repo="slurm_custom"), result["details"])
    else:
        tl.failed(LOG["repo_missing"].format(repo="slurm_custom"), result["details"])

    assert result["success"], ASSERT["repo_not_found"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(4)
def test_epel_repo_present(host):
    """TC_RM_DL_004: Verify epel repo present."""
    tl = TestLogger(TEST_NAMES["epel_repo_present"], "TC_RM_DL_004")
    result = check_repo_status_has_repo(host, "epel", arch="x86_64")

    if result["success"]:
        tl.passed(LOG["repo_present"].format(repo="epel"), result["details"])
    else:
        tl.failed(LOG["repo_missing"].format(repo="epel"), result["details"])

    assert result["success"], ASSERT["repo_not_found"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(5)
def test_x86_64_repos_present(host):
    """TC_RM_DL_005: Verify x86_64 baseos and appstream present."""
    tl = TestLogger(TEST_NAMES["x86_64_repos_present"], "TC_RM_DL_005")
    for repo in ["baseos", "appstream", "codeready-builder"]:
        result = check_repo_status_has_repo(host, repo, arch="x86_64")
        if not result["success"]:
            tl.failed(LOG["repo_missing"].format(repo=repo), result["details"])
            assert False, result["error"]

    tl.passed("x86_64 base repos present", "")


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(6)
def test_file_repos_present(host):
    """TC_RM_DL_006: Verify file repos (tarball) present."""
    tl = TestLogger(TEST_NAMES["file_repos_present"], "TC_RM_DL_006")
    result = check_repo_status_has_file_repo(host, "imb", arch="x86_64")

    if result["success"]:
        tl.passed(LOG["file_repo_present"].format(repo="imb"), result["details"])
    else:
        tl.failed(LOG["file_repo_missing"].format(repo="imb"), result["details"])

    assert result["success"], ASSERT["repo_not_found"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(7)
def test_software_download_status(host):
    """TC_RM_DL_007: Verify software.csv download status per architecture."""
    tl = TestLogger(TEST_NAMES["software_download_status"], "TC_RM_DL_007")
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
    """TC_RM_DL_008: Verify per-software status.csv for individual package download results."""
    tl = TestLogger(TEST_NAMES["per_software_package_status"], "TC_RM_DL_008")
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
    """TC_RM_DL_009: Verify all RPM repositories have latest_version_href (sync indicator)."""
    tl = TestLogger(TEST_NAMES["pulp_repositories_synced"], "TC_RM_DL_009")
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
    """TC_RM_DL_010: Verify all RPM distributions are published with repository attachment."""
    tl = TestLogger(TEST_NAMES["pulp_distributions_published"], "TC_RM_DL_010")
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
    """TC_RM_DL_011: Verify all container image repositories are synced."""
    tl = TestLogger(TEST_NAMES["container_repos_synced"], "TC_RM_DL_011")
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
    """TC_RM_DL_012: Verify all file repositories (tarball, git, etc.) are synced."""
    tl = TestLogger(TEST_NAMES["file_repos_synced"], "TC_RM_DL_012")
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
    """TC_RM_DL_013: Verify RPM content is reachable via HTTPS (repomd.xml check)."""
    tl = TestLogger(TEST_NAMES["pulp_content_accessible"], "TC_RM_DL_013")
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
    """TC_RM_DL_014: Verify all RPM packages from software_config.json are present in Pulp."""
    tl = TestLogger(TEST_NAMES["software_packages_in_pulp"], "TC_RM_DL_014")
    result = check_software_packages_in_pulp(host)

    if result["success"]:
        tl.passed(LOG["software_packages_ok"], result["details"])
    else:
        tl.failed(LOG["software_packages_missing"], result["details"])

    assert result["success"], ASSERT["software_packages_missing"]
