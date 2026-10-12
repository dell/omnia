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

"""VAST mount point, mount options, fstab, and RDMA I/O tests."""

import pytest

from library.functions import (
    TestLogger,
    check_vast_fstab_entries,
    check_vast_mount_options,
    check_vast_mount_points,
    check_vast_rdma_mount,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.sanity
@pytest.mark.vast_mounts
@pytest.mark.order(42102)
def test_vast_mount_points(host):
    """Verify /scratch, /home, /apps, /projects directories."""
    tc = TC["vast_mount_points"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_mount_points)


@pytest.mark.sanity
@pytest.mark.vast_mounts
@pytest.mark.order(42104)
def test_vast_mount_options(host):
    """Verify proto=rdma and port=20049 in /proc/mounts."""
    tc = TC["vast_mount_options"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_mount_options)


@pytest.mark.sanity
@pytest.mark.vast_mounts
@pytest.mark.order(42111)
def test_vast_fstab_entries(host):
    """Verify /etc/fstab entries with proto=rdma."""
    tc = TC["vast_fstab_entries"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_fstab_entries)


@pytest.mark.sanity
@pytest.mark.vast_mounts
@pytest.mark.order(42112)
def test_vast_rdma_mount(host):
    """Verify RDMA transport and 1 GB I/O checksum."""
    tc = TC["vast_rdma_mount"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_rdma_mount)
