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

"""VAST functional group targeting validation tests."""

import pytest

from library.functions import (
    TestLogger,
    check_vast_compute_node_mounts,
    check_vast_control_node_mounts,
    check_vast_control_node_no_vast,
    check_vast_login_node_mounts,
    check_vast_qss_mounts,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.sanity
@pytest.mark.vast_targeting
@pytest.mark.order(42109)
def test_vast_control_node_no_vast(host):
    """Verify Slurm control node has no VAST storage."""
    tc = TC["vast_control_node_no_vast"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_control_node_no_vast)


@pytest.mark.sanity
@pytest.mark.vast_targeting
@pytest.mark.order(42113)
def test_vast_qss_mounts(host):
    """Verify VAST on compute/login only; controller has none."""
    tc = TC["vast_qss_mounts"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_qss_mounts)


@pytest.mark.sanity
@pytest.mark.vast_targeting
@pytest.mark.order(42115)
def test_vast_control_node_mounts(host):
    """Verify controller mount table (NFS/PV only, no VAST)."""
    tc = TC["vast_control_node_mounts"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_control_node_mounts)


@pytest.mark.sanity
@pytest.mark.vast_targeting
@pytest.mark.order(42116)
def test_vast_compute_node_mounts(host):
    """Verify compute node mount table (NFS + VAST)."""
    tc = TC["vast_compute_node_mounts"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_compute_node_mounts)


@pytest.mark.sanity
@pytest.mark.vast_targeting
@pytest.mark.order(42117)
def test_vast_login_node_mounts(host):
    """Verify login/compiler node mount table."""
    tc = TC["vast_login_node_mounts"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_login_node_mounts)
