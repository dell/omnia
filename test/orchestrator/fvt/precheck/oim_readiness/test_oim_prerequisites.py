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

"""OIM SSH, internet, and OS-version readiness contracts."""

from functools import partial

import pytest
from library.functions import (
    TestLogger,
    check_oim_internet_reachability,
    check_oim_os_version,
    check_oim_ssh_preflight,
)
from library.vars import OIM_NEGATIVE_INPUTS as NEG
from library.vars import TEST_CASES as TC

from fvt.result import verify_precheck, verify_precheck_rejection

# ── positive tests ──────────────────────────────────────────────────


@pytest.mark.sanity
@pytest.mark.order(10207)
def test_oim_ssh_preflight(host):
    """Require passwordless SSH from OIM to a mapped target node."""
    tc = TC["oim_ssh_preflight"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_oim_ssh_preflight)


@pytest.mark.sanity
@pytest.mark.order(10208)
def test_oim_internet_reachability(host):
    """Require internet reachability when not in air-gapped mode."""
    tc = TC["oim_internet_reachability"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_oim_internet_reachability)


@pytest.mark.sanity
@pytest.mark.order(10209)
def test_oim_os_version(host):
    """Require the OIM OS to match the expected distribution and version."""
    tc = TC["oim_os_version"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_oim_os_version)


@pytest.mark.negative
@pytest.mark.order(10215)
def test_neg_internet_airgapped(host):
    """Verify air-gapped mode passes even without internet."""
    tc = TC["oim_airgapped_internet"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(
        test_log,
        tc,
        host,
        partial(check_oim_internet_reachability, require_internet=False),
    )


@pytest.mark.negative
@pytest.mark.order(10216)
def test_neg_ssh_unreachable_target(host):
    """Detect SSH failure to a bogus target address."""
    tc = TC["oim_unreachable_ssh_rejection"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck_rejection(
        test_log,
        tc,
        host,
        partial(check_oim_ssh_preflight, target=NEG["unreachable_target"]),
    )


@pytest.mark.negative
@pytest.mark.order(10217)
def test_neg_os_version_mismatch(host):
    """Detect failure when expected OS version does not match actual."""
    tc = TC["oim_os_mismatch_rejection"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck_rejection(
        test_log,
        tc,
        host,
        partial(
            check_oim_os_version,
            expected_id=NEG["os_id"],
            expected_version=NEG["os_version"],
        ),
    )
