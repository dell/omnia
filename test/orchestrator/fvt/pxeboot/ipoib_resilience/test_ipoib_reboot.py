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

"""TC-FVT-025/026: Slurm controller and compute reboot with IPoIB recovery."""

import pytest
from library.functions import (
    TestLogger,
    check_ipoib_compute_multi_reboot_recovery,
    check_ipoib_compute_reboot_recovery,
    check_ipoib_controller_reboot_recovery,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


def _verify(host, key, checker):
    tc = TC[key]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, checker)


@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.reboot
@pytest.mark.order(42621)
def test_ipoib_controller_reboot_recovery(host):
    """TC-FVT-025: IB, services, PowerVault, IB mesh, and accounting recover."""
    _verify(host, "ipoib_controller_reboot", check_ipoib_controller_reboot_recovery)


@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.reboot
@pytest.mark.order(42631)
def test_ipoib_compute_reboot_recovery(host):
    """TC-FVT-026 S1-S4,S6: one compute recovers IB; peers and jobs are undisturbed."""
    _verify(host, "ipoib_compute_reboot", check_ipoib_compute_reboot_recovery)


@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.reboot
@pytest.mark.order(42632)
def test_ipoib_compute_multi_reboot_recovery(host):
    """TC-FVT-026 S5: simultaneous compute reboot restores the full mesh and MPI over IB."""
    _verify(host, "ipoib_compute_multi_reboot", check_ipoib_compute_multi_reboot_recovery)
