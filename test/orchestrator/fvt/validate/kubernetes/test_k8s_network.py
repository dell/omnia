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
Orchestrator Validate — Kubernetes Network Pods.

TC_K8_041: Verify kube-vip pods are running
TC_K8_042: Verify Calico network pods are running
TC_K8_043: Verify MetalLB system pods are running
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_k8s_kube_vip_pods,
    check_k8s_calico_pods,
    check_k8s_metallb_pods,
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
def test_k8s_kube_vip_pods(host):
    """TC_K8_041: Verify kube-vip pods are running."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_kube_vip_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking kube-vip pods across all namespaces")
    result = check_k8s_kube_vip_pods(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["kube_vip_pods_ok"], result["details"])
    else:
        tl.failed(LOG["kube_vip_pods_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["kube_vip_pods_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(2)
def test_k8s_calico_pods(host):
    """TC_K8_042: Verify Calico network pods are running."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_calico_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Calico pods across all namespaces")
    result = check_k8s_calico_pods(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["calico_pods_ok"], result["details"])
    else:
        tl.failed(LOG["calico_pods_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["calico_pods_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(3)
def test_k8s_metallb_pods(host):
    """TC_K8_043: Verify MetalLB system pods are running."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_metallb_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking MetalLB pods in metallb-system namespace")
    result = check_k8s_metallb_pods(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["metallb_pods_ok"], result["details"])
    else:
        tl.failed(LOG["metallb_pods_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["metallb_pods_failed"]
