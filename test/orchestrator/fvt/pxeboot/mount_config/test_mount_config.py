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

pytestmark = [pytest.mark.sanity, pytest.mark.mount_config]


@pytest.mark.order(500)
def test_mount_config_mount_point(host):
    """Verify NFS mount point directories exist on all target nodes."""
    verify_pxeboot(host, "mount_config_mount_point", check_mount_config_mount_point)


@pytest.mark.order(501)
def test_mount_config_volume_mounted(host):
    """Verify NFS volumes are actively mounted on all target nodes."""
    verify_pxeboot(
        host, "mount_config_volume_mounted", check_mount_config_volume_mounted
    )


@pytest.mark.order(502)
def test_mount_config_mount_options(host):
    """Verify NFS mount options match storage_config.yml on target nodes."""
    verify_pxeboot(
        host, "mount_config_mount_options", check_mount_config_mount_options
    )


@pytest.mark.order(503)
def test_mount_config_fstab(host):
    """Verify NFS fstab entries are persistent on all target nodes."""
    verify_pxeboot(host, "mount_config_fstab", check_mount_config_fstab)


@pytest.mark.order(504)
def test_mount_config_bind_mounts(host):
    """Verify NFS bind mount targets are active on all target nodes."""
    verify_pxeboot(host, "mount_config_bind_mounts", check_mount_config_bind_mounts)


@pytest.mark.order(505)
def test_mount_config_bind_fstab(host):
    """Verify NFS bind mount fstab entries are persistent on target nodes."""
    verify_pxeboot(host, "mount_config_bind_fstab", check_mount_config_bind_fstab)


@pytest.mark.order(506)
def test_mount_config_node_subdirectory(host):
    """Verify per-node subdirectory exists under NFS mount point."""
    verify_pxeboot(
        host,
        "mount_config_node_subdirectory",
        check_mount_config_node_subdirectory,
    )


@pytest.mark.order(507)
def test_mount_config_permissions(host):
    """Verify NFS mount permissions match storage_config.yml on nodes."""
    verify_pxeboot(host, "mount_config_permissions", check_mount_config_permissions)


@pytest.mark.order(508)
def test_mount_config_fg_targeting(host):
    """Verify NFS mounts are present on target FGs and absent on others."""
    verify_pxeboot(host, "mount_config_fg_targeting", check_mount_config_fg_targeting)


@pytest.mark.order(509)
def test_mount_config_no_duplicate_fstab(host):
    """Verify no duplicate NFS fstab entries on target nodes."""
    verify_pxeboot(
        host,
        "mount_config_no_duplicate_fstab",
        check_mount_config_no_duplicate_fstab,
    )


@pytest.mark.order(510)
def test_mount_config_writable(host):
    """Verify all configured NFS mounts are writable on target nodes."""
    verify_pxeboot(host, "mount_config_writable", check_mount_config_writable)


@pytest.mark.order(511)
def test_mount_config_oim_mount(host):
    """Verify NFS storage is mounted on the OIM when mount_on_oim is true."""
    verify_pxeboot(host, "mount_config_oim_mount", check_mount_config_oim_mount)
