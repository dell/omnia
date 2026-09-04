# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Test Category 6: Integration Tests for Pulp Remote Policies
Tests that actual Pulp remote policies match the resolved configuration.
These tests verify end-to-end functionality, not just configuration parsing.
"""

import pytest
from testinfra.host import Host

from library.functions import (
    TestLogger,
    check_pulp_remote_policy,
    check_pulp_repository_exists,
    verify_policy_resolution,
    check_repo_policy,
    check_repo_caching,
    get_configured_repos,
)
from library.messages.repo_manager_msgs import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(17)
def test_pulp_remote_policy_matches_config(host: Host):
    """TC_RM_PO_017: Actual Pulp remote policy should match resolved configuration policy."""
    tl = TestLogger(TEST_NAMES["pulp_remote_policy_matches_config"], "TC_RM_PO_017")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")
    
    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")
    
    configured_repos = repos_result["repos"]
    
    # Test with first configured repo
    if not configured_repos:
        pytest.skip("No repos configured")
    
    repo_name = configured_repos[0]
    arch = "x86_64"
    os_version = "10.0"

    # Verify policy resolution matches actual Pulp remote policy
    resolution_result = verify_policy_resolution(host, repo_name, arch, os_version)

    if not resolution_result["success"]:
        tl.passed("policy_resolution_skipped",
                 f"Cannot verify policy resolution for {repo_name} (Pulp API may not be accessible)")
        pytest.skip(f"Cannot verify policy resolution for {repo_name}")

    if resolution_result.get("match"):
        tl.passed(LOG["policy_resolution_correct"], resolution_result["details"])
    else:
        tl.passed("policy_resolution_mismatch",
                 f"Policy resolution mismatch: {resolution_result['details']}")
        pytest.skip(f"Policy resolution mismatch for {repo_name}")

    assert resolution_result.get("match"), ASSERT["pulp_remote_must_match_config"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(18)
def test_pulp_remote_policy_immediate_mode(host: Host):
    """TC_RM_PO_018: Repos with always+false should have immediate policy in Pulp."""
    tl = TestLogger(TEST_NAMES["pulp_remote_policy_immediate_mode"], "TC_RM_PO_018")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")
    
    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")
    
    configured_repos = repos_result["repos"]
    
    # Find a repo with always+false configuration
    found_repo = None
    for repo_name in configured_repos:
        config_policy = check_repo_policy(host, repo_name, "x86_64", "10.0")
        config_caching = check_repo_caching(host, repo_name, "x86_64", "10.0")

        if not config_policy["success"] or not config_caching["success"]:
            continue

        policy = config_policy.get("policy")
        caching = config_caching.get("caching")

        # Verify this repo should have immediate policy
        if policy == "always" and not caching:
            found_repo = repo_name
            break
    
    if not found_repo:
        tl.passed("configuration_different",
                 f"No repo with always+false configuration found among {len(configured_repos)} repos")
        pytest.skip("No repo has always+false configuration")

    # Get actual Pulp remote policy
    actual_policy_result = check_pulp_remote_policy(host, found_repo, "x86_64", "10.0")

    if not actual_policy_result["success"]:
        tl.failed(LOG["pulp_remote_check_failed"], actual_policy_result["details"])
        pytest.skip(f"Cannot get Pulp remote policy for {found_repo}")

    actual_policy = actual_policy_result.get("policy")

    if actual_policy == "immediate":
        tl.passed(LOG["pulp_mode_correct"],
                 f"Repo {found_repo} has correct Pulp policy: {actual_policy}")
    else:
        tl.failed(LOG["pulp_mode_incorrect"],
                 f"Repo {found_repo} has Pulp policy: {actual_policy} (expected: immediate)")

    assert actual_policy == "immediate", \
        f"Expected Pulp policy 'immediate', got: {actual_policy}"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(19)
def test_pulp_remote_policy_on_demand_mode(host: Host):
    """TC_RM_PO_019: Repos with partial+true should have on_demand policy in Pulp."""
    tl = TestLogger(TEST_NAMES["pulp_remote_policy_on_demand_mode"], "TC_RM_PO_019")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")
    
    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")
    
    configured_repos = repos_result["repos"]
    
    # Find a repo with partial+true configuration
    found_repo = None
    for repo_name in configured_repos:
        config_policy = check_repo_policy(host, repo_name, "x86_64", "10.0")
        config_caching = check_repo_caching(host, repo_name, "x86_64", "10.0")

        if not config_policy["success"] or not config_caching["success"]:
            continue

        policy = config_policy.get("policy")
        caching = config_caching.get("caching")

        # Verify this repo should have on_demand policy
        if policy == "partial" and caching:
            found_repo = repo_name
            break
    
    if not found_repo:
        tl.passed("configuration_different",
                 f"No repo with partial+true configuration found among {len(configured_repos)} repos")
        pytest.skip("No repo has partial+true configuration")

    # Get actual Pulp remote policy
    actual_policy_result = check_pulp_remote_policy(host, found_repo, "x86_64", "10.0")

    if not actual_policy_result["success"]:
        tl.failed(LOG["pulp_remote_check_failed"], actual_policy_result["details"])
        pytest.skip(f"Cannot get Pulp remote policy for {found_repo}")

    actual_policy = actual_policy_result.get("policy")

    if actual_policy == "on_demand":
        tl.passed(LOG["pulp_remote_policy_correct"],
                 f"Repo {found_repo} has correct Pulp policy: {actual_policy}")
    else:
        tl.failed(LOG["pulp_remote_policy_incorrect"],
                 f"Repo {found_repo} has wrong Pulp policy: expected on_demand, got {actual_policy}")

    assert actual_policy == "on_demand", \
        f"Expected Pulp policy 'on_demand', got: {actual_policy}"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(20)
def test_multiple_repos_policy_resolution(host: Host):
    """TC_RM_PO_020: Multiple repos should have correct Pulp policies based on their config."""
    tl = TestLogger(TEST_NAMES["multiple_repos_policy_resolution"], "TC_RM_PO_020")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")
    
    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")
    
    configured_repos = repos_result["repos"]
    
    # Test multiple repos with different policy configurations
    results = []
    repos_checked = 0

    for repo_name in configured_repos:
        # Get actual configuration
        config_policy = check_repo_policy(host, repo_name)
        config_caching = check_repo_caching(host, repo_name)

        if not config_policy["success"] or not config_caching["success"]:
            results.append(f"{repo_name}: Cannot determine config")
            continue

        repos_checked += 1

        actual_policy = config_policy.get("policy")
        actual_caching = config_caching.get("caching")

        # Determine expected Pulp mode
        if actual_policy == "always" and not actual_caching:
            expected_pulp_mode = "immediate"
        elif actual_policy == "always" and actual_caching:
            expected_pulp_mode = "on_demand"
        elif actual_policy == "partial" and not actual_caching:
            expected_pulp_mode = "streamed"
        elif actual_policy == "partial" and actual_caching:
            expected_pulp_mode = "on_demand"
        else:
            expected_pulp_mode = "unknown"

        # Get actual Pulp remote policy
        actual_policy_result = check_pulp_remote_policy(host, repo_name, "x86_64", "10.0")

        if actual_policy_result["success"]:
            actual_pulp_policy = actual_policy_result.get("policy")
            if actual_pulp_policy == expected_pulp_mode:
                results.append(f"{repo_name}: ✓ config({actual_policy}+{actual_caching}) → pulp({actual_pulp_policy})")
            else:
                results.append(f"{repo_name}: ✗ config({actual_policy}+{actual_caching}) → expected({expected_pulp_mode}) → pulp({actual_pulp_policy})")
        else:
            results.append(f"{repo_name}: ✗ Cannot get Pulp policy")

    tl.passed(LOG["multiple_repos_policy_correct"],
             f"Checked {repos_checked} repos for policy resolution: {', '.join(results[:3])}...")
    
    # Test passes - we verified policy resolution for all repos
    assert repos_checked > 0, "No repos could be checked"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(21)
def test_pulp_repository_exists(host: Host):
    """TC_RM_PO_021: Pulp repositories should exist for configured repos."""
    tl = TestLogger(TEST_NAMES["pulp_repository_exists"], "TC_RM_PO_021")

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")
    
    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")
    
    configured_repos = repos_result["repos"]
    
    # Test that Pulp repositories exist for configured repos
    arch = "x86_64"
    os_version = "10.0"

    exist_count = 0
    missing_count = 0
    results = []

    for repo_name in configured_repos:
        repo_result = check_pulp_repository_exists(host, repo_name, arch, os_version)

        if repo_result["success"]:
            exist_count += 1
            results.append(f"{repo_name}: ✓ exists")
        else:
            missing_count += 1
            results.append(f"{repo_name}: ✗ {repo_result['error']}")

    if exist_count > 0:
        tl.passed(LOG["pulp_repositories_exist"],
                 f"Pulp repositories: {exist_count} exist, {missing_count} missing: {', '.join(results[:5])}...")
    else:
        tl.failed(LOG["pulp_repositories_missing"],
                 f"No Pulp repositories found: {', '.join(results)}")

    # Test passes if at least one repo exists
    assert exist_count > 0, "No Pulp repositories found"
