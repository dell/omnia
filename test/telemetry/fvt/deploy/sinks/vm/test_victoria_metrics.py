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
Telemetry Deploy — VictoriaMetrics Sink Verification Tests.

Test cases:
    TC_SK_001: Verify VictoriaMetrics cluster pods running
    TC_SK_002: Verify VictoriaMetrics PVC sizes match config
    TC_SK_003: Verify vmagent pods running
    TC_SK_004: Verify VictoriaMetrics TLS secret exists
    TC_SK_005: Verify VictoriaMetrics health endpoint responds
    TC_SK_006: Verify VictoriaMetrics services have endpoints
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import TELEMETRY_NAMESPACE, VICTORIA_TLS_SECRET
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.sink_func import (
    verify_vm_cluster_pods,
    verify_vm_pvc_sizes,
    verify_vmagent_pods,
    verify_vm_services,
    verify_vm_operator,
)
from library.functions.k8s_func import verify_secret_exists
from library.functions.telemetry_func import is_sink_enabled


def _skip_if_vm_disabled(host):
    """Skip test if victoria_metrics sink is not enabled."""
    if not is_sink_enabled(host, "victoria_metrics"):
        pytest.skip("VictoriaMetrics sink not enabled in config")


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(21)
def test_vm_cluster_pods(host):
    """TC_SK_001: Verify VictoriaMetrics cluster pods running.

    Checks vmstorage, vminsert, vmselect pods are all Running.
    """
    _skip_if_vm_disabled(host)
    tc = TC["vm_cluster_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying VictoriaMetrics cluster pods")
    result = verify_vm_cluster_pods(host)

    details_lines = []
    for comp, info in result.get("components", {}).items():
        status = "OK" if info["all_running"] else "FAIL"
        details_lines.append(
            f"  {comp}: {info['running_count']}/{info['total_count']} running [{status}]"
        )
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="VictoriaMetrics cluster",
                count=result["total_running"],
                expected=result["total_running"],
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="VictoriaMetrics cluster",
                running=result["total_running"],
                expected="all",
            ),
            details,
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="VictoriaMetrics cluster",
        running=result["total_running"],
        expected="all",
    )


@pytest.mark.sink
@pytest.mark.order(22)
def test_vm_persistence_size(host):
    """TC_SK_002: Verify VictoriaMetrics PVC sizes.

    Checks that vmstorage PVCs exist and have non-zero capacity.
    """
    _skip_if_vm_disabled(host)
    tc = TC["vm_persistence_size"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying VictoriaMetrics PVC sizes")
    result = verify_vm_pvc_sizes(host)

    if result["success"]:
        pvc_info = ", ".join(
            f"{p['name']}={p['capacity']}" for p in result["pvcs"]
        )
        tl.passed(
            LOG_MSGS["pvc_size_match"].format(size=pvc_info),
            f"PVCs found: {len(result['pvcs'])}",
        )
    else:
        tl.failed(LOG_MSGS["pvc_size_mismatch"], result.get("error", "No PVCs found"))

    assert result["success"], ASSERT_MSGS["pvc_size_mismatch"].format(
        component="VictoriaMetrics",
        expected="non-zero",
        actual="none found" if not result["pvcs"] else str(result["pvcs"]),
    )


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(23)
def test_vmagent_pods(host):
    """TC_SK_003: Verify vmagent pods running.

    Checks that vmagent pods (metrics scraper) are Running.
    """
    _skip_if_vm_disabled(host)
    tc = TC["vmagent_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying vmagent pods")
    result = verify_vmagent_pods(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="vmagent",
                count=result["running_count"],
                expected=result["total_count"],
            ),
            f"Running: {result['running_count']}/{result['total_count']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="vmagent",
                running=result["running_count"],
                expected=result["total_count"],
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="vmagent",
        running=result["running_count"],
        expected=result["total_count"],
    )


@pytest.mark.sink
@pytest.mark.order(24)
def test_vm_tls_secret(host):
    """TC_SK_004: Verify VictoriaMetrics TLS secret exists.

    Checks that the TLS secret used for VM cluster inter-node
    communication exists in the telemetry namespace.
    """
    _skip_if_vm_disabled(host)
    tc = TC["vm_tls_secret"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking TLS secret '{VICTORIA_TLS_SECRET}'")
    exists = verify_secret_exists(host, VICTORIA_TLS_SECRET)

    if exists:
        tl.passed(
            LOG_MSGS["tls_secret_exists"].format(
                secret=VICTORIA_TLS_SECRET,
                namespace=TELEMETRY_NAMESPACE,
            ),
            "",
        )
    else:
        tl.failed(
            LOG_MSGS["tls_secret_missing"].format(
                secret=VICTORIA_TLS_SECRET,
                namespace=TELEMETRY_NAMESPACE,
            ),
            "",
        )

    assert exists, ASSERT_MSGS["tls_secret_missing"].format(
        secret=VICTORIA_TLS_SECRET,
        namespace=TELEMETRY_NAMESPACE,
    )


@pytest.mark.sink
@pytest.mark.order(25)
def test_vm_health(host):
    """TC_SK_005: Verify VictoriaMetrics operator is running.

    Checks that the victoria-metrics-operator deployment has ready replicas.
    """
    _skip_if_vm_disabled(host)
    tc = TC["vm_health"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking VictoriaMetrics operator health")
    result = verify_vm_operator(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["health_ok"].format(component="VictoriaMetrics operator"),
            f"Ready replicas: {result['ready_replicas']}",
        )
    else:
        tl.failed(
            LOG_MSGS["health_failed"].format(component="VictoriaMetrics operator"),
            f"Ready replicas: {result['ready_replicas']}",
        )

    assert result["success"], ASSERT_MSGS["health_failed"].format(
        component="VictoriaMetrics operator",
    )


@pytest.mark.sink
@pytest.mark.order(26)
def test_vm_services(host):
    """TC_SK_006: Verify VictoriaMetrics services have endpoints.

    Checks that vminsert, vmselect, vmstorage services exist.
    """
    _skip_if_vm_disabled(host)
    tc = TC["vm_services"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying VictoriaMetrics services")
    result = verify_vm_services(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["services_ok"].format(component="VictoriaMetrics"),
            f"Services: {', '.join(result['services'])}",
        )
    else:
        tl.failed(
            LOG_MSGS["services_missing"].format(component="VictoriaMetrics"),
            f"Missing: {', '.join(result['missing'])}",
        )

    assert result["success"], (
        f"VictoriaMetrics services missing: {', '.join(result['missing'])}"
    )
