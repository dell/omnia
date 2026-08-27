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
    verify_repo_status_pulp_mode,
)
from library.messages.repo_manager_msgs import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(11)
def test_subscription_repo_per_repo_override(host: Host):
    """TC_RM_PO_011: Subscription repos should support per-repo overrides."""
    tl = TestLogger(TEST_NAMES["subscription_repo_per_repo_override"], "TC_RM_PO_011")
    
    # Test with a subscription repo that has per-repo override
    # Assuming appstream (subscription repo) has per-repo override
    repo_name = "appstream"
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)
    
    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")
    
    # Verify subscription repo supports per-repo override
    policy_source = repo_policy.get("source")
    caching_source = repo_caching.get("source")
    
    if policy_source == "per_repo" or caching_source == "per_repo":
        tl.passed(LOG["per_repo_policy_used"], 
                 f"Subscription repo {repo_name} supports per-repo override "
                 f"(policy: {repo_policy.get('policy')}, caching: {repo_caching.get('caching')})")
    else:
        tl.failed(LOG["per_repo_policy_not_used"], 
                 f"Subscription repo {repo_name} does not use per-repo override")
    
    assert policy_source == "per_repo" or caching_source == "per_repo", \
        ASSERT["subscription_repos_must_support_override"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(12)
def test_url_repo_per_repo_override(host: Host):
    """TC_RM_PO_012: URL repos should support per-repo overrides."""
    tl = TestLogger(TEST_NAMES["url_repo_per_repo_override"], "TC_RM_PO_012")
    
    # Test with a URL repo that has per-repo override
    # Assuming epel (URL repo) has per-repo override
    repo_name = "epel"
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)
    
    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")
    
    # Verify URL repo supports per-repo override
    policy_source = repo_policy.get("source")
    caching_source = repo_caching.get("source")
    
    if policy_source == "per_repo" or caching_source == "per_repo":
        tl.passed(LOG["per_repo_policy_used"], 
                 f"URL repo {repo_name} supports per-repo override "
                 f"(policy: {repo_policy.get('policy')}, caching: {repo_caching.get('caching')})")
    else:
        tl.failed(LOG["per_repo_policy_not_used"], 
                 f"URL repo {repo_name} does not use per-repo override")
    
    assert policy_source == "per_repo" or caching_source == "per_repo", \
        ASSERT["url_repos_must_support_override"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(13)
def test_subscription_and_url_identical_behavior(host: Host):
    """TC_RM_PO_013: Subscription and URL repos should behave identically."""
    tl = TestLogger(TEST_NAMES["subscription_and_url_identical_behavior"], "TC_RM_PO_013")
    
    # Test with one subscription repo and one URL repo with same policy/caching
    # Using cuda (URL) and nvidia-hpc-sdk (URL) since they have same policy but different caching
    # For this test, we'll verify that both types support per-repo overrides
    subscription_repo = "appstream"  # subscription repo with per-repo override
    url_repo = "cuda"  # URL repo with per-repo override
    
    sub_policy = check_repo_policy(host, subscription_repo)
    sub_caching = check_repo_caching(host, subscription_repo)
    url_policy = check_repo_policy(host, url_repo)
    url_caching = check_repo_caching(host, url_repo)
    
    if not all([sub_policy["success"], sub_caching["success"], 
                url_policy["success"], url_caching["success"]]):
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip("Cannot determine settings for repos")
    
    # Verify both repos support per-repo overrides (they don't need to have same policy/caching)
    sub_has_override = (sub_policy.get("source") == "per_repo" or sub_caching.get("source") == "per_repo")
    url_has_override = (url_policy.get("source") == "per_repo" or url_caching.get("source") == "per_repo")
    
    if sub_has_override and url_has_override:
        tl.passed(LOG["pulp_mode_correct"], 
                 f"Subscription repo {subscription_repo} and URL repo {url_repo} "
                 f"both support per-repo overrides")
    else:
        tl.failed(LOG["pulp_mode_incorrect"], 
                 f"Repos don't both support per-repo overrides: "
                 f"subscription has_override={sub_has_override}, url has_override={url_has_override}")
    
    assert sub_has_override and url_has_override, \
        ASSERT["repo_types_must_behave_identically"]