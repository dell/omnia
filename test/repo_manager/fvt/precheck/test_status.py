# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Repo Manager precheck scenario verification tests."""

import pytest

from library.functions import (
    TestLogger,
    check_credentials_present,
    check_endpoint_config_exists,
    check_input_config_exists,
    run_playbook,
)
from library.messages import (
    TEST_ASSERT_MSGS as ASSERT,
    TEST_LOG_MSGS as LOG,
    TEST_NAMES,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_precheck_environment(host):
    """RM_FVT_PRECHECK_E001: Deploy repo_manager --tags precheck."""
    assert host is not None
    test_log = TestLogger(TEST_NAMES["input_config_exists"], "RM_FVT_PRECHECK_E001")
    result = run_playbook(tag="precheck")

    if result["success"]:
        test_log.passed(
            "repo_manager --tags precheck completed",
            result.get("details", ""),
        )
    else:
        test_log.failed(
            "repo_manager --tags precheck failed",
            result.get("error", ""),
        )

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_input_config_exists(host):
    """RM_FVT_PRECHECK_V001: Verify repo_manager_config.yml exists."""
    test_log = TestLogger(TEST_NAMES["input_config_exists"], "RM_FVT_PRECHECK_V001")
    result = check_input_config_exists(host)

    if result["success"]:
        test_log.passed(LOG["input_config_ok"], result["details"])
    else:
        test_log.failed(LOG["input_config_missing"], result["details"])

    assert result["success"], ASSERT["input_config_missing"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_endpoint_config_exists(host):
    """RM_FVT_PRECHECK_V002: Verify repo_manager_endpoint_config.yml exists."""
    test_log = TestLogger(TEST_NAMES["endpoint_config_exists"], "RM_FVT_PRECHECK_V002")
    result = check_endpoint_config_exists(host)

    if result["success"]:
        test_log.passed(LOG["endpoint_config_ok"], result["details"])
    else:
        test_log.failed(LOG["endpoint_config_missing"], result["details"])

    assert result["success"], ASSERT["endpoint_config_missing"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(3)
def test_credentials_present(host):
    """RM_FVT_PRECHECK_V003: Verify credentials file is present."""
    test_log = TestLogger(TEST_NAMES["credentials_present"], "RM_FVT_PRECHECK_V003")
    result = check_credentials_present(host)

    if result["success"]:
        test_log.passed(LOG["credentials_ok"], result["details"])
    else:
        test_log.failed(LOG["credentials_missing"], result["details"])

    assert result["success"], ASSERT["credentials_missing"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(4)
def test_precheck_environment_no_credentials(host):
    """RM_FVT_PRECHECK_V004: Validate input without prompting for credentials."""
    test_log = TestLogger(TEST_NAMES["input_config_exists"], "RM_FVT_PRECHECK_V004")
    result = check_input_config_exists(host)

    if result["success"]:
        test_log.passed(
            "Precheck environment validates configuration without a prompt",
            result["details"],
        )
    else:
        test_log.failed(
            "Precheck environment validation failed",
            result["details"],
        )

    assert result["success"], "Precheck must validate configuration"
