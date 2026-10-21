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
Telemetry — Non-Functional Idempotency Tests.

Verifies that telemetry playbooks are idempotent: running them a second
time on an already-configured environment must succeed (exit code 0)
without errors or unintended changes.

This is critical because:
  - Ansible tasks must use proper idempotency guards (changed_when, creates, etc.)
  - Kubernetes resources must use declarative apply (not create)
  - Cleanup tasks must handle missing resources gracefully

Execution order:
  - Deploy idempotency runs early (order 105) — stack stays deployed.
  - Cleanup Phase 1 (orders 131-133) — cleanup without volume deletion,
    PVCs preserved. Verifies no pods and PVCs preserved.
  - Cleanup Phase 2 (orders 141-143) — cleanup with volume deletion,
    all PVCs deleted. Verifies no pods and no PVCs remain.

Test cases:
    TEL_NFT_004: Deploy idempotency (order 105)
    TEL_NFT_005: Cleanup idempotency without volume (order 131)
    TEL_NFT_015: Verify no pods after cleanup (order 132)
    TEL_NFT_017: Verify PVCs preserved after cleanup (order 133)
    TEL_NFT_021: Cleanup idempotency with volume deletion (order 141)
    TEL_NFT_022: Verify no pods after cleanup with volume (order 142)
    TEL_NFT_016: Verify no PVCs after cleanup with volume (order 143)
