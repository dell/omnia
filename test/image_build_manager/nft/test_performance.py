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
Image Build Manager — Non-Functional Performance Tests.

Verifies that key operations complete within expected timeframes:
  Playbook prepare completes within threshold
  Playbook build completes within threshold
  Playbook cleanup completes within threshold
"""

import pytest

from library.functions import TestLogger, run_playbook, load_test_config
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT

# Performance thresholds (seconds)
PREPARE_THRESHOLD = 300   # 5 minutes
BUILD_THRESHOLD = 3600    # 60 minutes
CLEANUP_THRESHOLD = 120   # 2 minutes


@pytest.mark.nft
@pytest.mark.order(1)
def test_prepare_performance(host):
    """Verify prepare completes within threshold."""
    tl = TestLogger("NFT: Prepare performance", "NFT_001")
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="prepare",
        timeout=PREPARE_THRESHOLD + 60,
    )

    duration = result.get("duration", 0)
    within = duration <= PREPARE_THRESHOLD

    if result["success"] and within:
        tl.passed(
            f"Prepare completed in {duration:.1f}s "
            f"(threshold: {PREPARE_THRESHOLD}s)"
        )
    elif result["success"] and not within:
        tl.failed(
            f"Prepare exceeded threshold: {duration:.1f}s > "
            f"{PREPARE_THRESHOLD}s"
        )
    else:
        tl.failed(
            f"Prepare failed (rc={result['rc']}, "
            f"duration={duration:.1f}s)"
        )

    assert result["success"], f"Playbook failed (rc={result['rc']})"
    assert within, (
        f"Prepare took {duration:.1f}s, exceeds "
        f"{PREPARE_THRESHOLD}s threshold"
    )


@pytest.mark.nft
@pytest.mark.order(2)
def test_build_performance(host):
    """Verify build completes within threshold."""
    tl = TestLogger("NFT: Build performance", "NFT_002")
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="build",
        timeout=BUILD_THRESHOLD + 60,
    )

    duration = result.get("duration", 0)
    within = duration <= BUILD_THRESHOLD

    if result["success"] and within:
        tl.passed(
            f"Build completed in {duration:.1f}s "
            f"(threshold: {BUILD_THRESHOLD}s)"
        )
    elif result["success"] and not within:
        tl.failed(
            f"Build exceeded threshold: {duration:.1f}s > "
            f"{BUILD_THRESHOLD}s"
        )
    else:
        tl.failed(
            f"Build failed (rc={result['rc']}, "
            f"duration={duration:.1f}s)"
        )

    assert result["success"], f"Playbook failed (rc={result['rc']})"
    assert within, (
        f"Build took {duration:.1f}s, exceeds "
        f"{BUILD_THRESHOLD}s threshold"
    )


@pytest.mark.nft
@pytest.mark.order(3)
def test_cleanup_performance(host):
    """Verify cleanup completes within threshold."""
    tl = TestLogger("NFT: Cleanup performance", "NFT_003")
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="cleanup",
        timeout=CLEANUP_THRESHOLD + 60,
    )

    duration = result.get("duration", 0)
    within = duration <= CLEANUP_THRESHOLD

    if result["success"] and within:
        tl.passed(
            f"Cleanup completed in {duration:.1f}s "
            f"(threshold: {CLEANUP_THRESHOLD}s)"
        )
    elif result["success"] and not within:
        tl.failed(
            f"Cleanup exceeded threshold: {duration:.1f}s > "
            f"{CLEANUP_THRESHOLD}s"
        )
    else:
        tl.failed(
            f"Cleanup failed (rc={result['rc']}, "
            f"duration={duration:.1f}s)"
        )

    assert result["success"], f"Playbook failed (rc={result['rc']})"
    assert within, (
        f"Cleanup took {duration:.1f}s, exceeds "
        f"{CLEANUP_THRESHOLD}s threshold"
    )
