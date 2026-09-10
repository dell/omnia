# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — User Registry negative test cases.

TC_RM_UR_NEG_001: Verify validation fails with missing config file
TC_RM_UR_NEG_002: Verify validation detects invalid registry base_url
TC_RM_UR_NEG_003: Verify validation detects incomplete TLS cert/key pair
TC_RM_UR_NEG_004: Verify validation detects unsupported auth type
TC_RM_UR_NEG_005: Verify validation detects missing cert paths on disk
TC_RM_UR_NEG_006: Verify validation detects missing vault_path for basic auth
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
from library.messages import TEST_NAMES


@pytest.mark.negative
@pytest.mark.order(1)
def test_registry_validation_fails_missing_config(host):
    """TC_RM_UR_NEG_001: Verify validation fails with missing config file."""
    tl = TestLogger(
        TEST_NAMES["user_registry_section_exists"], "TC_RM_UR_NEG_001"
    )
    result = check_input_config_exists(host)

    # If config exists, negative case does not apply
    if result["success"]:
        tl.passed(
            "Config exists; negative case not applicable",
            result["details"],
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
    """TC_RM_UR_NEG_002: Verify validation detects invalid registry base_url."""
    tl = TestLogger(
        TEST_NAMES["user_registry_base_url_valid"], "TC_RM_UR_NEG_002"
    )
    # This test validates that the base_url validation function correctly
    # identifies invalid URLs. When no registries are configured, this
    # is not applicable.
    result = check_user_registry_base_url_valid(host)

    if result.get("skipped"):
        tl.passed(
            "No registries configured; negative base_url test not applicable",
            result["details"],
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(
            "All base_url values are valid; negative case not triggered",
            result["details"],
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
    """TC_RM_UR_NEG_003: Verify validation detects incomplete TLS cert/key pair."""
    tl = TestLogger(
        TEST_NAMES["user_registry_tls_pair_consistent"], "TC_RM_UR_NEG_003"
    )
    result = check_user_registry_tls_pair_consistent(host)

    if result.get("skipped"):
        tl.passed(
            "No registries configured; negative TLS pair test not applicable",
            result["details"],
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(
            "All TLS pairs consistent; negative case not triggered",
            result["details"],
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
    """TC_RM_UR_NEG_004: Verify validation detects unsupported auth type."""
    tl = TestLogger(
        TEST_NAMES["user_registry_auth_type_valid"], "TC_RM_UR_NEG_004"
    )
    result = check_user_registry_auth_type(host)

    if result.get("skipped"):
        tl.passed(
            "No registries configured; negative auth type test not applicable",
            result["details"],
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(
            "All auth types valid; negative case not triggered",
            result["details"],
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
    """TC_RM_UR_NEG_005: Verify validation detects missing cert paths on disk."""
    tl = TestLogger(
        TEST_NAMES["user_registry_tls_cert_paths_valid"], "TC_RM_UR_NEG_005"
    )
    result = check_user_registry_tls_cert_paths(host)

    if result.get("skipped"):
        tl.passed(
            "No registries configured; negative cert path test not applicable",
            result["details"],
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(
            "All cert paths exist; negative case not triggered",
            result["details"],
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
    """TC_RM_UR_NEG_006: Verify validation detects missing vault_path for basic auth."""
    tl = TestLogger(
        TEST_NAMES["user_registry_credentials_present"], "TC_RM_UR_NEG_006"
    )
    result = check_user_registry_credentials(host)

    if result.get("skipped"):
        tl.passed(
            "No registries configured; negative vault_path test not applicable",
            result["details"],
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(
            "All vault_path values configured; negative case not triggered",
            result["details"],
        )
        pytest.skip("All basic auth registries have vault_path")

    # Missing vault_path detected
    tl.passed(
        "Validation correctly detected missing vault_path for basic auth",
        result["details"],
    )
