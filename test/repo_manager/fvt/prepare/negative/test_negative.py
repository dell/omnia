# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Prepare negative test cases.

RM_FVT_NEG_006: Verify Pulp CLI fails with invalid authentication
RM_FVT_NEG_010: Verify Pulp API unreachable when port is closed
"""

import pytest

from library.functions import TestLogger
from library.vars import TEST_CASES as TC


@pytest.mark.negative
@pytest.mark.order(1)
def test_pulp_cli_fails_invalid_auth():
    """RM_FVT_NEG_006: Verify Pulp CLI fails with invalid authentication."""
    tc = TC["neg_invalid_auth"]
    tl = TestLogger(tc["title"], tc["id"])
    tl.skipped_fields(
        "Negative test - skipped in normal verification",
        {
            "Test type": "negative",
            "Requirement": "auth modification",
            "Purpose": "test failure scenario",
        }
    )
    pytest.skip("Negative test requiring auth modification - skipped to avoid interference")


@pytest.mark.negative
@pytest.mark.order(2)
def test_pulp_api_unreachable_port_closed():
    """RM_FVT_NEG_010: Verify Pulp API unreachable when port is closed."""
    tl = TestLogger("Pulp API unreachable when port is closed", "RM_FVT_NEG_010")
    tl.skipped_fields(
        "Negative test - skipped in normal verification",
        {
            "Test type": "negative",
            "Requirement": "port modification",
            "Purpose": "test failure scenario",
        }
    )
    pytest.skip("Negative test requiring port modification - skipped to avoid interference")
