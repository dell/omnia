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
    TestLogger,
    check_powervault_setup_log,
    check_powervault_cloud_init_groups_dict,
    check_powervault_no_duplicate_fstab,
    check_powervault_all_mounts_writable,
    check_powervault_permissions,
)
from library.vars import TEST_CASES as TC


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40622)
@pytest.mark.powervault_cloudinit
def test_powervault_setup_log(host):
    """Verify cloud-init runcmd log exists and shows completion."""
    tc = TC["powervault_setup_log"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_setup_log)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40623)
@pytest.mark.powervault_cloudinit
def test_powervault_cloud_init_groups_dict(host):
    """Verify rendered iSCSI setup scripts deployed on target nodes."""
    tc = TC["powervault_cloud_init_groups_dict"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_cloud_init_groups_dict)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40624)
@pytest.mark.powervault_cloudinit
def test_powervault_no_duplicate_fstab(host):
    """Verify no duplicate fstab entries on all target nodes."""
    tc = TC["powervault_no_duplicate_fstab"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_no_duplicate_fstab)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40625)
@pytest.mark.powervault_cloudinit
def test_powervault_all_mounts_writable(host):
    """Verify all PV mounts (main + bind) are writable."""
    tc = TC["powervault_all_mounts_writable"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_all_mounts_writable)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(40626)
@pytest.mark.powervault_cloudinit
def test_powervault_permissions(host):
    """Verify permissions on mount point match config."""
    tc = TC["powervault_permissions"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_permissions)
