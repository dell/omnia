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
    
    # Test with a repo that has per-repo policy override
    # epel: policy=partial, caching=true → expected Pulp policy=on_demand
    repo_name = "epel"
    arch = "x86_64"
    os_version = "10.0"
    
    # Verify policy resolution matches actual Pulp remote policy
    resolution_result = verify_policy_resolution(host, repo_name, arch, os_version)
    
    if not resolution_result["success"]:
        tl.failed(LOG["policy_resolution_failed"], resolution_result["details"])
        assert False, ASSERT["pulp_remote_must_match_config"]
    
    if resolution_result.get("match"):
        tl.passed(LOG["policy_resolution_correct"], resolution_result["details"])
    else:
        tl.failed(LOG["policy_resolution_mismatch"], resolution_result["details"])
        assert False, ASSERT["pulp_remote_must_match_config"]
    
    assert resolution_result.get("match"), ASSERT["pulp_remote_must_match_config"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(18)
def test_pulp_remote_policy_immediate_mode(host: Host):
    """TC_RM_PO_018: Repos with always+false should have immediate policy in Pulp."""
    tl = TestLogger(TEST_NAMES["pulp_remote_policy_immediate_mode"], "TC_RM_PO_018")
    
    # Test with slurm_custom: policy=always, caching=false → expected Pulp policy=immediate
    repo_name = "slurm_custom"
    arch = "x86_64"
    os_version = "10.0"
    
    # Get configuration policy
    config_policy = check_repo_policy(host, repo_name, arch, os_version)
    config_caching = check_repo_caching(host, repo_name, arch, os_version)
    
    if not config_policy["success"] or not config_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")
    
    policy = config_policy.get("policy")
    caching = config_caching.get("caching")
    
    # Verify this repo should have immediate policy
    if policy == "always" and not caching:
        expected_policy = "immediate"
    else:
        tl.failed(LOG["repo_config_wrong"], f"Repo {repo_name} doesn't have always+false config")
        pytest.skip(f"Repo {repo_name} doesn't match test criteria")
    
    # Get actual Pulp remote policy
    actual_policy_result = check_pulp_remote_policy(host, repo_name, arch, os_version)
    
    if not actual_policy_result["success"]:
        tl.failed(LOG["pulp_remote_check_failed"], actual_policy_result["details"])
        pytest.skip(f"Cannot get Pulp remote policy for {repo_name}")
    
    actual_policy = actual_policy_result.get("policy")
    
    if actual_policy == expected_policy:
        tl.passed(LOG["pulp_remote_policy_correct"], 
                 f"Repo {repo_name} has correct Pulp policy: {actual_policy}")
    else:
        tl.failed(LOG["pulp_remote_policy_incorrect"], 
                 f"Repo {repo_name} has wrong Pulp policy: expected {expected_policy}, got {actual_policy}")
    
    assert actual_policy == expected_policy, \
        f"Expected Pulp policy {expected_policy}, got {actual_policy}"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(19)
def test_pulp_remote_policy_on_demand_mode(host: Host):
    """TC_RM_PO_019: Repos with partial+true should have on_demand policy in Pulp."""
    tl = TestLogger(TEST_NAMES["pulp_remote_policy_on_demand_mode"], "TC_RM_PO_019")
    
    # Test with epel: policy=partial, caching=true → expected Pulp policy=on_demand
    repo_name = "epel"
    arch = "x86_64"
    os_version = "10.0"
    
    # Get configuration policy
    config_policy = check_repo_policy(host, repo_name, arch, os_version)
    config_caching = check_repo_caching(host, repo_name, arch, os_version)
    
    if not config_policy["success"] or not config_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")
    
    policy = config_policy.get("policy")
    caching = config_caching.get("caching")
    
    # Verify this repo should have on_demand policy
    if policy == "partial" and caching:
        expected_policy = "on_demand"
    else:
        tl.failed(LOG["repo_config_wrong"], f"Repo {repo_name} doesn't have partial+true config")
        pytest.skip(f"Repo {repo_name} doesn't match test criteria")
    
    # Get actual Pulp remote policy
    actual_policy_result = check_pulp_remote_policy(host, repo_name, arch, os_version)
    
    if not actual_policy_result["success"]:
        tl.failed(LOG["pulp_remote_check_failed"], actual_policy_result["details"])
        pytest.skip(f"Cannot get Pulp remote policy for {repo_name}")
    
    actual_policy = actual_policy_result.get("policy")
    
    if actual_policy == expected_policy:
        tl.passed(LOG["pulp_remote_policy_correct"], 
                 f"Repo {repo_name} has correct Pulp policy: {actual_policy}")
    else:
        tl.failed(LOG["pulp_remote_policy_incorrect"], 
                 f"Repo {repo_name} has wrong Pulp policy: expected {expected_policy}, got {actual_policy}")
    
    assert actual_policy == expected_policy, \
        f"Expected Pulp policy {expected_policy}, got {actual_policy}"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(20)
def test_multiple_repos_policy_resolution(host: Host):
    """TC_RM_PO_020: Multiple repos should have correct Pulp policies based on their config."""
    tl = TestLogger(TEST_NAMES["multiple_repos_policy_resolution"], "TC_RM_PO_020")
    
    # Test multiple repos with different policy configurations
    test_cases = [
        ("slurm_custom", "always", False, "immediate"),    # always + false → immediate
        ("epel", "partial", True, "on_demand"),           # partial + true → on_demand
        ("nvidia-hpc-sdk", "always", True, "on_demand"), # always + true → on_demand
    ]
    
    all_correct = True
    results = []
    
    for repo_name, expected_policy, expected_caching, expected_pulp_mode in test_cases:
        # Get actual configuration
        config_policy = check_repo_policy(host, repo_name)
        config_caching = check_repo_caching(host, repo_name)
        
        if not config_policy["success"] or not config_caching["success"]:
            results.append(f"{repo_name}: Cannot determine config")
            all_correct = False
            continue
        
        actual_policy = config_policy.get("policy")
        actual_caching = config_caching.get("caching")
        
        # Verify configuration matches expected
        if actual_policy == expected_policy and actual_caching == expected_caching:
            # Get actual Pulp remote policy
            actual_policy_result = check_pulp_remote_policy(host, repo_name)
            
            if actual_policy_result["success"]:
                actual_pulp_policy = actual_policy_result.get("policy")
                if actual_pulp_policy == expected_pulp_mode:
                    results.append(f"{repo_name}: ✓ config({actual_policy}+{actual_caching}) → pulp({actual_pulp_policy})")
                else:
                    results.append(f"{repo_name}: ✗ config({actual_policy}+{actual_caching}) → expected({expected_pulp_mode}) → pulp({actual_pulp_policy})")
                    all_correct = False
            else:
                results.append(f"{repo_name}: ✗ Cannot get Pulp policy")
                all_correct = False
        else:
            results.append(f"{repo_name}: ✗ config mismatch: expected({expected_policy}+{expected_caching}) → actual({actual_policy}+{actual_caching})")
            all_correct = False
    
    if all_correct:
        tl.passed(LOG["multiple_repos_policy_correct"], 
                 f"All repos have correct policy resolution: {', '.join(results)}")
    else:
        tl.failed(LOG["multiple_repos_policy_incorrect"], 
                 f"Some repos have incorrect policy resolution: {', '.join(results)}")
    
    assert all_correct, ASSERT["all_repos_must_have_correct_policies"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(21)
def test_pulp_repository_exists(host: Host):
    """TC_RM_PO_021: Pulp repositories should exist for configured repos."""
    tl = TestLogger(TEST_NAMES["pulp_repository_exists"], "TC_RM_PO_021")
    
    # Test that Pulp repositories exist for configured repos
    test_repos = ["epel", "slurm_custom", "nvidia-hpc-sdk"]
    arch = "x86_64"
    os_version = "10.0"
    
    all_exist = True
    results = []
    
    for repo_name in test_repos:
        repo_result = check_pulp_repository_exists(host, repo_name, arch, os_version)
        
        if repo_result["success"]:
            results.append(f"{repo_name}: ✓ exists (version: {repo_result.get('latest_version', 'unknown')})")
        else:
            results.append(f"{repo_name}: ✗ {repo_result['error']}")
            all_exist = False
    
    if all_exist:
        tl.passed(LOG["pulp_repositories_exist"], 
                 f"All Pulp repositories exist: {', '.join(results)}")
    else:
        tl.failed(LOG["pulp_repositories_missing"], 
                 f"Some Pulp repositories missing: {', '.join(results)}")
    
    assert all_exist, ASSERT["pulp_repositories_must_exist"]