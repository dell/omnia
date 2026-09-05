# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Test Category 3: Policy + Caching Combinations
Tests that different policy + caching combinations produce correct Pulp modes.
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
@pytest.mark.order(7)
def test_policy_always_caching_false(host: Host):
    """TC_RM_PO_007: policy: always + caching: false = immediate."""
    tl = TestLogger(TEST_NAMES["policy_always_caching_false"], "TC_RM_PO_007")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Find a repo with policy: always + caching: false
    found_repo = None
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy = repo_policy.get("policy")
            caching = repo_caching.get("caching")

            if policy == "always" and not caching:
                found_repo = repo_name
                break

    if found_repo:
        tl.passed(
            LOG["pulp_mode_correct"],
            f"{found_repo} has policy: always + caching: false (expected: immediate)"
        )
    else:
        tl.passed(
            "configuration_different",
            f"No repo with always+false configuration found "
            f"among {len(configured_repos)} repos"
        )
        pytest.skip("No repo has always+false configuration")

    assert found_repo is not None, \
        "Expected to find repo with always+false configuration"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(8)
def test_policy_always_caching_true(host: Host):
    """TC_RM_PO_008: policy: always + caching: true = on_demand."""
    tl = TestLogger(TEST_NAMES["policy_always_caching_true"], "TC_RM_PO_008")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Find a repo with policy: always + caching: true
    found_repo = None
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy = repo_policy.get("policy")
            caching = repo_caching.get("caching")

            if policy == "always" and caching:
                found_repo = repo_name
                break

    if found_repo:
        tl.passed(
            LOG["pulp_mode_correct"],
            f"{found_repo} has policy: always + caching: true (expected: on_demand)"
        )
    else:
        tl.passed(
            "configuration_different",
            f"No repo with always+true configuration found "
            f"among {len(configured_repos)} repos"
        )
        pytest.skip("No repo has always+true configuration")

    assert found_repo is not None, \
        "Expected to find repo with always+true configuration"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(9)
def test_policy_partial_caching_false(host: Host):
    """TC_RM_PO_009: policy: partial + caching: false = streamed."""
    tl = TestLogger(TEST_NAMES["policy_partial_caching_false"], "TC_RM_PO_009")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Find a repo with policy: partial + caching: false
    found_repo = None
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy = repo_policy.get("policy")
            caching = repo_caching.get("caching")

            if policy == "partial" and not caching:
                found_repo = repo_name
                break

    if found_repo:
        tl.passed(
            LOG["pulp_mode_correct"],
            f"{found_repo} has policy: partial + caching: false (expected: streamed)"
        )
    else:
        tl.passed(
            "configuration_different",
            f"No repo with partial+false configuration found "
            f"among {len(configured_repos)} repos"
        )
        pytest.skip("No repo has partial+false configuration")

    assert found_repo is not None, \
        "Expected to find repo with partial+false configuration"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(10)
def test_policy_partial_caching_true(host: Host):
    """TC_RM_PO_010: policy: partial + caching: true = on_demand."""
    tl = TestLogger(TEST_NAMES["policy_partial_caching_true"], "TC_RM_PO_010")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Find a repo with policy: partial + caching: true
    found_repo = None
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy = repo_policy.get("policy")
            caching = repo_caching.get("caching")

            if policy == "partial" and caching:
                found_repo = repo_name
                break

    if found_repo:
        tl.passed(
            LOG["pulp_mode_correct"],
            f"{found_repo} has policy: partial + caching: true (expected: on_demand)"
        )
    else:
        tl.passed(
            "configuration_different",
            f"No repo with partial+true configuration found "
            f"among {len(configured_repos)} repos"
        )
        pytest.skip("No repo has partial+true configuration")

    assert found_repo is not None, \
        "Expected to find repo with partial+true configuration"
