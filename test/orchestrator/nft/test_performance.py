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
Orchestrator — Non-Functional Performance Tests.

Verifies that key orchestrator operations complete within expected timeframes:
  - Validate playbook completes within threshold (< 30s)
  - Prepare playbook completes within threshold (< 300s / 5 min)
  - Provision playbook completes within threshold (< 1800s / 30 min)
  - Cleanup playbook completes within threshold (< 180s / 3 min)

Test cases:
    NFT_OR_001: Validate performance (< 30s)
    NFT_OR_002: Prepare performance (< 300s)
    NFT_OR_003: Provision performance (< 1800s)
    NFT_OR_004: Cleanup performance (< 180s)
"""

import pytest

from library.functions import TestLogger, run_playbook, load_test_config
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

# Performance thresholds (seconds)
VALIDATE_THRESHOLD = 30     # 30 seconds - config validation only
PREPARE_THRESHOLD = 300     # 5 minutes - OpenCHAMI container deployment
PROVISION_THRESHOLD = 1800  # 30 minutes - full node provisioning
CLEANUP_THRESHOLD = 180     # 3 minutes - container/service removal


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.order(1)
def test_validate_performance(host):
    """NFT_OR_001: Verify validate completes within 30s threshold.

    Runs ``ansible-playbook orchestrator.yml --tags validate`` and asserts
    that configuration validation completes in under 30 seconds.
    """
    tl = TestLogger("NFT: Validate performance", "NFT_OR_001")

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
@pytest.mark.order(2)
def test_prepare_performance(host):
    """NFT_OR_002: Verify prepare completes within 300s (5 min) threshold.

    Runs ``ansible-playbook orchestrator.yml --tags prepare`` and asserts
    that OpenCHAMI deployment completes in under 5 minutes.
    """
    tl = TestLogger("NFT: Prepare performance", "NFT_OR_002")

    tl.check(f"Running prepare playbook (threshold: {PREPARE_THRESHOLD}s)")
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="prepare",
        timeout=PREPARE_THRESHOLD + 120,
    )

    duration = result.get("duration", 0)
    within_threshold = duration <= PREPARE_THRESHOLD

    if result["rc"] == 0 and within_threshold:
        tl.passed(
            f"Prepare completed in {duration:.1f}s "
            f"(threshold: {PREPARE_THRESHOLD}s)",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s",
        )
    elif result["rc"] == 0 and not within_threshold:
        tl.failed(
            f"Prepare exceeded threshold: {duration:.1f}s > {PREPARE_THRESHOLD}s",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s",
        )
    else:
        output_lines = result.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-30:])
        tl.failed(
            f"Prepare playbook failed (rc={result['rc']})",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s\n"
            f"Last output:\n{tail}",
        )

    assert result["rc"] == 0, f"Prepare playbook failed (rc={result['rc']})"
    assert within_threshold, (
        f"Prepare took {duration:.1f}s, exceeds {PREPARE_THRESHOLD}s threshold"
    )


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.order(3)
def test_provision_performance(host):
    """NFT_OR_003: Verify provision completes within 1800s (30 min) threshold.

    Runs ``ansible-playbook orchestrator.yml --tags provision`` and asserts
    that full node provisioning completes in under 30 minutes.
    Note: This test requires a fully configured environment with provisioned nodes.
    """
    tl = TestLogger("NFT: Provision performance", "NFT_OR_003")

    config = load_test_config()
    # Skip if provision is not enabled in config
    if not config.get("run_provision_tests", False):
        tl.skipped("Provision tests disabled in config")
        pytest.skip("Provision tests disabled in config")

    tl.check(f"Running provision playbook (threshold: {PROVISION_THRESHOLD}s)")
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="provision",
        timeout=PROVISION_THRESHOLD + 300,
    )

    duration = result.get("duration", 0)
    within_threshold = duration <= PROVISION_THRESHOLD

    if result["rc"] == 0 and within_threshold:
        tl.passed(
            f"Provision completed in {duration:.1f}s "
            f"(threshold: {PROVISION_THRESHOLD}s)",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s",
        )
    elif result["rc"] == 0 and not within_threshold:
        tl.failed(
            f"Provision exceeded threshold: {duration:.1f}s > {PROVISION_THRESHOLD}s",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s",
        )
    else:
        output_lines = result.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-30:])
        tl.failed(
            f"Provision playbook failed (rc={result['rc']})",
            f"Exit code: {result['rc']}\nDuration: {duration:.2f}s\n"
            f"Last output:\n{tail}",
        )

    assert result["rc"] == 0, f"Provision playbook failed (rc={result['rc']})"
    assert within_threshold, (
        f"Provision took {duration:.1f}s, exceeds {PROVISION_THRESHOLD}s threshold"
    )


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.order(4)
def test_cleanup_performance(host):
    """NFT_OR_004: Verify cleanup completes within 180s (3 min) threshold.

    Runs ``ansible-playbook orchestrator.yml --tags cleanup`` and asserts
    that container/service cleanup completes in under 3 minutes.
    """
    tl = TestLogger("NFT: Cleanup performance", "NFT_OR_004")

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