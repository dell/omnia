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
omnia.sh --uninstall / Cleanup — Deploy Tests.

Runs ``omnia.sh --uninstall`` with automatic 'y' confirmation.

Test cases:
    TC_UT_001  Run omnia.sh --uninstall

Usage:
    run_validation omnia_sh_uninstall deploy
    run_validation omnia_sh_uninstall test
"""

import pytest

from main.library import (
    TestLogger,
    PlaybookRunner,
    OMNIA_SH_VARS,
    TEST_NAMES,
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
    SKIP_MSGS,
    check_container_running,
    check_omnia_sh_exists,
)


# =============================================================================
# 0. UNINSTALL (TC-0)
# =============================================================================

@pytest.mark.order(0)
def test_omnia_sh_uninstall(host):
    """TC_UT_001: Run omnia.sh --uninstall."""
    log = TestLogger("[TC_UT_001] " + TEST_NAMES["omnia_sh_uninstall"])

    # Skip if container not running — nothing to uninstall
    container_result = check_container_running(host)
    if not container_result["success"]:
        log.skipped(SKIP_MSGS["container_not_running"])
        pytest.skip(SKIP_MSGS["container_not_running"])

    # Verify omnia.sh exists
    omnia_sh = OMNIA_SH_VARS["omnia_sh_path"]
    log.check(f"Checking omnia.sh at {omnia_sh}")
    sh_result = check_omnia_sh_exists(host)
    if not sh_result["success"]:
        log.failed("omnia.sh not found", sh_result["error"])
        pytest.fail(sh_result["error"])
    log.passed(f"Found: {sh_result['path']} ({sh_result['ref_type']})")

    # Run omnia.sh --uninstall with 'y' confirmation and live output
    log.check("Running omnia.sh --uninstall...")
    runner = PlaybookRunner()
    result = runner.run_shell(
        f"echo 'y' | bash {omnia_sh} --uninstall",
        label="omnia.sh --uninstall",
        timeout=OMNIA_SH_VARS.get("uninstall_timeout", 300),
    )

    if result["success"]:
        log.passed(
            LOG_MSGS["uninstall_success"],
            f"rc={result['rc']}, duration={result['duration']:.1f}s"
        )
    else:
        log.failed(LOG_MSGS["uninstall_failed"], result["error"])

    assert result["success"], ASSERT_MSGS["uninstall_failed"].format(
        error=result["error"]
    )
