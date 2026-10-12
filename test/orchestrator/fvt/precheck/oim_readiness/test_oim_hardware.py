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

from functools import partial

import pytest
from library.functions import (
    TestLogger,
    check_oim_cpu_threshold,
    check_oim_disk_threshold,
    check_oim_memory_threshold,
)
from library.vars import OIM_NEGATIVE_INPUTS as NEG
from library.vars import TEST_CASES as TC

from fvt.result import verify_precheck, verify_precheck_rejection

# ── positive tests ──────────────────────────────────────────────────


@pytest.mark.sanity
@pytest.mark.order(10201)
def test_oim_cpu_threshold(host):
    """Require OIM CPU core count to meet the configured minimum."""
    tc = TC["oim_cpu_threshold"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_oim_cpu_threshold)


@pytest.mark.sanity
@pytest.mark.order(10202)
def test_oim_memory_threshold(host):
    """Require OIM memory to meet the configured minimum."""
    tc = TC["oim_memory_threshold"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_oim_memory_threshold)


@pytest.mark.sanity
@pytest.mark.order(10203)
def test_oim_disk_threshold(host):
    """Require OIM root filesystem to meet the configured minimum."""
    tc = TC["oim_disk_threshold"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_oim_disk_threshold)


@pytest.mark.negative
@pytest.mark.order(10210)
def test_neg_cpu_below_threshold(host):
    """Detect failure when CPU threshold exceeds actual cores."""
    tc = TC["oim_cpu_rejection"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck_rejection(
        test_log,
        tc,
        host,
        partial(check_oim_cpu_threshold, min_cores=NEG["min_cores"]),
    )


@pytest.mark.negative
@pytest.mark.order(10211)
def test_neg_memory_below_threshold(host):
    """Detect failure when memory threshold exceeds actual RAM."""
    tc = TC["oim_memory_rejection"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck_rejection(
        test_log,
        tc,
        host,
        partial(check_oim_memory_threshold, min_memory_gb=NEG["min_memory_gb"]),
    )


@pytest.mark.negative
@pytest.mark.order(10212)
def test_neg_disk_below_threshold(host):
    """Detect failure when disk threshold exceeds actual capacity."""
    tc = TC["oim_disk_rejection"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck_rejection(
        test_log,
        tc,
        host,
        partial(check_oim_disk_threshold, min_disk_gb=NEG["min_disk_gb"]),
    )
