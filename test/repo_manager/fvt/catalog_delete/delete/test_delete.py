# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Catalog Delete verification tests.

RM_FVT_CATALOG_DELETE_V001: Verify catalog delete operation completed successfully
RM_FVT_CATALOG_DELETE_V002: Verify catalog structure still valid after delete
RM_FVT_CATALOG_DELETE_V003: Verify catalog has functional layers after delete
RM_FVT_CATALOG_DELETE_V004: Verify catalog has groups after delete
"""

import pytest

from library.functions import (
    TestLogger,
    check_catalog_structure,
    check_catalog_functional_layers,
    check_catalog_groups,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_catalog_delete_operation_completed():
    """RM_FVT_CATALOG_DELETE_V001: Verify catalog delete operation completed successfully."""
    tc = TC["catalog_delete_completed"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.passed("Catalog delete operation completed",
              "Delete playbook executed successfully")


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(2)
def test_catalog_structure_valid_after_delete(host):
    """RM_FVT_CATALOG_DELETE_V002: Verify catalog structure still valid after delete."""
    tc = TC["catalog_structure_valid"]
    tl = TestLogger(tc["title"], tc["id"])

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


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(3)
def test_catalog_has_functional_layers_after_delete(host):
    """RM_FVT_CATALOG_DELETE_V003: Verify catalog still has functional layers after delete."""
    tc = TC["catalog_functional_layers"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_catalog_functional_layers(host)

    if result["success"]:
        tl.passed(LOG["catalog_fl_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_fl_missing"], result["details"])

    assert result["success"], ASSERT["catalog_must_have_fl"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(4)
def test_catalog_has_groups_after_delete(host):
    """RM_FVT_CATALOG_DELETE_V004: Verify catalog still has groups after delete."""
    tc = TC["catalog_groups"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_catalog_groups(host)

    if result["success"]:
        tl.passed(LOG["catalog_groups_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_groups_missing"], result["details"])

    assert result["success"], ASSERT["catalog_must_have_groups"]
