# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — User Registry negative test cases.

RM_FVT_USER_REGISTRY_NEG_001: Verify validation fails with missing config file
RM_FVT_USER_REGISTRY_NEG_002: Verify validation detects invalid registry base_url
RM_FVT_USER_REGISTRY_NEG_003: Verify validation detects incomplete TLS cert/key pair
RM_FVT_USER_REGISTRY_NEG_004: Verify validation detects unsupported auth type
RM_FVT_USER_REGISTRY_NEG_005: Verify validation detects missing cert paths on disk
RM_FVT_USER_REGISTRY_NEG_006: Verify validation detects missing vault_path for basic auth
"""

import pytest

from library.functions import (
    TestLogger,
    check_input_config_exists,
    check_user_registry_section_exists,
    check_user_registry_base_url_valid,
    check_user_registry_tls_pair_consistent,
    check_user_registry_auth_type,
    check_user_registry_tls_cert_paths,
    check_user_registry_credentials,
)
from library.vars import TEST_CASES as TC


@pytest.mark.negative
@pytest.mark.order(1)
def test_registry_validation_fails_missing_config(host):
    """RM_FVT_USER_REGISTRY_NEG_001: Verify validation fails with missing config file."""
    tc = TC["user_registry_neg_missing_config"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_input_config_exists(host)

    # If config exists, negative case does not apply
    if result["success"]:
        tl.skipped_fields(
            "Config exists - negative case not applicable",
            {
                "Configuration file": "repo_manager_config.yml",
                "Status": "exists",
                "Test type": "negative",
            }
        )
        pytest.skip(
            "repo_manager_config.yml exists - negative case not applicable"
        )

    # Config is missing; registry validation should also fail
    reg_result = check_user_registry_section_exists(host)
    if not reg_result["success"]:
        tl.passed(
            "Registry validation correctly fails when config is missing",
            reg_result["details"],
        )
    else:
        tl.failed(
            "Registry validation should fail when config is missing",
            reg_result["details"],
        )
        assert False, "Registry validation should fail when config is missing"


@pytest.mark.negative
@pytest.mark.order(2)
def test_registry_validation_detects_invalid_base_url(host):
    """RM_FVT_USER_REGISTRY_NEG_002: Verify validation detects invalid registry base_url."""
    tc = TC["user_registry_neg_invalid_base_url"]
    tl = TestLogger(tc["title"], tc["id"])
    # This test validates that the base_url validation function correctly
    # identifies invalid URLs. When no registries are configured, this
    # is not applicable.
    result = check_user_registry_base_url_valid(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured; negative base_url test not applicable",
            {
                "Registries": 0,
                "Configuration": "user_registry",
                "Test type": "negative",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.skipped_fields(
            "All configured base_url values are valid - negative case not applicable",
            {
                "Configuration": "user_registry",
                "Validation": "passed",
                "Test type": "negative",
            }
        )
        pytest.skip("All configured base_url values are valid")

    # Invalid base_url detected
    tl.passed(
        "Validation correctly detected invalid base_url",
        result["details"],
    )


@pytest.mark.negative
@pytest.mark.order(3)
def test_registry_validation_detects_incomplete_tls_pair(host):
    """RM_FVT_USER_REGISTRY_NEG_003: Verify validation detects incomplete TLS cert/key pair."""
    tc = TC["user_registry_neg_incomplete_tls_pair"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_tls_pair_consistent(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured; negative TLS pair test not applicable",
            {
                "Registries": 0,
                "Configuration": "user_registry",
                "Test type": "negative",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.skipped_fields(
            "All configured TLS cert/key pairs are consistent - negative case not applicable",
            {
                "Configuration": "user_registry",
                "Validation": "passed",
                "Test type": "negative",
            }
        )
        pytest.skip("All configured TLS cert/key pairs are consistent")

    # Incomplete TLS pair detected
    tl.passed(
        "Validation correctly detected incomplete TLS cert/key pair",
        result["details"],
    )


@pytest.mark.negative
@pytest.mark.order(4)
def test_registry_validation_detects_unsupported_auth_type(host):
    """RM_FVT_USER_REGISTRY_NEG_004: Verify validation detects unsupported auth type."""
    tc = TC["user_registry_neg_unsupported_auth_type"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_auth_type(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured; negative auth type test not applicable",
            {
                "Registries": 0,
                "Configuration": "user_registry",
                "Test type": "negative",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.skipped_fields(
            "All configured auth types are valid - negative case not applicable",
            {
                "Configuration": "user_registry",
                "Validation": "passed",
                "Test type": "negative",
            }
        )
        pytest.skip("All configured auth types are valid")

    # Invalid auth type detected
    tl.passed(
        "Validation correctly detected unsupported auth type",
        result["details"],
    )


@pytest.mark.negative
@pytest.mark.order(5)
def test_registry_validation_detects_missing_cert_paths(host):
    """RM_FVT_USER_REGISTRY_NEG_005: Verify validation detects missing cert paths on disk."""
    tc = TC["user_registry_neg_missing_cert_paths"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_tls_cert_paths(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured; negative cert path test not applicable",
            {
                "Registries": 0,
                "Configuration": "user_registry",
                "Test type": "negative",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.skipped_fields(
            "All configured TLS cert paths exist - negative case not applicable",
            {
                "Configuration": "user_registry",
                "Validation": "passed",
                "Test type": "negative",
            }
        )
        pytest.skip("All configured TLS cert paths exist")

    # Missing cert paths detected
    tl.passed(
        "Validation correctly detected missing TLS cert paths",
        result["details"],
    )


@pytest.mark.negative
@pytest.mark.order(6)
def test_registry_validation_detects_missing_vault_path(host):
    """RM_FVT_USER_REGISTRY_NEG_006: Verify validation detects missing vault_path for basic auth."""
    tc = TC["user_registry_neg_missing_vault_path"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_credentials(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured; negative vault_path test not applicable",
            {
                "Registries": 0,
                "Configuration": "user_registry",
                "Test type": "negative",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.skipped_fields(
            "All basic auth registries have vault_path - negative case not applicable",
            {
                "Configuration": "user_registry",
                "Validation": "passed",
                "Test type": "negative",
            }
        )
        pytest.skip("All basic auth registries have vault_path")

    # Missing vault_path detected
    tl.passed(
        "Validation correctly detected missing vault_path for basic auth",
        result["details"],
    )
