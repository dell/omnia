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
Telemetry Precheck — Cluster Verification Tests.

Test cases:
    TC_PC_002: Verify kube_vip is defined in telemetry_config.yml
    TC_PC_003: Verify kube_vip is reachable (ICMP + SSH)
    TC_PC_004: Verify K8s control plane nodes are Ready
    TC_PC_005: Verify worker nodes meet minimum readiness threshold
    TC_PC_006: Verify all pods (outside telemetry ns) are healthy
    TC_PC_007: Verify kubectl is available on kube_vip
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import IPV4_PATTERN
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.telemetry_func import (
    load_telemetry_config_from_target,
)
from library.functions.k8s_func import (
    verify_kubectl_available,
    verify_control_plane_ready,
    verify_worker_nodes_ready,
    verify_pods_healthy,
    verify_kube_vip_reachable,
)


@pytest.mark.sanity
@pytest.mark.order(2)
def test_kube_vip_defined(host):
    """TC_PC_002: Verify kube_vip is defined in telemetry_config.yml.

    Reads the config from the target host and verifies:
    - kube_vip key exists
    - kube_vip value is a non-empty string
    - kube_vip is a valid IPv4 address format
    """
    tc = TC["kube_vip_defined"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Reading telemetry_config.yml from target")
    config = load_telemetry_config_from_target(host)
    kube_vip = config.get("kube_vip", "")

    if kube_vip and IPV4_PATTERN.match(kube_vip):
        tl.passed(
            LOG_MSGS["kube_vip_defined"].format(kube_vip=kube_vip),
            f"kube_vip: {kube_vip} (valid IPv4)",
        )
    else:
        detail = f"kube_vip value: '{kube_vip}'"
        if kube_vip and not IPV4_PATTERN.match(kube_vip):
            detail += " (not a valid IPv4 format)"
        tl.failed(LOG_MSGS["kube_vip_not_defined"], detail)

    assert kube_vip, ASSERT_MSGS["kube_vip_not_defined"]
    assert IPV4_PATTERN.match(kube_vip), (
        f"kube_vip '{kube_vip}' is not a valid IPv4 address"
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_kube_vip_reachable(host):
    """TC_PC_003: Verify kube_vip is reachable (ICMP + SSH).

    Verifies the kube_vip host responds to:
    - ICMP ping (2 packets, 3s timeout)
    - SSH connection (port 22, BatchMode)
    """
    tc = TC["kube_vip_reachable"]
    tl = TestLogger(tc["title"], tc["id"])

    config = load_telemetry_config_from_target(host)
    kube_vip = config.get("kube_vip", "")
    if not kube_vip:
        tl.failed(LOG_MSGS["kube_vip_not_defined"], "Cannot test reachability")
        pytest.skip("kube_vip not defined")

    tl.check(f"Testing reachability to kube_vip: {kube_vip}")
    result = verify_kube_vip_reachable(host, kube_vip)

    details = (
        f"Ping: {'OK' if result['ping_ok'] else 'FAILED'}\n"
        f"SSH:  {'OK' if result['ssh_ok'] else 'FAILED'}"
    )

    if result["success"]:
        tl.passed(
            LOG_MSGS["kube_vip_reachable"].format(kube_vip=kube_vip),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["kube_vip_not_reachable"].format(kube_vip=kube_vip),
            details,
        )

    assert result["success"], ASSERT_MSGS["kube_vip_not_reachable"].format(
        kube_vip=kube_vip,
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_control_plane_ready(host):
    """TC_PC_004: Verify all K8s control plane nodes are Ready.

    All control plane nodes (labeled node-role.kubernetes.io/control-plane)
    must have status condition Ready=True.
    """
    tc = TC["control_plane_ready"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying K8s control plane node readiness")
    result = verify_control_plane_ready(host)

    if result.get("error"):
        tl.failed("Failed to check control plane", result["error"])
        assert False, result["error"]

    # Build details
    details_lines = []
    for node in result.get("nodes", []):
        status = "Ready" if node["ready"] else "NOT Ready"
        icon = "+" if node["ready"] else "x"
        details_lines.append(f"  {icon} {node['name']}: {status}")
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["control_plane_ready"].format(count=result["total"]),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["control_plane_not_ready"].format(
                not_ready=result["not_ready"],
                total=result["total"],
            ),
            details,
        )

    assert result["success"], ASSERT_MSGS["control_plane_not_ready"].format(
        not_ready=result["not_ready"],
        total=result["total"],
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_worker_nodes_ready(host):
    """TC_PC_005: Verify worker nodes meet minimum readiness threshold.

    Threshold:
        1 worker  -> 1 Ready required
        2 workers -> 2 Ready required
        3+ workers -> at least 2 Ready required
    """
    tc = TC["worker_nodes_ready"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying worker node readiness threshold")
    result = verify_worker_nodes_ready(host)

    if result.get("error"):
        tl.failed("Failed to check worker nodes", result["error"])
        assert False, result["error"]

    # Build details
    details_lines = [
        f"Total workers: {result['total']}",
        f"Ready: {result['ready']}",
        f"Minimum required: {result['minimum']}",
    ]
    for node in result.get("nodes", []):
        status = "Ready" if node["ready"] else "NOT Ready"
        icon = "+" if node["ready"] else "x"
        details_lines.append(f"  {icon} {node['name']}: {status}")
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["workers_ready"].format(
                ready=result["ready"], total=result["total"],
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["workers_not_ready"].format(
                ready=result["ready"], total=result["total"],
            ),
            details,
        )

    assert result["success"], ASSERT_MSGS["workers_not_ready"].format(
        ready=result["ready"],
        total=result["total"],
        minimum=result["minimum"],
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_pods_healthy(host):
    """TC_PC_006: Verify all pods (outside telemetry ns) are healthy.

    All pods in namespaces other than 'telemetry' must be in
    Running or Succeeded phase.
    """
    tc = TC["pods_healthy"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying pod health (excluding telemetry namespace)")
    result = verify_pods_healthy(host)

    if result.get("error"):
        tl.failed("Failed to check pod health", result["error"])
        assert False, result["error"]

    # Build details
    details_lines = [
        f"Total pods: {result['total']}",
        f"Healthy: {result['healthy']}",
        f"Unhealthy: {result['unhealthy']}",
    ]
    for pod in result.get("unhealthy_pods", [])[:10]:
        details_lines.append(
            f"  x {pod['namespace']}/{pod['name']}: {pod['status']}"
        )
    if result["unhealthy"] > 10:
        details_lines.append(f"  ... and {result['unhealthy'] - 10} more")
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_healthy"].format(count=result["total"]),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["pods_unhealthy"].format(
                unhealthy=result["unhealthy"],
                total=result["total"],
            ),
            details,
        )

    assert result["success"], ASSERT_MSGS["pods_unhealthy"].format(
        unhealthy=result["unhealthy"],
        total=result["total"],
    )


@pytest.mark.sanity
@pytest.mark.order(7)
def test_kubectl_available(host):
    """TC_PC_007: Verify kubectl is available on kube_vip.

    Checks that kubectl binary is installed and can report its version.
    """
    tc = TC["kubectl_available"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking kubectl availability on kube_vip")
    result = verify_kubectl_available(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["kubectl_available"],
            f"Version: {result['version']}",
        )
    else:
        tl.failed(
            LOG_MSGS["kubectl_not_available"],
            result.get("error", "kubectl not found"),
        )

    assert result["success"], ASSERT_MSGS["kubectl_not_available"]