"""

import pytest
from library.functions.cleanup_func import (
    verify_no_pods_remaining,
    verify_pvcs_preserved,
    verify_source_pvcs_deleted,
    verify_sink_pvcs_deleted,
)
from library.messages.telemetry_msgs import (
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
)
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR
from library.vars.test_case_vars import TEST_CASES as TC
from omnia_auto import TestLogger, run_playbook


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(105)
def test_deploy_idempotency(host):
    """TEL_NFT_004: Deploy idempotency — second run exits 0.

    Runs the full deploy playbook twice in sequence:
      1. First run: deploys telemetry infrastructure (sinks + sources).
      2. Second run: must succeed (rc=0) on an already-deployed environment.

    This validates that all deploy tasks are idempotent and don't fail
    when resources already exist.  Runs early (before resilience tests)
    so the stack is deployed for subsequent tests.
    """
    tc = TC["nft_deploy_idempotent"]
    tl = TestLogger(tc["title"], tc["id"])

    # -- Run 1: Initial deploy --------------------------------------------
    tl.check("Running first deploy (initial deployment)")
    run1 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="execute",
    )

    if run1["rc"] != 0:
        output_lines = run1.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-20:])
        tl.failed(
            LOG_MSGS["deploy_failed"],
            f"First deploy failed (rc={run1['rc']}). "
            f"Cannot test idempotency.\nLast output:\n{tail}",
        )
        pytest.fail(
            f"First deploy run failed (rc={run1['rc']}). "
            f"Idempotency test requires the first run to succeed."
        )

    # -- Run 2: Idempotent re-run -----------------------------------------
    tl.check("Running second deploy (idempotency check)")
    run2 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="execute",
    )

    if run2["rc"] == 0:
        tl.passed(
            f"Deploy idempotency verified: second run exited 0 "
            f"(duration={run2.get('duration', 'N/A')}s)",
            f"Run 1: rc={run1['rc']} ({run1.get('duration', 'N/A')}s)\n"
            f"Run 2: rc={run2['rc']} ({run2.get('duration', 'N/A')}s)",
        )
    else:
        output_lines = run2.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-30:])
        tl.failed(
            f"Deploy idempotency failed: second run exited {run2['rc']}",
            f"Second deploy run failed.\n"
            f"Exit code: {run2['rc']}\n"
            f"Last output:\n{tail}",
        )

    assert run2["rc"] == 0, (
        f"Deploy idempotency check failed. Second deploy run returned "
        f"exit code {run2['rc']}. A deploy playbook must be safe to run "
        f"multiple times without errors."
    )


def _run_cleanup_idempotency(host, tl, extra_vars=None):
    """Shared cleanup idempotency logic for both volume modes."""
    # -- Run 1: Initial cleanup -------------------------------------------
    tl.check("Running first cleanup (initial cleanup)")
    run1 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="cleanup",
        extra_vars=extra_vars,
    )

    if run1["rc"] != 0:
        output_lines = run1.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-20:])
        tl.failed(
            LOG_MSGS["cleanup_failed"],
            f"First cleanup failed (rc={run1['rc']}). "
            f"Cannot test idempotency.\nLast output:\n{tail}",
        )
        pytest.fail(
            f"First cleanup run failed (rc={run1['rc']}). "
            f"Idempotency test requires the first run to succeed."
        )

    # -- Run 2: Idempotent re-run -----------------------------------------
    tl.check("Running second cleanup (idempotency check)")
    run2 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="cleanup",
        extra_vars=extra_vars,
    )

    if run2["rc"] == 0:
        tl.passed(
            LOG_MSGS["idempotent_passed"].format(
                duration=run2.get("duration", "N/A"),
            ),
            f"Run 1: rc={run1['rc']} ({run1.get('duration', 'N/A')}s)\n"
            f"Run 2: rc={run2['rc']} ({run2.get('duration', 'N/A')}s)",
        )
    else:
        output_lines = run2.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-30:])
        tl.failed(
            LOG_MSGS["idempotent_failed"].format(rc=run2["rc"]),
            f"Second cleanup run failed.\n"
            f"Exit code: {run2['rc']}\n"
            f"Last output:\n{tail}",
        )

    assert run2["rc"] == 0, ASSERT_MSGS["idempotent_failed"].format(
        rc=run2["rc"],
    )


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(131)
def test_cleanup_idempotency(host):
    """TEL_NFT_005: Cleanup idempotency — second run exits 0.

    Runs the full cleanup playbook twice in sequence WITHOUT volume deletion:
      1. First run: cleans up remaining resources (PVCs preserved).
      2. Second run: must succeed (rc=0) on an already-clean namespace.

    Phase 1 of cleanup — ordered AFTER cleanup performance (order 130).
    """
    tc = TC["nft_cleanup_idempotent"]
    tl = TestLogger(tc["title"], tc["id"])
    _run_cleanup_idempotency(host, tl)


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(141)
def test_cleanup_with_volume_idempotency(host):
    """TEL_NFT_021: Cleanup with volume idempotency — second run exits 0.

    Runs the full cleanup playbook twice in sequence WITH Delete_sinks_volume=true:
      1. First run: cleans up all resources including PVCs.
      2. Second run: must succeed (rc=0) on a fully-clean namespace.

    Phase 2 of cleanup — ordered AFTER cleanup with volume performance (order 140).
    """
    tc = TC["nft_cleanup_vol_idempotent"]
    tl = TestLogger(tc["title"], tc["id"])
    _run_cleanup_idempotency(
        host, tl, extra_vars={"Delete_sinks_volume": "true"},
    )


def _verify_no_pods(host, tl):
    """Shared no-pods verification logic."""
    result = verify_no_pods_remaining(host)

    if result["success"]:
        tl.passed(LOG_MSGS["no_pods_remaining"], result["details"])
    else:
        tl.failed(
            LOG_MSGS["pods_remaining"].format(count=result["count"]),
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["pods_remaining"].format(
        count=result["count"],
    )


# =========================================================================
# Phase 1: Cleanup WITHOUT volume deletion (PVCs preserved)
# =========================================================================


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(132)
def test_cleanup_idempotency_no_pods(host):
    """TEL_NFT_015: Verify no pods after idempotent cleanup (Phase 1).

    After two cleanup runs without volume deletion, the telemetry namespace
    must have zero pods — the second run must not re-create any resources.
    """
    tc = TC["nft_cleanup_no_pods"]
    tl = TestLogger(tc["title"], tc["id"])
    _verify_no_pods(host, tl)


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(133)
def test_cleanup_pvcs_preserved(host):
    """TEL_NFT_017: Verify PVCs preserved after cleanup without volume deletion.

    After cleanup without Delete_sinks_volume=true:
      - Source PVCs must be deleted
      - Sink PVCs (Kafka, VictoriaMetrics, VictoriaLogs) must be preserved
    """
    tc = TC["nft_cleanup_pvcs_preserved"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying source PVCs were deleted after idempotent cleanup")
    result_source = verify_source_pvcs_deleted(host)
    if not result_source["success"]:
        tl.failed(
            LOG_MSGS["pvcs_remaining"].format(count=result_source["count"]),
            result_source["details"],
        )
    assert result_source["success"], (
        f"Source PVCs were not deleted: {result_source['error']}"
    )

    tl.check("Verifying sink PVCs were preserved after idempotent cleanup")
    result = verify_pvcs_preserved(host)
    if result["success"]:
        tl.passed(LOG_MSGS["pvcs_preserved"], result["details"])
    else:
        tl.failed(
            LOG_MSGS["pvcs_not_preserved"],
            result["details"],
        )
    assert result["success"], ASSERT_MSGS["pvcs_not_preserved"]


# =========================================================================
# Phase 2: Cleanup WITH volume deletion (all PVCs deleted)
# =========================================================================


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(142)
def test_cleanup_with_volume_no_pods(host):
    """TEL_NFT_022: Verify no pods after cleanup with volume deletion (Phase 2).

    After two cleanup runs with Delete_sinks_volume=true, the telemetry
    namespace must have zero pods.
    """
    tc = TC["nft_cleanup_vol_no_pods"]
    tl = TestLogger(tc["title"], tc["id"])
    _verify_no_pods(host, tl)


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(143)
def test_cleanup_with_volume_no_pvcs(host):
    """TEL_NFT_016: Verify no PVCs after cleanup with volume deletion.

    After cleanup with Delete_sinks_volume=true:
      - Source PVCs must be deleted
      - Sink PVCs must also be deleted (all PVCs removed)
    """
    tc = TC["nft_cleanup_no_pvcs"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying source PVCs were deleted after idempotent cleanup")
    result_source = verify_source_pvcs_deleted(host)
    if not result_source["success"]:
        tl.failed(
            LOG_MSGS["pvcs_remaining"].format(count=result_source["count"]),
            result_source["details"],
        )
    assert result_source["success"], (
        f"Source PVCs were not deleted: {result_source['error']}"
    )

    tl.check("Verifying sink PVCs were deleted after idempotent cleanup")
    result_sink = verify_sink_pvcs_deleted(host)
    if result_sink["success"]:
        tl.passed(
            LOG_MSGS["no_pvcs_remaining"],
            f"{result_source['details']}\n{result_sink['details']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pvcs_remaining"].format(count=result_sink["count"]),
            result_sink["details"],
        )
    assert result_sink["success"], (
        f"Sink PVCs were not deleted: {result_sink['error']}"
    )

