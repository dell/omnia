# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Cleanup scenario verification tests.

TC_RM_CL_000: Deploy repo_manager --tags cleanup
TC_RM_CL_001: Verify Pulp container removed
TC_RM_CL_002: Verify Pulp CLI removed
TC_RM_CL_003: Verify Pulp directories removed
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_pulp_container_removed,
    check_pulp_cli_removed,
    check_pulp_directories_removed,
)
from library.vars.common_vars import _get_input_path
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(100)
def test_deploy_cleanup(host):
    """TC_RM_CL_000: Deploy repo_manager --tags cleanup."""
    # Check if cleanup input configuration exists
    input_path = _get_input_path()
    cleanup_input = f"{input_path}/cleanup_input.yml"
    
    result = host.run(f"test -f {cleanup_input} && echo 'exists' || echo 'missing'")
    if "missing" in result.stdout:
        pytest.skip("Cleanup input configuration not found - cleanup test skipped")
    
    tl = TestLogger(TEST_NAMES["pulp_container_removed"], "TC_RM_CL_000")
    result = run_playbook(tag="cleanup")

    if result["success"]:
        tl.passed("repo_manager --tags cleanup completed", result.get("details", ""))
    else:
        tl.failed("repo_manager --tags cleanup failed", result.get("error", ""))

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(101)
def test_pulp_container_removed(host):
    """TC_RM_CL_001: Verify Pulp container removed."""
    # Skip if cleanup input doesn't exist
    input_path = _get_input_path()
    cleanup_input = f"{input_path}/cleanup_input.yml"
    
    result = host.run(f"test -f {cleanup_input} && echo 'exists' || echo 'missing'")
    if "missing" in result.stdout:
        pytest.skip("Cleanup input configuration not found - cleanup test skipped")
    
    tl = TestLogger(TEST_NAMES["pulp_container_removed"], "TC_RM_CL_001")
    result = check_pulp_container_removed(host)

    if result["success"]:
        tl.passed(LOG["pulp_container_removed"], result["details"])
    else:
        tl.failed(LOG["pulp_container_still_exists"], result["details"])

    assert result["success"], ASSERT["pulp_container_still_exists"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(102)
def test_pulp_cli_removed(host):
    """TC_RM_CL_002: Verify Pulp CLI removed."""
    # Skip if cleanup input doesn't exist
    input_path = _get_input_path()
    cleanup_input = f"{input_path}/cleanup_input.yml"
    
    result = host.run(f"test -f {cleanup_input} && echo 'exists' || echo 'missing'")
    if "missing" in result.stdout:
        pytest.skip("Cleanup input configuration not found - cleanup test skipped")
    
    tl = TestLogger(TEST_NAMES["pulp_cli_removed"], "TC_RM_CL_002")
    result = check_pulp_cli_removed(host)

    if result["success"]:
        tl.passed(LOG["pulp_cli_removed"], result["details"])
    else:
        tl.failed(LOG["pulp_cli_still_exists"], result["details"])

    assert result["success"], ASSERT["pulp_cli_still_exists"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(103)
def test_pulp_directories_removed(host):
    """TC_RM_CL_003: Verify Pulp directories removed."""
    # Skip if cleanup input doesn't exist
    input_path = _get_input_path()
    cleanup_input = f"{input_path}/cleanup_input.yml"
    
    result = host.run(f"test -f {cleanup_input} && echo 'exists' || echo 'missing'")
    if "missing" in result.stdout:
        pytest.skip("Cleanup input configuration not found - cleanup test skipped")
    
    tl = TestLogger(TEST_NAMES["pulp_directories_removed"], "TC_RM_CL_003")
    result = check_pulp_directories_removed(host)

    if result["success"]:
        tl.passed(LOG["pulp_dirs_removed"], result["details"])
    else:
        tl.failed(LOG["pulp_dirs_still_exist"], result["details"])

    assert result["success"], ASSERT["pulp_dirs_still_exist"]
