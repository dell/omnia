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

"""OIM admin/public NIC presence, IPv4, and overlap contracts."""

from functools import partial

import pytest
from library.functions import (
    TestLogger,
    check_oim_forced_pxe_public_overlap,
    check_oim_pxe_nic_ipv4,
    check_oim_pxe_nic_present,
    check_oim_public_nic_present,
)
from library.vars import OIM_NEGATIVE_INPUTS as NEG
from library.vars import TEST_CASES as TC

from fvt.result import verify_precheck, verify_precheck_rejection

# ── positive tests ──────────────────────────────────────────────────


@pytest.mark.sanity
@pytest.mark.order(10204)
def test_oim_pxe_nic_present(host):
    """Require the configured admin NIC to exist and be UP."""
    tc = TC["oim_pxe_nic_present"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_oim_pxe_nic_present)


@pytest.mark.sanity
@pytest.mark.order(10205)
def test_oim_public_nic_present(host):
    """Require the public/default-route NIC to exist and be UP."""
    tc = TC["oim_public_nic_present"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_oim_public_nic_present)


@pytest.mark.sanity
@pytest.mark.order(10206)
def test_oim_pxe_nic_ipv4(host):
    """Require the admin NIC to carry the configured IPv4 address."""
    tc = TC["oim_pxe_nic_ipv4"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_oim_pxe_nic_ipv4)


@pytest.mark.negative
@pytest.mark.order(10213)
def test_neg_pxe_nic_missing(host):
    """Detect failure when a nonexistent NIC name is checked."""
    tc = TC["oim_missing_nic_rejection"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck_rejection(
        test_log,
        tc,
        host,
        partial(check_oim_pxe_nic_present, nic_name=NEG["missing_nic"]),
    )


@pytest.mark.negative
@pytest.mark.order(10214)
def test_neg_pxe_public_overlap(host):
    """Detect overlap when PXE NIC is forced to match the public NIC."""
    tc = TC["oim_nic_overlap_rejection"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck_rejection(
        test_log, tc, host, check_oim_forced_pxe_public_overlap
    )
