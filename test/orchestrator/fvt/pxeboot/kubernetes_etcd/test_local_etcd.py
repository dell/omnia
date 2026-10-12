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

"""Kubernetes local-etcd mount, provisioning, and disk-media contracts."""

import pytest
from library.functions import (
    TestLogger,
    check_kubernetes_local_etcd,
    check_kubernetes_local_etcd_integrity,
    check_kubernetes_local_etcd_media,
    check_kubernetes_local_etcd_provisioning,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(40903)
def test_kubernetes_local_etcd(host):
    """Verify each control plane has the configured etcd mount."""
    tc = TC["kubernetes_local_etcd"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_local_etcd)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(40904)
def test_kubernetes_local_etcd_integrity(host):
    """Verify disk selection, ext4 label, UUID fstab, and boot persistence."""
    tc = TC["kubernetes_local_etcd_integrity"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_local_etcd_integrity)


@pytest.mark.kubernetes
@pytest.mark.order(40905)
def test_kubernetes_local_etcd_provisioning(host):
    """Verify GPT selection and local-etcd scripts, logs, and selected disk."""
    tc = TC["kubernetes_local_etcd_provisioning"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_local_etcd_provisioning)


@pytest.mark.kubernetes
@pytest.mark.order(40906)
def test_kubernetes_local_etcd_media(host):
    """Verify every control plane places etcd on the configured disk media."""
    tc = TC["kubernetes_local_etcd_media"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_local_etcd_media)
