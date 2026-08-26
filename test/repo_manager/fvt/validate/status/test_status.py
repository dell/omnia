# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Validate scenario verification tests.

TC_RM_VL_001: Verify repo_manager_config.yml exists
TC_RM_VL_002: Verify repo_manager_endpoint_config.yml exists
TC_RM_VL_003: Verify credentials file present
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_input_config_exists,
    check_endpoint_config_exists,
    check_credentials_present,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_validate(host):
    """TC_RM_VL_000: Deploy repo_manager --tags validate."""
    tl = TestLogger(TEST_NAMES["input_config_exists"], "TC_RM_VL_000")
    result = run_playbook(tag="validate")

    if result["success"]:
        tl.passed("repo_manager --tags validate completed", result.get("details", ""))
    else:
        tl.failed("repo_manager --tags validate failed", result.get("error", ""))

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_input_config_exists(host):
    """TC_RM_VL_001: Verify repo_manager_config.yml exists."""
    tl = TestLogger(TEST_NAMES["input_config_exists"], "TC_RM_VL_001")
    result = check_input_config_exists(host)

    if result["success"]:
        tl.passed(LOG["input_config_ok"], result["details"])
    else:
        tl.failed(LOG["input_config_missing"], result["details"])

    assert result["success"], ASSERT["input_config_missing"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_endpoint_config_exists(host):
    """TC_RM_VL_002: Verify repo_manager_endpoint_config.yml exists."""
    tl = TestLogger(TEST_NAMES["endpoint_config_exists"], "TC_RM_VL_002")
    result = check_endpoint_config_exists(host)

    if result["success"]:
        tl.passed(LOG["endpoint_config_ok"], result["details"])
    else:
        tl.failed(LOG["endpoint_config_missing"], result["details"])

    assert result["success"], ASSERT["endpoint_config_missing"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(3)
def test_credentials_present(host):
    """TC_RM_VL_003: Verify credentials file present."""
    tl = TestLogger(TEST_NAMES["credentials_present"], "TC_RM_VL_003")
    result = check_credentials_present(host)

    if result["success"]:
        tl.passed(LOG["credentials_ok"], result["details"])
    else:
        tl.failed(LOG["credentials_missing"], result["details"])

    assert result["success"], ASSERT["credentials_missing"]
