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

"""VAST functional group targeting validation tests
(TC-009, TC-013, TC-015, TC-016, TC-017)."""

import pytest

from fvt.result import verify_pxeboot
from library.functions import (
    check_vast_control_node_no_vast,
    check_vast_qss_mounts,
    check_vast_control_node_mounts,
    check_vast_compute_node_mounts,
    check_vast_login_node_mounts,
)


@pytest.mark.sanity
@pytest.mark.order(708)
@pytest.mark.vast_targeting
def test_vast_control_node_no_vast(host):
    """TC-009: Verify Slurm control node has no VAST storage."""
    verify_pxeboot(host, "vast_control_node_no_vast", check_vast_control_node_no_vast)


@pytest.mark.sanity
@pytest.mark.order(712)
@pytest.mark.vast_targeting
def test_vast_qss_mounts(host):
    """TC-013: Verify VAST on compute/login only; controller has none."""
    verify_pxeboot(host, "vast_qss_mounts", check_vast_qss_mounts)


@pytest.mark.sanity
@pytest.mark.order(714)
@pytest.mark.vast_targeting
def test_vast_control_node_mounts(host):
    """TC-015: Verify controller mount table (NFS/PV only, no VAST)."""
    verify_pxeboot(host, "vast_control_node_mounts", check_vast_control_node_mounts)


@pytest.mark.sanity
@pytest.mark.order(715)
@pytest.mark.vast_targeting
def test_vast_compute_node_mounts(host):
    """TC-016: Verify compute node mount table (NFS + VAST)."""
    verify_pxeboot(host, "vast_compute_node_mounts", check_vast_compute_node_mounts)


@pytest.mark.sanity
@pytest.mark.order(716)
@pytest.mark.vast_targeting
def test_vast_login_node_mounts(host):
    """TC-017: Verify login/compiler node mount table."""
    verify_pxeboot(host, "vast_login_node_mounts", check_vast_login_node_mounts)
