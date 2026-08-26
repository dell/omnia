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
Telemetry Precheck — Cluster Health Verification Tests.

Test cases:
    TC_PC_002: Verify omnia.env variables present
    TC_PC_003: Verify K8s nodes are Ready
    TC_PC_004: Verify kube_vip is reachable
"""

import pytest

from library.functions import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.telemetry_func import (
    check_env_vars_present,
    resolve_kube_vip_ip,
    run_on_kube_vip,
)
from library.vars.common_vars import CMDS


@pytest.mark.sanity
@pytest.mark.order(1)
def test_env_vars_present(host):
    """TC_PC_002: Verify omnia.env variables present."""
    tc = TC["env_vars_present"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking required omnia.env variables")
    result = check_env_vars_present(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["env_vars_ok"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["env_vars_missing"].format(
                count=len([
                    r for r in result["results"] if not r["found"]
                ]),
            ),
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["env_vars_missing"].format(
        error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_k8s_nodes_ready(host):
    """TC_PC_003: Verify K8s nodes are Ready."""
    tc = TC["k8s_nodes_ready"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking K8s node readiness")
    cmd = CMDS["kubectl_get_nodes_ready"]
    result = run_on_kube_vip(host, cmd)

    nodes = []
    not_ready = []
    if result.rc == 0 and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                name, ready = parts[0], parts[1]
                nodes.append({"name": name, "ready": ready})
                if ready != "True":
                    not_ready.append(name)

    all_ready = len(not_ready) == 0 and len(nodes) > 0

    if all_ready:
        tl.passed(
            LOG_MSGS["nodes_ready"].format(count=len(nodes)),
            f"Nodes: {len(nodes)}",
        )
    else:
        tl.failed(
            LOG_MSGS["nodes_not_ready"].format(
                not_ready_count=len(not_ready),
            ),
            f"Not ready: {', '.join(not_ready)}",
        )

    assert all_ready, ASSERT_MSGS["pods_not_running"].format(
        component="K8s nodes",
        expected="all Ready",
        running=f"{len(nodes) - len(not_ready)}/{len(nodes)}",
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_kube_vip_reachable(host):
    """TC_PC_004: Verify kube_vip is reachable."""
    tc = TC["kube_vip_reachable"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Resolving and testing kube_vip connectivity")
    kube_vip_ip = resolve_kube_vip_ip(host)
    if not kube_vip_ip:
        tl.failed(
            LOG_MSGS["health_failed"].format(component="kube_vip resolution"),
            "Cannot resolve kube_vip IP",
        )
        pytest.fail("Cannot resolve kube_vip IP from cluster inventory")

    result = run_on_kube_vip(host, "echo ok")
    reachable = result.rc == 0 and "ok" in result.stdout

    if reachable:
        tl.passed(
            LOG_MSGS["health_ok"].format(component=f"kube_vip ({kube_vip_ip})"),
            f"IP: {kube_vip_ip}",
        )
    else:
        tl.failed(
            LOG_MSGS["health_failed"].format(
                component=f"kube_vip ({kube_vip_ip})",
            ),
            f"rc={result.rc}",
        )

    assert reachable, ASSERT_MSGS["pods_not_running"].format(
        component="kube_vip connectivity",
        expected="reachable",
        running="unreachable",
    )
