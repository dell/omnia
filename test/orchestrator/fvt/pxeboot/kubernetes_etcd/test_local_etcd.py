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

"""Kubernetes local-etcd mount and disk safety contracts."""

import pytest
from library.functions import (
    check_kubernetes_local_etcd,
    check_kubernetes_local_etcd_integrity,
)

from fvt.result import verify_pxeboot


@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(214)
def test_kubernetes_local_etcd(host):
    """Verify each control plane has the configured etcd mount."""
    verify_pxeboot(host, "kubernetes_local_etcd", check_kubernetes_local_etcd)


@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(215)
def test_kubernetes_local_etcd_integrity(host):
    """Verify disk selection, ext4 label, UUID fstab, and boot persistence."""
    verify_pxeboot(
        host,
        "kubernetes_local_etcd_integrity",
        check_kubernetes_local_etcd_integrity,
    )
