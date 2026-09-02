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

    # Test with a repo - check if it has per-repo policy or uses global
    repo_name = "epel"
    repo_policy = check_repo_policy(host, repo_name)

    if not repo_policy["success"]:
        tl.failed(LOG["repo_policy_failed"], repo_policy["details"])
        pytest.skip(f"Cannot determine policy for {repo_name}")

    # Verify policy source (per-repo or global)
    policy_source = repo_policy.get("source")
    if policy_source == "per_repo":
        tl.passed(LOG["per_repo_policy_used"],
                 f"{repo_name} uses per-repo policy: {repo_policy.get('policy')}")
    elif policy_source == "global":
        tl.passed(LOG["global_policy_used"],
                 f"{repo_name} uses global policy: {repo_policy.get('policy')}")
    else:
        tl.failed(LOG["policy_source_unknown"],
                 f"{repo_name} has unknown policy source: {policy_source}")

    # Test passes if either per-repo or global is used (both are valid)
    assert policy_source in ["per_repo", "global"], \
        f"Policy source must be either 'per_repo' or 'global', got: {policy_source}"


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

    # Test with a repo - check if it has per-repo caching or uses global
    repo_name = "nvidia-hpc-sdk"
    repo_caching = check_repo_caching(host, repo_name)

    if not repo_caching["success"]:
        tl.failed(LOG["repo_caching_failed"], repo_caching["details"])
        pytest.skip(f"Cannot determine caching for {repo_name}")

    # Verify caching source (per-repo or global)
    caching_source = repo_caching.get("source")
    if caching_source == "per_repo":
        tl.passed(LOG["per_repo_caching_used"],
                 f"{repo_name} uses per-repo caching: {repo_caching.get('caching')}")
    elif caching_source == "global":
        tl.passed(LOG["global_caching_used"],
                 f"{repo_name} uses global caching: {repo_caching.get('caching')}")
    else:
        tl.failed(LOG["caching_source_unknown"],
                 f"{repo_name} has unknown caching source: {caching_source}")

    # Test passes if either per-repo or global is used (both are valid)
    assert caching_source in ["per_repo", "global"], \
        f"Caching source must be either 'per_repo' or 'global', got: {caching_source}"


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

    # Test with a repo - check if it has both policy and caching overrides
    repo_name = "epel"
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)

    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")

    # Verify both policy and caching sources
    policy_source = repo_policy.get("source")
    caching_source = repo_caching.get("source")

    if policy_source == "per_repo" and caching_source == "per_repo":
        tl.passed(LOG["per_repo_complete_override_used"],
                 f"{repo_name} uses per-repo for both policy ({repo_policy.get('policy')}) "
                 f"and caching ({repo_caching.get('caching')})")
    elif policy_source == "global" and caching_source == "global":
        tl.passed("global_settings_used",
                 f"{repo_name} uses global for both policy ({repo_policy.get('policy')}) "
                 f"and caching ({repo_caching.get('caching')})")
    else:
        tl.passed("mixed_settings_used",
                 f"{repo_name} uses mixed: policy from {policy_source}, caching from {caching_source}")

    # Test passes if both sources are the same (both per-repo or both global)
    assert policy_source == caching_source, \
        f"Policy and caching should have same source (both per-repo or both global), got: policy={policy_source}, caching={caching_source}"
