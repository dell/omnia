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
Cleanup (Combined) Scenario - Test Automation.

Tests for utils.yml --tags cleanup functionality.
Validates that the cleanup tag properly cleans all utils artifacts:
- All log collection artifacts (cleanup_logs)
- All OS installation artifacts (cleanup_install_os)
"""

import pytest

from library.functions import (
    TestLogger,
    load_test_config,
    run_playbook,
    get_utils_input_path,
    get_utils_output_path,
    check_all_logs_cleaned,
    check_all_install_os_cleaned,
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
@pytest.mark.cleanup
@pytest.mark.order(0)
def test_deploy_cleanup(host):
    """Deploy utils.yml with cleanup tag (combined cleanup)."""
    tc = TC["deploy_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_UTILS, tag="cleanup")

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
        tag="cleanup",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" +
        PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


# =============================================================================
# COMBINED CLEANUP VERIFICATION TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.cleanup
@pytest.mark.order(1)
def test_cleanup_all_logs_cleaned(host):
    """Verify all log collection artifacts are cleaned."""
    tc = TC["cleanup_all_logs_cleaned"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    result = check_all_logs_cleaned(host, output_path)

    # Report detailed status
    tl.info("Log cleanup status:")
    tl.info(f"  Old bundles removed: {'Yes' if result['bundles_cleaned'] else 'No'}")
    tl.info(f"  Empty dirs removed: {'Yes' if result['empty_dirs_cleaned'] else 'No'}")
    tl.info(f"  Temp dirs cleaned: {'Yes' if result['temp_dirs_cleaned'] else 'No'}")

    if result["success"]:
        tl.passed("All log collection artifacts cleaned")
    else:
        issues = []
        if not result["bundles_cleaned"]:
            issues.append("old bundles remain")
        if not result["empty_dirs_cleaned"]:
            issues.append("empty directories remain")
        if not result["temp_dirs_cleaned"]:
            issues.append("temp directories not cleaned")
        tl.failed(f"Log cleanup incomplete: {', '.join(issues)}")

    assert result["success"], (
        f"Log collection artifacts not fully cleaned: "
        f"bundles={result['bundles_cleaned']}, "
        f"empty_dirs={result['empty_dirs_cleaned']}, "
        f"temp_dirs={result['temp_dirs_cleaned']}"
    )


@pytest.mark.sanity
@pytest.mark.cleanup
@pytest.mark.order(2)
def test_cleanup_all_install_os_cleaned(host):
    """Verify all install_os artifacts are cleaned."""
    tc = TC["cleanup_all_install_os_cleaned"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    result = check_all_install_os_cleaned(host, input_path)

    # Report detailed status
    tl.info("Install OS cleanup status:")
    tl.info(f"  Temp ISO dir removed: {'Yes' if result['temp_dir_cleaned'] else 'No'}")
    tl.info(f"  NFS unmounted: {'Yes' if result['nfs_cleaned'] else 'No'}")
    tl.info(f"  Credentials removed: {'Yes' if result['credentials_cleaned'] else 'No (may be intentional)'}")

    if result["success"]:
        tl.passed("All install_os artifacts cleaned")
    else:
        issues = []
        if not result["temp_dir_cleaned"]:
            issues.append("temp ISO directory remains")
        if not result["nfs_cleaned"]:
            issues.append("NFS mount not cleaned")
        tl.failed(f"Install OS cleanup incomplete: {', '.join(issues)}")

    # Note: credentials_cleaned is not required for success
    # (cleanup_credentials flag controls this behavior)
    assert result["success"], (
        f"Install OS artifacts not fully cleaned: "
        f"temp_dir={result['temp_dir_cleaned']}, "
        f"nfs={result['nfs_cleaned']}"
    )
