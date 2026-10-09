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
    TestLogger,
    check_powervault_gpt_partition,
    check_powervault_filesystem_type,
    check_powervault_mount_point_directory,
    check_powervault_volume_mounted,
    check_powervault_mount_options,
    check_powervault_fstab_entry,
    check_powervault_io_write_read,
)
from library.vars import TEST_CASES as TC


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40610)
@pytest.mark.powervault_mounts
def test_powervault_gpt_partition(host):
    """Verify GPT partition exists on multipath device."""
    tc = TC["powervault_gpt_partition"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_gpt_partition)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40611)
@pytest.mark.powervault_mounts
def test_powervault_filesystem_type(host):
    """Verify filesystem formatted with correct type."""
    tc = TC["powervault_filesystem_type"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_filesystem_type)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40612)
@pytest.mark.powervault_mounts
def test_powervault_mount_point_directory(host):
    """Verify mount point directory exists on all target nodes."""
    tc = TC["powervault_mount_point_directory"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_mount_point_directory)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40613)
@pytest.mark.powervault_mounts
def test_powervault_volume_mounted(host):
    """Verify PowerVault volume is actively mounted on all target nodes."""
    tc = TC["powervault_volume_mounted"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_volume_mounted)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40614)
@pytest.mark.powervault_mounts
def test_powervault_mount_options(host):
    """Verify mount options applied correctly on all target nodes."""
    tc = TC["powervault_mount_options"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_mount_options)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40615)
@pytest.mark.powervault_mounts
def test_powervault_fstab_entry(host):
    """Verify persistent fstab entry created on all target nodes."""
    tc = TC["powervault_fstab_entry"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_fstab_entry)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40627)
@pytest.mark.powervault_mounts
def test_powervault_io_write_read(host):
    """Verify write-read I/O succeeds on every PV mount point."""
    tc = TC["powervault_io_write_read"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_io_write_read)
