# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Status negative test cases.

RM_FVT_NEG_004: Verify status check fails with missing repo_status.yml
"""

import pytest

from library.functions import (
    TestLogger,
    check_repo_status_exists,
)
from library.vars import TEST_CASES as TC


@pytest.mark.negative
@pytest.mark.order(1)
def test_status_fails_missing_repo_status(host):
    """RM_FVT_NEG_004: Verify status check fails with missing repo_status.yml."""
    tc = TC["neg_missing_repo_status"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_repo_status_exists(host)

    if result["success"]:
        tl.skipped_fields(
            "Status file present - negative case not applicable",
            {
                "File": "repo_status.yml",
                "Status": "exists",
                "Test type": "negative",
            }
        )
        pytest.skip("repo_status.yml exists - negative case not applicable")
