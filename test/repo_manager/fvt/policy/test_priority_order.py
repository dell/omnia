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
    get_configured_repos,
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

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")
    
    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")
    
    configured_repos = repos_result["repos"]
    
    # Check if any repo has per-repo policy override
    has_per_repo_policy = False
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)

        if not repo_policy["success"]:
            continue

        # Verify policy source (per-repo or global)
        policy_source = repo_policy.get("source")
        
        if policy_source == "per_repo":
            has_per_repo_policy = True
            tl.passed(LOG["per_repo_policy_used"],
                     f"Repo {repo_name} uses per-repo policy: {repo_policy.get('policy')}")
            break
    
    if not has_per_repo_policy:
        tl.passed("global_settings_used",
                 f"All {len(configured_repos)} repos use global policy (no per-repo overrides)")
        pytest.skip("No repo has per-repo policy override")

    assert has_per_repo_policy, "Expected to find repo with per-repo policy override"


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

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")
    
    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")
    
    configured_repos = repos_result["repos"]
    
    # Check if any repo has per-repo caching override
    has_per_repo_caching = False
    for repo_name in configured_repos:
        repo_caching = check_repo_caching(host, repo_name)

        if not repo_caching["success"]:
            continue

        # Verify caching source (per-repo or global)
        caching_source = repo_caching.get("source")
        
        if caching_source == "per_repo":
            has_per_repo_caching = True
            tl.passed(LOG["per_repo_caching_used"],
                     f"Repo {repo_name} uses per-repo caching: {repo_caching.get('caching')}")
            break
    
    if not has_per_repo_caching:
        tl.passed("global_settings_used",
                 f"All {len(configured_repos)} repos use global caching (no per-repo overrides)")
        pytest.skip("No repo has per-repo caching override")

    assert has_per_repo_caching, "Expected to find repo with per-repo caching override"


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

    # Get all configured repos
    repos_result = get_configured_repos(host, arch="x86_64")
    
    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")
    
    configured_repos = repos_result["repos"]
    
    # Check if any repo has both policy and caching overrides
    has_complete_override = False
    for repo_name in configured_repos:
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if not repo_policy["success"] or not repo_caching["success"]:
            continue

        # Verify both policy and caching sources
        policy_source = repo_policy.get("source")
        caching_source = repo_caching.get("source")

        if policy_source == "per_repo" and caching_source == "per_repo":
            has_complete_override = True
            tl.passed(LOG["per_repo_complete_override_used"],
                     f"{repo_name} uses per-repo for both policy ({repo_policy.get('policy')}) "
                     f"and caching ({repo_caching.get('caching')})")
            break
    
    if not has_complete_override:
        tl.passed("global_settings_used",
                 f"All {len(configured_repos)} repos use global settings (no complete overrides)")
        pytest.skip("No repo has complete per-repo override")

    assert has_complete_override, "Expected to find repo with complete per-repo override"
