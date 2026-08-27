# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Test Category 1: Priority Order Testing
Tests that per-repo policy overrides take precedence over global settings.
"""

import pytest
from testinfra.host import Host

from library.functions import (
    TestLogger,
    check_repo_policy,
    check_repo_caching,
    check_global_repo_config,
    check_global_caching_policy,
)
from library.messages.repo_manager_msgs import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_per_repo_policy_overrides_global(host: Host):
    """TC_RM_PO_001: Per-repo policy should win over global repo_config."""
    tl = TestLogger(TEST_NAMES["per_repo_policy_override"], "TC_RM_PO_001")
    
    # Get global settings
    global_config = check_global_repo_config(host)
    if not global_config["success"]:
        tl.failed(LOG["global_config_failed"], global_config["details"])
        pytest.skip("Cannot verify without global config")
    
    # Test with a repo that has per-repo policy override
    # Assuming epel has per-repo policy override in test config
    repo_name = "epel"
    repo_policy = check_repo_policy(host, repo_name)
    
    if not repo_policy["success"]:
        tl.failed(LOG["repo_policy_failed"], repo_policy["details"])
        pytest.skip(f"Cannot determine policy for {repo_name}")
    
    # Verify per-repo policy is used
    if repo_policy.get("source") == "per_repo":
        tl.passed(LOG["per_repo_policy_used"], 
                 f"{repo_name} uses per-repo policy: {repo_policy.get('policy')}")
    else:
        tl.failed(LOG["per_repo_policy_not_used"], 
                 f"{repo_name} uses global policy instead of per-repo")
    
    assert repo_policy.get("source") == "per_repo", ASSERT["per_repo_policy_must_override"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_per_repo_caching_overrides_global(host: Host):
    """TC_RM_PO_002: Per-repo caching should win over global CACHING_POLICY."""
    tl = TestLogger(TEST_NAMES["per_repo_caching_override"], "TC_RM_PO_002")
    
    # Get global settings
    global_caching = check_global_caching_policy(host)
    if not global_caching["success"]:
        tl.failed(LOG["global_caching_failed"], global_caching["details"])
        pytest.skip("Cannot verify without global caching config")
    
    # Test with a repo that has per-repo caching override
    # Assuming nvidia-hpc-sdk has per-repo caching override in test config
    repo_name = "nvidia-hpc-sdk"
    repo_caching = check_repo_caching(host, repo_name)
    
    if not repo_caching["success"]:
        tl.failed(LOG["repo_caching_failed"], repo_caching["details"])
        pytest.skip(f"Cannot determine caching for {repo_name}")
    
    # Verify per-repo caching is used
    if repo_caching.get("source") == "per_repo":
        tl.passed(LOG["per_repo_caching_used"], 
                 f"{repo_name} uses per-repo caching: {repo_caching.get('caching')}")
    else:
        tl.failed(LOG["per_repo_caching_not_used"], 
                 f"{repo_name} uses global caching instead of per-repo")
    
    assert repo_caching.get("source") == "per_repo", ASSERT["per_repo_caching_must_override"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(3)
def test_per_repo_complete_override(host: Host):
    """TC_RM_PO_003: Per-repo should completely override global settings."""
    tl = TestLogger(TEST_NAMES["per_repo_complete_override"], "TC_RM_PO_003")
    
    # Get global settings
    global_config = check_global_repo_config(host)
    global_caching = check_global_caching_policy(host)
    
    if not global_config["success"] or not global_caching["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read global settings")
        pytest.skip("Cannot verify without global config")
    
    # Test with a repo that has both policy and caching overrides
    # Assuming a test repo has complete override
    repo_name = "epel"  # This should have both policy and caching overrides
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)
    
    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")
    
    # Verify both policy and caching are from per-repo
    policy_source = repo_policy.get("source")
    caching_source = repo_caching.get("source")
    
    if policy_source == "per_repo" and caching_source == "per_repo":
        tl.passed(LOG["per_repo_complete_override_used"], 
                 f"{repo_name} uses per-repo for both policy ({repo_policy.get('policy')}) "
                 f"and caching ({repo_caching.get('caching')})")
    else:
        tl.failed(LOG["per_repo_complete_override_not_used"], 
                 f"{repo_name} policy source: {policy_source}, caching source: {caching_source}")
    
    assert policy_source == "per_repo" and caching_source == "per_repo", \
        ASSERT["per_repo_must_completely_override"]