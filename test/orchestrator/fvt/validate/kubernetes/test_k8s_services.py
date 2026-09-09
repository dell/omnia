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
Orchestrator Validate — Kubernetes Services & Versions.

TC_K8_031: Verify CRI-O service is running on all nodes
TC_K8_032: Verify chronyd service is active on control plane nodes
TC_K8_033: Verify kubectl version matches software config
TC_K8_034: Verify kubeadm version matches CRI-O version
TC_K8_035: Verify all nodes use expected container runtime
TC_K8_036: Verify K8s component status (controller, scheduler, etcd)
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_crio_running,
    check_chronyd_running,
    check_kubectl_version,
    check_kubeadm_crio_version_match,
    check_container_runtime,
    check_k8s_component_status,
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
def test_k8s_crio_running(host):
    """TC_K8_031: Verify CRI-O service is running on all nodes."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_crio_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking CRI-O service status on all nodes")
    result = check_crio_running(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["crio_check_ok"], result["details"])
    else:
        tl.failed(LOG["crio_check_failed"].format(nodes=result.get("failed_nodes", [])), result["error"])

    assert result["success"], ASSERT["crio_not_running"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(2)
def test_k8s_chronyd_running(host):
    """TC_K8_032: Verify chronyd service is active on control plane nodes."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_chronyd_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking chronyd service on control plane nodes")
    result = check_chronyd_running(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["chronyd_check_ok"], result["details"])
    else:
        tl.failed(LOG["chronyd_check_failed"].format(nodes=result.get("failed_nodes", [])), result["error"])

    assert result["success"], ASSERT["chronyd_not_running"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(3)
def test_k8s_kubectl_version(host):
    """TC_K8_033: Verify kubectl version matches software config."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_kubectl_version"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking kubectl version against software_config.json")
    result = check_kubectl_version(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["kubectl_version_ok"].format(version=result.get("expected_version", "")),
            result["details"],
        )
    else:
        tl.failed(LOG["kubectl_version_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["kubectl_version_mismatch"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(4)
def test_k8s_kubeadm_crio_version_match(host):
    """TC_K8_034: Verify kubeadm version matches CRI-O version."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_kubeadm_crio_version_match"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking kubeadm vs CRI-O version on control planes")
    result = check_kubeadm_crio_version_match(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["kubeadm_crio_match_ok"], result["details"])
    else:
        tl.failed(LOG["kubeadm_crio_match_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["kubeadm_crio_mismatch"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(5)
def test_k8s_container_runtime(host):
    """TC_K8_035: Verify all nodes use expected container runtime."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_container_runtime"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying container runtime on all nodes")
    result = check_container_runtime(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["container_runtime_ok"].format(runtime=result["details"]), result["details"])
    else:
        tl.failed(LOG["container_runtime_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["container_runtime_mismatch"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(6)
def test_k8s_component_status(host):
    """TC_K8_036: Verify K8s component status (controller, scheduler, etcd)."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_component_status"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking K8s component status")
    result = check_k8s_component_status(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["component_status_ok"], result["details"])
    else:
        tl.failed(
            LOG["component_status_failed"].format(
                components=result.get("unhealthy_components", [])
            ),
            result["error"],
        )

    assert result["success"], ASSERT["component_status_failed"]
