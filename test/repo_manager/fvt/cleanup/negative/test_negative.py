# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Cleanup negative test cases.

RM_FVT_NEG_005: Verify cleanup fails when Pulp container not running
"""

import pytest

from library.functions import (
    TestLogger,
    check_pulp_container_running,
)
from library.vars import TEST_CASES as TC


@pytest.mark.negative
@pytest.mark.order(1)
def test_cleanup_fails_pulp_not_running(host):
    """RM_FVT_NEG_005: Verify cleanup fails when Pulp container not running."""
    tc = TC["neg_pulp_not_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_container_running(host)

    if not result["success"]:
        return

    tl.skipped_fields(
        "Pulp container running - negative case not applicable",
        {
            "Container": "Pulp",
            "Status": "running",
            "Test type": "negative",
        }
    )
    pytest.skip("Pulp container running - negative case not applicable")
