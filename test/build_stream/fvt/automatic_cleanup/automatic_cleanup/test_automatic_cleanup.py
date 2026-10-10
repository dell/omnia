# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Read-only verification of production automatic cleanup."""

import shlex

import pytest

from library.functions import (
    TestLogger,
    run_on_host,
    check_automatic_cleanup_runtime,
    verify_registry_images_absent,
    verify_s3_boot_images_absent,
    wait_for_automatic_cleanup,
)
from library.functions._config_helpers import resolve_omnia_path
from library.vars import TEST_CASES as TC


def _logger(name):
    case = TC[name]
    return TestLogger(case["title"], case["id"])


@pytest.mark.sanity
@pytest.mark.order(2)
def test_automatic_cleanup_runtime(host):
    """BuildStream and watcher services required by cleanup are active."""
    logger = _logger("automatic_cleanup_runtime")
    result = check_automatic_cleanup_runtime(host)
    assert result["success"], result["error"]
    logger.passed("BuildStream, watcher, and shared queue prerequisites are active")


@pytest.mark.sanity
@pytest.mark.order(3)
def test_automatic_cleanup_completed(host, automatic_cleanup_state):
    """The exact target reaches CLEANED with type=auto log evidence."""
    logger = _logger("automatic_cleanup_completed")
    result = wait_for_automatic_cleanup(
        host,
        automatic_cleanup_state.job_id,
        automatic_cleanup_state.image_group_id,
    )
    assert result["success"], result["error"]
    assert result["status"] == "CLEANED"
    logger.passed(result["evidence"])


@pytest.mark.sanity
@pytest.mark.order(4)
def test_automatic_cleanup_nfs_absent(host, automatic_cleanup_state):
    """Automatic cleanup removes the exact Job artifact directory."""
    logger = _logger("automatic_cleanup_nfs_absent")
    path = resolve_omnia_path(
        host,
        "build_stream_root",
        "artifacts",
        automatic_cleanup_state.job_id,
    )
    result = run_on_host(host, f"test ! -e {shlex.quote(path)}")
    assert result.rc == 0, f"Automatic-cleanup NFS artifacts still exist: {path}"
    logger.passed(f"NFS artifact directory is absent: {path}")


@pytest.mark.sanity
@pytest.mark.order(5)
def test_automatic_cleanup_s3_absent(host, automatic_cleanup_state):
    """Automatic cleanup removes S3 boot artifacts for every recorded role."""
    logger = _logger("automatic_cleanup_s3_absent")
    result = verify_s3_boot_images_absent(
        host, automatic_cleanup_state.job_id, automatic_cleanup_state.roles,
    )
    assert result["success"], result["error"] or result["details"]
    logger.passed(result["details"])


@pytest.mark.sanity
@pytest.mark.order(6)
def test_automatic_cleanup_registry_absent(host, automatic_cleanup_state):
    """Automatic cleanup removes registry artifacts for every recorded role."""
    logger = _logger("automatic_cleanup_registry_absent")
    result = verify_registry_images_absent(
        host, automatic_cleanup_state.job_id, automatic_cleanup_state.roles,
    )
    assert result["success"], result["error"] or result["details"]
    logger.passed(result["details"])
