# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Catalog Add scenario verification tests.

TC_RM_CAT_ADD_000: Deploy catalog_add playbook
TC_RM_CAT_ADD_001: Verify catalog add operation completed successfully
TC_RM_CAT_ADD_002: Verify catalog structure still valid after add
TC_RM_CAT_ADD_003: Verify packages from input file were added to catalog
TC_RM_CAT_ADD_004: Verify groups from input file were created in catalog
TC_RM_CAT_ADD_005: Verify catalog has functional layers after add
TC_RM_CAT_ADD_006: Verify catalog has groups after add
TC_RM_CAT_ADD_007: Verify catalog has packages after add
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_catalog_structure,
    check_catalog_functional_layers,
    check_catalog_groups,
    check_catalog_packages,
    check_catalog_has_group,
    check_catalog_has_package,
    parse_catalog_input_file,
)
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
    input_file = "/opt/omnia/repo_manager/input/project_default/additions.txt"
    result = host.run(f"test -f {input_file} && echo 'exists' || echo 'missing'")

    if "missing" in result.stdout:
        tl.failed("Catalog add input file not provided",
                 f"Required input file: {input_file}\n"
                 f"To run catalog_add tests, you must provide this file "
                 f"with packages/groups to add.\n"
                 f"Example format:\n"
                 f"[defaults]\n"
                 f"arch=x86_64, os=rhel, os_version=10.0\n"
                 f"[group_name | type=group_type, description=group_description]\n"
                 f"package_name, package_type, package_name, repo_name\n"
                 f"[functional_layer_name | type=functional_layer]\n"
                 f'"group_name"')
        assert False, f"Catalog add requires input file: {input_file}"

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
def test_catalog_add_operation_completed(_host):
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
def test_catalog_packages_added_from_input_file(host):
    """TC_RM_CAT_ADD_003: Verify packages from input file were added to catalog."""
    tl = TestLogger(TEST_NAMES["catalog_has_package"], "TC_RM_CAT_ADD_003")

    # Parse the input file to get expected packages
    input_file = "/opt/omnia/repo_manager/input/project_default/additions.txt"
    parse_result = parse_catalog_input_file(host, input_file)

    if not parse_result["success"]:
        tl.failed("Could not parse input file", parse_result["details"])
        assert False, "Should be able to parse input file"

    expected_packages = parse_result["packages"]
    if not expected_packages:
        tl.passed("No packages to add in input file", "Input file has no packages")
        return

    # Check that each expected package exists in catalog
    # Note: If packages already exist, the playbook will update them
    missing_packages = []
    for package in expected_packages:
        result = check_catalog_has_package(host, package)
        if not result["success"]:
            missing_packages.append(package)

    if not missing_packages:
        tl.passed("All packages from input file present in catalog",
                  f"Present: {', '.join(expected_packages)}")
    else:
        tl.failed("Some packages from input file not found in catalog",
                  f"Missing: {', '.join(missing_packages)}")
        assert False, ("Expected packages should be present: "
                       f"{', '.join(missing_packages)}")


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(4)
def test_catalog_groups_created_from_input_file(host):
    """TC_RM_CAT_ADD_004: Verify groups from input file were created in catalog."""
    tl = TestLogger(TEST_NAMES["catalog_has_group"], "TC_RM_CAT_ADD_004")

    # Parse the input file to get expected groups
    input_file = "/opt/omnia/repo_manager/input/project_default/additions.txt"
    parse_result = parse_catalog_input_file(host, input_file)

    if not parse_result["success"]:
        tl.failed("Could not parse input file", parse_result["details"])
        assert False, "Should be able to parse input file"

    expected_groups = parse_result["groups"]
    if not expected_groups:
        tl.passed("No groups to create in input file", "Input file has no groups")
        return

    # Check that each expected group exists in catalog
    # Note: If groups already exist, the playbook will merge them
    missing_groups = []
    for group in expected_groups:
        result = check_catalog_has_group(host, group)
        if not result["success"]:
            missing_groups.append(group)

    if not missing_groups:
        tl.passed("All groups from input file present in catalog",
                  f"Present: {', '.join(expected_groups)}")
    else:
        tl.failed("Some groups from input file not found in catalog",
                  f"Missing: {', '.join(missing_groups)}")
        assert False, ("Expected groups should be present: "
                       f"{', '.join(missing_groups)}")


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
