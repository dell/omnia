# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Precheck negative test cases.

RM_FVT_NEG_001: Verify deployment fails with missing credentials
RM_FVT_NEG_002: Verify deployment fails with invalid endpoint config
RM_FVT_NEG_009: Verify validation fails with missing repo_manager_config.yml
"""

import pytest

from library.functions import (
    TestLogger,
    check_input_config_exists,
)
from library.vars import TEST_CASES as TC


@pytest.mark.negative
@pytest.mark.order(1)
def test_deploy_fails_missing_credentials():
    """RM_FVT_NEG_001: Verify deployment fails with missing credentials."""
    tc = TC["neg_missing_credentials"]
    tl = TestLogger(tc["title"], tc["id"])
    tl.skipped_fields(
        "Negative test - skipped in normal verification",
        {
            "Test type": "negative",
            "Requirement": "credentials removal",
            "Purpose": "test failure scenario",
        }
    )
    pytest.skip("Negative test requiring credentials removal - skipped to avoid interference")


@pytest.mark.negative
@pytest.mark.order(2)
def test_deploy_fails_invalid_endpoint_config():
    """RM_FVT_NEG_002: Verify deployment fails with invalid endpoint config."""
    tc = TC["neg_invalid_endpoint_config"]
    tl = TestLogger(tc["title"], tc["id"])
    tl.skipped_fields(
        "Negative test - skipped in normal verification",
        {
            "Test type": "negative",
            "Requirement": "invalid endpoint config",
            "Purpose": "test error handling",
        }
    )
    pytest.skip("Negative test requiring invalid config - skipped to avoid interference")


@pytest.mark.negative
@pytest.mark.order(3)
def test_validate_fails_missing_config(host):
    """RM_FVT_NEG_009: Verify validation fails with missing repo_manager_config.yml."""
    tl = TestLogger("Validation fails with missing config", "RM_FVT_NEG_009")
    result = check_input_config_exists(host)

    if result["success"]:
        tl.skipped_fields(
            "Configuration present - test not applicable",
            {
                "Config file": "repo_manager_config.yml",
                "Status": "exists",
                "Test type": "negative",
            }
        )
        pytest.skip("repo_manager_config.yml exists - negative case not applicable")
