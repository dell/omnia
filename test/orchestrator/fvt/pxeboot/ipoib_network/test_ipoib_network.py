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


"""ER-ORCH-005 post-boot IPoIB verification for the active ib_addr_mode."""

import pytest
from library.functions import (
    TestLogger,
    check_ipoib_mode_address_assignment,
    check_ipoib_address_state,
    check_ipoib_nm_profile,
    check_ipoib_routes,
    check_ipoib_peer_mesh,
    check_ipoib_smd_records,
    check_ipoib_slurm_nodeaddr,
    check_ipoib_custom_slurm_conf,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.ipoib
@pytest.mark.non_disruptive
@pytest.mark.order(42501)
def test_ipoib_mode_address_assignment(host):
    """Each node carries exactly the IB addresses ib_addr_mode selects."""
    tc = TC["ipoib_mode_address_assignment"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_ipoib_mode_address_assignment)


@pytest.mark.ipoib
@pytest.mark.non_disruptive
@pytest.mark.order(42502)
def test_ipoib_address_state(host):
    """TC-FVT-015/017: each approved IB address is static, healthy, and alone."""
    tc = TC["ipoib_address_state"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_ipoib_address_state)


@pytest.mark.ipoib
@pytest.mark.non_disruptive
@pytest.mark.order(42503)
def test_ipoib_nm_profile(host):
    """TC-FVT-002/009: NetworkManager profile matches the IPoIB mode."""
    tc = TC["ipoib_nm_profile"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_ipoib_nm_profile)


@pytest.mark.ipoib
@pytest.mark.non_disruptive
@pytest.mark.order(42504)
def test_ipoib_routes(host):
    """TC-FVT-009/015: IPoIB is on-link only; peers route directly via IB."""
    tc = TC["ipoib_routes"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_ipoib_routes)


@pytest.mark.ipoib
@pytest.mark.non_disruptive
@pytest.mark.order(42505)
def test_ipoib_peer_mesh(host):
    """TC-FVT-023: every IB node reaches every peer in each mode family."""
    tc = TC["ipoib_peer_mesh"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_ipoib_peer_mesh)


@pytest.mark.ipoib
@pytest.mark.non_disruptive
@pytest.mark.order(42506)
def test_ipoib_smd_records(host):
    """TC-FVT-011: SMD holds every approved IPoIB address."""
    tc = TC["ipoib_smd_records"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_ipoib_smd_records)


@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42507)
def test_ipoib_slurm_nodeaddr(host):
    """TC-FVT-019/031: Slurm NodeAddr follows the IB allocation."""
    tc = TC["ipoib_slurm_nodeaddr"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_ipoib_slurm_nodeaddr)


@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42508)
def test_ipoib_custom_slurm_conf(host):
    """TC-FVT-027: custom slurm.conf nodes respond over IB."""
    tc = TC["ipoib_custom_slurm_conf"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_ipoib_custom_slurm_conf)
