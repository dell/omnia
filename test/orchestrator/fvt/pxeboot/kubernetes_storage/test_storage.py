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

"""Kubernetes storage inventory and opt-in provisioning behavior."""

import pytest
from library.functions import (
    TestLogger,
    check_kubernetes_csi_dynamic_provisioning,
    check_kubernetes_default_storage_class,
    check_kubernetes_nfs_dynamic_provisioning,
    check_kubernetes_snapshot_controller,
    check_kubernetes_storage,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(41001)
def test_kubernetes_storage(host):
    """Verify configured NFS and PowerScale storage objects."""
    tc = TC["kubernetes_storage"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_storage)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(41002)
def test_kubernetes_default_storage_class(host):
    """Verify exactly one expected default StorageClass."""
    tc = TC["kubernetes_default_storage"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_default_storage_class)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(41003)
def test_kubernetes_snapshot_controller(host):
    """Verify PowerScale snapshot components when configured."""
    tc = TC["kubernetes_snapshot_controller"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_snapshot_controller)


@pytest.mark.functional
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(41004)
def test_kubernetes_nfs_dynamic_provisioning(host):
    """Create and remove an isolated NFS-backed workload."""
    tc = TC["kubernetes_nfs_dynamic"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_nfs_dynamic_provisioning)


@pytest.mark.functional
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(41005)
def test_kubernetes_csi_dynamic_provisioning(host):
    """Create and remove an isolated PowerScale-backed workload."""
    tc = TC["kubernetes_csi_dynamic"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_csi_dynamic_provisioning)
