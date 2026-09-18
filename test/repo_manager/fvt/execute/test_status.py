# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Execute scenario verification tests.

RM_FVT_EXECUTE_E001: Deploy repo_manager --tags execute
RM_FVT_EXECUTE_V001: Verify repo_status.yml generated
RM_FVT_EXECUTE_V002: Verify overall_status is success
RM_FVT_EXECUTE_V003: Verify slurm_custom repo present
RM_FVT_EXECUTE_V004: Verify epel repo present
RM_FVT_EXECUTE_V005: Verify x86_64 repositories present
RM_FVT_EXECUTE_V006: Verify file repos present
RM_FVT_EXECUTE_V007: Verify software.csv download status per architecture
RM_FVT_EXECUTE_V008: Verify per-software status.csv for individual package download results
RM_FVT_EXECUTE_V009: Verify all RPM repositories have latest_version_href (sync indicator)
RM_FVT_EXECUTE_V010: Verify all RPM distributions are published with repository attachment
RM_FVT_EXECUTE_V011: Verify all container image repositories are synced
RM_FVT_EXECUTE_V012: Verify all file repositories (tarball, git, etc.) are synced
RM_FVT_EXECUTE_V013: Verify RPM content is reachable via HTTPS (repomd.xml check)
RM_FVT_EXECUTE_V014: Verify all RPM packages from software_config.json are present in Pulp
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_repo_status_exists,
    check_repo_status_success,
    check_repo_status_has_repo,
    check_repo_status_has_file_repo,
    check_repo_configured,
    check_software_download_status,
    check_per_software_package_status,
    check_pulp_repositories_synced,
    check_pulp_distributions_published,
    check_container_repos_synced,
    check_file_repos_synced,
    check_pulp_content_accessible,
    check_software_packages_in_pulp,
    get_configured_repos,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_execute_download(host):
    """RM_FVT_EXECUTE_E001: Deploy repo_manager --tags execute."""
    tl = TestLogger(TEST_NAMES["repo_status_exists"], "RM_FVT_EXECUTE_E001")
    result = run_playbook(tag="execute")

    if result["success"]:
        tl.passed("repo_manager --tags execute completed", result.get("details", ""))
    else:
        tl.failed("repo_manager --tags execute failed", result.get("error", ""))

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_repo_status_exists(host):
    """RM_FVT_EXECUTE_V001: Verify repo_status.yml generated."""
    tl = TestLogger(TEST_NAMES["repo_status_exists"], "RM_FVT_EXECUTE_V001")
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
    """RM_FVT_EXECUTE_V002: Verify overall_status is success."""
    tl = TestLogger(TEST_NAMES["repo_status_success"], "RM_FVT_EXECUTE_V002")
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
    """RM_FVT_EXECUTE_V003: Verify slurm_custom repo present (if configured)."""
    # Check if slurm_custom is configured in repo_manager_config.yml
    config_result = check_repo_configured(host, "slurm_custom", arch="x86_64")

    if not config_result["success"]:
        # Skip test if slurm_custom is not configured
        pytest.skip("slurm_custom not configured in repo_manager_config.yml")

    # Only test if slurm_custom is configured
    tl = TestLogger(TEST_NAMES["slurm_custom_repo_present"], "RM_FVT_EXECUTE_V003")
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
    """RM_FVT_EXECUTE_V004: Verify epel repo present (if configured)."""
    # Check if epel is configured in repo_manager_config.yml
    config_result = check_repo_configured(host, "epel", arch="x86_64")

    if not config_result["success"]:
        # Skip test if epel is not configured
        pytest.skip("epel not configured in repo_manager_config.yml")

    # Only test if epel is configured
    tl = TestLogger(TEST_NAMES["epel_repo_present"], "RM_FVT_EXECUTE_V004")
    result = check_repo_status_has_repo(host, "epel", arch="x86_64")

    if result["success"]:
        tl.passed(LOG["repo_present"].format(repo="epel"), result["details"])
    else:
        tl.failed(LOG["repo_missing"].format(repo="epel"), result["details"])

    assert result["success"], ASSERT["repo_not_found"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(5)
def test_x86_64_repos_present(host):
    """RM_FVT_EXECUTE_V005: Verify x86_64 baseos and appstream present (if configured)."""
    # Check if base repos are configured in repo_manager_config.yml
    base_repos = ["baseos", "appstream", "codeready-builder"]
    configured_repos = []

    for repo in base_repos:
        config_result = check_repo_configured(host, repo, arch="x86_64")
        if config_result["success"]:
            configured_repos.append(repo)

    if not configured_repos:
        # Skip test if no base repos are configured
        pytest.skip("No base repos (baseos, appstream, codeready-builder) configured in repo_manager_config.yml")

    # Only test configured repos
    tl = TestLogger(TEST_NAMES["x86_64_repos_present"], "RM_FVT_EXECUTE_V005")
    for repo in configured_repos:
        result = check_repo_status_has_repo(host, repo, arch="x86_64")
        if not result["success"]:
            tl.failed(LOG["repo_missing"].format(repo=repo), result["details"])
            assert False, result["error"]

    tl.passed(f"x86_64 base repos present: {', '.join(configured_repos)}", "")


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(6)
def test_file_repos_present(host):
    """RM_FVT_EXECUTE_V006: Verify file repos (tarball) present (if configured)."""
    # Check if imb is configured in repo_manager_config.yml
    config_result = check_repo_configured(host, "imb", arch="x86_64")

    if not config_result["success"]:
        # Skip test if imb is not configured
        pytest.skip("imb file repo not configured in repo_manager_config.yml")

    # Only test if imb is configured
    tl = TestLogger(TEST_NAMES["file_repos_present"], "RM_FVT_EXECUTE_V006")
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
    """RM_FVT_EXECUTE_V007: Verify software.csv download status per architecture."""
    tl = TestLogger(TEST_NAMES["software_download_status"], "RM_FVT_EXECUTE_V007")
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
    """RM_FVT_EXECUTE_V008: Verify per-software status.csv for individual package download results."""
    tl = TestLogger(TEST_NAMES["per_software_package_status"], "RM_FVT_EXECUTE_V008")
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
    """RM_FVT_EXECUTE_V009: Verify all RPM repositories have latest_version_href (sync indicator)."""
    tl = TestLogger(TEST_NAMES["pulp_repositories_synced"], "RM_FVT_EXECUTE_V009")
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
    """RM_FVT_EXECUTE_V010: Verify all RPM distributions are published with repository attachment."""
    tl = TestLogger(TEST_NAMES["pulp_distributions_published"], "RM_FVT_EXECUTE_V010")
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
    """RM_FVT_EXECUTE_V011: Verify all container image repositories are synced."""
    tl = TestLogger(TEST_NAMES["container_repos_synced"], "RM_FVT_EXECUTE_V011")
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
    """RM_FVT_EXECUTE_V012: Verify all file repositories (tarball, git, etc.) are synced."""
    tl = TestLogger(TEST_NAMES["file_repos_synced"], "RM_FVT_EXECUTE_V012")
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
    """RM_FVT_EXECUTE_V013: Verify RPM content is reachable via HTTPS (repomd.xml check)."""
    tl = TestLogger(TEST_NAMES["pulp_content_accessible"], "RM_FVT_EXECUTE_V013")
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
    """RM_FVT_EXECUTE_V014: Verify all RPM packages from software_config.json are present in Pulp."""
    tl = TestLogger(TEST_NAMES["software_packages_in_pulp"], "RM_FVT_EXECUTE_V014")
    result = check_software_packages_in_pulp(host)

    if result["success"]:
        tl.passed(LOG["software_packages_ok"], result["details"])
    else:
        tl.failed(LOG["software_packages_missing"], result["details"])

    assert result["success"], ASSERT["software_packages_missing"]
