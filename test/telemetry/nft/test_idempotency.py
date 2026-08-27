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

Test cases:
    NFT_TL_004: Deploy idempotency (second run exits 0)
    NFT_TL_005: Cleanup idempotency (second run exits 0)
"""

import pytest

from omnia_auto import TestLogger, run_playbook

from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.cleanup_func import (
    verify_no_pods_remaining,
    verify_no_pvcs_remaining,
)


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(110)
def test_deploy_idempotency(host):
    """NFT_TL_004: Deploy idempotency — second run exits 0.

    Runs the full deploy playbook twice in sequence:
      1. First run: deploys telemetry infrastructure (sinks + sources).
      2. Second run: must succeed (rc=0) on an already-deployed environment.

    This validates that all deploy tasks are idempotent and don't fail
    when resources already exist.
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


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(111)
def test_cleanup_idempotency(host):
    """NFT_TL_005: Cleanup idempotency — second run exits 0.

    Runs the full cleanup playbook twice in sequence:
      1. First run: cleans up telemetry resources (may or may not find any).
      2. Second run: must succeed (rc=0) on an already-clean namespace.

    This validates that all cleanup tasks handle missing resources
    gracefully (--ignore-not-found, failed_when: false, helm guards).
    """
    tc = TC["nft_cleanup_idempotent"]
    tl = TestLogger(tc["title"], tc["id"])

    # -- Run 1: Initial cleanup -------------------------------------------
    tl.check("Running first cleanup (initial cleanup)")
    run1 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="cleanup",
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
@pytest.mark.order(112)
def test_cleanup_idempotency_no_pods(host):
    """NFT_TL_005b: Verify no pods after idempotent cleanup.

    After two cleanup runs, the telemetry namespace must still have
    zero pods — the second run must not re-create any resources.
    """
    tc = TC["no_pods_after_full_cleanup"]
    tl = TestLogger(
        "Verify no pods after idempotent cleanup",
        tc["id"] + "-idem",
    )

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


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(113)
def test_cleanup_idempotency_no_pvcs(host):
    """NFT_TL_005c: Verify no PVCs after idempotent cleanup.

    After two cleanup runs, the telemetry namespace must still have
    zero PVCs — the second run must not re-create any resources.
    """
    tc = TC["no_pvcs_after_full_cleanup"]
    tl = TestLogger(
        "Verify no PVCs after idempotent cleanup",
        tc["id"] + "-idem",
    )

    result = verify_no_pvcs_remaining(host)

    if result["success"]:
        tl.passed(LOG_MSGS["no_pvcs_remaining"], result["details"])
    else:
        tl.failed(
            LOG_MSGS["pvcs_remaining"].format(count=result["count"]),
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["pvcs_remaining"].format(
        count=result["count"],
    )
