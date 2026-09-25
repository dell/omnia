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
Telemetry Cleanup — Preservation and Deletion Verification Tests.

Tests for cleanup_credentials and cleanup_logs flags to verify that
credential files and log directories are preserved or deleted as expected.

Execution order:
    Order 0: E002  — Deploy cleanup with preservation flags
    Order 1: V015  — Verify credentials preserved
    Order 2: V017  — Verify logs preserved
    Order 3: E001  — Deploy default cleanup (in test_playbook.py)
    Order 4: V016  — Verify credentials deleted
    Order 5: V018  — Verify logs deleted
    Order 6+:       — Remaining verification tests (in status/ files)

Variable interactions (from Ansible source):
    - cleanup_credentials=false  → preserves credential files
    - cleanup_logs=false         → preserves log directory
    - Delete_sinks_volume=true   → OVERRIDES both flags: credentials and
      logs are always deleted in cleanup-with-volume mode.

When delete_sinks_volume=true the entire preservation phase is skipped
because the Ansible role ignores preservation flags in that mode.

Test cases:
    TEL_FVT_CLEANUP_E002: Deploy cleanup with preservation flags
    TEL_FVT_CLEANUP_V015: Verify credentials preserved (cleanup_credentials=false)
    TEL_FVT_CLEANUP_V016: Verify credentials deleted after default cleanup
    TEL_FVT_CLEANUP_V017: Verify logs preserved (cleanup_logs=false)
    TEL_FVT_CLEANUP_V018: Verify logs deleted after default cleanup
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
# PHASE 1: PRESERVATION CLEANUP + VERIFICATION (orders 0-2)
# =============================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_cleanup_with_preservation_flags(host, delete_sinks_volume):
    """TEL_FVT_CLEANUP_E002: Deploy cleanup with preservation flags.

    Runs cleanup with:
      - cleanup_credentials=false (preserve credentials)
      - cleanup_logs=false (preserve logs)

    Ordered FIRST (order 0) so preservation can be verified before the
    default cleanup wipes credentials and logs.

    Skipped when delete_sinks_volume=true because the Ansible role
    overrides preservation flags and always deletes credentials/logs
    in cleanup-with-volume mode.
    """
    if delete_sinks_volume:
        pytest.skip(
            "delete_sinks_volume=true — preservation flags are overridden; "
            "credentials and logs are always deleted in this mode"
        )

    tc = TC["deploy_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])

    extra_vars = {
        "cleanup_credentials": "false",
        "cleanup_logs": "false",
    }
    tl.check("Running cleanup with preservation flags "
             "(cleanup_credentials=false, cleanup_logs=false)")
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


@pytest.mark.functional
@pytest.mark.order(1)
def test_cleanup_credentials_preserved(host, delete_sinks_volume):
    """TEL_FVT_CLEANUP_V015: Verify credentials preserved after cleanup.

    After cleanup with cleanup_credentials=false:
      - telemetry_credentials.yml must exist
      - .telemetry_credentials_key must exist

    Depends on: test_deploy_cleanup_with_preservation_flags (order 0).
    Skipped when delete_sinks_volume=true (preservation not applicable).
    """
    if delete_sinks_volume:
        pytest.skip(
            "delete_sinks_volume=true — preservation flags are overridden; "
            "credentials are always deleted in this mode"
        )

    tc = TC["cleanup_credentials_preserved"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_credentials_preserved(host)

    if result["success"]:
        tl.passed("Credential files preserved", result["details"])
    else:
        tl.failed("Credential files not preserved", result["details"])

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(2)
def test_cleanup_logs_preserved(host, delete_sinks_volume):
    """TEL_FVT_CLEANUP_V017: Verify logs preserved after cleanup.

    After cleanup with cleanup_logs=false:
      - <OMNIA_DATA_PATH>/telemetry/log/<OMNIA_PROJECT_NAME>/ must exist

    Depends on: test_deploy_cleanup_with_preservation_flags (order 0).
    Skipped when delete_sinks_volume=true (preservation not applicable).
    """
    if delete_sinks_volume:
        pytest.skip(
            "delete_sinks_volume=true — preservation flags are overridden; "
            "logs are always deleted in this mode"
        )

    tc = TC["cleanup_logs_preserved"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_logs_preserved(host)

    if result["success"]:
        tl.passed("Log directory preserved", result["details"])
    else:
        tl.failed("Log directory not preserved", result["details"])

    assert result["success"], result["error"]


# =============================================================================
# PHASE 2: DEFAULT CLEANUP (order 3)
# =============================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(3)
def test_deploy_cleanup(host, delete_sinks_volume):
    """TEL_FVT_CLEANUP_E001: Deploy telemetry (--tags cleanup).

    Runs after both preservation checks. When delete_sinks_volume=true,
    passes -e Delete_sinks_volume=true to also delete sink PVCs.
    """
    tc = TC["deploy_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])

    extra_vars = {"Delete_sinks_volume": "true"} if delete_sinks_volume else None
    mode_label = "with volume deletion" if delete_sinks_volume else "default"
    tl.check(f"Running telemetry playbook --tags cleanup ({mode_label})")
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
# PHASE 3: DELETION VERIFICATION (orders 4-5)
# These run AFTER the default cleanup (E001) to verify that credentials
# and logs were actually deleted by the default cleanup.
# =============================================================================

@pytest.mark.functional
@pytest.mark.order(4)
def test_cleanup_credentials_deleted(host):
    """TEL_FVT_CLEANUP_V016: Verify credentials deleted after default cleanup.

    After the default cleanup (cleanup_credentials=true by default):
      - telemetry_credentials.yml must be deleted
      - .telemetry_credentials_key must be deleted

    Depends on: test_deploy_cleanup (order 3 in this module).
    Also applies when delete_sinks_volume=true because that mode always
    deletes credentials.
    """
    tc = TC["cleanup_credentials_deleted"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_credentials_deleted(host)

    if result["success"]:
        tl.passed("Credential files deleted", result["details"])
    else:
        tl.failed("Credential files not deleted", result["details"])

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(5)
def test_cleanup_logs_deleted(host):
    """TEL_FVT_CLEANUP_V018: Verify logs deleted after default cleanup.

    After the default cleanup (cleanup_logs=true by default):
      - <OMNIA_DATA_PATH>/telemetry/log/<OMNIA_PROJECT_NAME>/ must be deleted

    Depends on: test_deploy_cleanup (order 3 in this module).
    Also applies when delete_sinks_volume=true because that mode always
    deletes logs.
    """
    tc = TC["cleanup_logs_deleted"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_logs_deleted(host)

    if result["success"]:
        tl.passed("Log directory deleted", result["details"])
    else:
        tl.failed("Log directory not deleted", result["details"])

    assert result["success"], result["error"]
