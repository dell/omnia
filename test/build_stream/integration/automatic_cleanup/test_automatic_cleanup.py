# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Execute and verify explicit production automatic cleanup."""

import shlex

import pytest

from library.functions import (
    TestLogger,
    check_automatic_cleanup_runtime,
    run_automatic_cleanup_cycle,
    run_on_host,
    verify_registry_images_absent,
    verify_s3_boot_images_absent,
    wait_for_automatic_cleanup,
)
from library.functions._config_helpers import resolve_omnia_path


@pytest.mark.sanity
@pytest.mark.deploy
@pytest.mark.disruptive
@pytest.mark.order(0)
def test_execute_automatic_cleanup(host, automatic_cleanup_state):
    """Run cleanup only when the configured Job is the sole FAILED target."""
    logger = TestLogger(
        "Execute automatic cleanup for explicit integration target",
        "BSM_INT_AUTOMATIC_CLEANUP_E001",
    )
    result = run_automatic_cleanup_cycle(host, automatic_cleanup_state.job_id)
    assert result["success"], result["error"]
    assert result["image_group_id"] == automatic_cleanup_state.image_group_id
    logger.passed(f"Cleanup accepted {result['image_group_id']}")


@pytest.mark.sanity
@pytest.mark.order(1)
def test_automatic_cleanup_runtime(host):
    """Verify services and shared queue required by cleanup are active."""
    logger = TestLogger(
        "Verify automatic-cleanup runtime",
        "BSM_INT_AUTOMATIC_CLEANUP_V001",
    )
    result = check_automatic_cleanup_runtime(host)
    assert result["success"], result["error"]
    logger.passed("Automatic-cleanup runtime prerequisites are active")


@pytest.mark.sanity
@pytest.mark.order(2)
def test_automatic_cleanup_completed(host, automatic_cleanup_state):
    """Verify the exact target reaches CLEANED with automatic log evidence."""
    logger = TestLogger(
        "Verify automatic cleanup completion",
        "BSM_INT_AUTOMATIC_CLEANUP_V002",
    )
    result = wait_for_automatic_cleanup(
        host,
        automatic_cleanup_state.job_id,
        automatic_cleanup_state.image_group_id,
    )
    assert result["success"], result["error"]
    assert result["status"] == "CLEANED"
    logger.passed(result["evidence"])


@pytest.mark.sanity
@pytest.mark.order(3)
def test_automatic_cleanup_artifacts_absent(host, automatic_cleanup_state):
    """Verify NFS, S3, and registry artifacts are absent for the exact Job."""
    logger = TestLogger(
        "Verify automatic cleanup artifact removal",
        "BSM_INT_AUTOMATIC_CLEANUP_V003",
    )
    path = resolve_omnia_path(
        host,
        "build_stream_root",
        "artifacts",
        automatic_cleanup_state.job_id,
    )
    nfs_result = run_on_host(host, f"test ! -e {shlex.quote(path)}")
    assert nfs_result.rc == 0, f"NFS artifacts still exist: {path}"

    s3_result = verify_s3_boot_images_absent(
        host,
        automatic_cleanup_state.job_id,
        automatic_cleanup_state.roles,
    )
    assert s3_result["success"], s3_result["error"] or s3_result["details"]
    registry = verify_registry_images_absent(
        host,
        automatic_cleanup_state.job_id,
        automatic_cleanup_state.roles,
    )
    assert registry["success"], registry["error"] or registry["details"]
    logger.passed("NFS, S3, and registry artifacts are absent")
