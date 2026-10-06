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

"""OIM CPU, memory, and disk-space readiness contracts."""

import pytest
from library.functions import (
    check_oim_cpu_threshold,
    check_oim_disk_threshold,
    check_oim_memory_threshold,
)

from fvt.result import verify_precheck

pytestmark = [pytest.mark.sanity]


# ── positive tests ──────────────────────────────────────────────────


@pytest.mark.order(10)
def test_oim_cpu_threshold(host):
    """Require OIM CPU core count to meet the configured minimum."""
    verify_precheck(host, "oim_cpu_threshold", check_oim_cpu_threshold)


@pytest.mark.order(11)
def test_oim_memory_threshold(host):
    """Require OIM memory to meet the configured minimum."""
    verify_precheck(host, "oim_memory_threshold", check_oim_memory_threshold)


@pytest.mark.order(12)
def test_oim_disk_threshold(host):
    """Require OIM root filesystem to meet the configured minimum."""
    verify_precheck(host, "oim_disk_threshold", check_oim_disk_threshold)


# ── negative tests ──────────────────────────────────────────────────


@pytest.mark.negative
@pytest.mark.order(20)
def test_neg_cpu_below_threshold(host):
    """Detect failure when CPU threshold exceeds actual cores."""
    result = check_oim_cpu_threshold(host, min_cores=99999)
    assert not result["success"], (
        "CPU check should fail when threshold exceeds actual cores"
    )
    assert result["error"], "Failure must include an actionable message"


@pytest.mark.negative
@pytest.mark.order(21)
def test_neg_memory_below_threshold(host):
    """Detect failure when memory threshold exceeds actual RAM."""
    result = check_oim_memory_threshold(host, min_memory_gb=99999)
    assert not result["success"], (
        "Memory check should fail when threshold exceeds actual RAM"
    )
    assert result["error"], "Failure must include an actionable message"


@pytest.mark.negative
@pytest.mark.order(22)
def test_neg_disk_below_threshold(host):
    """Detect failure when disk threshold exceeds actual capacity."""
    result = check_oim_disk_threshold(host, min_disk_gb=99999)
    assert not result["success"], (
        "Disk check should fail when threshold exceeds actual capacity"
    )
    assert result["error"], "Failure must include an actionable message"
