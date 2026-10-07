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

"""VAST mount point, mount options, fstab, and RDMA I/O tests
(TC-002, TC-004, TC-011, TC-012)."""

import pytest

from fvt.result import verify_pxeboot
from library.functions import (
    check_vast_mount_points,
    check_vast_mount_options,
    check_vast_fstab_entries,
    check_vast_rdma_mount,
)


@pytest.mark.sanity
@pytest.mark.order(701)
@pytest.mark.vast_mounts
def test_vast_mount_points(host):
    """TC-002: Verify /scratch, /home, /apps, /projects directories."""
    verify_pxeboot(host, "vast_mount_points", check_vast_mount_points)


@pytest.mark.sanity
@pytest.mark.order(703)
@pytest.mark.vast_mounts
def test_vast_mount_options(host):
    """TC-004: Verify proto=rdma and port=20049 in /proc/mounts."""
    verify_pxeboot(host, "vast_mount_options", check_vast_mount_options)


@pytest.mark.sanity
@pytest.mark.order(710)
@pytest.mark.vast_mounts
def test_vast_fstab_entries(host):
    """TC-011: Verify /etc/fstab entries with proto=rdma."""
    verify_pxeboot(host, "vast_fstab_entries", check_vast_fstab_entries)


@pytest.mark.sanity
@pytest.mark.order(711)
@pytest.mark.vast_mounts
def test_vast_rdma_mount(host):
    """TC-012: Verify RDMA transport and 1 GB I/O checksum."""
    verify_pxeboot(host, "vast_rdma_mount", check_vast_rdma_mount)
