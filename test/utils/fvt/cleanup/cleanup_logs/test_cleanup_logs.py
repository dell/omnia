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

"""
Cleanup Logs Scenario - Test Automation.

Tests for utils.yml --tags cleanup_logs functionality.
Validates that the cleanup_logs tag properly cleans log collection artifacts:
- Removes old log bundles based on retention policy
- Removes empty log collection directories
- Cleans temporary directories (k8s, slurm)
"""

import pytest

from library.functions import (
    TestLogger,
    load_test_config,
    run_playbook,
    get_utils_output_path,
    check_old_log_bundles_removed,
    check_empty_log_dirs_removed,
    check_temp_log_dirs_cleaned,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_UTILS,
    PLAYBOOK_WORKDIR,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# PLAYBOOK DEPLOYMENT TESTS
# =============================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.cleanup_logs
@pytest.mark.order(0)
def test_deploy_cleanup_logs(host):
    """Deploy utils.yml with cleanup_logs tag."""
    tc = TC["deploy_cleanup_logs"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_UTILS, tag="cleanup_logs")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_UTILS,
        tag="cleanup_logs",
        rc=result["rc"],
        duration=result["duration"],
        input_path="N/A",
        workdir=config.get("clone_path", "/root/omnia") + "/" +
        PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


# =============================================================================
# CLEANUP LOGS VERIFICATION TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.cleanup_logs
@pytest.mark.order(1)
def test_cleanup_logs_old_bundles_removed(host):
    """Verify old log bundles are removed based on retention policy."""
    tc = TC["cleanup_logs_old_bundles_removed"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    result = check_old_log_bundles_removed(host, output_path)

    if result["success"]:
        current_count = len(result["current_bundles"])
        tl.passed(f"Old bundles removed. Current bundles: {current_count}")
        if result["current_bundles"]:
            for bundle in result["current_bundles"]:
                tl.info(f"  Retained: {bundle}")
    else:
        old_count = len(result["old_bundles"])
        tl.failed(f"Found {old_count} old bundles that should have been removed")
        for bundle in result["old_bundles"]:
            tl.info(f"  Old bundle: {bundle}")

    assert result["success"], (
        f"Old log bundles not removed: {result['old_bundles']}"
    )


@pytest.mark.sanity
@pytest.mark.cleanup_logs
@pytest.mark.order(2)
def test_cleanup_logs_empty_dirs_removed(host):
    """Verify empty log collection directories are removed."""
    tc = TC["cleanup_logs_empty_dirs_removed"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    result = check_empty_log_dirs_removed(host, output_path)

    if result["success"]:
        tl.passed("No empty log directories found")
    else:
        empty_count = len(result["empty_dirs"])
        tl.failed(f"Found {empty_count} empty directories that should have been removed")
        for empty_dir in result["empty_dirs"]:
            tl.info(f"  Empty dir: {empty_dir}")

    assert result["success"], (
        f"Empty log directories not removed: {result['empty_dirs']}"
    )


@pytest.mark.sanity
@pytest.mark.cleanup_logs
@pytest.mark.order(3)
def test_cleanup_logs_temp_dirs_cleaned(host):
    """Verify temporary directories (k8s, slurm) are cleaned."""
    tc = TC["cleanup_logs_temp_dirs_cleaned"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    result = check_temp_log_dirs_cleaned(host, output_path)

    if result["success"]:
        tl.passed("Temporary directories cleaned")
        for dir_name, status in result["temp_dirs_status"].items():
            tl.info(f"  {dir_name}: {status}")
    else:
        tl.failed("Temporary directories not properly cleaned")
        for dir_name, status in result["temp_dirs_status"].items():
            tl.info(f"  {dir_name}: {status}")

    assert result["success"], (
        f"Temporary directories not cleaned: {result['temp_dirs_status']}"
    )
