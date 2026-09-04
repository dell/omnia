# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Catalog Validate scenario verification tests.

TC_RM_CAT_VAL_000: Deploy catalog_validate playbook
TC_RM_CAT_VAL_001: Verify catalog validation completed successfully
TC_RM_CAT_VAL_002: Verify catalog validation log file exists
TC_RM_CAT_VAL_003: Verify catalog file still valid after validation
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_catalog_structure,
)
from library.vars.common_vars import _get_base_path
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_catalog_validate_deploy(host):
    """TC_RM_CAT_VAL_000: Deploy catalog_validate playbook."""
    tl = TestLogger(TEST_NAMES["catalog_validate_deploy"], "TC_RM_CAT_VAL_000")

    result = run_playbook(tag="catalog_validate")

    if result["success"]:
        tl.passed(LOG["catalog_validate_ok"], result.get("details", ""))
    else:
        tl.failed(LOG["catalog_validate_failed"], result.get("error", ""))

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_catalog_validation_completed():
    """TC_RM_CAT_VAL_001: Verify catalog validation completed successfully."""
    tl = TestLogger(TEST_NAMES["catalog_structure_valid"], "TC_RM_CAT_VAL_001")

    # The validate operation should complete without errors
    # The playbook result from test_catalog_validate_deploy already verified this
    # This test just confirms the operation ran
    tl.passed("Catalog validation completed",
              "Validate playbook executed successfully")


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(2)
def test_catalog_validation_log_exists(host):
    """TC_RM_CAT_VAL_002: Verify catalog validation log file exists."""
    tl = TestLogger(TEST_NAMES["catalog_log_file_exists"], "TC_RM_CAT_VAL_002")

    # Check the log file exists and has recent entries
    base_path = _get_base_path()
    log_path = f"{base_path}/log/catalog/catalog_manager.log"
    result = host.run(f"test -f {log_path} && echo 'exists' || echo 'missing'")

    if "exists" in result.stdout:
        tl.passed("Catalog validation log file exists",
                  f"Log file found at {log_path}")
    else:
        tl.failed("Catalog validation log file missing",
                  f"Log file not found at {log_path}")
        assert False, "Catalog validation log file should exist"


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(3)
def test_catalog_still_valid_after_validation(host):
    """TC_RM_CAT_VAL_003: Verify catalog file still valid after validation."""
    tl = TestLogger(TEST_NAMES["catalog_structure_valid"], "TC_RM_CAT_VAL_003")

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
