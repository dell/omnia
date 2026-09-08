# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Catalog Generate scenario verification tests.

TC_RM_CAT_GEN_001: Verify catalog input directory exists
TC_RM_CAT_GEN_002: Verify catalog file exists after generate
TC_RM_CAT_GEN_003: Verify catalog structure is valid
TC_RM_CAT_GEN_004: Verify catalog has functional layers
TC_RM_CAT_GEN_005: Verify catalog has groups
TC_RM_CAT_GEN_006: Verify catalog has packages
TC_RM_CAT_GEN_007: Verify catalog log file exists
"""

import pytest

from library.functions import (
    TestLogger,
    check_catalog_input_file_exists,
    check_catalog_file_exists,
    check_catalog_structure,
    check_catalog_functional_layers,
    check_catalog_groups,
    check_catalog_packages,
    check_catalog_log_file_exists,
)
from library.vars.common_vars import _get_input_path
import os
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(0)
def test_catalog_input_dir_exists(host):
    """TC_RM_CAT_GEN_001: Verify catalog input directory exists."""
    tl = TestLogger(TEST_NAMES["catalog_input_dir_exists"], "TC_RM_CAT_GEN_001")
    result = check_catalog_input_file_exists(host)

    if result["success"]:
        tl.passed(LOG["catalog_input_dir_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_input_dir_missing"], result["details"])

    assert result["success"], ASSERT["catalog_input_dir_must_exist"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_catalog_file_exists(host):
    """TC_RM_CAT_GEN_002: Verify catalog file exists after generate."""
    tl = TestLogger(TEST_NAMES["catalog_file_exists"], "TC_RM_CAT_GEN_002")
    
    # This test only makes sense if catalog_generate succeeded
    # If catalog file doesn't exist, it means generate didn't run
    result = check_catalog_file_exists(host)

    if result["success"]:
        tl.passed(LOG["catalog_file_ok"], result["details"])
    else:
        catalog_path = os.environ.get("CATALOG_FILE_PATH", "/opt/omnia/catalog/catalog_rhel.json")
        tl.failed(LOG["catalog_file_missing"], 
                 f"Catalog file not found at {catalog_path}\n"
                 f"This test requires catalog_generate to complete successfully first.\n"
                 f"Ensure the input file is provided and catalog_generate test passes.")

    assert result["success"], ASSERT["catalog_file_must_exist"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_catalog_structure_valid(host):
    """TC_RM_CAT_GEN_003: Verify catalog structure is valid."""
    tl = TestLogger(TEST_NAMES["catalog_structure_valid"], "TC_RM_CAT_GEN_003")
    result = check_catalog_structure(host)

    if result["success"]:
        tl.passed(LOG["catalog_structure_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_structure_invalid"], result["details"])

    assert result["success"], ASSERT["catalog_structure_must_be_valid"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(3)
def test_catalog_functional_layers(host):
    """TC_RM_CAT_GEN_004: Verify catalog has functional layers."""
    tl = TestLogger(TEST_NAMES["catalog_functional_layers"], "TC_RM_CAT_GEN_004")
    result = check_catalog_functional_layers(host)

    if result["success"]:
        tl.passed(LOG["catalog_fl_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_fl_missing"], result["details"])

    assert result["success"], ASSERT["catalog_must_have_fl"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(4)
def test_catalog_groups(host):
    """TC_RM_CAT_GEN_005: Verify catalog has groups."""
    tl = TestLogger(TEST_NAMES["catalog_groups"], "TC_RM_CAT_GEN_005")
    result = check_catalog_groups(host)

    if result["success"]:
        tl.passed(LOG["catalog_groups_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_groups_missing"], result["details"])

    assert result["success"], ASSERT["catalog_must_have_groups"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(5)
def test_catalog_packages(host):
    """TC_RM_CAT_GEN_006: Verify catalog has packages."""
    tl = TestLogger(TEST_NAMES["catalog_packages"], "TC_RM_CAT_GEN_006")
    result = check_catalog_packages(host)

    if result["success"]:
        tl.passed(LOG["catalog_packages_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_packages_missing"], result["details"])

    assert result["success"], ASSERT["catalog_must_have_packages"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(6)
def test_catalog_log_file_exists(host):
    """TC_RM_CAT_GEN_007: Verify catalog log file exists."""
    tl = TestLogger(TEST_NAMES["catalog_log_file_exists"], "TC_RM_CAT_GEN_007")
    result = check_catalog_log_file_exists(host)

    if result["success"]:
        tl.passed(LOG["catalog_log_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_log_missing"], result["details"])

    assert result["success"], ASSERT["catalog_log_must_exist"]
