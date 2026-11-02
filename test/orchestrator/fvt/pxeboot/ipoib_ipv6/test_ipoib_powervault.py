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

"""TC-FVT-024: Slurm controller PowerVault Ethernet iSCSI and IPoIB coexistence."""

import pytest
from library.functions import (
    TestLogger,
    check_ipoib_powervault_coexistence,
    check_ipoib_powervault_dns_resilience,
    check_ipoib_powervault_ib_reprovision,
    check_ipoib_powervault_iscsi_path,
    check_ipoib_powervault_nfs_coexistence,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


def _verify(host, key, checker):
    tc = TC[key]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, checker)


@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42508)
def test_ipoib_powervault_coexistence(host):
    """TC-FVT-024 S1: IB UP with approved address and PowerVault mounted together."""
    _verify(host, "ipoib_pv_coexistence", check_ipoib_powervault_coexistence)


@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42509)
def test_ipoib_powervault_iscsi_path(host):
    """TC-FVT-024 S2: iSCSI routes via Ethernet; no IB route captures the portals."""
    _verify(host, "ipoib_pv_iscsi_path", check_ipoib_powervault_iscsi_path)


@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42510)
def test_ipoib_powervault_dns_resilience(host):
    """TC-FVT-024 S4: IB DNS injection does not break iSCSI target discovery."""
    _verify(host, "ipoib_pv_dns_resilience", check_ipoib_powervault_dns_resilience)


@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42511)
def test_ipoib_powervault_nfs_coexistence(host):
    """TC-FVT-024 S5: NFS (TCP, Ethernet), PowerVault, and IB coexist without conflict."""
    _verify(host, "ipoib_pv_nfs_coexistence", check_ipoib_powervault_nfs_coexistence)


@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.fault_injection
@pytest.mark.order(42512)
def test_ipoib_powervault_ib_reprovision(host):
    """TC-FVT-024 S3: PowerVault binds and Slurm state survive IB re-provisioning."""
    _verify(host, "ipoib_pv_ib_reprovision", check_ipoib_powervault_ib_reprovision)
