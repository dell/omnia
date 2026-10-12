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
    TestLogger,
    check_kubernetes_control_plane,
    check_kubernetes_node_services,
    check_kubernetes_nodes,
    check_kubernetes_system_pods,
    check_kubernetes_virtual_ip,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(40801)
def test_kubernetes_nodes(host):
    """Verify mapped Kubernetes membership and Ready state."""
    tc = TC["kubernetes_nodes"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_nodes)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(40802)
def test_kubernetes_node_services(host):
    """Verify required services on every Kubernetes role."""
    tc = TC["kubernetes_services"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_node_services)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(40805)
def test_kubernetes_control_plane(host):
    """Verify API readiness and the configured control plane."""
    tc = TC["kubernetes_control_plane"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_control_plane)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(40806)
def test_kubernetes_system_pods(host):
    """Verify required system, CNI, storage, and HA workloads."""
    tc = TC["kubernetes_system_pods"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_system_pods)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(40807)
def test_kubernetes_virtual_ip(host):
    """Verify exactly one owner for the configured Kubernetes VIP."""
    tc = TC["kubernetes_virtual_ip"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_virtual_ip)
