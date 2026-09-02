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
    TC_SR_060: Verify UFM external service exists with correct endpoint
    TC_SR_061: Verify UFM VMServiceScrape CR exists
    TC_SR_062: Verify UFM credentials K8s secret exists
    TC_SR_063: Verify UFM InfiniBand metrics in VictoriaMetrics
"""

import pytest

from library.functions import TestLogger
from library.messages.ufm_msgs import (
    UFM_ASSERT_MSGS as ASSERT_MSGS,
    UFM_DETAIL_MSGS as DETAIL_MSGS,
    UFM_LOG_MSGS as LOG_MSGS,
)
from library.functions.telemetry_func import is_source_enabled
from library.functions.ufm_func import (
    verify_ufm_external_service,
    verify_ufm_vmscrape,
    verify_ufm_credentials_secret,
    verify_ufm_metrics,
)
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.ufm_vars import UFM_EXPECTED_METRICS, UFM_SOURCE_NAME


def _skip_if_ufm_disabled(host):
    """Skip test if UFM source is not enabled."""
    if not is_source_enabled(host, UFM_SOURCE_NAME):
        pytest.skip(LOG_MSGS["disabled"])


# =========================================================================
# TC_SR_060: Verify UFM external service exists with correct endpoint
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.ufm
@pytest.mark.order(70)
def test_ufm_external_service(host):
    """TC_SR_060: Verify UFM external service exists with correct endpoint."""
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
# TC_SR_061: Verify UFM VMServiceScrape CR exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.ufm
@pytest.mark.order(71)
def test_ufm_vmscrape(host):
    """TC_SR_061: Verify UFM VMServiceScrape CR exists."""
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
# TC_SR_062: Verify UFM credentials K8s secret exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.ufm
@pytest.mark.order(72)
def test_ufm_credentials_secret(host):
    """TC_SR_062: Verify UFM credentials K8s secret exists."""
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
# TC_SR_063: Verify UFM InfiniBand metrics in VictoriaMetrics
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ufm
@pytest.mark.order(73)
def test_ufm_metrics_in_vm(host):
    """TC_SR_063: Verify UFM InfiniBand metrics in VictoriaMetrics."""
    _skip_if_ufm_disabled(host)
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
