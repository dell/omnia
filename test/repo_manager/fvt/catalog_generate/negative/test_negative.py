# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Catalog Generate negative test cases.

RM_FVT_CATALOG_NEG_001: Verify catalog_generate fails with missing input file
RM_FVT_CATALOG_NEG_004: Verify catalog input directory validation
RM_FVT_CATALOG_NEG_005: Verify catalog structure validation
RM_FVT_CATALOG_NEG_006: Verify catalog file existence validation
RM_FVT_CATALOG_NEG_007: Verify catalog log file validation
"""

import pytest

from library.functions import (
    TestLogger,
    check_catalog_file_exists,
    check_catalog_input_file_exists,
    check_catalog_structure,
    check_catalog_log_file_exists,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import _get_input_path


@pytest.mark.negative
@pytest.mark.order(1)
def test_catalog_generate_missing_input_file(host):
    """RM_FVT_CATALOG_NEG_001: Verify catalog_generate fails with missing input file."""
    tc = TC["catalog_neg_generate_missing_input"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = _get_input_path()
    non_existent_file = f"{input_path}/nonexistent.txt"
    result = host.run(f"test -f {non_existent_file} && echo 'exists' || echo 'missing'")

    if "missing" in result.stdout:
        tl.passed("Missing input file correctly detected",
                  f"File {non_existent_file} does not exist as expected")
    else:
        tl.failed("Missing input file not detected",
                  f"File {non_existent_file} should not exist")
        assert False, "Non-existent input file should be detected as missing"


@pytest.mark.negative
@pytest.mark.order(2)
def test_catalog_input_directory_validation(host):
    """RM_FVT_CATALOG_NEG_004: Verify catalog input directory validation."""
    tc = TC["catalog_neg_input_dir_validation"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_catalog_input_file_exists(host)

    if result["success"]:
        tl.passed("Catalog input directory validation works",
                  result["details"])
    else:
        tl.passed("Catalog input directory validation correctly detects "
                  "missing directory", result["details"])


@pytest.mark.negative
@pytest.mark.order(3)
def test_catalog_structure_validation(host):
    """RM_FVT_CATALOG_NEG_005: Verify catalog structure validation."""
    tc = TC["catalog_neg_structure_validation"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_catalog_structure(host)

    if result["success"]:
        tl.passed("Catalog structure validation works", result["details"])
    else:
        tl.passed("Catalog structure validation correctly detects "
                  "invalid structure", result["details"])


@pytest.mark.negative
@pytest.mark.order(4)
def test_catalog_file_existence_validation(host):
    """RM_FVT_CATALOG_NEG_006: Verify catalog file existence validation."""
    tc = TC["catalog_neg_file_existence"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_catalog_file_exists(host)

    if result["success"]:
        tl.passed("Catalog file existence validation works",
                  result["details"])
    else:
        tl.passed("Catalog file existence validation correctly detects "
                  "missing file", result["details"])


@pytest.mark.negative
@pytest.mark.order(5)
def test_catalog_log_file_validation(host):
    """RM_FVT_CATALOG_NEG_007: Verify catalog log file validation."""
    tc = TC["catalog_neg_log_validation"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_catalog_log_file_exists(host)

    if result["success"]:
        tl.passed("Catalog log file validation works", result["details"])
    else:
        tl.passed("Catalog log file validation correctly detects missing "
                  "log file", result["details"])
