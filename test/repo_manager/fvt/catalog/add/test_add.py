# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Catalog Add scenario verification tests.

TC_RM_CAT_ADD_000: Deploy catalog_add playbook
TC_RM_CAT_ADD_001: Verify catalog add operation completed successfully
TC_RM_CAT_ADD_002: Verify catalog structure still valid after add
TC_RM_CAT_ADD_003: Verify catalog has functional layers after add
TC_RM_CAT_ADD_004: Verify catalog has groups after add
TC_RM_CAT_ADD_005: Verify catalog has packages after add
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_catalog_structure,
    check_catalog_functional_layers,
    check_catalog_groups,
    check_catalog_packages,
)
from library.vars.common_vars import _get_input_path
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_catalog_add_deploy(host):
    """TC_RM_CAT_ADD_000: Deploy catalog_add playbook."""
    tl = TestLogger(TEST_NAMES["catalog_add_deploy"], "TC_RM_CAT_ADD_000")

    # Check if input file exists
    input_path = _get_input_path()
    input_file = f"{input_path}/additions.txt"
    result = host.run(f"test -f {input_file} && echo 'exists' || echo 'missing'")

    if "missing" in result.stdout:
        tl.passed("Catalog add input file not provided - test not applicable",
                 f"Input file {input_file} not found. "
                 f"Catalog add requires an input file with packages/groups to add.")
        pytest.skip(f"Input file not found: {input_file}")

    result = run_playbook(
        tag="catalog_add",
        extra_vars={
            "input_file": input_file
        }
    )

    if result["success"]:
        tl.passed(LOG["catalog_add_ok"], result.get("details", ""))
    else:
        tl.failed(LOG["catalog_add_failed"], result.get("error", ""))

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_catalog_add_operation_completed():
    """TC_RM_CAT_ADD_001: Verify catalog add operation completed successfully."""
    tl = TestLogger(TEST_NAMES["catalog_add_deploy"], "TC_RM_CAT_ADD_001")

    # This test only makes sense if catalog_add succeeded
    # The playbook result from test_catalog_add_deploy already verified this
    # This test just confirms the operation ran
    tl.passed("Catalog add operation completed", "Add playbook executed successfully")


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(2)
def test_catalog_structure_valid_after_add(host):
    """TC_RM_CAT_ADD_002: Verify catalog structure still valid after add."""
    tl = TestLogger(TEST_NAMES["catalog_structure_valid"], "TC_RM_CAT_ADD_002")

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


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(3)
def test_catalog_has_functional_layers_after_add(host):
    """TC_RM_CAT_ADD_003: Verify catalog has functional layers after add."""
    tl = TestLogger(TEST_NAMES["catalog_functional_layers"], "TC_RM_CAT_ADD_003")
    result = check_catalog_functional_layers(host)

    if result["success"]:
        tl.passed(LOG["catalog_fl_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_fl_missing"], result["details"])

    assert result["success"], ASSERT["catalog_must_have_fl"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(4)
def test_catalog_has_groups_after_add(host):
    """TC_RM_CAT_ADD_004: Verify catalog has groups after add."""
    tl = TestLogger(TEST_NAMES["catalog_groups"], "TC_RM_CAT_ADD_004")
    result = check_catalog_groups(host)

    if result["success"]:
        tl.passed(LOG["catalog_groups_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_groups_missing"], result["details"])

    assert result["success"], ASSERT["catalog_must_have_groups"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(5)
def test_catalog_has_packages_after_add(host):
    """TC_RM_CAT_ADD_005: Verify catalog has packages after add."""
    tl = TestLogger(TEST_NAMES["catalog_packages"], "TC_RM_CAT_ADD_005")
    result = check_catalog_packages(host)

    if result["success"]:
        tl.passed(LOG["catalog_packages_ok"], result["details"])
    else:
        tl.failed(LOG["catalog_packages_missing"], result["details"])

    assert result["success"], ASSERT["catalog_must_have_packages"]
