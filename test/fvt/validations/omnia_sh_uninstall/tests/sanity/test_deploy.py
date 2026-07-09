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
Omnia.sh Uninstall — Deploy Test.

Runs omnia.sh --uninstall to remove the omnia_core container.
This test runs BEFORE the verification tests (test_uninstall.py).

Usage:
    run_validation omnia_sh_uninstall deploy      # Uninstall only
    run_validation omnia_sh_uninstall test         # Uninstall + verify
    run_validation omnia_sh_uninstall verify       # Verification tests only
"""

import pytest

from automation_library.core import TestLogger
from automation_library.omnia_sh.messages.omnia_sh_msgs import (
    TEST_NAMES, TEST_LOG_MSGS as LOG_MSGS, TEST_ASSERT_MSGS as ASSERT_MSGS, SKIP_MSGS
)
from automation_library.omnia_sh.functions.omnia_sh_func import (
    check_container_running,
    run_omnia_sh_uninstall_testinfra,
)


# =============================================================================
# 0. UNINSTALL (TC-0)
# =============================================================================

@pytest.mark.deploy
@pytest.mark.order(0)
def test_omnia_sh_uninstall(host):
    """
    Deploy TC-0: Run omnia.sh --uninstall with progress output.

    Skip if omnia_core container is NOT running (nothing to uninstall).
    Uses background execution with 10-second progress updates.
    """
    log = TestLogger(TEST_NAMES["omnia_sh_uninstall"])

    # Check if container is running - skip if not
    container_result = check_container_running(host)
    if not container_result["success"]:
        print(f"    │ {SKIP_MSGS['container_not_running']}", flush=True)
        log.skipped(SKIP_MSGS["container_not_running"])
        pytest.skip(SKIP_MSGS["container_not_running"])

    # Run uninstall with progress callback
    print("    ▸ Running omnia.sh --uninstall...", flush=True)

    def _progress(elapsed: int) -> None:
        print(f"    │ Running... {elapsed}s elapsed", flush=True)

    result = run_omnia_sh_uninstall_testinfra(host, progress_callback=_progress)

    if result["success"]:
        output_lines = result["output"].strip().split("\n")
        for line in output_lines:
            print(f"    │ {line}", flush=True)
        log.passed(LOG_MSGS["uninstall_success"], "")
    else:
        log.failed(LOG_MSGS["uninstall_failed"], result["error"])

    assert result["success"], ASSERT_MSGS["uninstall_failed"].format(error=result["error"])
