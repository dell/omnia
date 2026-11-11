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

"""Explicitly authorized Kubernetes reboot and recovery contracts."""

import pytest
from library.functions import (
    TestLogger,
    check_kubernetes_control_plane_recovery,
    check_kubernetes_local_etcd_recovery,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.reboot
@pytest.mark.kubernetes
@pytest.mark.order(42201)
def test_kubernetes_local_etcd_recovery(host):
    """Reboot a control plane and prove its local-etcd UUID is preserved."""
    tc = TC["kubernetes_local_etcd_recovery"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_local_etcd_recovery)


@pytest.mark.reboot
@pytest.mark.kubernetes
@pytest.mark.order(42202)
def test_kubernetes_control_plane_recovery(host):
    """Reboot the VIP owner and verify control-plane recovery."""
    tc = TC["kubernetes_recovery"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_control_plane_recovery)
