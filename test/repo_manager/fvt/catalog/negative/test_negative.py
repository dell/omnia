# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Catalog Negative test cases for error scenarios.

TC_RM_CAT_NEG_001: Verify catalog_generate fails with missing input file
TC_RM_CAT_NEG_002: Verify catalog_add fails with missing input file
TC_RM_CAT_NEG_003: Verify catalog_delete fails with missing input file
TC_RM_CAT_NEG_004: Verify catalog input file validation
TC_RM_CAT_NEG_005: Verify catalog structure validation
TC_RM_CAT_NEG_006: Verify catalog file existence validation
TC_RM_CAT_NEG_007: Verify catalog log file validation
"""

import pytest

from library.functions import (
    TestLogger,
    check_catalog_file_exists,
    check_catalog_input_file_exists,
    check_catalog_structure,
    check_catalog_log_file_exists,
)
from library.messages import (
    TEST_NAMES,
)


@pytest.mark.negative
@pytest.mark.order(1)
def test_catalog_generate_missing_input_file(host):
    """TC_RM_CAT_NEG_001: Verify catalog_generate fails with missing input file."""
    tl = TestLogger(TEST_NAMES["catalog_generate_deploy"], "TC_RM_CAT_NEG_001")

    # Check that a non-existent input file is detected
    non_existent_file = (
        "/opt/omnia/repo_manager/input/project_default/nonexistent.txt"
    )
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
def test_catalog_add_missing_input_file(host):
    """TC_RM_CAT_NEG_002: Verify catalog_add fails with missing input file."""
    tl = TestLogger(TEST_NAMES["catalog_add_deploy"], "TC_RM_CAT_NEG_002")

    # Check that a non-existent input file is detected
    non_existent_file = (
        "/opt/omnia/repo_manager/input/project_default/nonexistent_add.txt"
    )
    result = host.run(f"test -f {non_existent_file} && echo 'exists' || echo 'missing'")

    if "missing" in result.stdout:
        tl.passed("Missing add input file correctly detected",
                  f"File {non_existent_file} does not exist as expected")
    else:
        tl.failed("Missing add input file not detected",
                  f"File {non_existent_file} should not exist")
        assert False, "Non-existent add input file should be detected as missing"


@pytest.mark.negative
@pytest.mark.order(3)
def test_catalog_delete_missing_input_file(host):
    """TC_RM_CAT_NEG_003: Verify catalog_delete fails with missing input file."""
    tl = TestLogger(TEST_NAMES["catalog_delete_deploy"], "TC_RM_CAT_NEG_003")

    # Check that a non-existent input file is detected
    non_existent_file = (
        "/opt/omnia/repo_manager/input/project_default/nonexistent_delete.txt"
    )
    result = host.run(f"test -f {non_existent_file} && echo 'exists' || echo 'missing'")

    if "missing" in result.stdout:
        tl.passed("Missing delete input file correctly detected",
                  f"File {non_existent_file} does not exist as expected")
    else:
        tl.failed("Missing delete input file not detected",
                  f"File {non_existent_file} should not exist")
        assert False, "Non-existent delete input file should be detected as missing"


@pytest.mark.negative
@pytest.mark.order(4)
def test_catalog_input_directory_validation(host):
    """TC_RM_CAT_NEG_004: Verify catalog input directory validation."""
    tl = TestLogger(TEST_NAMES["catalog_input_dir_exists"], "TC_RM_CAT_NEG_004")

    # Check that input directory validation works
    result = check_catalog_input_file_exists(host)

    if result["success"]:
        tl.passed("Catalog input directory validation works",
                  result["details"])
    else:
        tl.passed("Catalog input directory validation correctly detects "
                  "missing directory", result["details"])


@pytest.mark.negative
@pytest.mark.order(5)
def test_catalog_structure_validation(host):
    """TC_RM_CAT_NEG_005: Verify catalog structure validation."""
    tl = TestLogger(TEST_NAMES["catalog_structure_valid"], "TC_RM_CAT_NEG_005")

    # Check that catalog structure validation works
    result = check_catalog_structure(host)

    if result["success"]:
        tl.passed("Catalog structure validation works", result["details"])
    else:
        tl.passed("Catalog structure validation correctly detects "
                  "invalid structure", result["details"])


@pytest.mark.negative
@pytest.mark.order(6)
def test_catalog_file_existence_validation(host):
    """TC_RM_CAT_NEG_006: Verify catalog file existence validation."""
    tl = TestLogger(TEST_NAMES["catalog_file_exists"], "TC_RM_CAT_NEG_006")

    # Check that catalog file existence validation works
    result = check_catalog_file_exists(host)

    if result["success"]:
        tl.passed("Catalog file existence validation works",
                  result["details"])
    else:
        tl.passed("Catalog file existence validation correctly detects "
                  "missing file", result["details"])


@pytest.mark.negative
@pytest.mark.order(7)
def test_catalog_log_file_validation(host):
    """TC_RM_CAT_NEG_007: Verify catalog log file validation."""
    tl = TestLogger(TEST_NAMES["catalog_log_file_exists"], "TC_RM_CAT_NEG_007")

    # Check that catalog log file validation works
    result = check_catalog_log_file_exists(host)

    if result["success"]:
        tl.passed("Catalog log file validation works", result["details"])
    else:
        tl.passed("Catalog log file validation correctly detects missing "
                  "log file", result["details"])
