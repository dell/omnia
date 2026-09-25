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

"""Read-only Kubernetes membership, runtime, control-plane, and HA checks."""

import pytest
from library.functions import (
    check_kubernetes_control_plane,
    check_kubernetes_node_services,
    check_kubernetes_nodes,
    check_kubernetes_system_pods,
    check_kubernetes_version_compatibility,
    check_kubernetes_virtual_ip,
)

from fvt.result import verify_pxeboot

pytestmark = [pytest.mark.sanity, pytest.mark.kubernetes]


@pytest.mark.order(205)
def test_kubernetes_nodes(host):
    """Verify mapped Kubernetes membership and Ready state."""
    verify_pxeboot(host, "kubernetes_nodes", check_kubernetes_nodes)


@pytest.mark.order(206)
def test_kubernetes_node_services(host):
    """Verify required services on every Kubernetes role."""
    verify_pxeboot(host, "kubernetes_services", check_kubernetes_node_services)


@pytest.mark.order(207)
def test_kubernetes_version_compatibility(host):
    """Verify Kubernetes, kubeadm, and CRI-O version alignment."""
    verify_pxeboot(host, "kubernetes_versions", check_kubernetes_version_compatibility)


@pytest.mark.order(208)
def test_kubernetes_control_plane(host):
    """Verify API readiness and the configured control plane."""
    verify_pxeboot(host, "kubernetes_control_plane", check_kubernetes_control_plane)


@pytest.mark.order(209)
def test_kubernetes_system_pods(host):
    """Verify required system, CNI, storage, and HA workloads."""
    verify_pxeboot(host, "kubernetes_system_pods", check_kubernetes_system_pods)


@pytest.mark.order(210)
def test_kubernetes_virtual_ip(host):
    """Verify exactly one owner for the configured Kubernetes VIP."""
    verify_pxeboot(host, "kubernetes_virtual_ip", check_kubernetes_virtual_ip)
