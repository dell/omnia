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

"""VAST NFS client installation verification tests."""

import pytest

from library.functions import (
    TestLogger,
    check_vast_vastnfs_installation,
    check_vast_vastnfs_rpm_and_module,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.sanity
@pytest.mark.vast_installation
@pytest.mark.order(42101)
def test_vast_vastnfs_installation(host):
    """Verify vastnfs-ctl status on compute nodes."""
    tc = TC["vast_vastnfs_installation"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_vastnfs_installation)


@pytest.mark.sanity
@pytest.mark.vast_installation
@pytest.mark.order(42110)
def test_vast_vastnfs_rpm_and_module(host):
    """Verify vastnfs RPM, kernel module, and service."""
    tc = TC["vast_vastnfs_rpm_and_module"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_vastnfs_rpm_and_module)
