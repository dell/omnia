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
Orchestrator Validate — Kubernetes Node Validation.

TC_K8_002: Verify Kubernetes nodes are in Ready state
TC_K8_003: Verify Kubernetes control plane nodes are Ready
TC_K8_004: Verify Kubernetes worker nodes are Ready
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_k8s_nodes_ready,
    check_k8s_control_plane_nodes,
    check_k8s_worker_nodes,
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
@pytest.mark.buildstream
@pytest.mark.order(1)
def test_k8s_nodes_ready(host):
    """TC_K8_002: Verify Kubernetes nodes are in Ready state."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_nodes_ready"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kubernetes node readiness")
    result = check_k8s_nodes_ready(host)

    if result["success"]:
        tl.passed(LOG["k8s_nodes_ready_ok"], result["details"])
    else:
        tl.failed(LOG["k8s_nodes_ready_failed"], result["error"])

    assert result["success"], ASSERT["k8s_nodes_not_ready"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(2)
def test_k8s_control_plane_nodes(host):
    """TC_K8_003: Verify Kubernetes control plane nodes are Ready."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_control_plane_nodes"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kubernetes control plane node readiness")
    result = check_k8s_control_plane_nodes(host)

    if result["success"]:
        tl.passed(LOG["k8s_cp_nodes_ok"], result["details"])
    else:
        tl.failed(LOG["k8s_cp_nodes_failed"], result["error"])

    assert result["success"], ASSERT["k8s_control_plane_nodes_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(3)
def test_k8s_worker_nodes(host):
    """TC_K8_004: Verify Kubernetes worker nodes are Ready."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_worker_nodes"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kubernetes worker node readiness")
    result = check_k8s_worker_nodes(host)

    if result["success"]:
        tl.passed(LOG["k8s_worker_nodes_ok"], result["details"])
    else:
        tl.failed(LOG["k8s_worker_nodes_failed"], result["error"])

    assert result["success"], ASSERT["k8s_worker_nodes_failed"]

