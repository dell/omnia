# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Download scenario verification tests.

TC_RM_DL_000: Deploy repo_manager --tags download
TC_RM_DL_001: Verify repo_status.yml generated
TC_RM_DL_002: Verify overall_status is success
TC_RM_DL_003: Verify slurm_custom repo present
TC_RM_DL_004: Verify epel repo present
TC_RM_DL_005: Verify x86_64 repositories present
TC_RM_DL_006: Verify file repos present
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_repo_status_exists,
    check_repo_status_success,
    check_repo_status_has_repo,
    check_repo_status_has_file_repo,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_download(host):
    """TC_RM_DL_000: Deploy repo_manager --tags download."""
    tl = TestLogger(TEST_NAMES["repo_status_exists"], "TC_RM_DL_000")
    result = run_playbook(tag="download")

    if result["success"]:
        tl.passed("repo_manager --tags download completed", result.get("details", ""))
    else:
        tl.failed("repo_manager --tags download failed", result.get("error", ""))

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_repo_status_exists(host):
    """TC_RM_DL_001: Verify repo_status.yml generated."""
    tl = TestLogger(TEST_NAMES["repo_status_exists"], "TC_RM_DL_001")
    result = check_repo_status_exists(host)

    if result["success"]:
        tl.passed(LOG["repo_status_exists"], result["details"])
    else:
        tl.failed(LOG["repo_status_missing"], result["details"])

    assert result["success"], ASSERT["repo_status_missing"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_repo_status_success(host):
    """TC_RM_DL_002: Verify overall_status is success."""
    tl = TestLogger(TEST_NAMES["repo_status_success"], "TC_RM_DL_002")
    result = check_repo_status_success(host)

    if result["success"]:
        tl.passed(LOG["repo_status_success"], result["details"])
    else:
        tl.failed(LOG["repo_status_failed"], result["details"])

    assert result["success"], ASSERT["repo_status_not_success"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(3)
def test_slurm_custom_repo_present(host):
    """TC_RM_DL_003: Verify slurm_custom repo present."""
    tl = TestLogger(TEST_NAMES["slurm_custom_repo_present"], "TC_RM_DL_003")
    result = check_repo_status_has_repo(host, "slurm_custom", arch="x86_64")

    if result["success"]:
        tl.passed(LOG["repo_present"].format(repo="slurm_custom"), result["details"])
    else:
        tl.failed(LOG["repo_missing"].format(repo="slurm_custom"), result["details"])

    assert result["success"], ASSERT["repo_not_found"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(4)
def test_epel_repo_present(host):
    """TC_RM_DL_004: Verify epel repo present."""
    tl = TestLogger(TEST_NAMES["epel_repo_present"], "TC_RM_DL_004")
    result = check_repo_status_has_repo(host, "epel", arch="x86_64")

    if result["success"]:
        tl.passed(LOG["repo_present"].format(repo="epel"), result["details"])
    else:
        tl.failed(LOG["repo_missing"].format(repo="epel"), result["details"])

    assert result["success"], ASSERT["repo_not_found"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(5)
def test_x86_64_repos_present(host):
    """TC_RM_DL_005: Verify x86_64 baseos and appstream present."""
    tl = TestLogger(TEST_NAMES["x86_64_repos_present"], "TC_RM_DL_005")
    for repo in ["baseos", "appstream", "codeready-builder"]:
        result = check_repo_status_has_repo(host, repo, arch="x86_64")
        if not result["success"]:
            tl.failed(LOG["repo_missing"].format(repo=repo), result["details"])
            assert False, result["error"]

    tl.passed("x86_64 base repos present", "")


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(6)
def test_file_repos_present(host):
    """TC_RM_DL_006: Verify file repos (tarball) present."""
    tl = TestLogger(TEST_NAMES["file_repos_present"], "TC_RM_DL_006")
    result = check_repo_status_has_file_repo(host, "imb", arch="x86_64")

    if result["success"]:
        tl.passed(LOG["file_repo_present"].format(repo="imb"), result["details"])
    else:
        tl.failed(LOG["file_repo_missing"].format(repo="imb"), result["details"])

    assert result["success"], ASSERT["repo_not_found"]
