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
Orchestrator Kubernetes — Verification Tests.

Kubernetes tests for orchestrator test automation.
Tests cover node readiness, service checks, pod verification,
control plane components, workload tests, and integration.

TC_K8_001: Verify Kubernetes is enabled in catalog
TC_K8_022: Verify node labels match functional group roles
TC_K8_023: Verify control plane nodes have correct taints
TC_K8_027: Verify kube-apiserver static pod is running
TC_K8_028: Verify kube-controller-manager static pod is running
TC_K8_029: Verify kube-scheduler static pod is running
TC_K8_030: Verify kubectl cluster-info returns valid data
TC_K8_019: Verify pod creation and scheduling works
TC_K8_020: Verify DNS resolution works inside pods
TC_K8_021: Verify Kubernetes service creation works
TC_K8_026: Verify OpenLDAP integration with Kubernetes
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_k8s_node_labels,
    check_k8s_node_taints,
    check_k8s_static_pod,
    check_k8s_cluster_info,
    check_k8s_pod_create,
    check_k8s_dns_resolution,
    check_k8s_service_create,
    check_k8s_ldap_integration,
)
from library.vars.k8s_vars import TEST_CASES
from library.messages import (
    K8S_TEST_LOG_MSGS,
    K8S_TEST_ASSERT_MSGS,
)

LOG = K8S_TEST_LOG_MSGS
ASSERT = K8S_TEST_ASSERT_MSGS


