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
Discovery — Non-Functional Performance Tests.

Verifies that key operations complete within expected timeframes:
  Playbook precheck completes within threshold
  Playbook execute completes within threshold
  Playbook cleanup completes within threshold
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.vars import TEST_CASES as TC
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT

# Performance thresholds (seconds)
PRECHECK_THRESHOLD = 60  # 1 minute
EXECUTE_THRESHOLD = 600  # 10 minutes
CLEANUP_THRESHOLD = 120  # 2 minutes


@pytest.mark.nft
@pytest.mark.order(1)
def test_precheck_performance():
    """Verify precheck completes within threshold."""
    tc = TC["precheck_performance"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="precheck",
        timeout=PRECHECK_THRESHOLD + 60,
    )

    duration = result.get("duration", 0)
    within = duration <= PRECHECK_THRESHOLD

    if result["success"] and within:
        tl.passed(
            f"Precheck completed in {duration:.1f}s "
            f"(threshold: {PRECHECK_THRESHOLD}s)"
        )
    elif result["success"] and not within:
        tl.failed(
            f"Precheck exceeded threshold: {duration:.1f}s > "
            f"{PRECHECK_THRESHOLD}s"
        )
    else:
        tl.failed(
            f"Precheck failed (rc={result['rc']}, "
            f"duration={duration:.1f}s)"
        )

    assert result["success"], f"Playbook failed (rc={result['rc']})"
    assert within, (
        f"Precheck took {duration:.1f}s, exceeds "
        f"{PRECHECK_THRESHOLD}s threshold"
    )


@pytest.mark.nft
@pytest.mark.order(2)
def test_execute_performance():
    """Verify execute completes within threshold."""
    tc = TC["execute_performance"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="execute",
        timeout=EXECUTE_THRESHOLD + 60,
    )

    duration = result.get("duration", 0)
    within = duration <= EXECUTE_THRESHOLD

    if result["success"] and within:
        tl.passed(
            f"Execute completed in {duration:.1f}s "
            f"(threshold: {EXECUTE_THRESHOLD}s)"
        )
    elif result["success"] and not within:
        tl.failed(
            f"Execute exceeded threshold: {duration:.1f}s > "
            f"{EXECUTE_THRESHOLD}s"
        )
    else:
        tl.failed(
            f"Execute failed (rc={result['rc']}, "
            f"duration={duration:.1f}s)"
        )

    assert result["success"], f"Playbook failed (rc={result['rc']})"
    assert within, (
        f"Execute took {duration:.1f}s, exceeds "
        f"{EXECUTE_THRESHOLD}s threshold"
    )


@pytest.mark.nft
@pytest.mark.order(3)
def test_cleanup_performance():
    """Verify cleanup completes within threshold."""
    tc = TC["cleanup_performance"]
    tl = TestLogger(tc["title"], tc["id"])
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
