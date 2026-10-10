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
Telemetry Deploy — UFM Source Verification Tests.

UFM Architecture:
    UFM itself is external (NOT deployed by Omnia).
    Omnia creates a headless K8s service (ufm-external) pointing to the
    UFM appliance IP, and a VMServiceScrape CR that instructs vmagent
    to scrape the UFM Prometheus exporter.

    Data pipeline:
        UFM Prometheus Exporter (HTTPS) -> vmagent(shared) -> VictoriaMetrics

Test cases:
    TEL_FVT_DEPLOY_V060: Verify UFM external service exists with correct endpoint
    TEL_FVT_DEPLOY_V061: Verify UFM VMServiceScrape CR exists
    TEL_FVT_DEPLOY_V062: Verify UFM credentials K8s secret exists
    TEL_FVT_DEPLOY_V063: Verify UFM InfiniBand metrics in VictoriaMetrics
    TEL_FVT_DEPLOY_V064: Verify configured-disabled UFM state
"""

import time

import pytest

from library.functions import TestLogger
from library.messages.ufm_msgs import (
    UFM_ASSERT_MSGS as ASSERT_MSGS,
    UFM_DETAIL_MSGS as DETAIL_MSGS,
    UFM_LOG_MSGS as LOG_MSGS,
)
from library.functions.telemetry_func import is_source_enabled, is_sink_enabled_for_source
from library.functions.k8s_func import verify_enabled_shared_sinks
from library.functions.ufm_func import (
    verify_ufm_external_service,
    verify_ufm_vmscrape,
    verify_ufm_credentials_secret,
    verify_ufm_metrics,
    verify_ufm_resources_absent,
)
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.ufm_vars import UFM_EXPECTED_METRICS, UFM_SOURCE_NAME


def _skip_if_ufm_disabled(host):
    """Skip test if UFM source is not enabled."""
    if not is_source_enabled(host, UFM_SOURCE_NAME):
        pytest.skip(LOG_MSGS["disabled"])


# =========================================================================
# TEL_FVT_DEPLOY_V060: Verify UFM external service exists with correct endpoint
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.ufm
@pytest.mark.order(70)
def test_ufm_external_service(host):
    """TEL_FVT_DEPLOY_V060: Verify UFM external service exists with correct endpoint."""
    _skip_if_ufm_disabled(host)
    tc = TC["ufm_external_svc"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(LOG_MSGS["service_check"])
    result = verify_ufm_external_service(host)

    detail = DETAIL_MSGS["service"].format(
        endpoint_ip=result.get("endpoint_ip", ""),
        endpoint_port=result.get("endpoint_port", ""),
        expected_endpoint=result.get("expected_endpoint", ""),
        expected_port=result.get("expected_port", ""),
    )

    if result["success"]:
        tl.passed(
            LOG_MSGS["service_exists"].format(
                service=result["service_name"],
                endpoint_ip=result["endpoint_ip"],
                endpoint_port=result["endpoint_port"],
            ),
            detail,
        )
    else:
        tl.failed(
            LOG_MSGS["service_missing"].format(service=result["service_name"]),
            DETAIL_MSGS["failure"].format(
                details=detail,
                error=result.get(
                    "error",
                    LOG_MSGS["service_missing"].format(
                        service=result["service_name"],
                    ),
                ),
            ),
        )

    assert result["success"], ASSERT_MSGS["service_missing"].format(
        service=result["service_name"],
    )


# =========================================================================
# TEL_FVT_DEPLOY_V061: Verify UFM VMServiceScrape CR exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.ufm
@pytest.mark.order(71)
def test_ufm_vmscrape(host):
    """TEL_FVT_DEPLOY_V061: Verify UFM VMServiceScrape CR exists."""
    _skip_if_ufm_disabled(host)
    tc = TC["ufm_vmscrape"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(LOG_MSGS["vmscrape_check"])
    result = verify_ufm_vmscrape(host)

    if result["success"]:
        detail = DETAIL_MSGS["vmscrape"].format(
            port=result.get("port", ""),
            path=result.get("path", ""),
            scrape_interval=result.get("scrape_interval", ""),
        )
        tl.passed(
            LOG_MSGS["vmscrape_exists"].format(name=result["name"]),
            detail,
        )
    else:
        tl.failed(
            LOG_MSGS["vmscrape_missing"].format(name=result["name"]),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["vmscrape_missing"].format(
        name=result["name"],
    )


# =========================================================================
# TEL_FVT_DEPLOY_V062: Verify UFM credentials K8s secret exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.ufm
@pytest.mark.order(72)
def test_ufm_credentials_secret(host):
    """TEL_FVT_DEPLOY_V062: Verify UFM credentials K8s secret exists."""
    _skip_if_ufm_disabled(host)
    tc = TC["ufm_credentials_secret"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(LOG_MSGS["secret_check"])
    result = verify_ufm_credentials_secret(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["secret_exists"].format(secret=result["secret_name"]),
            DETAIL_MSGS["secret"].format(
                keys=", ".join(result.get("keys_found", [])),
            ),
        )
    else:
        tl.failed(
            LOG_MSGS["secret_missing"].format(secret=result["secret_name"]),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["secret_missing"].format(
        secret=result["secret_name"],
    )


# =========================================================================
# TEL_FVT_DEPLOY_V063: Verify UFM InfiniBand metrics in VictoriaMetrics
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ufm
@pytest.mark.order(73)
def test_ufm_metrics_in_vm(host):
    """TEL_FVT_DEPLOY_V063: Verify UFM InfiniBand metrics in VictoriaMetrics."""
    _skip_if_ufm_disabled(host)
    # Skip if UFM does not target VictoriaMetrics sink
    if not is_sink_enabled_for_source(host, "ufm", "victoria_metrics"):
        pytest.skip("UFM source does not target VictoriaMetrics sink")
    
    tc = TC["ufm_metrics_in_vm"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(LOG_MSGS["metrics_check"])
    result = verify_ufm_metrics(host, UFM_EXPECTED_METRICS)

    if result["success"]:
        tl.passed(
            LOG_MSGS["metrics_found"].format(
                count=result["found_metric_count"],
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["metrics_missing"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["metrics_missing"].format(
        missing=", ".join(result["missing"]),
    )


# =========================================================================
# TEL_FVT_DEPLOY_V064: Verify configured-disabled UFM state
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.ufm
@pytest.mark.order(74)
def test_ufm_disabled_state(host):
    """Verify disabled UFM has no Service, Endpoints, or VMServiceScrape."""
    if is_source_enabled(host, UFM_SOURCE_NAME):
        pytest.skip("UFM source is enabled; disabled-state check is not applicable")

    tc = TC["ufm_disabled_state"]
    tl = TestLogger(tc["title"], tc["id"])
    tl.check(LOG_MSGS["disabled_check"])

    # --- Verify UFM-owned resources are absent ---
    absent = verify_ufm_resources_absent(host)

    # --- Verify shared sinks remain healthy ---
    shared = verify_enabled_shared_sinks(host)

    # --- Verify no fresh UFM metrics are flowing ---
    quiet_started = time.time()
    vm_quiet = verify_ufm_metrics(host, UFM_EXPECTED_METRICS)
    quiet_ended = time.time()
    # Metrics should NOT be found when disabled
    vm_data_stopped = (
        not vm_quiet["found"]
        or vm_quiet.get("error") == "vmselect endpoint not found"
    )

    # --- Build detail output ---
    detail_lines = [
        "Configured state: metrics_enabled=false",
    ]
    for resource in absent["resources"]:
        detail_lines.append(
            f"{resource['kind']}/{resource['name']}: "
            f"{'absent' if resource['absent'] else 'STILL PRESENT'}"
        )
    detail_lines.append(
        f"Credentials secret: "
        f"{'preserved' if absent['secret_preserved'] else 'MISSING'}"
    )
    detail_lines.append(
        f"VictoriaMetrics quiet window ({quiet_ended - quiet_started:.1f}s): "
        f"metrics_found={len(vm_quiet['found'])}/{vm_quiet['expected_metric_count']}"
    )
    detail_lines.extend(
        f"Shared {name}: {result['details']}"
        for name, result in shared["sinks"].items()
    )
    details = "\n".join(detail_lines)

    success = (
        absent["success"]
        and shared["success"]
        and vm_data_stopped
    )

    if success:
        tl.passed(LOG_MSGS["disabled_passed"], details)
    else:
        errors = []
        if not absent["success"]:
            errors.append(absent["error"])
        if not shared["success"]:
            errors.append(shared["error"])
        if not vm_data_stopped:
            errors.append(
                "fresh UFM metrics arrived in VictoriaMetrics while disabled"
            )
        tl.failed(
            LOG_MSGS["disabled_failed"],
            "\n".join(filter(None, [details, *errors])),
        )

    assert success, ASSERT_MSGS["disabled_state_incorrect"]
