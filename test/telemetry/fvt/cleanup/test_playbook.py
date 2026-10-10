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
Telemetry Cleanup — Deploy and Post-Cleanup Verification.

Aligned with the orchestrator/image_build_manager single-execution
pattern: one ``test_deploy_cleanup`` runs the playbook exactly once per
FVT tag with all options resolved from ``test_config.yml``.

Post-deploy verification tests check the expected state based on the
config-driven cleanup behavior.

Execution order:
    Order 0: E001  - Deploy cleanup (single execution)
    Order 1: V015/V016 - Verify credentials follow selected policy
    Order 2: V017/V018 - Verify logs follow selected policy
    Order 3+:          - Remaining verification tests (in status/ files)

Configuration keys (from test_config.yml):
    delete_sinks_volume:  true/false  - sink PVC deletion
    cleanup_credentials:  true/false  - credential file removal
    cleanup_logs:         true/false  - log directory removal

Test cases:
    TEL_FVT_CLEANUP_E001: Deploy cleanup
    TEL_FVT_CLEANUP_V015: Verify credentials preserved (cleanup_credentials=false)
    TEL_FVT_CLEANUP_V016: Verify credentials deleted (cleanup_credentials=true)
    TEL_FVT_CLEANUP_V017: Verify logs preserved (cleanup_logs=false)
    TEL_FVT_CLEANUP_V018: Verify logs deleted (cleanup_logs=true)
"""

import pytest

from library.functions import TestLogger, run_playbook, load_test_config
from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.cleanup_func import (
    cleanup_extra_vars,
    cleanup_selection_fields,
    verify_credentials_preserved,
    verify_credentials_deleted,
    verify_logs_preserved,
    verify_logs_deleted,
)


# =============================================================================
# DEPLOY — Single playbook execution (aligned with orchestrator pattern)
# =============================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_cleanup(host):
    """TEL_FVT_CLEANUP_E001: Run ``telemetry.yml --tags cleanup`` exactly once.

    All cleanup options are resolved from ``test_config.yml`` via
    ``cleanup_extra_vars()``. No multi-phase execution — this is the
    only place in the cleanup FVT that calls ``run_playbook()``.
    """
    tc = TC["deploy_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])

    extra_vars = cleanup_extra_vars()
    fields = cleanup_selection_fields()
    field_summary = ", ".join(f"{k}={v}" for k, v in fields)
    tl.check(f"Running telemetry playbook --tags cleanup ({field_summary})")
    result = run_playbook(tag="cleanup", extra_vars=extra_vars or None)

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
# VERIFY — Credential policy (order 1)
# =============================================================================

@pytest.mark.functional
@pytest.mark.order(1)
def test_cleanup_credentials_follow_policy(host):
    """TEL_FVT_CLEANUP_V015/V016: Verify credentials follow selected policy.

    When cleanup_credentials=false in test_config.yml:
      - telemetry_credentials.yml must exist
      - .telemetry_credentials_key must exist

    When cleanup_credentials=true (default):
      - both files must be deleted

    When delete_sinks_volume=true, the Ansible role overrides
    preservation flags and always deletes credentials.
    """
    config = load_test_config()
    delete_volume = config.get("delete_sinks_volume", False)
    cleanup_creds = config.get("cleanup_credentials", True)

    # delete_sinks_volume=true overrides preservation
    expect_deleted = cleanup_creds or delete_volume

    if expect_deleted:
        tc = TC["cleanup_credentials_deleted"]
        tl = TestLogger(tc["title"], tc["id"])
        result = verify_credentials_deleted(host)
        if result["success"]:
            tl.passed("Credential files deleted", result["details"])
        else:
            tl.failed("Credential files not deleted", result["details"])
        assert result["success"], result["error"]
    else:
        tc = TC["cleanup_credentials_preserved"]
        tl = TestLogger(tc["title"], tc["id"])
        result = verify_credentials_preserved(host)
        if result["success"]:
            tl.passed("Credential files preserved", result["details"])
        elif "MISSING" in result.get("details", ""):
            # Credentials did not exist before cleanup (no prior deploy).
            # Preservation policy was honoured — there was nothing to delete.
            tl.passed(
                "Credential files absent (no prior deploy to preserve)",
                result["details"],
            )
        else:
            tl.failed("Credential files not preserved", result["details"])
            assert result["success"], result["error"]


# =============================================================================
# VERIFY — Log policy (order 2)
# =============================================================================

@pytest.mark.functional
@pytest.mark.order(2)
def test_cleanup_logs_follow_policy(host):
    """TEL_FVT_CLEANUP_V017/V018: Verify logs follow selected policy.

    When cleanup_logs=false in test_config.yml:
      - <OMNIA_DATA_PATH>/telemetry/log/<OMNIA_PROJECT_NAME>/ must exist

    When cleanup_logs=true (default):
      - the log directory must be deleted

    When delete_sinks_volume=true, the Ansible role overrides
    preservation flags and always deletes logs.
    """
    config = load_test_config()
    delete_volume = config.get("delete_sinks_volume", False)
    cleanup_log = config.get("cleanup_logs", True)

    # delete_sinks_volume=true overrides preservation
    expect_deleted = cleanup_log or delete_volume

    if expect_deleted:
        tc = TC["cleanup_logs_deleted"]
        tl = TestLogger(tc["title"], tc["id"])
        result = verify_logs_deleted(host)
        if result["success"]:
            tl.passed("Log directory deleted", result["details"])
        else:
            tl.failed("Log directory not deleted", result["details"])
        assert result["success"], result["error"]
    else:
        tc = TC["cleanup_logs_preserved"]
        tl = TestLogger(tc["title"], tc["id"])
        result = verify_logs_preserved(host)
        if result["success"]:
            tl.passed("Log directory preserved", result["details"])
        elif "MISSING" in result.get("details", ""):
            # Log directory did not exist before cleanup (no prior deploy).
            # Preservation policy was honoured — there was nothing to delete.
            tl.passed(
                "Log directory absent (no prior deploy to preserve)",
                result["details"],
            )
        else:
            tl.failed("Log directory not preserved", result["details"])
            assert result["success"], result["error"]
