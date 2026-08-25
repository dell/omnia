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
Telemetry Cleanup — Idempotency Tests.

Verifies that the telemetry cleanup playbook is idempotent: running it
a second time on an already-clean environment must succeed (exit code 0)
without errors.

This is critical because:
  - Ansible tasks use ``--ignore-not-found=true`` and ``failed_when: false``
    to handle missing resources gracefully.
  - The pre-sink guard must not fail when no source pods exist.
  - Helm uninstall guards must handle already-uninstalled releases.

Test cases:
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


@pytest.mark.functional
@pytest.mark.regression
@pytest.mark.order(70)
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
        host=host,
        playbook=PLAYBOOK_ENTRY_POINT,
        workdir=PLAYBOOK_WORKDIR,
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
        host=host,
        playbook=PLAYBOOK_ENTRY_POINT,
        workdir=PLAYBOOK_WORKDIR,
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


@pytest.mark.functional
@pytest.mark.regression
@pytest.mark.order(71)
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


@pytest.mark.functional
@pytest.mark.regression
@pytest.mark.order(72)
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
