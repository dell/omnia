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


@pytest.mark.sanity
@pytest.mark.order(316)
@pytest.mark.powervault_binds
def test_powervault_node_subdirectory(host):
    """Verify per-node subdirectory exists under mount point."""
    verify_pxeboot(host, "powervault_node_subdirectory", check_powervault_node_subdirectory)


@pytest.mark.sanity
@pytest.mark.order(317)
@pytest.mark.powervault_binds
def test_powervault_bind_mounts(host):
    """Verify bind mount targets are active on all target nodes."""
    verify_pxeboot(host, "powervault_bind_mounts", check_powervault_bind_mounts)


@pytest.mark.sanity
@pytest.mark.order(318)
@pytest.mark.powervault_binds
def test_powervault_bind_fstab_entries(host):
    """Verify bind mount fstab entries are persistent on all target nodes."""
    verify_pxeboot(host, "powervault_bind_fstab_entries", check_powervault_bind_fstab_entries)


@pytest.mark.sanity
@pytest.mark.order(319)
@pytest.mark.powervault_binds
def test_powervault_bind_isolation(host):
    """Verify per-node data separation via bind mounts."""
    verify_pxeboot(host, "powervault_bind_isolation", check_powervault_bind_isolation)


@pytest.mark.sanity
@pytest.mark.order(320)
@pytest.mark.powervault_binds
def test_powervault_functional_group_targeting(host):
    """Verify PV mount only on correct functional groups."""
    verify_pxeboot(host, "powervault_functional_group_targeting", check_powervault_functional_group_targeting)


@pytest.mark.sanity
@pytest.mark.order(321)
@pytest.mark.powervault_binds
def test_powervault_multiple_prefix_targeting(host):
    """Verify multiple prefixes target all groups correctly."""
    verify_pxeboot(host, "powervault_multiple_prefix_targeting", check_powervault_multiple_prefix_targeting)


@pytest.mark.sanity
@pytest.mark.order(328)
@pytest.mark.powervault_binds
def test_powervault_bind_io(host):
    """Verify bind-mount I/O reaches the PV backing store."""
    verify_pxeboot(host, "powervault_bind_io", check_powervault_bind_io)


@pytest.mark.sanity
@pytest.mark.order(329)
@pytest.mark.powervault_binds
def test_powervault_slurm_mandatory_bind_mounts(host):
    """Verify /var/lib/mysql and /var/spool/slurm configured as bind targets."""
    verify_pxeboot(
        host,
        "powervault_slurm_mandatory_bind_mounts",
        check_powervault_slurm_mandatory_bind_mounts,
    )


@pytest.mark.sanity
@pytest.mark.order(330)
@pytest.mark.powervault_binds
def test_powervault_mysql_data_on_mount(host):
    """Verify MySQL/MariaDB datadir is on a PowerVault mount."""
    verify_pxeboot(host, "powervault_mysql_data_on_mount", check_powervault_mysql_data_on_mount)
