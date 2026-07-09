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
Omnia.sh Uninstall — Verification Tests.

Verifies that omnia.sh --uninstall completed successfully by checking
the expected cleanup state.

Test cases (executed in order):
1. Verify omnia_core container is removed
2. Verify omnia_core.container service file is removed
3. Verify fstab entry is removed
4. Verify mount is removed

Usage:
    run_validation omnia_sh_uninstall verify       # Verification tests only
    run_validation omnia_sh_uninstall test          # Uninstall + verify
"""

import pytest

from automation_library.core import TestLogger
from automation_library.omnia_sh.vars.omnia_sh_vars import TEST_VARS
from automation_library.omnia_sh.messages.omnia_sh_msgs import (
    TEST_NAMES, TEST_LOG_MSGS as LOG_MSGS, TEST_ASSERT_MSGS as ASSERT_MSGS
)
from automation_library.omnia_sh.functions.omnia_sh_func import (
    check_container_not_running,
    check_service_not_exists,
    check_fstab_entry_removed,
    check_mount_removed,
)


# =============================================================================
# VERIFICATION TESTS (TC-1 to TC-4)
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(1)
def test_uninstall_container_removed(host):
    """
    Test Case 1: Verify omnia_core container is NOT running after uninstall.
    """
    log = TestLogger(TEST_NAMES["cleanup_container_removed"])
    result = check_container_not_running(host)

    if result["success"]:
        print(f"    │ {result['details']}", flush=True)
        log.passed(LOG_MSGS["cleanup_container_removed"], result["details"])
    else:
        log.failed(LOG_MSGS["cleanup_container_still_running"], result["error"])

    assert result["success"], ASSERT_MSGS["cleanup_failed"].format(error=result["error"])


@pytest.mark.sanity
@pytest.mark.order(2)
def test_uninstall_service_file_removed(host):
    """
    Test Case 2: Verify omnia_core.container service file is removed.
    """
    log = TestLogger(TEST_NAMES["cleanup_service_removed"])
    path = TEST_VARS["container_file"]
    result = check_service_not_exists(host)

    if result["success"]:
        print(f"    │ Path: {path}", flush=True)
        print(f"    │ {result['details']}", flush=True)
        log.passed(LOG_MSGS["cleanup_service_removed"], f"Path: {path}\n{result['details']}")
    else:
        log.failed(LOG_MSGS["cleanup_service_exists"], f"Path: {path}\n{result['error']}")

    assert result["success"], ASSERT_MSGS["cleanup_failed"].format(error=result["error"])


@pytest.mark.sanity
@pytest.mark.order(3)
def test_uninstall_fstab_entry_removed(host):
    """
    Test Case 3: Verify fstab entry for omnia_shared_path is removed.
    """
    log = TestLogger(TEST_NAMES["cleanup_fstab_removed"])
    result = check_fstab_entry_removed(host)

    # Skip if omnia_shared_path is not configured
    if "No omnia_shared_path configured" in result.get("details", ""):
        log.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        print(f"    │ {result['details']}", flush=True)
        log.passed(LOG_MSGS["cleanup_fstab_removed"], result["details"])
    else:
        log.failed(LOG_MSGS["cleanup_fstab_exists"], result["error"])

    assert result["success"], ASSERT_MSGS["cleanup_failed"].format(error=result["error"])


@pytest.mark.sanity
@pytest.mark.order(4)
def test_uninstall_mount_removed(host):
    """
    Test Case 4: Verify omnia_shared_path is NOT mounted.
    """
    log = TestLogger(TEST_NAMES["cleanup_mount_removed"])
    result = check_mount_removed(host)

    # Skip if omnia_shared_path is not configured
    if "No omnia_shared_path configured" in result.get("details", ""):
        log.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        print(f"    │ {result['details']}", flush=True)
        log.passed(LOG_MSGS["cleanup_mount_removed"], result["details"])
    else:
        log.failed(LOG_MSGS["cleanup_mount_exists"], result["error"])

    assert result["success"], ASSERT_MSGS["cleanup_failed"].format(error=result["error"])
