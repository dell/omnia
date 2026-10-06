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

"""PowerVault partition, filesystem, and mount validation tests."""

import pytest

from fvt.result import verify_pxeboot
from library.functions import (
    check_powervault_gpt_partition,
    check_powervault_filesystem_type,
    check_powervault_mount_point_directory,
    check_powervault_volume_mounted,
    check_powervault_mount_options,
    check_powervault_fstab_entry,
    check_powervault_io_write_read,
)


@pytest.mark.sanity
@pytest.mark.order(310)
@pytest.mark.powervault_mounts
def test_powervault_gpt_partition(host):
    """Verify GPT partition exists on multipath device."""
    verify_pxeboot(host, "powervault_gpt_partition", check_powervault_gpt_partition)


@pytest.mark.sanity
@pytest.mark.order(311)
@pytest.mark.powervault_mounts
def test_powervault_filesystem_type(host):
    """Verify filesystem formatted with correct type."""
    verify_pxeboot(host, "powervault_filesystem_type", check_powervault_filesystem_type)


@pytest.mark.sanity
@pytest.mark.order(312)
@pytest.mark.powervault_mounts
def test_powervault_mount_point_directory(host):
    """Verify mount point directory exists on all target nodes."""
    verify_pxeboot(host, "powervault_mount_point_directory", check_powervault_mount_point_directory)


@pytest.mark.sanity
@pytest.mark.order(313)
@pytest.mark.powervault_mounts
def test_powervault_volume_mounted(host):
    """Verify PowerVault volume is actively mounted on all target nodes."""
    verify_pxeboot(host, "powervault_volume_mounted", check_powervault_volume_mounted)


@pytest.mark.sanity
@pytest.mark.order(314)
@pytest.mark.powervault_mounts
def test_powervault_mount_options(host):
    """Verify mount options applied correctly on all target nodes."""
    verify_pxeboot(host, "powervault_mount_options", check_powervault_mount_options)


@pytest.mark.sanity
@pytest.mark.order(315)
@pytest.mark.powervault_mounts
def test_powervault_fstab_entry(host):
    """Verify persistent fstab entry created on all target nodes."""
    verify_pxeboot(host, "powervault_fstab_entry", check_powervault_fstab_entry)


@pytest.mark.sanity
@pytest.mark.order(327)
@pytest.mark.powervault_mounts
def test_powervault_io_write_read(host):
    """Verify write-read I/O succeeds on every PV mount point."""
    verify_pxeboot(host, "powervault_io_write_read", check_powervault_io_write_read)
