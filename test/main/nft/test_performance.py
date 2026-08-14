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
Omnia Main — Non-Functional Performance Tests.

Verifies that key omnia.sh operations complete within expected timeframes:
  NFT_MA_001: --setup-venv --deps-only completes within threshold
  NFT_MA_002: --init completes within threshold
"""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import run_omnia_cmd

# Performance thresholds (seconds)
SETUP_VENV_THRESHOLD = 300   # 5 minutes (pip + Galaxy install)
INIT_THRESHOLD = 120          # 2 minutes (log dirs + input copy)


@pytest.mark.nft
@pytest.mark.order(1)
def test_setup_venv_performance(host):
    """NFT_MA_001: Verify --setup-venv --deps-only completes within threshold."""
    tl = TestLogger(
        "NFT: setup-venv --deps-only performance", "NFT_MA_001"
    )
    result = run_omnia_cmd(host, "omnia_sh_setup_venv")

    duration = result.get("duration", 0)
    within = duration <= SETUP_VENV_THRESHOLD

    if result["success"] and within:
        tl.passed(
            f"setup-venv completed in {duration:.1f}s "
            f"(threshold: {SETUP_VENV_THRESHOLD}s)"
        )
    elif result["success"] and not within:
        tl.failed(
            f"setup-venv exceeded threshold: {duration:.1f}s > "
            f"{SETUP_VENV_THRESHOLD}s"
        )
    else:
        tl.failed(
            f"setup-venv failed (rc={result['rc']}, "
            f"duration={duration:.1f}s)"
        )

    assert result["success"], (
        f"omnia.sh --setup-venv --deps-only failed (rc={result['rc']})"
    )
    assert within, (
        f"setup-venv took {duration:.1f}s, "
        f"exceeds {SETUP_VENV_THRESHOLD}s threshold"
    )


@pytest.mark.nft
@pytest.mark.order(2)
def test_init_performance(host):
    """NFT_MA_002: Verify --init completes within threshold."""
    tl = TestLogger("NFT: init performance", "NFT_MA_002")
    result = run_omnia_cmd(host, "omnia_sh_init")

    duration = result.get("duration", 0)
    within = duration <= INIT_THRESHOLD

    if result["success"] and within:
        tl.passed(
            f"init completed in {duration:.1f}s "
            f"(threshold: {INIT_THRESHOLD}s)"
        )
    elif result["success"] and not within:
        tl.failed(
            f"init exceeded threshold: {duration:.1f}s > "
            f"{INIT_THRESHOLD}s"
        )
    else:
        tl.failed(
            f"init failed (rc={result['rc']}, "
            f"duration={duration:.1f}s)"
        )

    assert result["success"], (
        f"omnia.sh --init failed (rc={result['rc']})"
    )
    assert within, (
        f"init took {duration:.1f}s, "
        f"exceeds {INIT_THRESHOLD}s threshold"
    )
