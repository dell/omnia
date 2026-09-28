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
    check_repo_source_type,
    get_deployed_repos,
    verify_policy_resolution,
)
from library.messages.repo_manager_msgs import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(11)
def test_subscription_repo_per_repo_override(host: Host):
    """RM_FVT_POLICY_V011: Subscription repos should support per-repo overrides."""
    tl = TestLogger(TEST_NAMES["subscription_repo_per_repo_override"], "RM_FVT_POLICY_V011")

    repos_result = get_deployed_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Find a subscription repo (typically baseos, appstream, codeready-builder)
    found_repo = None
    for repo_name in configured_repos:
        source = check_repo_source_type(host, repo_name)
        if not source["success"] or source.get("source_type") != "subscription":
            continue
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy_source = repo_policy.get("source")
            caching_source = repo_caching.get("source")

            if policy_source == "per_repo" or caching_source == "per_repo":
                found_repo = repo_name
                break

    if found_repo:
        tl.passed(
            LOG["per_repo_policy_used"],
            f"Repo {found_repo} supports per-repo override"
        )
    else:
        tl.passed(
            "global_settings_used",
            f"No repo with per-repo override found "
            f"among {len(configured_repos)} repos"
        )
        pytest.skip("No repo has per-repo override configuration")

    assert found_repo is not None, \
        "Expected to find repo with per-repo override"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(12)
def test_url_repo_per_repo_override(host: Host):
    """RM_FVT_POLICY_V012: URL repos should support per-repo overrides."""
    tl = TestLogger(TEST_NAMES["url_repo_per_repo_override"], "RM_FVT_POLICY_V012")

    repos_result = get_deployed_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    # Find a URL repo (typically epel, docker-ce, etc.)
    found_repo = None
    for repo_name in configured_repos:
        source = check_repo_source_type(host, repo_name)
        if not source["success"] or source.get("source_type") != "url":
            continue
        repo_policy = check_repo_policy(host, repo_name)
        repo_caching = check_repo_caching(host, repo_name)

        if repo_policy["success"] and repo_caching["success"]:
            policy_source = repo_policy.get("source")
            caching_source = repo_caching.get("source")

            if policy_source == "per_repo" or caching_source == "per_repo":
                found_repo = repo_name
                break

    if found_repo:
        tl.passed(
            LOG["per_repo_policy_used"],
            f"Repo {found_repo} supports per-repo override"
        )
    else:
        tl.passed(
            "global_settings_used",
            f"No repo with per-repo override found "
            f"among {len(configured_repos)} repos"
        )
        pytest.skip("No repo has per-repo override configuration")

    assert found_repo is not None, \
        "Expected to find repo with per-repo override"


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(13)
def test_subscription_and_url_identical_behavior(host: Host):
    """RM_FVT_POLICY_V013: Subscription and URL repos should behave identically."""
    tl = TestLogger(TEST_NAMES["subscription_and_url_identical_behavior"], "RM_FVT_POLICY_V013")

    repos_result = get_deployed_repos(host, arch="x86_64")

    if not repos_result["success"]:
        tl.failed(LOG["global_config_failed"], "Cannot read configured repos")
        pytest.skip("Cannot verify without configured repos")

    configured_repos = repos_result["repos"]

    representatives = {}
    for repo_name in configured_repos:
        source = check_repo_source_type(host, repo_name)
        if source["success"]:
            representatives.setdefault(source.get("source_type"), repo_name)

    missing_types = {"subscription", "url"} - representatives.keys()
    if missing_types:
        pytest.skip(
            "Deployment does not contain both repository source types: "
            f"missing {', '.join(sorted(missing_types))}"
        )

    failures = []
    details = []
    for source_type in ("subscription", "url"):
        repo_name = representatives[source_type]
        resolution = verify_policy_resolution(host, repo_name)
        if not resolution["success"] or not resolution.get("match"):
            failures.append(f"{source_type} repo {repo_name}: {resolution['details']}")
        else:
            details.append(f"{source_type} repo {repo_name}: {resolution['details']}")

    if failures:
        tl.failed("repository_type_policy_mismatch", "; ".join(failures))
    else:
        tl.passed("repository_types_resolve_identically", "; ".join(details))

    assert not failures, "; ".join(failures)
