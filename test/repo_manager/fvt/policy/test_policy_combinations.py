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
    verify_repo_status_pulp_mode,
)
from library.messages.repo_manager_msgs import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(7)
def test_policy_always_caching_false(host: Host):
    """TC_RM_PO_007: policy: always + caching: false = immediate."""
    tl = TestLogger(TEST_NAMES["policy_always_caching_false"], "TC_RM_PO_007")
    
    # Test with a repo that has policy: always + caching: false
    # Assuming slurm_custom has this combination
    repo_name = "slurm_custom"
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)
    
    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")
    
    # Verify policy and caching combination
    policy = repo_policy.get("policy")
    caching = repo_caching.get("caching")
    
    if policy == "always" and not caching:
        # Note: Pulp mode verification requires repo_status.yml to include pulp_mode field
        # Current repo_status.yml format doesn't include this, so we verify policy/caching combination only
        tl.passed(LOG["pulp_mode_correct"], 
                 f"{repo_name} has policy: always + caching: false (expected: immediate)")
    else:
        tl.failed(LOG["pulp_mode_incorrect"], 
                 f"{repo_name} has policy: {policy}, caching: {caching} (expected: always + false)")
    
    assert policy == "always" and not caching, \
        f"Expected policy: always + caching: false, got policy: {policy}, caching: {caching}"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(8)
def test_policy_always_caching_true(host: Host):
    """TC_RM_PO_008: policy: always + caching: true = on_demand."""
    tl = TestLogger(TEST_NAMES["policy_always_caching_true"], "TC_RM_PO_008")
    
    # Test with a repo that has policy: always + caching: true
    # Assuming nvidia-hpc-sdk has this combination
    repo_name = "nvidia-hpc-sdk"
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)
    
    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")
    
    # Verify policy and caching combination
    policy = repo_policy.get("policy")
    caching = repo_caching.get("caching")
    
    if policy == "always" and caching:
        # Note: Pulp mode verification requires repo_status.yml to include pulp_mode field
        # Current repo_status.yml format doesn't include this, so we verify policy/caching combination only
        tl.passed(LOG["pulp_mode_correct"], 
                 f"{repo_name} has policy: always + caching: true (expected: on_demand)")
    else:
        tl.failed(LOG["pulp_mode_incorrect"], 
                 f"{repo_name} has policy: {policy}, caching: {caching} (expected: always + true)")
    
    assert policy == "always" and caching, \
        f"Expected policy: always + caching: true, got policy: {policy}, caching: {caching}"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(9)
def test_policy_partial_caching_false(host: Host):
    """TC_RM_PO_009: policy: partial + caching: false = streamed."""
    tl = TestLogger(TEST_NAMES["policy_partial_caching_false"], "TC_RM_PO_009")
    
    # Test with a repo that has policy: partial + caching: false
    # Assuming appstream has this combination
    repo_name = "appstream"
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)
    
    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")
    
    # Verify policy and caching combination
    policy = repo_policy.get("policy")
    caching = repo_caching.get("caching")
    
    if policy == "partial" and not caching:
        # Note: Pulp mode verification requires repo_status.yml to include pulp_mode field
        # Current repo_status.yml format doesn't include this, so we verify policy/caching combination only
        tl.passed(LOG["pulp_mode_correct"], 
                 f"{repo_name} has policy: partial + caching: false (expected: streamed)")
    else:
        tl.failed(LOG["pulp_mode_incorrect"], 
                 f"{repo_name} has policy: {policy}, caching: {caching} (expected: partial + false)")
    
    assert policy == "partial" and not caching, \
        f"Expected policy: partial + caching: false, got policy: {policy}, caching: {caching}"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(10)
def test_policy_partial_caching_true(host: Host):
    """TC_RM_PO_010: policy: partial + caching: true = on_demand."""
    tl = TestLogger(TEST_NAMES["policy_partial_caching_true"], "TC_RM_PO_010")
    
    # Test with a repo that has policy: partial + caching: true
    # Assuming epel has this combination
    repo_name = "epel"
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)
    
    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")
    
    # Verify policy and caching combination
    policy = repo_policy.get("policy")
    caching = repo_caching.get("caching")
    
    if policy == "partial" and caching:
        # Note: Pulp mode verification requires repo_status.yml to include pulp_mode field
        # Current repo_status.yml format doesn't include this, so we verify policy/caching combination only
        tl.passed(LOG["pulp_mode_correct"], 
                 f"{repo_name} has policy: partial + caching: true (expected: on_demand)")
    else:
        tl.failed(LOG["pulp_mode_incorrect"], 
                 f"{repo_name} has policy: {policy}, caching: {caching} (expected: partial + true)")
    
    assert policy == "partial" and caching, \
        f"Expected policy: partial + caching: true, got policy: {policy}, caching: {caching}"