# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — User Registry validation tests.

RM_FVT_USER_REGISTRY_E001: Deploy validation playbook (includes user registry checks)
RM_FVT_USER_REGISTRY_V001: Verify registries section exists in repo_manager_config.yml
RM_FVT_USER_REGISTRY_V002: Verify registry entries have valid structure
RM_FVT_USER_REGISTRY_V003: Verify registry base_url values are valid HTTP(S) origins
RM_FVT_USER_REGISTRY_V004: Verify configured registries are reachable
RM_FVT_USER_REGISTRY_V005: Verify TLS certificate paths exist on disk
RM_FVT_USER_REGISTRY_V006: Verify client cert and key are configured together
RM_FVT_USER_REGISTRY_V007: Verify registry auth type is valid (none or basic)
RM_FVT_USER_REGISTRY_V008: Verify credentials are configured for basic auth registries
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_user_registry_section_exists,
    check_user_registry_structure,
    check_user_registry_base_url_valid,
    check_user_registry_reachability,
    check_user_registry_tls_cert_paths,
    check_user_registry_tls_pair_consistent,
    check_user_registry_auth_type,
    check_user_registry_credentials,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_user_registry_validation_deploy(host):
    """RM_FVT_USER_REGISTRY_E001: Deploy validation playbook (includes user registry checks)."""
    assert host is not None
    tl = TestLogger(TEST_NAMES["user_registry_validation_deploy"], "RM_FVT_USER_REGISTRY_E001")
    result = run_playbook(tag="precheck", verbosity=1)

    if result["success"]:
        tl.passed(LOG["user_registry_validation_ok"], result.get("details", ""))
    else:
        tl.failed(LOG["user_registry_validation_failed"], result.get("error", ""))

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_user_registry_section_exists(host):
    """RM_FVT_USER_REGISTRY_V001: Verify registries section exists in repo_manager_config.yml."""
    tl = TestLogger(TEST_NAMES["user_registry_section_exists"], "RM_FVT_USER_REGISTRY_V001")
    result = check_user_registry_section_exists(host)

    if result["success"]:
        tl.passed(LOG["user_registry_section_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_section_missing"], result["details"])

    assert result["success"], ASSERT["user_registry_section_must_exist"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_user_registry_structure_valid(host):
    """RM_FVT_USER_REGISTRY_V002: Verify registry entries have valid structure."""
    tl = TestLogger(TEST_NAMES["user_registry_structure_valid"], "RM_FVT_USER_REGISTRY_V002")
    result = check_user_registry_structure(host)

    if result.get("skipped"):
        tl.passed(LOG["user_registry_no_registries"], result["details"])
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_structure_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_structure_invalid"], result["details"])

    assert result["success"], ASSERT["user_registry_structure_must_be_valid"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(3)
def test_user_registry_base_url_valid(host):
    """RM_FVT_USER_REGISTRY_V003: Verify registry base_url values are valid HTTP(S) origins."""
    tl = TestLogger(TEST_NAMES["user_registry_base_url_valid"], "RM_FVT_USER_REGISTRY_V003")
    result = check_user_registry_base_url_valid(host)

    if result.get("skipped"):
        tl.passed(LOG["user_registry_no_registries"], result["details"])
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_base_url_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_base_url_invalid"], result["details"])

    assert result["success"], ASSERT["user_registry_base_url_must_be_valid"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(4)
def test_user_registry_reachable(host):
    """RM_FVT_USER_REGISTRY_V004: Verify configured registries are reachable."""
    tl = TestLogger(TEST_NAMES["user_registry_reachable"], "RM_FVT_USER_REGISTRY_V004")
    result = check_user_registry_reachability(host)

    if result.get("skipped"):
        tl.passed(LOG["user_registry_no_registries"], result["details"])
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_reachable_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_unreachable"], result["details"])

    assert result["success"], ASSERT["user_registry_must_be_reachable"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(5)
def test_user_registry_tls_cert_paths_valid(host):
    """RM_FVT_USER_REGISTRY_V005: Verify TLS certificate paths exist on disk."""
    tl = TestLogger(TEST_NAMES["user_registry_tls_cert_paths_valid"], "RM_FVT_USER_REGISTRY_V005")
    result = check_user_registry_tls_cert_paths(host)

    if result.get("skipped"):
        tl.passed(LOG["user_registry_no_registries"], result["details"])
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_tls_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_tls_invalid"], result["details"])

    assert result["success"], ASSERT["user_registry_tls_must_be_valid"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(6)
def test_user_registry_tls_pair_consistent(host):
    """RM_FVT_USER_REGISTRY_V006: Verify client cert and key are configured together."""
    tl = TestLogger(TEST_NAMES["user_registry_tls_pair_consistent"], "RM_FVT_USER_REGISTRY_V006")
    result = check_user_registry_tls_pair_consistent(host)

    if result.get("skipped"):
        tl.passed(LOG["user_registry_no_registries"], result["details"])
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_tls_pair_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_tls_pair_invalid"], result["details"])

    assert result["success"], ASSERT["user_registry_tls_pair_must_be_consistent"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(7)
def test_user_registry_auth_type_valid(host):
    """RM_FVT_USER_REGISTRY_V007: Verify registry auth type is valid (none or basic)."""
    tl = TestLogger(TEST_NAMES["user_registry_auth_type_valid"], "RM_FVT_USER_REGISTRY_V007")
    result = check_user_registry_auth_type(host)

    if result.get("skipped"):
        tl.passed(LOG["user_registry_no_registries"], result["details"])
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_auth_type_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_auth_type_invalid"], result["details"])

    assert result["success"], ASSERT["user_registry_auth_type_must_be_valid"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(8)
def test_user_registry_credentials_present(host):
    """RM_FVT_USER_REGISTRY_V008: Verify credentials are configured for basic auth registries."""
    tl = TestLogger(TEST_NAMES["user_registry_credentials_present"], "RM_FVT_USER_REGISTRY_V008")
    result = check_user_registry_credentials(host)

    if result.get("skipped"):
        tl.passed(LOG["user_registry_no_registries"], result["details"])
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_credentials_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_credentials_missing"], result["details"])

    assert result["success"], ASSERT["user_registry_credentials_must_exist"]
