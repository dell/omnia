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
Omnia Main — Non-Functional CLI Performance Tests.

Verifies that omnia-cli commands complete within expected timeframes:
  MAIN_NFT_007: omnia-cli status completes within threshold
  MAIN_NFT_011: omnia-cli help completes within threshold
"""

import time

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger
from library.functions.omnia_main_func import run_omnia_cli_cmd

# Performance thresholds (seconds)
CLI_STATUS_THRESHOLD = 30    # 30 seconds
CLI_HELP_THRESHOLD = 5       # 5 seconds


@pytest.mark.nft
@pytest.mark.order(1)
def test_cli_status_performance(host):
    """MAIN_NFT_007: Verify omnia-cli status completes within threshold."""
    tc = TC["cli_status_performance"]
    tl = TestLogger(tc["title"], tc["id"])

    start = time.time()
    result = run_omnia_cli_cmd(host, "omnia_cli_status")
    duration = time.time() - start

    # omnia-cli status may exit 0 or 1 (domain not yet run)
    ran_ok = result["rc"] in (0, 1)
    within = duration <= CLI_STATUS_THRESHOLD

    if ran_ok and within:
        tl.passed(
            f"omnia-cli status completed in {duration:.1f}s "
            f"(threshold: {CLI_STATUS_THRESHOLD}s)"
        )
    elif ran_ok and not within:
        tl.failed(
            f"omnia-cli status exceeded threshold: "
            f"{duration:.1f}s > {CLI_STATUS_THRESHOLD}s"
        )
    else:
        tl.failed(
            f"omnia-cli status failed (rc={result['rc']}, "
            f"duration={duration:.1f}s)"
        )

    assert ran_ok, (
        f"omnia-cli status failed (rc={result['rc']})"
    )
    assert within, (
        f"omnia-cli status took {duration:.1f}s, "
        f"exceeds {CLI_STATUS_THRESHOLD}s threshold"
    )


@pytest.mark.nft
@pytest.mark.order(2)
def test_cli_help_performance(host):
    """MAIN_NFT_011: Verify omnia-cli help completes within threshold."""
    tc = TC["cli_help_performance"]
    tl = TestLogger(tc["title"], tc["id"])

    start = time.time()
    result = run_omnia_cli_cmd(host, "omnia_cli_help")
    duration = time.time() - start

    within = duration <= CLI_HELP_THRESHOLD

    if result["success"] and within:
        tl.passed(
            f"omnia-cli help completed in {duration:.1f}s "
            f"(threshold: {CLI_HELP_THRESHOLD}s)"
        )
    elif result["success"] and not within:
        tl.failed(
            f"omnia-cli help exceeded threshold: "
            f"{duration:.1f}s > {CLI_HELP_THRESHOLD}s"
        )
    else:
        tl.failed(
            f"omnia-cli help failed (rc={result['rc']}, "
            f"duration={duration:.1f}s)"
        )

    assert result["success"], (
        f"omnia-cli help failed (rc={result['rc']})"
    )
    assert within, (
        f"omnia-cli help took {duration:.1f}s, "
        f"exceeds {CLI_HELP_THRESHOLD}s threshold"
    )
