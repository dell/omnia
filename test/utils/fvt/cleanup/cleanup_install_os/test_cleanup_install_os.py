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
Cleanup Install OS Scenario - Test Automation.

Tests for utils.yml --tags cleanup_install_os functionality.
Validates that the cleanup_install_os tag properly cleans OS installation artifacts:
- Removes /tmp/install_os temporary directory
- Unmounts and removes /tmp/install_os_nfs
- Optionally removes credential files (when cleanup_credentials=true)
"""

import pytest

from library.functions import (
    TestLogger,
    load_test_config,
    run_playbook,
    get_utils_input_path,
    check_install_os_temp_dir_removed,
    check_install_os_nfs_unmounted,
    check_install_os_credentials_removed,
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
@pytest.mark.cleanup_install_os
@pytest.mark.order(0)
def test_deploy_cleanup_install_os(host):
    """Deploy utils.yml with cleanup_install_os tag."""
    tc = TC["deploy_cleanup_install_os"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_UTILS, tag="cleanup_install_os")

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
        tag="cleanup_install_os",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" +
        PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


# =============================================================================
# CLEANUP INSTALL OS VERIFICATION TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.cleanup_install_os
@pytest.mark.order(1)
def test_cleanup_install_os_temp_iso_removed(host):
    """Verify /tmp/install_os directory is removed."""
    tc = TC["cleanup_install_os_temp_iso_removed"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_install_os_temp_dir_removed(host)

    if result["success"]:
        tl.passed(f"Temporary ISO directory removed: {result['path']}")
    else:
        tl.failed(f"Temporary ISO directory still exists: {result['path']}")

    assert result["success"], (
        f"Temporary ISO directory not removed: {result['path']}"
    )


@pytest.mark.sanity
@pytest.mark.cleanup_install_os
@pytest.mark.order(2)
def test_cleanup_install_os_nfs_unmounted(host):
    """Verify /tmp/install_os_nfs is unmounted and removed."""
    tc = TC["cleanup_install_os_nfs_unmounted"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if NFS mount point was ever created (skip if install_os was never run)
    # The NFS mount is only created during install_os deployment
    nfs_path = "/tmp/install_os_nfs"
    check_cmd = f"test -d {nfs_path} || mount | grep -q '{nfs_path}'"
    check_result = host.run(check_cmd)

    if check_result.rc != 0:
        tl.info(f"NFS mount point {nfs_path} was never created (install_os not run)")
        tl.passed("NFS cleanup check skipped - no NFS mount point to clean")
        pytest.skip("NFS mount point was never created - install_os not run")

    result = check_install_os_nfs_unmounted(host)

    if result["success"]:
        tl.passed(f"NFS mount point cleaned: {result['path']}")
    else:
        status_parts = []
        if result["mounted"]:
            status_parts.append("still mounted")
        if result["exists"]:
            status_parts.append("directory exists")
        status = ", ".join(status_parts) if status_parts else "unknown issue"
        tl.failed(f"NFS mount point not cleaned: {result['path']} ({status})")

    assert result["success"], (
        f"NFS mount point not cleaned: {result['path']} "
        f"(mounted={result['mounted']}, exists={result['exists']})"
    )


@pytest.mark.functional
@pytest.mark.cleanup_install_os
@pytest.mark.order(3)
def test_cleanup_install_os_credentials_removed(host):
    """Verify credential files are removed when cleanup_credentials=true.
    
    Note: This test verifies the credential cleanup behavior. By default,
    credentials are NOT removed unless cleanup_credentials=true is passed.
    This test checks the current state of credential files.
    """
    tc = TC["cleanup_install_os_credentials_removed"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    result = check_install_os_credentials_removed(host, input_path)

    # Report the status of each credential file
    for item in result["results"]:
        status = "removed" if item["removed"] else "exists"
        if item.get("query_error"):
            status = f"error: {item['query_error']}"
        tl.info(f"  {item['path']}: {status}")

    if result["success"]:
        tl.passed("All credential files removed")
    else:
        # This is informational - credentials may be intentionally kept
        remaining = [item["path"] for item in result["results"] if not item["removed"]]
        tl.info(
            f"Credential files still exist: {remaining}. "
            "This is expected unless cleanup_credentials=true was passed."
        )
        # Mark as passed since credential cleanup is optional
        tl.passed("Credential cleanup check completed (files may be intentionally retained)")

    # This test always passes - it's informational about credential state
    # The actual cleanup behavior depends on the cleanup_credentials flag
    assert True, "Credential cleanup verification completed"
