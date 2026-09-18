# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Status scenario verification tests.

RM_FVT_STATUS_E001: Deploy repo_manager --tags status
RM_FVT_STATUS_V001: Verify repo_status.yml regenerated
RM_FVT_STATUS_V002: Verify overall_status is success
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_repo_status_exists,
    check_repo_status_success,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_status(host):
    """RM_FVT_STATUS_E001: Deploy repo_manager --tags status."""
    tl = TestLogger(TEST_NAMES["repo_status_regenerated"], "RM_FVT_STATUS_E001")
    result = run_playbook(tag="status")

    if result["success"]:
        tl.passed("repo_manager --tags status completed", result.get("details", ""))
    else:
        tl.failed("repo_manager --tags status failed", result.get("error", ""))

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_repo_status_regenerated(host):
    """RM_FVT_STATUS_V001: Verify repo_status.yml regenerated."""
    tl = TestLogger(TEST_NAMES["repo_status_regenerated"], "RM_FVT_STATUS_V001")
    result = check_repo_status_exists(host)

    if result["success"]:
        tl.passed(LOG["repo_status_exists"], result["details"])
    else:
        tl.failed(LOG["repo_status_missing"], result["details"])

    assert result["success"], ASSERT["repo_status_missing"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_repo_status_success_after_status(host):
    """RM_FVT_STATUS_V002: Verify overall_status is success."""
    tl = TestLogger(TEST_NAMES["repo_status_success"], "RM_FVT_STATUS_V002")
    result = check_repo_status_success(host)

    if result["success"]:
        tl.passed(LOG["repo_status_success"], result["details"])
    else:
        tl.failed(LOG["repo_status_failed"], result["details"])

    assert result["success"], ASSERT["repo_status_not_success"]
