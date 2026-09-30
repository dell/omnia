# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Catalog Generate verification tests.

RM_FVT_CATALOG_GENERATE_V001: Verify catalog input directory exists
RM_FVT_CATALOG_GENERATE_V002: Verify catalog file exists after generate
RM_FVT_CATALOG_GENERATE_V003: Verify catalog structure is valid
RM_FVT_CATALOG_GENERATE_V004: Verify catalog has functional layers
RM_FVT_CATALOG_GENERATE_V005: Verify catalog has groups
RM_FVT_CATALOG_GENERATE_V006: Verify catalog has packages
RM_FVT_CATALOG_GENERATE_V007: Verify catalog log file exists
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
from library.vars import TEST_CASES as TC
from library.vars.common_vars import _get_catalog_path
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(0)
def test_catalog_input_dir_exists(host):
    """RM_FVT_CATALOG_GENERATE_V001: Verify catalog input directory exists."""
    tc = TC["catalog_input_dir_exists"]
    tl = TestLogger(tc["title"], tc["id"])
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
    """RM_FVT_CATALOG_GENERATE_V002: Verify catalog file exists after generate."""
    tc = TC["catalog_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_catalog_file_exists(host)

    if result["success"]:
        tl.passed(LOG["catalog_file_ok"], result["details"])
    else:
        catalog_path = _get_catalog_path()
        tl.failed(
            LOG["catalog_file_missing"],
            f"Catalog file not found at {catalog_path}\n"
            "This test requires catalog_generate to complete successfully "
            "first.\nEnsure its input exists and the generate test passes.",
        )

    assert result["success"], ASSERT["catalog_file_must_exist"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_catalog_structure_valid(host):
    """RM_FVT_CATALOG_GENERATE_V003: Verify catalog structure is valid."""
    tc = TC["catalog_structure_valid"]
    tl = TestLogger(tc["title"], tc["id"])
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
    """RM_FVT_CATALOG_GENERATE_V004: Verify catalog has functional layers."""
    tc = TC["catalog_functional_layers"]
    tl = TestLogger(tc["title"], tc["id"])
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
    """RM_FVT_CATALOG_GENERATE_V005: Verify catalog has groups."""
    tc = TC["catalog_groups"]
    tl = TestLogger(tc["title"], tc["id"])
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
    """RM_FVT_CATALOG_GENERATE_V006: Verify catalog has packages."""
    tc = TC["catalog_packages"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_catalog_packages(host)

    if result["success"]:
        tl.passed(LOG["catalog_packages_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_packages_missing"], result["details"])

    assert result["success"], ASSERT["catalog_must_have_packages"]


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(6)
def test_catalog_log_file_exists(host):
    """RM_FVT_CATALOG_GENERATE_V007: Verify catalog log file exists."""
    tc = TC["catalog_log_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_catalog_log_file_exists(host)

    if result["success"]:
        tl.passed(LOG["catalog_log_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_log_missing"], result["details"])

    assert result["success"], ASSERT["catalog_log_must_exist"]
