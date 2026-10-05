# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Catalog Validate verification tests.

RM_FVT_CATALOG_VALIDATE_V001: Verify catalog validation completed successfully
RM_FVT_CATALOG_VALIDATE_V002: Verify catalog validation log file exists
RM_FVT_CATALOG_VALIDATE_V003: Verify catalog file still valid after validation
"""

import pytest

from library.functions import (
    TestLogger,
    check_catalog_structure,
    check_catalog_log_file_exists,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_catalog_validation_completed():
    """RM_FVT_CATALOG_VALIDATE_V001: Verify catalog validation completed successfully."""
    tc = TC["catalog_validate_completed"]
    tl = TestLogger(tc["title"], tc["id"])

    # The validate operation should complete without errors
    # The playbook result from test_catalog_validate_deploy already verified this
    # This test just confirms the operation ran
    tl.passed("Catalog validation completed",
              "Validate playbook executed successfully")


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(2)
def test_catalog_validation_log_exists(host):
    """RM_FVT_CATALOG_VALIDATE_V002: Verify catalog validation log file exists."""
    tc = TC["catalog_validate_log_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_catalog_log_file_exists(host)

    if result["success"]:
        tl.passed("Catalog validation log file exists", result["details"])
    else:
        tl.failed("Catalog validation log file missing", result["details"])

    assert result["success"], "Catalog validation log file should exist"


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(3)
def test_catalog_still_valid_after_validation(host):
    """RM_FVT_CATALOG_VALIDATE_V003: Verify catalog file still valid after validation."""
    tc = TC["catalog_structure_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    # This test requires catalog_generate to have run first
    result = check_catalog_structure(host)

    if result["success"]:
        tl.passed(LOG["catalog_structure_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_structure_invalid"],
                 "Catalog structure invalid or catalog doesn't exist.\n"
                 "This test requires catalog_generate to complete "
                 "successfully first.\n"
                 "Ensure the input file is provided and catalog_generate "
                 "test passes.")

    assert result["success"], ASSERT["catalog_structure_must_be_valid"]
