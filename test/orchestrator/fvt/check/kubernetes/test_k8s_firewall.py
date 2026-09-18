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
Kubernetes firewall port and systemd target verification tests.

Verifies that firewall ports from cloud-init templates are open on K8s nodes
and that required systemd targets (nfs-client.target) are active.
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_firewall_ports_control_plane,
    check_k8s_firewall_ports_workers,
    check_k8s_nfs_client_target,
)
from library.vars.k8s_vars import TEST_CASES
from library.messages import (
    K8S_TEST_LOG_MSGS as LOG,
    K8S_TEST_ASSERT_MSGS as ASSERT,
)


# =============================================================================
# Firewall Port Tests
# =============================================================================

@pytest.mark.order(52)
@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
def test_k8s_firewall_ports_control_plane(host):
    """TC_K8_051: Verify firewall ports on control plane nodes match cloud-init."""
    tc = TEST_CASES["k8s_firewall_ports_control_plane"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking firewall ports on control plane nodes")
    result = check_k8s_firewall_ports_control_plane(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["firewall_ports_cp_ok"].format(
                count=result.get("nodes_checked", 0)
            ),
            "",
        )
    else:
        tl.failed(LOG["firewall_ports_cp_failed"].format(error=result["error"]), result["error"])

    assert result["success"], (
        LOG["firewall_ports_cp_failed"].format(error=result["error"])
    )


@pytest.mark.order(53)
@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
def test_k8s_firewall_ports_workers(host):
    """TC_K8_052: Verify firewall ports on worker nodes match cloud-init."""
    tc = TEST_CASES["k8s_firewall_ports_workers"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking firewall ports on worker nodes")
    result = check_k8s_firewall_ports_workers(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["firewall_ports_workers_ok"].format(
                count=result.get("nodes_checked", 0)
            ),
            "",
        )
    else:
        tl.failed(LOG["firewall_ports_workers_failed"].format(error=result["error"]), result["error"])

    assert result["success"], (
        LOG["firewall_ports_workers_failed"].format(error=result["error"])
    )


# =============================================================================
# Systemd Target Tests
# =============================================================================

@pytest.mark.order(54)
@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
def test_k8s_nfs_client_target(host):
    """TC_K8_053: Verify nfs-client.target is active on all K8s nodes."""
    tc = TEST_CASES["k8s_nfs_client_target"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking nfs-client.target on K8s nodes")
    result = check_k8s_nfs_client_target(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["nfs_client_target_ok"].format(
                count=result.get("nodes_checked", 0)
            ),
            "",
        )
    else:
        tl.failed(LOG["nfs_client_target_failed"].format(error=result["error"]), result["error"])

    assert result["success"], (
        LOG["nfs_client_target_failed"].format(error=result["error"])
    )
