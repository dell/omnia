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

"""PowerVault bind mount and functional group targeting validation tests."""

import pytest

from fvt.result import verify_pxeboot
from library.functions import (
    TestLogger,
    check_powervault_node_subdirectory,
    check_powervault_bind_mounts,
    check_powervault_bind_fstab_entries,
    check_powervault_bind_isolation,
    check_powervault_functional_group_targeting,
    check_powervault_multiple_prefix_targeting,
    check_powervault_bind_io,
    check_powervault_slurm_mandatory_bind_mounts,
    check_powervault_mysql_data_on_mount,
)
from library.vars import TEST_CASES as TC


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40616)
@pytest.mark.powervault_binds
def test_powervault_node_subdirectory(host):
    """Verify per-node subdirectory exists under mount point."""
    tc = TC["powervault_node_subdirectory"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_node_subdirectory)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40617)
@pytest.mark.powervault_binds
def test_powervault_bind_mounts(host):
    """Verify bind mount targets are active on all target nodes."""
    tc = TC["powervault_bind_mounts"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_bind_mounts)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40618)
@pytest.mark.powervault_binds
def test_powervault_bind_fstab_entries(host):
    """Verify bind mount fstab entries are persistent on all target nodes."""
    tc = TC["powervault_bind_fstab_entries"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_bind_fstab_entries)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40619)
@pytest.mark.powervault_binds
def test_powervault_bind_isolation(host):
    """Verify per-node data separation via bind mounts."""
    tc = TC["powervault_bind_isolation"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_bind_isolation)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40620)
@pytest.mark.powervault_binds
def test_powervault_functional_group_targeting(host):
    """Verify PV mount only on correct functional groups."""
    tc = TC["powervault_functional_group_targeting"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_functional_group_targeting)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40621)
@pytest.mark.powervault_binds
def test_powervault_multiple_prefix_targeting(host):
    """Verify multiple prefixes target all groups correctly."""
    tc = TC["powervault_multiple_prefix_targeting"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_multiple_prefix_targeting)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40628)
@pytest.mark.powervault_binds
def test_powervault_bind_io(host):
    """Verify bind-mount I/O reaches the PV backing store."""
    tc = TC["powervault_bind_io"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_bind_io)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40629)
@pytest.mark.powervault_binds
def test_powervault_slurm_mandatory_bind_mounts(host):
    """Verify /var/lib/mysql and /var/spool/slurm configured as bind targets."""
    tc = TC["powervault_slurm_mandatory_bind_mounts"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_slurm_mandatory_bind_mounts)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40630)
@pytest.mark.powervault_binds
def test_powervault_mysql_data_on_mount(host):
    """Verify MySQL/MariaDB datadir is on a PowerVault mount."""
    tc = TC["powervault_mysql_data_on_mount"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_mysql_data_on_mount)