def skip_if_k8s_disabled(host):
    """Helper to skip test if Kubernetes is not enabled."""
    result = check_k8s_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])
    return result


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(1)
def test_k8s_enabled(host):
    """TC_K8_001: Verify Kubernetes is enabled in catalog."""
    tl = TestLogger(
        TEST_CASES["k8s_enabled"]["title"],
        TEST_CASES["k8s_enabled"]["id"]
    )

    result = check_k8s_enabled(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["k8s_enabled_ok"], result["details"])
    else:
        tl.failed(LOG["k8s_enabled_failed"], result["error"])

    assert result["success"], ASSERT["k8s_enabled_required"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(2)
def test_k8s_node_labels(host):
    """TC_K8_022: Verify node labels match functional group roles."""
    skip_if_k8s_disabled(host)

    tl = TestLogger(
        TEST_CASES["k8s_node_labels"]["title"],
        TEST_CASES["k8s_node_labels"]["id"]
    )

    result = check_k8s_node_labels(host)

    if result.get("skipped"):
        tl.passed("No labeled nodes found - skipping", result["details"])
        pytest.skip("No Kubernetes labeled nodes available")

    if result["success"]:
        tl.passed(LOG["node_labels_ok"], result["details"])
    else:
        tl.failed(LOG["node_labels_failed"], result["error"])

    assert result["success"], ASSERT["node_labels_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(3)
def test_k8s_node_taints(host):
    """TC_K8_023: Verify control plane nodes have correct taints."""
    skip_if_k8s_disabled(host)

    tl = TestLogger(
        TEST_CASES["k8s_node_taints"]["title"],
        TEST_CASES["k8s_node_taints"]["id"]
    )

    result = check_k8s_node_taints(host)

    if result.get("skipped"):
        tl.passed("No control plane nodes found - skipping", result["details"])
        pytest.skip("No Kubernetes control plane nodes available")

    if result["success"]:
        tl.passed(LOG["node_taints_ok"], result["details"])
    else:
        tl.failed(LOG["node_taints_failed"], result["error"])

    assert result["success"], ASSERT["node_taints_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(4)
def test_k8s_apiserver_pod(host):
    """TC_K8_027: Verify kube-apiserver static pod is running."""
    skip_if_k8s_disabled(host)

    tl = TestLogger(
        TEST_CASES["k8s_apiserver_pod"]["title"],
        TEST_CASES["k8s_apiserver_pod"]["id"]
    )

    result = check_k8s_static_pod(host, "kube-apiserver")

    if result.get("skipped"):
        tl.passed("No control plane nodes found - skipping", result["details"])
        pytest.skip("No control plane nodes available for static pod check")

    if result["success"]:
        tl.passed(
            LOG["static_pod_ok"].format(component="kube-apiserver"),
            result["details"]
        )
    else:
        tl.failed(
            LOG["static_pod_failed"].format(component="kube-apiserver"),
            result["error"]
        )

    assert result["success"], ASSERT["static_pod_failed"].format(
        component="kube-apiserver"
    )


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(5)
def test_k8s_controller_manager_pod(host):
    """TC_K8_028: Verify kube-controller-manager static pod is running."""
    skip_if_k8s_disabled(host)

    tl = TestLogger(
        TEST_CASES["k8s_controller_manager_pod"]["title"],
        TEST_CASES["k8s_controller_manager_pod"]["id"]
    )

    result = check_k8s_static_pod(host, "kube-controller-manager")

    if result.get("skipped"):
        tl.passed("No control plane nodes found - skipping", result["details"])
        pytest.skip("No control plane nodes available for static pod check")

    if result["success"]:
        tl.passed(
            LOG["static_pod_ok"].format(component="kube-controller-manager"),
            result["details"]
        )
    else:
        tl.failed(
            LOG["static_pod_failed"].format(component="kube-controller-manager"),
            result["error"]
        )

    assert result["success"], ASSERT["static_pod_failed"].format(
        component="kube-controller-manager"
    )


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(6)
def test_k8s_scheduler_pod(host):
    """TC_K8_029: Verify kube-scheduler static pod is running."""
    skip_if_k8s_disabled(host)

    tl = TestLogger(
        TEST_CASES["k8s_scheduler_pod"]["title"],
        TEST_CASES["k8s_scheduler_pod"]["id"]
    )

    result = check_k8s_static_pod(host, "kube-scheduler")

    if result.get("skipped"):
        tl.passed("No control plane nodes found - skipping", result["details"])
        pytest.skip("No control plane nodes available for static pod check")

    if result["success"]:
        tl.passed(
            LOG["static_pod_ok"].format(component="kube-scheduler"),
            result["details"]
        )
    else:
        tl.failed(
            LOG["static_pod_failed"].format(component="kube-scheduler"),
            result["error"]
        )

    assert result["success"], ASSERT["static_pod_failed"].format(
        component="kube-scheduler"
    )


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(7)
def test_k8s_cluster_info(host):
    """TC_K8_030: Verify kubectl cluster-info returns valid data."""
    skip_if_k8s_disabled(host)

    tl = TestLogger(
        TEST_CASES["k8s_cluster_info"]["title"],
        TEST_CASES["k8s_cluster_info"]["id"]
    )

    result = check_k8s_cluster_info(host)

    if result.get("skipped"):
        tl.passed("Cluster info unavailable - skipping", result["details"])
        pytest.skip("Kubernetes cluster info not available")

    if result["success"]:
        tl.passed(LOG["cluster_info_ok"], result["details"])
    else:
        tl.failed(LOG["cluster_info_failed"], result["error"])

    assert result["success"], ASSERT["cluster_info_failed"]


@pytest.mark.kubernetes
@pytest.mark.functional
@pytest.mark.order(8)
def test_k8s_pod_create(host):
    """TC_K8_019: Verify pod creation and scheduling works."""
    skip_if_k8s_disabled(host)

    tl = TestLogger(
        TEST_CASES["k8s_pod_create"]["title"],
        TEST_CASES["k8s_pod_create"]["id"]
    )

    result = check_k8s_pod_create(host)

    if result.get("skipped"):
        tl.passed("Pod creation skipped", result["details"])
        pytest.skip("Pod creation test not available")

    if result["success"]:
        tl.passed(LOG["pod_create_ok"], result["details"])
    else:
        tl.failed(LOG["pod_create_failed"], result["error"])

    assert result["success"], ASSERT["pod_create_failed"].format(
        error=result.get("error", "Unknown error")
    )


@pytest.mark.kubernetes
@pytest.mark.functional
@pytest.mark.order(9)
def test_k8s_dns_resolution(host):
    """TC_K8_020: Verify DNS resolution works inside pods."""
    skip_if_k8s_disabled(host)

    tl = TestLogger(
        TEST_CASES["k8s_pod_dns_resolution"]["title"],
        TEST_CASES["k8s_pod_dns_resolution"]["id"]
    )

    result = check_k8s_dns_resolution(host)

    if result.get("skipped"):
        tl.passed("DNS resolution skipped", result["details"])
        pytest.skip("DNS resolution test not available")

    if result["success"]:
        tl.passed(LOG["dns_resolution_ok"], result["details"])
    else:
        tl.failed(LOG["dns_resolution_failed"], result["error"])

    assert result["success"], ASSERT["dns_resolution_failed"].format(
        error=result.get("error", "Unknown error")
    )


@pytest.mark.kubernetes
@pytest.mark.functional
@pytest.mark.order(10)
def test_k8s_service_create(host):
    """TC_K8_021: Verify Kubernetes service creation works."""
    skip_if_k8s_disabled(host)

    tl = TestLogger(
        TEST_CASES["k8s_service_create"]["title"],
        TEST_CASES["k8s_service_create"]["id"]
    )

    result = check_k8s_service_create(host)

    if result.get("skipped"):
        tl.passed("Service creation skipped", result["details"])
        pytest.skip("Service creation test not available")

    if result["success"]:
        tl.passed(LOG["service_create_ok"], result["details"])
    else:
        tl.failed(LOG["service_create_failed"], result["error"])

    assert result["success"], ASSERT["service_create_failed"].format(
        error=result.get("error", "Unknown error")
    )


@pytest.mark.kubernetes
@pytest.mark.functional
@pytest.mark.order(11)
def test_k8s_ldap_integration(host):
    """TC_K8_026: Verify OpenLDAP integration with Kubernetes."""
    skip_if_k8s_disabled(host)

    tl = TestLogger(
        TEST_CASES["k8s_ldap_integration"]["title"],
        TEST_CASES["k8s_ldap_integration"]["id"]
    )

    result = check_k8s_ldap_integration(host)

    if result.get("skipped"):
        tl.passed("LDAP not configured - skipping", result["details"])
        pytest.skip("LDAP integration not configured")

    if result["success"]:
        tl.passed(LOG["ldap_ok"], result["details"])
    else:
        tl.failed(LOG["ldap_failed"], result["error"])

    assert result["success"], ASSERT["ldap_failed"].format(
        error=result.get("error", "Unknown error")
    )
