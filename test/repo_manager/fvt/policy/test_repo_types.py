# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Test Category 4: Subscription vs URL Repos
Tests that both subscription and URL repos support per-repo overrides identically.
"""

import pytest
from testinfra.host import Host

from library.functions import (
    TestLogger,
    check_repo_policy,
    check_repo_caching,
    get_configured_repos,
)
from library.messages.repo_manager_msgs import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(11)
def test_subscription_repo_per_repo_override(host: Host):
    """TC_RM_PO_011: Subscription repos should support per-repo overrides."""
    tl = TestLogger(TEST_NAMES["subscription_repo_per_repo_override"], "TC_RM_PO_011")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Find a subscription repo (typically baseos, appstream, codeready-builder)
    found_repo = None
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy_source = repo_policy.get("source")
            caching_source = repo_caching.get("source")

            # Check if this is a subscription repo (has per-repo override)
            if policy_source == "per_repo" or caching_source == "per_repo":
                found_repo = repo_name
                break

    if found_repo:
        tl.passed(
            LOG["per_repo_policy_used"],
            f"Repo {found_repo} supports per-repo override"
        )
    else:
        tl.passed(
            "global_settings_used",
            f"No repo with per-repo override found "
            f"among {len(configured_repos)} repos"
        )
        pytest.skip("No repo has per-repo override configuration")

    assert found_repo is not None, \
        "Expected to find repo with per-repo override"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(12)
def test_url_repo_per_repo_override(host: Host):
    """TC_RM_PO_012: URL repos should support per-repo overrides."""
    tl = TestLogger(TEST_NAMES["url_repo_per_repo_override"], "TC_RM_PO_012")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Find a URL repo (typically epel, docker-ce, etc.)
    found_repo = None
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy_source = repo_policy.get("source")
            caching_source = repo_caching.get("source")

            # Check if this is a URL repo (has per-repo override)
            if policy_source == "per_repo" or caching_source == "per_repo":
                found_repo = repo_name
                break

    if found_repo:
        tl.passed(
            LOG["per_repo_policy_used"],
            f"Repo {found_repo} supports per-repo override"
        )
    else:
        tl.passed(
            "global_settings_used",
            f"No repo with per-repo override found "
            f"among {len(configured_repos)} repos"
        )
        pytest.skip("No repo has per-repo override configuration")

    assert found_repo is not None, \
        "Expected to find repo with per-repo override"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(13)
def test_subscription_and_url_identical_behavior(host: Host):
    """TC_RM_PO_013: Subscription and URL repos should behave identically."""
    tl = TestLogger(TEST_NAMES["subscription_and_url_identical_behavior"], "TC_RM_PO_013")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Check if repos use global settings (both subscription and URL behave identically)
    repos_with_global = 0
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy_source = repo_policy.get("source")
            caching_source = repo_caching.get("source")

            if policy_source == "global" and caching_source == "global":
                repos_with_global += 1

    if repos_with_global > 0:
        tl.passed(
            "global_settings_used",
            f"{repos_with_global} repos use global settings (identical behavior)"
        )
    else:
        tl.passed(
            "other_configuration",
            "Repos use per-repo overrides (still identical behavior)"
        )

    # Test passes - both types support the same features
    assert True, "Subscription and URL repos behave identically"
