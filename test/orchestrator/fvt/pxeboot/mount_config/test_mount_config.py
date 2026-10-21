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

"""NFS mount_config functional verification tests.

Validates that NFS mounts defined in storage_config.yml → mounts: are
correctly applied on provisioned nodes after PXE boot: mount point
directory, active mount, mount options, fstab persistence, bind mounts,
per-node subdirectory, permissions, functional-group targeting, fstab
uniqueness, writability, and OIM-side mount.
"""

import pytest

from fvt.result import verify_pxeboot
from library.functions import (
    TestLogger,
    check_mount_config_bind_fstab,
    check_mount_config_bind_mounts,
    check_mount_config_fg_targeting,
    check_mount_config_fstab,
    check_mount_config_mount_options,
    check_mount_config_mount_point,
    check_mount_config_no_duplicate_fstab,
    check_mount_config_node_subdirectory,
    check_mount_config_oim_mount,
    check_mount_config_permissions,
    check_mount_config_volume_mounted,
    check_mount_config_writable,
)
from library.vars import TEST_CASES as TC

@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40401)
def test_mount_config_mount_point(host):
    """Verify NFS mount point directories exist on all target nodes."""
    tc = TC["mount_config_mount_point"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_mount_point)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40402)
def test_mount_config_volume_mounted(host):
    """Verify NFS volumes are actively mounted on all target nodes."""
    tc = TC["mount_config_volume_mounted"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_volume_mounted)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40403)
def test_mount_config_mount_options(host):
    """Verify NFS mount options match storage_config.yml on target nodes."""
    tc = TC["mount_config_mount_options"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_mount_options)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40404)
def test_mount_config_fstab(host):
    """Verify NFS fstab entries are persistent on all target nodes."""
    tc = TC["mount_config_fstab"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_fstab)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40405)
def test_mount_config_bind_mounts(host):
    """Verify NFS bind mount targets are active on all target nodes."""
    tc = TC["mount_config_bind_mounts"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_bind_mounts)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40406)
def test_mount_config_bind_fstab(host):
    """Verify NFS bind mount fstab entries are persistent on target nodes."""
    tc = TC["mount_config_bind_fstab"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_bind_fstab)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40407)
def test_mount_config_node_subdirectory(host):
    """Verify per-node subdirectory exists under NFS mount point."""
    tc = TC["mount_config_node_subdirectory"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_node_subdirectory)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40408)
def test_mount_config_permissions(host):
    """Verify NFS mount permissions match storage_config.yml on nodes."""
    tc = TC["mount_config_permissions"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_permissions)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40409)
def test_mount_config_fg_targeting(host):
    """Verify NFS mounts are present on target FGs and absent on others."""
    tc = TC["mount_config_fg_targeting"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_fg_targeting)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40410)
def test_mount_config_no_duplicate_fstab(host):
    """Verify no duplicate NFS fstab entries on target nodes."""
    tc = TC["mount_config_no_duplicate_fstab"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_no_duplicate_fstab)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40411)
def test_mount_config_writable(host):
    """Verify all configured NFS mounts are writable on target nodes."""
    tc = TC["mount_config_writable"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_writable)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.mount_config
@pytest.mark.order(40412)
def test_mount_config_oim_mount(host):
    """Verify NFS storage is mounted on the OIM when mount_on_oim is true."""
    tc = TC["mount_config_oim_mount"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_mount_config_oim_mount)
