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

"""PowerVault cloud-init and misc validation tests."""

import pytest

from fvt.result import verify_pxeboot
from library.functions import (
    check_powervault_setup_log,
    check_powervault_cloud_init_groups_dict,
    check_powervault_no_duplicate_fstab,
    check_powervault_all_mounts_writable,
    check_powervault_permissions,
)


@pytest.mark.sanity
@pytest.mark.order(322)
@pytest.mark.powervault_cloudinit
def test_powervault_setup_log(host):
    """Verify cloud-init runcmd log exists and shows completion."""
    verify_pxeboot(host, "powervault_setup_log", check_powervault_setup_log)


@pytest.mark.sanity
@pytest.mark.order(323)
@pytest.mark.powervault_cloudinit
def test_powervault_cloud_init_groups_dict(host):
    """Verify rendered iSCSI setup scripts deployed on target nodes."""
    verify_pxeboot(host, "powervault_cloud_init_groups_dict", check_powervault_cloud_init_groups_dict)


@pytest.mark.sanity
@pytest.mark.order(324)
@pytest.mark.powervault_cloudinit
def test_powervault_no_duplicate_fstab(host):
    """Verify no duplicate fstab entries on all target nodes."""
    verify_pxeboot(host, "powervault_no_duplicate_fstab", check_powervault_no_duplicate_fstab)


@pytest.mark.sanity
@pytest.mark.order(325)
@pytest.mark.powervault_cloudinit
def test_powervault_all_mounts_writable(host):
    """Verify all PV mounts (main + bind) are writable."""
    verify_pxeboot(host, "powervault_all_mounts_writable", check_powervault_all_mounts_writable)


@pytest.mark.sanity
@pytest.mark.order(326)
@pytest.mark.powervault_cloudinit
def test_powervault_permissions(host):
    """Verify permissions on mount point match config."""
    verify_pxeboot(host, "powervault_permissions", check_powervault_permissions)
