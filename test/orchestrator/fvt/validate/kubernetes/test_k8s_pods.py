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

"""
Orchestrator Validate — Kubernetes Pod Validation.

TC_K8_007: Verify kube-system pods are Running
TC_K8_012: Verify etcd cluster is healthy
TC_K8_013: Verify CoreDNS pods are Running
TC_K8_014: Verify kube-proxy pods are Running
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_k8s_system_pods,
    check_k8s_etcd_healthy,
    check_k8s_coredns_running,
    check_k8s_kube_proxy_running,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.k8s_vars import TEST_CASES as TC


def _skip_if_k8s_disabled(host):
    """Skip test if Kubernetes is not enabled in catalog."""
    result = check_k8s_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(1)
def test_k8s_system_pods(host):
    """TC_K8_007: Verify kube-system pods are Running."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_system_pods_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking kube-system pod status")
    result = check_k8s_system_pods(host)

    if result["success"]:
        tl.passed(LOG["system_pods_ok"], result["details"])
    else:
        tl.failed(LOG["system_pods_failed"], result["error"])

    assert result["success"], ASSERT["system_pods_not_running"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(2)
def test_k8s_etcd_healthy(host):
    """TC_K8_012: Verify etcd cluster is healthy."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_etcd_healthy"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking etcd cluster health")
    result = check_k8s_etcd_healthy(host)

    if result["success"]:
        tl.passed(LOG["etcd_ok"], result["details"])
    else:
        tl.failed(LOG["etcd_failed"], result["error"])

    assert result["success"], ASSERT["etcd_not_healthy"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(3)
def test_k8s_coredns_running(host):
    """TC_K8_013: Verify CoreDNS pods are Running."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_coredns_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking CoreDNS pod status")
    result = check_k8s_coredns_running(host)

    if result["success"]:
        tl.passed(LOG["coredns_ok"], result["details"])
    else:
        tl.failed(LOG["coredns_failed"], result["error"])

    assert result["success"], ASSERT["k8s_coredns_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(4)
def test_k8s_kube_proxy_running(host):
    """TC_K8_014: Verify kube-proxy pods are Running."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_kube_proxy_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking kube-proxy pod status")
    result = check_k8s_kube_proxy_running(host)

    if result["success"]:
        tl.passed(LOG["kube_proxy_ok"], result["details"])
    else:
        tl.failed(LOG["kube_proxy_failed"], result["error"])

    assert result["success"], ASSERT["k8s_kube_proxy_failed"]
