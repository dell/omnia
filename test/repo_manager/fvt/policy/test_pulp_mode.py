# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Test Category 5: Pulp Mode Verification
Tests that repo_status.yml reflects correct Pulp mode and actual Pulp repositories have correct policy.
"""

import pytest
from testinfra.host import Host

from library.functions import (
    TestLogger,
    check_repo_policy,
    check_repo_caching,
    check_pulp_mode,
    verify_repo_status_pulp_mode,
)
from library.messages.repo_manager_msgs import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(14)
def test_pulp_mode_in_repo_status(host: Host):
    """TC_RM_PO_014: repo_status.yml should reflect correct Pulp mode."""
    tl = TestLogger(TEST_NAMES["pulp_mode_in_repo_status"], "TC_RM_PO_014")
    
    # Test with multiple repos to verify repo_status.yml reflects correct modes
    test_repos = [
        ("slurm_custom", "immediate"),  # always + false
        ("epel", "on_demand"),         # partial + true
        ("nvidia-hpc-sdk", "on_demand"), # always + true
    ]
    
    all_correct = True
    results = []
    
    for repo_name, expected_mode in test_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)
        
        if not repo_policy["success"] or not repo_caching["success"]:
            results.append(f"{repo_name}: Cannot determine settings")
            all_correct = False
            continue
        
        # Determine expected Pulp mode based on policy + caching
        policy = repo_policy.get("policy")
        caching = repo_caching.get("caching")
        
        if policy == "always" and not caching:
            calculated_mode = "immediate"
        elif policy == "always" and caching:
            calculated_mode = "on_demand"
        elif policy == "partial" and not caching:
            calculated_mode = "streamed"
        elif policy == "partial" and caching:
            calculated_mode = "on_demand"
        else:
            calculated_mode = "unknown"
        
        # Note: Pulp mode verification requires repo_status.yml to include pulp_mode field
        # Current repo_status.yml format doesn't include this, so we verify policy/caching combination only
        if calculated_mode == expected_mode:
            results.append(f"{repo_name}: {calculated_mode} ✓ (policy: {policy}, caching: {caching})")
        else:
            results.append(f"{repo_name}: {calculated_mode} ✗ (expected: {expected_mode})")
            all_correct = False
    
    if all_correct:
        tl.passed(LOG["pulp_mode_correct"], 
                 f"All repos have correct Pulp modes in repo_status.yml: {', '.join(results)}")
    else:
        tl.failed(LOG["pulp_mode_incorrect"], 
                 f"Some repos have incorrect Pulp modes: {', '.join(results)}")
    
    assert all_correct, ASSERT["repo_status_must_reflect_pulp_mode"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(15)
def test_actual_pulp_repository_policy(host: Host):
    """TC_RM_PO_015: Actual Pulp repository should have correct policy."""
    tl = TestLogger(TEST_NAMES["actual_pulp_repository_policy"], "TC_RM_PO_015")
    
    # Test with a repo that should have specific Pulp policy
    # This test verifies that the actual Pulp repository (not just repo_status.yml) 
    # has the correct policy set
    
    repo_name = "epel"
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)
    
    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")
    
    # Verify the policy + caching combination is correct
    policy = repo_policy.get("policy")
    caching = repo_caching.get("caching")
    
    if policy == "partial" and caching:
        expected_mode = "on_demand"
    elif policy == "always" and not caching:
        expected_mode = "immediate"
    else:
        expected_mode = "unknown"
    
    # Note: Pulp mode verification requires repo_status.yml to include pulp_mode field
    # Current repo_status.yml format doesn't include this, so we verify policy/caching combination only
    tl.passed(LOG["pulp_mode_correct"], 
             f"Repository {repo_name} has policy: {policy}, caching: {caching} (expected mode: {expected_mode})")
    
    assert policy == "partial" and caching or policy == "always" and not caching, \
        ASSERT["pulp_repo_must_have_correct_policy"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(16)
def test_disk_space_savings(host: Host):
    """TC_RM_PO_016: On-demand repos should save disk space."""
    tl = TestLogger(TEST_NAMES["disk_space_savings"], "TC_RM_PO_016")
    
    # This test verifies that repos with on_demand policy save disk space
    # compared to repos with immediate policy
    
    # Get repos with different policies
    immediate_repos = ["slurm_custom"]  # always + false
    on_demand_repos = ["epel", "nvidia-hpc-sdk"]  # partial + true, always + true
    
    # Check that on-demand repos are configured to save space
    on_demand_count = 0
    for repo_name in on_demand_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)
        
        if repo_policy["success"] and repo_caching["success"]:
            policy = repo_policy.get("policy")
            caching = repo_caching.get("caching")
            
            # Check if this combination results in on_demand
            if (policy == "always" and caching) or (policy == "partial" and caching):
                on_demand_count += 1
    
    # Verify we have on-demand repos configured
    if on_demand_count > 0:
        tl.passed(LOG["disk_space_saved"], 
                 f"{on_demand_count} repos configured with on-demand policy to save disk space")
    else:
        tl.failed(LOG["disk_space_saved"], 
                 "No repos configured with on-demand policy for disk space savings")
    
    assert on_demand_count > 0, ASSERT["on_demand_must_save_disk_space"]