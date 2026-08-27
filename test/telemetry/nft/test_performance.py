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

Test cases:
    NFT_TL_001: Validate performance (< 30s)
    NFT_TL_002: Deploy performance (< 600s)
    NFT_TL_003: Cleanup performance (< 300s)
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
VALIDATE_THRESHOLD = 30    # 30 seconds
DEPLOY_THRESHOLD = 600     # 10 minutes
CLEANUP_THRESHOLD = 300    # 5 minutes


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.order(100)
def test_validate_performance(host):
    """NFT_TL_001: Verify validate completes within 30s threshold.

    Runs ``ansible-playbook telemetry.yml --tags validate`` and asserts
    that execution completes in under 30 seconds.
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
    """NFT_TL_002: Verify deploy completes within 600s (10 min) threshold.

    Runs ``ansible-playbook telemetry.yml --tags execute`` and asserts
    that full deployment completes in under 10 minutes.
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


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.order(102)
def test_cleanup_performance(host):
    """NFT_TL_003: Verify cleanup completes within 300s (5 min) threshold.

    Runs ``ansible-playbook telemetry.yml --tags cleanup`` and asserts
    that full cleanup completes in under 5 minutes.
    """
    tc = TC["nft_cleanup_perf"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Running cleanup playbook (threshold: {CLEANUP_THRESHOLD}s)")
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="cleanup",
        timeout=CLEANUP_THRESHOLD + 60,
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
