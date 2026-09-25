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

"""Kubernetes etcd endpoint and topology contracts."""

import pytest
from library.functions import (
    check_kubernetes_etcd_health,
    check_kubernetes_etcd_topology,
)

from fvt.result import verify_pxeboot

pytestmark = [pytest.mark.sanity, pytest.mark.kubernetes]


@pytest.mark.order(212)
def test_kubernetes_etcd_health(host):
    """Verify health for all etcd endpoints."""
    verify_pxeboot(host, "kubernetes_etcd_health", check_kubernetes_etcd_health)


@pytest.mark.order(213)
def test_kubernetes_etcd_topology(host):
    """Verify etcd membership, leader election, and raft consistency."""
    verify_pxeboot(host, "kubernetes_etcd_topology", check_kubernetes_etcd_topology)
