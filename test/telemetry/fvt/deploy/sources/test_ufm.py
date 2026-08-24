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
    TC_SR_016: Verify UFM external service exists with correct endpoint
    TC_SR_017: Verify UFM VMServiceScrape CR exists
    TC_SR_018: Verify UFM credentials K8s secret exists
    TC_SR_019: Verify UFM InfiniBand metrics in VictoriaMetrics
"""

from datetime import datetime

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import UFM_EXPECTED_METRICS
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.telemetry_func import is_source_enabled
from library.functions.ufm_func import (
    verify_ufm_external_service,
    verify_ufm_vmscrape,
    verify_ufm_credentials_secret,
    verify_ufm_metrics,
)


def _skip_if_ufm_disabled(host):
    """Skip test if UFM source is not enabled."""
    if not is_source_enabled(host, "ufm"):
        pytest.skip("UFM source not enabled in config")


def _format_metric_lines(metric_details):
    """Format metrics into ✓ lines with value and timestamp."""
    if not metric_details:
        return "  (no metrics found)"

    lines = []
    for m in metric_details:
        ts = m.get("timestamp", 0)
        try:
            ts_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            ts_str = str(ts)
        lines.append(
            f"  \u2713 {m['metric']}: {m['value']} ({ts_str})"
        )
    return "\n".join(lines)


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(70)
def test_ufm_external_service(host):
    """TC_SR_016: Verify UFM external service exists with correct endpoint."""
    _skip_if_ufm_disabled(host)
    tc = TC["ufm_external_svc"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying UFM external headless service")
    result = verify_ufm_external_service(host)

    detail = (
        f"endpoint={result.get('endpoint_ip', '')}:{result.get('endpoint_port', '')}, "
        f"expected={result.get('expected_endpoint', '')}:{result.get('expected_port', '')}"
    )

    if result["success"]:
        tl.passed(
            LOG_MSGS["ufm_svc_exists"].format(
                service=result["service_name"],
                endpoint=f"{result['endpoint_ip']}:{result['endpoint_port']}",
            ),
            detail,
        )
    else:
        tl.failed(
            LOG_MSGS["ufm_svc_missing"].format(service=result["service_name"]),
            detail,
        )

    assert result["success"], ASSERT_MSGS["ufm_svc_missing"].format(
        service=result["service_name"],
    )


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(71)
def test_ufm_vmscrape(host):
    """TC_SR_017: Verify UFM VMServiceScrape CR exists."""
    _skip_if_ufm_disabled(host)
    tc = TC["ufm_vmscrape"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking UFM VMServiceScrape CR")
    result = verify_ufm_vmscrape(host)

    if result["success"]:
        detail = (
            f"port={result.get('port', '')}, "
            f"path={result.get('path', '')}, "
            f"interval={result.get('scrape_interval', '')}"
        )
        tl.passed(
            LOG_MSGS["ufm_vmscrape_exists"].format(name=result["name"]),
            detail,
        )
    else:
        tl.failed(
            LOG_MSGS["ufm_vmscrape_missing"].format(name=result["name"]),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["ufm_vmscrape_missing"].format(
        name=result["name"],
    )


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(72)
def test_ufm_credentials_secret(host):
    """TC_SR_018: Verify UFM credentials K8s secret exists."""
    _skip_if_ufm_disabled(host)
    tc = TC["ufm_credentials_secret"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking UFM credentials secret")
    result = verify_ufm_credentials_secret(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["ufm_secret_exists"].format(secret=result["secret_name"]),
            f"keys: {', '.join(result.get('keys_found', []))}",
        )
    else:
        tl.failed(
            LOG_MSGS["ufm_secret_missing"].format(secret=result["secret_name"]),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["ufm_secret_missing"].format(
        secret=result["secret_name"],
    )


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(73)
def test_ufm_metrics_in_vm(host):
    """TC_SR_019: Verify UFM InfiniBand metrics in VictoriaMetrics."""
    _skip_if_ufm_disabled(host)
    tc = TC["ufm_metrics_in_vm"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Querying VictoriaMetrics for UFM InfiniBand metrics")
    result = verify_ufm_metrics(host, UFM_EXPECTED_METRICS)

    metric_lines = _format_metric_lines(result.get("metric_details", []))

    if result["success"]:
        details_lines = [
            f"Found: {len(result['found'])}/{len(UFM_EXPECTED_METRICS)} metrics",
            "",
            metric_lines,
        ]
        tl.passed(
            LOG_MSGS["ufm_metrics_found"].format(count=len(result["found"])),
            "\n".join(details_lines),
        )
    else:
        missing_str = ", ".join(result["missing"])
        details_lines = [
            f"Found: {len(result['found'])}/{len(UFM_EXPECTED_METRICS)} metrics",
        ]
        for m in result["missing"]:
            details_lines.append(f"  \u2717 {m}: MISSING")
        if result.get("metric_details"):
            details_lines.append("")
            details_lines.append(metric_lines)
        tl.failed(
            LOG_MSGS["ufm_metrics_missing"].format(missing=missing_str),
            "\n".join(details_lines),
        )

    assert result["success"], ASSERT_MSGS["ufm_metrics_missing"].format(
        missing=", ".join(result["missing"]),
    )
