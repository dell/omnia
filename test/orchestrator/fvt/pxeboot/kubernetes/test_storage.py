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
    check_kubernetes_csi_dynamic_provisioning,
    check_kubernetes_default_storage_class,
    check_kubernetes_nfs_dynamic_provisioning,
    check_kubernetes_snapshot_controller,
    check_kubernetes_storage,
    check_kubernetes_workload_scheduling,
)

from fvt.result import verify_pxeboot


@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(213)
def test_kubernetes_storage(host):
    """Verify configured NFS and PowerScale storage objects."""
    verify_pxeboot(host, "kubernetes_storage", check_kubernetes_storage)


@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(214)
def test_kubernetes_default_storage_class(host):
    """Verify exactly one expected default StorageClass."""
    verify_pxeboot(
        host, "kubernetes_default_storage", check_kubernetes_default_storage_class
    )


@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(215)
def test_kubernetes_snapshot_controller(host):
    """Verify PowerScale snapshot components when configured."""
    verify_pxeboot(
        host, "kubernetes_snapshot_controller", check_kubernetes_snapshot_controller
    )


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(218)
def test_kubernetes_workload_scheduling(host):
    """Create, verify, and remove an isolated scheduling probe."""
    verify_pxeboot(host, "kubernetes_workload", check_kubernetes_workload_scheduling)


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(219)
def test_kubernetes_nfs_dynamic_provisioning(host):
    """Create and remove an isolated NFS-backed workload."""
    verify_pxeboot(
        host, "kubernetes_nfs_dynamic", check_kubernetes_nfs_dynamic_provisioning
    )


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(220)
def test_kubernetes_csi_dynamic_provisioning(host):
    """Create and remove an isolated PowerScale-backed workload."""
    verify_pxeboot(
        host, "kubernetes_csi_dynamic", check_kubernetes_csi_dynamic_provisioning
    )
