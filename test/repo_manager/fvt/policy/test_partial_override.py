# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Test Category 2: Partial Override Testing
Tests that per-repo partial overrides work correctly (policy only, caching only, or empty).
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
@pytest.mark.order(4)
def test_per_repo_policy_only(host: Host):
    """TC_RM_PO_004: Per-repo policy only, caching from global."""
    tl = TestLogger(TEST_NAMES["per_repo_policy_only"], "TC_RM_PO_004")

    # Get global settings
    global_config = check_global_repo_config(host)
    global_caching = check_global_caching_policy(host)

    if not global_config["success"] or not global_caching["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read global settings")
        pytest.skip("Cannot verify without global config")

    # Test with a repo that has only policy override (no caching)
    # Assuming cuda has only policy override in test config
    repo_name = "cuda"
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)

    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")

    # Verify policy is from per-repo, caching is from global
    policy_source = repo_policy.get("source")
    caching_source = repo_caching.get("source")

    if policy_source == "per_repo" and caching_source == "global":
        tl.passed(LOG["per_repo_policy_used"],
                 f"{repo_name} uses per-repo policy ({repo_policy.get('policy')}) "
                 f"and global caching ({repo_caching.get('caching')})")
    else:
        tl.failed(LOG["per_repo_policy_not_used"],
                 f"{repo_name} policy source: {policy_source}, caching source: {caching_source}")

    assert policy_source == "per_repo" and caching_source == "global", \
        ASSERT["per_repo_policy_must_use_global_caching"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(5)
def test_per_repo_caching_only(host: Host):
    """TC_RM_PO_005: Per-repo caching only, policy from global."""
    tl = TestLogger(TEST_NAMES["per_repo_caching_only"], "TC_RM_PO_005")

    # Get global settings
    global_config = check_global_repo_config(host)
    global_caching = check_global_caching_policy(host)

    if not global_config["success"] or not global_caching["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read global settings")
        pytest.skip("Cannot verify without global config")

    # Test with a repo that has only caching override (no policy)
    # Assuming docker-ce has only caching override in test config
    repo_name = "docker-ce"
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)

    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")

    # Verify caching is from per-repo, policy is from global
    policy_source = repo_policy.get("source")
    caching_source = repo_caching.get("source")

    if policy_source == "global" and caching_source == "per_repo":
        tl.passed(LOG["per_repo_caching_used"],
                 f"{repo_name} uses global policy ({repo_policy.get('policy')}) "
                 f"and per-repo caching ({repo_caching.get('caching')})")
    else:
        tl.failed(LOG["per_repo_caching_not_used"],
                 f"{repo_name} policy source: {policy_source}, caching source: {caching_source}")

    assert policy_source == "global" and caching_source == "per_repo", \
        ASSERT["per_repo_caching_must_use_global_policy"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(6)
def test_empty_per_repo_config(host: Host):
    """TC_RM_PO_006: Empty per-repo config should use global settings."""
    tl = TestLogger(TEST_NAMES["empty_per_repo_config"], "TC_RM_PO_006")

    # Get global settings
    global_config = check_global_repo_config(host)
    global_caching = check_global_caching_policy(host)

    if not global_config["success"] or not global_caching["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read global settings")
        pytest.skip("Cannot verify without global config")

    # Test with a repo that has empty config (no overrides)
    # Assuming baseos has empty config in test config
    repo_name = "baseos"
    repo_policy = check_repo_policy(host, repo_name)
    repo_caching = check_repo_caching(host, repo_name)

    if not repo_policy["success"] or not repo_caching["success"]:
        tl.failed(LOG["repo_config_failed"], "Cannot determine repo settings")
        pytest.skip(f"Cannot determine settings for {repo_name}")

    # Verify both policy and caching are from global
    policy_source = repo_policy.get("source")
    caching_source = repo_caching.get("source")

    if policy_source == "global" and caching_source == "global":
        tl.passed(LOG["empty_config_uses_global"],
                 f"{repo_name} uses global policy ({repo_policy.get('policy')}) "
                 f"and global caching ({repo_caching.get('caching')})")
    else:
        tl.failed(LOG["empty_config_uses_global"],
                 f"{repo_name} policy source: {policy_source}, caching source: {caching_source}")

    assert policy_source == "global" and caching_source == "global", \
        ASSERT["empty_config_must_use_global"]
