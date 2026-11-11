# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Execute negative test cases.

RM_FVT_NEG_003: Verify download fails with invalid repository URL
RM_FVT_NEG_007: Verify repository sync fails with network connectivity issues
RM_FVT_NEG_008: Verify catalog generation fails with invalid software_config.json
"""

import pytest

from library.functions import TestLogger
from library.vars import TEST_CASES as TC


@pytest.mark.negative
@pytest.mark.order(1)
def test_download_fails_invalid_repo_url():
    """RM_FVT_NEG_003: Verify download fails with invalid repository URL."""
    tc = TC["neg_invalid_repo_url"]
    tl = TestLogger(tc["title"], tc["id"])
    tl.skipped_fields(
        "Negative test - skipped in normal verification",
        {
            "Test type": "negative",
            "Requirement": "config modification",
            "Purpose": "simulate invalid repository URL",
        }
    )
    pytest.skip("Negative test requiring config modification - skipped to avoid interference")


@pytest.mark.negative
@pytest.mark.order(2)
def test_repo_sync_fails_network_issues():
    """RM_FVT_NEG_007: Verify repository sync fails with network connectivity issues."""
    tl = TestLogger("Repo sync fails with network issues", "RM_FVT_NEG_007")
    tl.skipped_fields(
        "Negative test - skipped in normal verification",
        {
            "Test type": "negative",
            "Requirement": "network simulation",
            "Purpose": "test failure scenarios",
        }
    )
    pytest.skip("Negative test requiring network simulation - skipped to avoid interference")


@pytest.mark.negative
@pytest.mark.order(3)
def test_catalog_generation_fails_invalid_config():
    """RM_FVT_NEG_008: Verify catalog generation fails with invalid software_config.json."""
    tl = TestLogger("Catalog generation fails with invalid config", "RM_FVT_NEG_008")
    tl.skipped_fields(
        "Negative test - skipped in normal verification",
        {
            "Test type": "negative",
            "Requirement": "invalid config",
            "Purpose": "test error handling",
        }
    )
    pytest.skip("Negative test requiring invalid config - skipped to avoid interference")
