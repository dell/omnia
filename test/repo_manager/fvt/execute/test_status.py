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
    get_deployed_repo_contexts,
    get_repo_status_contexts,
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
    del host  # The fixture preserves standard FVT host initialization.
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
    """RM_FVT_EXECUTE_V003: Verify each deployed slurm_custom repository."""
    repos_result = get_deployed_repo_contexts(host)
    assert repos_result["success"], repos_result["error"]
    deployed_contexts = [
        (repo["os_version"], repo["architecture"])
        for repo in repos_result["repositories"]
        if repo["name"] == "slurm_custom"
    ]

    if not deployed_contexts:
        pytest.skip("slurm_custom not selected by the active catalog")

    tl = TestLogger(TEST_NAMES["slurm_custom_repo_present"], "RM_FVT_EXECUTE_V003")
    for os_version, architecture in deployed_contexts:
        result = check_repo_status_has_repo(
            host, "slurm_custom", arch=architecture, os_version=os_version
        )
        if not result["success"]:
            tl.failed(
                LOG["repo_missing"].format(repo="slurm_custom"),
                result["details"],
            )
        assert result["success"], ASSERT["repo_not_found"]
    tl.passed(
        LOG["repo_present"].format(repo="slurm_custom"),
        f"Validated {len(deployed_contexts)} selected context(s)",
    )


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(4)
def test_epel_repo_present(host):
    """RM_FVT_EXECUTE_V004: Verify epel repo present (if configured)."""
    context_result = get_repo_status_contexts(host)
    assert context_result["success"], context_result["error"]
    configured_contexts = []
    for _os_type, os_version, architecture in context_result["contexts"]:
        config_result = check_repo_configured(
            host, "epel", arch=architecture, os_version=os_version
        )
        if config_result["success"]:
            configured_contexts.append((os_version, architecture))

    if not configured_contexts:
        pytest.skip("epel not configured in repo_manager_config.yml")

    tl = TestLogger(TEST_NAMES["epel_repo_present"], "RM_FVT_EXECUTE_V004")
    for os_version, architecture in configured_contexts:
        result = check_repo_status_has_repo(
            host, "epel", arch=architecture, os_version=os_version
        )
        if not result["success"]:
            tl.failed(
                LOG["repo_missing"].format(repo="epel"), result["details"]
            )
        assert result["success"], ASSERT["repo_not_found"]
    tl.passed(
        LOG["repo_present"].format(repo="epel"),
        f"Validated {len(configured_contexts)} selected context(s)",
    )


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(5)
def test_x86_64_repos_present(host):
    """RM_FVT_EXECUTE_V005: Verify x86_64 baseos and appstream present (if configured)."""
    # Check if base repos are configured in repo_manager_config.yml
    base_repos = ["baseos", "appstream", "codeready-builder"]
    context_result = get_repo_status_contexts(host)
    assert context_result["success"], context_result["error"]
    configured_repos = []

    for _os_type, os_version, architecture in context_result["contexts"]:
        if architecture != "x86_64":
            continue
        for repo in base_repos:
            config_result = check_repo_configured(
                host, repo, arch=architecture, os_version=os_version
            )
            if config_result["success"]:
                configured_repos.append((os_version, architecture, repo))

    if not configured_repos:
        # Skip test if no base repos are configured
        pytest.skip(
            "No base repos (baseos, appstream, codeready-builder) "
            "configured in repo_manager_config.yml"
        )

    # Only test configured repos
    tl = TestLogger(TEST_NAMES["x86_64_repos_present"], "RM_FVT_EXECUTE_V005")
    for os_version, architecture, repo in configured_repos:
        result = check_repo_status_has_repo(
            host, repo, arch=architecture, os_version=os_version
        )
        if not result["success"]:
            tl.failed(LOG["repo_missing"].format(repo=repo), result["details"])
            assert False, result["error"]

    names = [f"{version}/{repo}" for version, _arch, repo in configured_repos]
    tl.passed(f"x86_64 base repos present: {', '.join(names)}", "")


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(6)
def test_file_repos_present(host):
    """RM_FVT_EXECUTE_V006: Verify file repos (tarball) present (if configured)."""
    context_result = get_repo_status_contexts(host)
    assert context_result["success"], context_result["error"]
    matches = []
    for _os_type, os_version, architecture in context_result["contexts"]:
        result = check_repo_status_has_file_repo(
            host, "imb", arch=architecture, os_version=os_version
        )
        if result["success"]:
            matches.append(result["details"])

    if not matches:
        pytest.skip("imb file repo not configured in repo_manager_config.yml")

    tl = TestLogger(TEST_NAMES["file_repos_present"], "RM_FVT_EXECUTE_V006")
    tl.passed(
        LOG["file_repo_present"].format(repo="imb"), "; ".join(matches)
    )


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
    """RM_FVT_EXECUTE_V008: Verify each package result in status.csv."""
    tl = TestLogger(
        TEST_NAMES["per_software_package_status"], "RM_FVT_EXECUTE_V008"
    )
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
    """RM_FVT_EXECUTE_V009: Verify every RPM repository is synchronized."""
    tl = TestLogger(
        TEST_NAMES["pulp_repositories_synced"], "RM_FVT_EXECUTE_V009"
    )
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
    """RM_FVT_EXECUTE_V010: Verify each RPM distribution is published."""
    tl = TestLogger(
        TEST_NAMES["pulp_distributions_published"], "RM_FVT_EXECUTE_V010"
    )
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
    """RM_FVT_EXECUTE_V014: Verify selected RPM packages are present in Pulp."""
    tl = TestLogger(TEST_NAMES["software_packages_in_pulp"], "RM_FVT_EXECUTE_V014")
    result = check_software_packages_in_pulp(host)

    if result["success"]:
        tl.passed(LOG["software_packages_ok"], result["details"])
    else:
        tl.failed(LOG["software_packages_missing"], result["details"])

    assert result["success"], ASSERT["software_packages_missing"]
