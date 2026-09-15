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
Orchestrator Validate — Kubernetes SSH Connectivity Validation.

TC_K8_016: Passwordless SSH from control plane to worker nodes
TC_K8_017: Passwordless SSH from worker to control plane nodes
TC_K8_018: Passwordless SSH between worker nodes
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_k8s_ssh,
)
from library.messages import (
    K8S_TEST_LOG_MSGS as LOG,
    K8S_TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.k8s_vars import TEST_CASES as TC


def _skip_if_k8s_disabled(host):
    """Skip test if Kubernetes is not enabled in catalog."""
    result = check_k8s_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])


@pytest.mark.kubernetes
@pytest.mark.functional
@pytest.mark.order(1)
def test_ssh_control_plane_to_worker(host):
    """TC_K8_016: Passwordless SSH from control plane to worker nodes."""
    _skip_if_k8s_disabled(host)

    tc = TC["ssh_control_plane_to_worker"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from control plane to worker nodes")
    result = check_k8s_ssh(host, "control_plane", "worker")

    if result["success"]:
        tl.passed(
            LOG["ssh_ok"].format(from_type="control_plane", to_type="worker"),
            result["details"],
        )
    else:
        tl.failed(
            LOG["ssh_failed"].format(
                from_type="control_plane", to_type="worker",
                pairs=result.get("error", ""),
            ),
            result["error"],
        )

    assert result["success"], ASSERT["ssh_failed"]


@pytest.mark.kubernetes
@pytest.mark.functional
@pytest.mark.order(2)
def test_ssh_worker_to_control_plane(host):
    """TC_K8_017: Passwordless SSH from worker to control plane nodes."""
    _skip_if_k8s_disabled(host)

    tc = TC["ssh_worker_to_control_plane"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from worker to control plane nodes")
    result = check_k8s_ssh(host, "worker", "control_plane")

    if result["success"]:
        tl.passed(
            LOG["ssh_ok"].format(from_type="worker", to_type="control_plane"),
            result["details"],
        )
    else:
        tl.failed(
            LOG["ssh_failed"].format(
                from_type="worker", to_type="control_plane",
                pairs=result.get("error", ""),
            ),
            result["error"],
        )

    assert result["success"], ASSERT["ssh_failed"]


@pytest.mark.kubernetes
@pytest.mark.functional
@pytest.mark.order(3)
def test_ssh_worker_to_worker(host):
    """TC_K8_018: Passwordless SSH between worker nodes."""
    _skip_if_k8s_disabled(host)

    tc = TC["ssh_worker_to_worker"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH between worker nodes")
    result = check_k8s_ssh(host, "worker", "worker")

    if result["success"]:
        tl.passed(
            LOG["ssh_ok"].format(from_type="worker", to_type="worker"),
            result["details"],
        )
    else:
        tl.failed(
            LOG["ssh_failed"].format(
                from_type="worker", to_type="worker",
                pairs=result.get("error", ""),
            ),
            result["error"],
        )

    assert result["success"], ASSERT["ssh_failed"]
