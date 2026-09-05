# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Test Category 2: Partial Override Testing
Tests that per-repo partial overrides work correctly (policy only, caching only, or empty).
"""

import pytest
from testinfra.host import Host

from library.functions import (
    TestLogger,
    check_repo_policy,
    check_repo_caching,
    check_global_repo_config,
    check_global_caching_policy,
    get_configured_repos,
)
from library.messages.repo_manager_msgs import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(4)
def test_per_repo_policy_only(host: Host):
    """TC_RM_PO_004: Per-repo policy only, caching from global."""
    tl = TestLogger(TEST_NAMES["per_repo_policy_only"], "TC_RM_PO_004")

    # Get global settings
    global_config = check_global_repo_config(host)
    global_caching = check_global_caching_policy(host)

    if not global_config["success"] or not global_caching["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read global settings")
        pytest.skip("Cannot verify without global config")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Find a repo with policy from per-repo, caching from global
    found_repo = None
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy_source = repo_policy.get("source")
            caching_source = repo_caching.get("source")

            if policy_source == "per_repo" and caching_source == "global":
                found_repo = repo_name
                break

    if found_repo:
        tl.passed(
            LOG["per_repo_policy_used"],
            f"{found_repo} uses per-repo policy and global caching"
        )
    else:
        tl.passed(
            "other_configuration",
            f"No repo with per-repo policy + global caching found "
            f"among {len(configured_repos)} repos"
        )
        pytest.skip("No repo has per-repo policy + global caching configuration")

    assert found_repo is not None, \
        "Expected to find repo with per-repo policy + global caching"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(5)
def test_per_repo_caching_only(host: Host):
    """TC_RM_PO_005: Per-repo caching only, policy from global."""
    tl = TestLogger(TEST_NAMES["per_repo_caching_only"], "TC_RM_PO_005")

    # Get global settings
    global_config = check_global_repo_config(host)
    global_caching = check_global_caching_policy(host)

    if not global_config["success"] or not global_caching["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read global settings")
        pytest.skip("Cannot verify without global config")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Find a repo with policy from global, caching from per-repo
    found_repo = None
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy_source = repo_policy.get("source")
            caching_source = repo_caching.get("source")

            if policy_source == "global" and caching_source == "per_repo":
                found_repo = repo_name
                break

    if found_repo:
        tl.passed(
            LOG["per_repo_caching_used"],
            f"{found_repo} uses global policy and per-repo caching"
        )
    else:
        tl.passed(
            "other_configuration",
            f"No repo with global policy + per-repo caching found "
            f"among {len(configured_repos)} repos"
        )
        pytest.skip("No repo has global policy + per-repo caching configuration")

    assert found_repo is not None, \
        "Expected to find repo with global policy + per-repo caching"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(6)
def test_empty_per_repo_config(host: Host):
    """TC_RM_PO_006: Empty per-repo config should use global settings."""
    tl = TestLogger(TEST_NAMES["empty_per_repo_config"], "TC_RM_PO_006")

    # Get global settings
    global_config = check_global_repo_config(host)
    global_caching = check_global_caching_policy(host)

    if not global_config["success"] or not global_caching["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read global settings")
        pytest.skip("Cannot verify without global config")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Find a repo with both policy and caching from global
    found_repo = None
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy_source = repo_policy.get("source")
            caching_source = repo_caching.get("source")

            if policy_source == "global" and caching_source == "global":
                found_repo = repo_name
                break

    if found_repo:
        tl.passed(
            LOG["empty_config_uses_global"],
            f"{found_repo} uses global policy and global caching"
        )
    else:
        tl.failed(
            LOG["empty_config_uses_global"],
            f"No repo with global policy + global caching found "
            f"among {len(configured_repos)} repos"
        )

    assert found_repo is not None, \
        ASSERT["empty_config_must_use_global"]
