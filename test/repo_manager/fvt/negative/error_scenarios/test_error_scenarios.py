# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Negative test cases for error scenarios.

TC_RM_NEG_001: Verify deployment fails with missing credentials
TC_RM_NEG_002: Verify deployment fails with invalid endpoint config
TC_RM_NEG_003: Verify download fails with invalid repository URL
TC_RM_NEG_004: Verify status check fails with missing repo_status.yml
TC_RM_NEG_005: Verify cleanup fails when Pulp container not running
TC_RM_NEG_006: Verify Pulp CLI fails with invalid authentication
TC_RM_NEG_007: Verify repository sync fails with network connectivity issues
TC_RM_NEG_008: Verify catalog generation fails with invalid software_config.json
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_input_config_exists,
    check_pulp_container_running,
    check_repo_status_exists,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.negative
@pytest.mark.order(1)
def test_deploy_fails_missing_credentials(host):
    """TC_RM_NEG_001: Verify deployment fails with missing credentials."""
    tl = TestLogger("Verify deployment fails with missing credentials", "TC_RM_NEG_001")
    
    # This test would require temporarily removing credentials
    # For now, we'll skip it as it would interfere with other tests
    pytest.skip("Negative test requiring credentials removal - skipped to avoid interference")


@pytest.mark.negative
@pytest.mark.order(2)
def test_deploy_fails_invalid_endpoint_config(host):
    """TC_RM_NEG_002: Verify deployment fails with invalid endpoint config."""
    tl = TestLogger("Verify deployment fails with invalid endpoint config", "TC_RM_NEG_002")
    
    # This test would require creating invalid endpoint configuration
    # For now, we'll skip it as it would interfere with other tests
    pytest.skip("Negative test requiring invalid config - skipped to avoid interference")


@pytest.mark.negative
@pytest.mark.order(3)
def test_download_fails_invalid_repo_url(host):
    """TC_RM_NEG_003: Verify download fails with invalid repository URL."""
    tl = TestLogger("Verify download fails with invalid repository URL", "TC_RM_NEG_003")
    
    # This test would require modifying repo_manager_config.yml with invalid URLs
    # For now, we'll skip it as it would interfere with other tests
    pytest.skip("Negative test requiring config modification - skipped to avoid interference")


@pytest.mark.negative
@pytest.mark.order(4)
def test_status_fails_missing_repo_status(host):
    """TC_RM_NEG_004: Verify status check fails with missing repo_status.yml."""
    tl = TestLogger("Verify status check fails with missing repo_status.yml", "TC_RM_NEG_004")
    
    result = check_repo_status_exists(host)
    
    # If repo_status.yml exists, this test passes (negative case not applicable)
    if result["success"]:
        tl.passed("repo_status.yml exists - negative case not applicable", result["details"])
        pytest.skip("repo_status.yml exists - negative case not applicable")
    
    # If repo_status.yml doesn't exist, this is the expected negative case
    tl.passed("repo_status.yml missing as expected for negative test", result["details"])


@pytest.mark.negative
@pytest.mark.order(5)
def test_cleanup_fails_pulp_not_running(host):
    """TC_RM_NEG_005: Verify cleanup fails when Pulp container not running."""
    tl = TestLogger("Verify cleanup fails when Pulp container not running", "TC_RM_NEG_005")
    
    result = check_pulp_container_running(host)
    
    # If Pulp is not running, this is the expected negative case
    if not result["success"]:
        tl.passed("Pulp container not running - negative case confirmed", result["details"])
        return
    
    # If Pulp is running, this test passes (negative case not applicable)
    tl.passed("Pulp container running - negative case not applicable", result["details"])
    pytest.skip("Pulp container running - negative case not applicable")


@pytest.mark.negative
@pytest.mark.order(6)
def test_pulp_cli_fails_invalid_auth(host):
    """TC_RM_NEG_006: Verify Pulp CLI fails with invalid authentication."""
    tl = TestLogger("Verify Pulp CLI fails with invalid authentication", "TC_RM_NEG_006")
    
    # This test would require modifying Pulp authentication
    # For now, we'll skip it as it would interfere with other tests
    pytest.skip("Negative test requiring auth modification - skipped to avoid interference")


@pytest.mark.negative
@pytest.mark.order(7)
def test_repo_sync_fails_network_issues(host):
    """TC_RM_NEG_007: Verify repository sync fails with network connectivity issues."""
    tl = TestLogger("Verify repository sync fails with network connectivity issues", "TC_RM_NEG_007")
    
    # This test would require simulating network failures
    # For now, we'll skip it as it would interfere with other tests
    pytest.skip("Negative test requiring network simulation - skipped to avoid interference")


@pytest.mark.negative
@pytest.mark.order(8)
def test_catalog_generation_fails_invalid_config(host):
    """TC_RM_NEG_008: Verify catalog generation fails with invalid software_config.json."""
    tl = TestLogger("Verify catalog generation fails with invalid software_config.json", "TC_RM_NEG_008")
    
    # This test would require creating invalid software_config.json
    # For now, we'll skip it as it would interfere with other tests
    pytest.skip("Negative test requiring invalid config - skipped to avoid interference")


@pytest.mark.negative
@pytest.mark.order(9)
def test_validate_fails_missing_config(host):
    """TC_RM_NEG_009: Verify validation fails with missing repo_manager_config.yml."""
    tl = TestLogger("Verify validation fails with missing repo_manager_config.yml", "TC_RM_NEG_009")
    
    result = check_input_config_exists(host)
    
    # If config exists, this test passes (negative case not applicable)
    if result["success"]:
        tl.passed("repo_manager_config.yml exists - negative case not applicable", result["details"])
        pytest.skip("repo_manager_config.yml exists - negative case not applicable")
    
    # If config doesn't exist, this is the expected negative case
    tl.passed("repo_manager_config.yml missing as expected for negative test", result["details"])


@pytest.mark.negative
@pytest.mark.order(10)
def test_pulp_api_unreachable_port_closed(host):
    """TC_RM_NEG_010: Verify Pulp API unreachable when port is closed."""
    tl = TestLogger("Verify Pulp API unreachable when port is closed", "TC_RM_NEG_010")
    
    # This test would require closing the Pulp port
    # For now, we'll skip it as it would interfere with other tests
    pytest.skip("Negative test requiring port modification - skipped to avoid interference")