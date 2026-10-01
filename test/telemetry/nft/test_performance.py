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
Telemetry — Non-Functional Performance Tests.

Verifies that key operations complete within expected timeframes:
  - Validate playbook completes within threshold (< 30s)
  - Deploy playbook completes within threshold (< 600s / 10 minutes)
  - Cleanup playbook completes within threshold (< 300s / 5 minutes)

Execution order:
  - Validate (order 100) and Deploy (order 101) run first.
  - Cleanup Phase 1 (order 130) runs after all resilience tests — cleanup
    without volume deletion (PVCs preserved).
  - Cleanup Phase 2 (order 140) runs last — cleanup with volume deletion
    (all PVCs deleted).

Test cases:
    TEL_NFT_001: Validate performance (order 100)
    TEL_NFT_002: Deploy performance (order 101)
    TEL_NFT_003: Cleanup performance without volume (order 130)
    TEL_NFT_020: Cleanup performance with volume deletion (order 140)
"""

import pytest

from omnia_auto import TestLogger, run_playbook

from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)

# Performance thresholds (seconds)
# Thresholds calculated based on maximum possible configuration flow with buffer:
# - VALIDATE: Config validation (fast operation) + 50% buffer
# - DEPLOY: Phase 0 (60s) + Phase 1 sinks (400s) + Phase 2 sources (200s) + Phase 3-4 (60s) + 20% buffer = 792s
# - CLEANUP: Phase 1 cleanup (200s) + Phase 2 verification (60s) + 20% buffer = 312s
VALIDATE_THRESHOLD = 45    # 45 seconds (30s + 50% buffer)
DEPLOY_THRESHOLD = 800     # 13.3 minutes (792s + buffer for infrastructure variability)
CLEANUP_THRESHOLD = 360    # 6 minutes (300s + buffer for infrastructure variability)


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.order(100)
def test_validate_performance(host):
    """TEL_NFT_001: Verify validate completes within 45s threshold.

    Runs the validation phase and asserts that execution completes in under
    45 seconds. Threshold includes 50% buffer for infrastructure variability.
    """
    tc = TC["nft_validate_perf"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Running validate playbook (threshold: {VALIDATE_THRESHOLD}s)")
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="validate",
        timeout=VALIDATE_THRESHOLD + 60,
    )

    duration = result.get("duration", 0)
    within_threshold = duration <= VALIDATE_THRESHOLD

    if result["rc"] == 0 and within_threshold:
        tl.passed(
            f"Validate completed in {duration:.1f}s "
            f"(threshold: {VALIDATE_THRESHOLD}s)",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s",
        )
    elif result["rc"] == 0 and not within_threshold:
        tl.failed(
            f"Validate exceeded threshold: {duration:.1f}s > {VALIDATE_THRESHOLD}s",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s",
        )
    else:
        output_lines = result.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-20:])
        tl.failed(
            f"Validate playbook failed (rc={result['rc']})",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s\n"
            f"Last output:\n{tail}",
        )

    assert result["rc"] == 0, f"Validate playbook failed (rc={result['rc']})"
    assert within_threshold, (
        f"Validate took {duration:.1f}s, exceeds {VALIDATE_THRESHOLD}s threshold"
    )


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.order(101)
def test_deploy_performance(host):
    """TEL_NFT_002: Verify deploy completes within 800s (13.3 min) threshold.

    Runs the deployment phase and asserts that full deployment completes in
    under 13.3 minutes. Threshold calculated as:
      Phase 0 (prerequisites): 60s
      Phase 1 (sinks: Kafka, VictoriaMetrics, VictoriaLogs): 400s
      Phase 2 (sources: iDRAC, LDMS, PowerScale, UFM, VAST, OME): 200s
      Phase 3-4 (verification + status): 60s
      Infrastructure buffer (20%): 132s
      Total: 792s + buffer = 800s
    """
    tc = TC["nft_deploy_perf"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Running deploy playbook (threshold: {DEPLOY_THRESHOLD}s)")
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="execute",
        timeout=DEPLOY_THRESHOLD + 120,
    )

    duration = result.get("duration", 0)
    within_threshold = duration <= DEPLOY_THRESHOLD

    if result["rc"] == 0 and within_threshold:
        tl.passed(
            f"Deploy completed in {duration:.1f}s "
            f"(threshold: {DEPLOY_THRESHOLD}s)",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s",
        )
    elif result["rc"] == 0 and not within_threshold:
        tl.failed(
            f"Deploy exceeded threshold: {duration:.1f}s > {DEPLOY_THRESHOLD}s",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s",
        )
    else:
        output_lines = result.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-30:])
        tl.failed(
            f"Deploy playbook failed (rc={result['rc']})",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s\n"
            f"Last output:\n{tail}",
        )

    assert result["rc"] == 0, f"Deploy playbook failed (rc={result['rc']})"
    assert within_threshold, (
        f"Deploy took {duration:.1f}s, exceeds {DEPLOY_THRESHOLD}s threshold"
    )


def _run_cleanup_performance(host, tl, extra_vars=None):
    """Shared cleanup performance logic for both volume modes."""
    tl.check(f"Running cleanup playbook (threshold: {CLEANUP_THRESHOLD}s)")
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="cleanup",
        timeout=CLEANUP_THRESHOLD + 60,
        extra_vars=extra_vars,
    )

    duration = result.get("duration", 0)
    within_threshold = duration <= CLEANUP_THRESHOLD

    if result["rc"] == 0 and within_threshold:
        tl.passed(
            f"Cleanup completed in {duration:.1f}s "
            f"(threshold: {CLEANUP_THRESHOLD}s)",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s",
        )
    elif result["rc"] == 0 and not within_threshold:
        tl.failed(
            f"Cleanup exceeded threshold: {duration:.1f}s > {CLEANUP_THRESHOLD}s",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s",
        )
    else:
        output_lines = result.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-30:])
        tl.failed(
            f"Cleanup playbook failed (rc={result['rc']})",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s\n"
            f"Last output:\n{tail}",
        )

    assert result["rc"] == 0, f"Cleanup playbook failed (rc={result['rc']})"
    assert within_threshold, (
        f"Cleanup took {duration:.1f}s, exceeds {CLEANUP_THRESHOLD}s threshold"
    )


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.order(130)
def test_cleanup_performance(host):
    """TEL_NFT_003: Verify cleanup completes within 360s (6 min) threshold.

    Runs the cleanup phase WITHOUT volume deletion and asserts that full
    cleanup completes in under 6 minutes. PVCs are preserved. Threshold
    calculated as:
      Phase 1 (cleanup sources + sinks): 200s
      Phase 2 (verification): 60s
      Infrastructure buffer (20%): 100s
      Total: 360s
    
    Ordered AFTER all resilience tests (Phase 1 of cleanup).
    """
    tc = TC["nft_cleanup_perf"]
    tl = TestLogger(tc["title"], tc["id"])
    _run_cleanup_performance(host, tl)


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.order(140)
def test_cleanup_with_volume_performance(host):
    """TEL_NFT_020: Verify cleanup with volume deletion completes within 360s (6 min).

    Runs the cleanup phase WITH Delete_sinks_volume=true and asserts that
    full cleanup completes in under 6 minutes. All PVCs are deleted. Same
    threshold as Phase 1 cleanup since volume deletion doesn't significantly
    increase cleanup time (PVCs are deleted asynchronously).

    Ordered LAST (Phase 2 of cleanup), after all Phase 1 tests complete.
    """
    tc = TC["nft_cleanup_vol_perf"]
    tl = TestLogger(tc["title"], tc["id"])
    _run_cleanup_performance(host, tl, extra_vars={"Delete_sinks_volume": "true"})
