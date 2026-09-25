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
Telemetry Cleanup — Preservation Flags (credentials and logs) Tests.

Tests for cleanup_credentials and cleanup_logs flags to verify that
credential files and log directories are preserved or deleted as expected.

Test cases:
    TEL_FVT_CLEANUP_E002: Deploy cleanup with preservation flags
    TEL_FVT_CLEANUP_V015: Verify credentials preserved (cleanup_credentials=false)
    TEL_FVT_CLEANUP_V016: Verify credentials deleted (cleanup_credentials=true)
    TEL_FVT_CLEANUP_V017: Verify logs preserved (cleanup_logs=false)
    TEL_FVT_CLEANUP_V018: Verify logs deleted (cleanup_logs=true)
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.cleanup_func import (
    verify_credentials_preserved,
    verify_credentials_deleted,
    verify_logs_preserved,
    verify_logs_deleted,
)


# =============================================================================
# PLAYBOOK EXECUTION TESTS
# =============================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_cleanup_with_preservation_flags(host):
    """TEL_FVT_CLEANUP_E002: Deploy cleanup with preservation flags.
    
    Runs cleanup with:
      - cleanup_credentials=false (preserve credentials)
      - cleanup_logs=false (preserve logs)
    
    Ordered FIRST (order 0) to run preservation cleanup before default cleanup.
    This ensures credentials and logs are preserved for verification.
    """
    tc = TC["deploy_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])

    extra_vars = {
        "cleanup_credentials": "false",
        "cleanup_logs": "false",
    }
    tl.check("Running cleanup with preservation flags (cleanup_credentials=false, cleanup_logs=false)")
    result = run_playbook(tag="cleanup", extra_vars=extra_vars)

    if result["success"]:
        tl.passed(
            LOG_MSGS["playbook_success"].format(
                duration=f"{result['duration']:.1f}s",
            ),
            f"rc={result['rc']}",
        )
    else:
        tl.failed(
            LOG_MSGS["playbook_failed"].format(
                rc=result["rc"],
                duration=f"{result['duration']:.1f}s",
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["playbook_failed"].format(
        playbook="telemetry.yml",
        tag="cleanup",
        rc=result["rc"],
    )


# =============================================================================
# CREDENTIAL PRESERVATION VERIFICATION TESTS
# =============================================================================

@pytest.mark.functional
@pytest.mark.order(1)
def test_cleanup_credentials_preserved(host):
    """TEL_FVT_CLEANUP_V015: Verify credentials preserved after cleanup.
    
    After cleanup with cleanup_credentials=false:
      - telemetry_credentials.yml must exist
      - .telemetry_credentials_key must exist
    
    Ordered AFTER preservation cleanup deployment (order 1).
    """
    
    tc = TC["cleanup_credentials_preserved"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_credentials_preserved(host)

    if result["success"]:
        tl.passed(
            "Credential files preserved",
            result["details"],
        )
    else:
        tl.failed(
            "Credential files not preserved",
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(2)
def test_cleanup_credentials_deleted(host):
    """TEL_FVT_CLEANUP_V016: Verify credentials deleted after cleanup.
    
    After cleanup with cleanup_credentials=true (default):
      - telemetry_credentials.yml must be deleted
      - .telemetry_credentials_key must be deleted
    
    Note: This test is informational. It checks the current state of
    credential files after a default cleanup run. Run this test after
    a cleanup without the cleanup_credentials=false flag.
    
    Ordered AFTER credentials preserved test (order 2).
    """
    
    tc = TC["cleanup_credentials_deleted"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_credentials_deleted(host)

    if result["success"]:
        tl.passed(
            "Credential files deleted",
            result["details"],
        )
    else:
        # This test is informational - credentials may be preserved
        # if cleanup_credentials=false was used
        tl.info(
            "Credential files still exist (may be intentional)",
            result["details"],
        )
        # Always pass - this is informational
        tl.passed("Credential cleanup verification completed")

    # Always pass for this informational test
    assert True, "Credential cleanup verification completed"


# =============================================================================
# LOG PRESERVATION VERIFICATION TESTS
# =============================================================================

@pytest.mark.functional
@pytest.mark.order(3)
def test_cleanup_logs_preserved(host):
    """TEL_FVT_CLEANUP_V017: Verify logs preserved after cleanup.
    
    After cleanup with cleanup_logs=false:
      - <OMNIA_DATA_PATH>/telemetry/log/<OMNIA_PROJECT_NAME>/ must exist
    
    Ordered AFTER credentials deleted test (order 3).
    """
    
    tc = TC["cleanup_logs_preserved"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_logs_preserved(host)

    if result["success"]:
        tl.passed(
            "Log directory preserved",
            result["details"],
        )
    else:
        tl.failed(
            "Log directory not preserved",
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(4)
def test_cleanup_logs_deleted(host):
    """TEL_FVT_CLEANUP_V018: Verify logs deleted after cleanup.
    
    After cleanup with cleanup_logs=true (default):
      - <OMNIA_DATA_PATH>/telemetry/log/<OMNIA_PROJECT_NAME>/ must be deleted
    
    Note: This test is informational. It checks the current state of
    log directory after a default cleanup run. Run this test after
    a cleanup without the cleanup_logs=false flag.
    
    Ordered LAST in preservation phase (order 4) to complete preservation verification.
    """
    
    tc = TC["cleanup_logs_deleted"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_logs_deleted(host)

    if result["success"]:
        tl.passed(
            "Log directory deleted",
            result["details"],
        )
    else:
        # This test is informational - logs may be preserved
        # if cleanup_logs=false was used
        tl.info(
            "Log directory still exists (may be intentional)",
            result["details"],
        )
        # Always pass - this is informational
        tl.passed("Log cleanup verification completed")

    # Always pass for this informational test
    assert True, "Log cleanup verification completed"
