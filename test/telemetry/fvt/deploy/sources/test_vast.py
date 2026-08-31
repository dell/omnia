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
Telemetry Deploy — VAST Source Verification Tests.

VAST Architecture:
    VAST itself is external (NOT deployed by Omnia).
    Omnia creates a headless K8s service (vast-external) pointing to the
    VAST appliance IP, and a VMServiceScrape CR that instructs vmagent
    to scrape the VAST Prometheus exporter.

    Data pipeline (metrics):
        VAST Prometheus API (HTTPS) -> vmagent(shared) -> VictoriaMetrics
    Data pipeline (logs):
        VAST syslog -> VLAgent -> VictoriaLogs

Test cases:
    TC_SR_080: Verify VAST external service exists with correct endpoint
    TC_SR_081: Verify VAST VMServiceScrape CR exists
    TC_SR_082: Verify VAST credentials K8s secret exists
    TC_SR_083: Verify VAST storage metrics in VictoriaMetrics
    TC_SR_084: Verify VAST logs in VictoriaLogs
"""

from datetime import datetime

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import VAST_EXPECTED_METRICS
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.telemetry_func import (
    is_source_enabled,
    is_logs_enabled,
)
from library.functions.vast_func import (
    verify_vast_external_service,
    verify_vast_vmscrape,
    verify_vast_credentials_secret,
    verify_vast_metrics,
    verify_vast_logs,
    get_vast_endpoint_from_config,
)


def _skip_if_vast_disabled(host):
    """Skip test if VAST source is not enabled."""
    if not is_source_enabled(host, "vast"):
        pytest.skip("VAST source not enabled in config")


def _format_metric_lines(metric_details):
    """Format metrics into lines with value and timestamp."""
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


# =========================================================================
# TC_SR_080: Verify VAST external service exists with correct endpoint
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(80)
def test_vast_external_service(host):
    """Verify VAST external service exists with correct endpoint."""
    _skip_if_vast_disabled(host)
    tc = TC["vast_external_svc"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying VAST external headless service")
    result = verify_vast_external_service(host)

    detail = (
        f"endpoint={result.get('endpoint_ip', '')}:"
        f"{result.get('endpoint_port', '')}, "
        f"expected={result.get('expected_endpoint', '')}:"
        f"{result.get('expected_port', '')}"
    )

    if result["success"]:
        tl.passed(
            LOG_MSGS["vast_svc_exists"].format(
                service=result["service_name"],
                endpoint=f"{result['endpoint_ip']}:{result['endpoint_port']}",
            ),
            detail,
        )
    else:
        tl.failed(
            LOG_MSGS["vast_svc_missing"].format(service=result["service_name"]),
            detail,
        )

    assert result["success"], ASSERT_MSGS["vast_svc_missing"].format(
        service=result["service_name"],
    )


# =========================================================================
# TC_SR_081: Verify VAST VMServiceScrape CR exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(81)
def test_vast_vmscrape(host):
    """Verify VAST VMServiceScrape CR exists."""
    _skip_if_vast_disabled(host)
    tc = TC["vast_vmscrape"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking VAST VMServiceScrape CR")
    result = verify_vast_vmscrape(host)

    if result["success"]:
        detail = (
            f"port={result.get('port', '')}, "
            f"path={result.get('path', '')}, "
            f"interval={result.get('scrape_interval', '')}"
        )
        tl.passed(
            LOG_MSGS["vast_vmscrape_exists"].format(name=result["name"]),
            detail,
        )
    else:
        tl.failed(
            LOG_MSGS["vast_vmscrape_missing"].format(name=result["name"]),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["vast_vmscrape_missing"].format(
        name=result["name"],
    )


# =========================================================================
# TC_SR_082: Verify VAST credentials K8s secret exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(82)
def test_vast_credentials_secret(host):
    """Verify VAST credentials K8s secret exists."""
    _skip_if_vast_disabled(host)
    tc = TC["vast_credentials_secret"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if auth_mode is basic (secret required)
    cfg_result = get_vast_endpoint_from_config(host)
    if not cfg_result["success"]:
        tl.skipped("VAST endpoint not configured")
        pytest.skip("VAST endpoint not configured")

    tl.check("Checking VAST credentials secret")
    result = verify_vast_credentials_secret(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["vast_secret_exists"].format(secret=result["secret_name"]),
            f"keys: {', '.join(result.get('keys_found', []))}",
        )
    else:
        tl.failed(
            LOG_MSGS["vast_secret_missing"].format(secret=result["secret_name"]),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["vast_secret_missing"].format(
        secret=result["secret_name"],
    )


# =========================================================================
# TC_SR_083: Verify VAST storage metrics in VictoriaMetrics
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(83)
def test_vast_metrics_in_vm(host):
    """Verify VAST storage metrics in VictoriaMetrics."""
    _skip_if_vast_disabled(host)
    tc = TC["vast_metrics_in_vm"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Querying VictoriaMetrics for VAST storage metrics")
    result = verify_vast_metrics(host, VAST_EXPECTED_METRICS)

    metric_lines = _format_metric_lines(result.get("metric_details", []))

    if result["success"]:
        details_lines = [
            f"Found: {len(result['found'])}/{len(VAST_EXPECTED_METRICS)} metrics",
            "",
            metric_lines,
        ]
        tl.passed(
            LOG_MSGS["vast_metrics_found"].format(count=len(result["found"])),
            "\n".join(details_lines),
        )
    else:
        missing_str = ", ".join(result["missing"])
        details_lines = [
            f"Found: {len(result['found'])}/{len(VAST_EXPECTED_METRICS)} metrics",
        ]
        for m in result["missing"]:
            details_lines.append(f"  \u2717 {m}: MISSING")
        if result.get("metric_details"):
            details_lines.append("")
            details_lines.append(metric_lines)
        tl.failed(
            LOG_MSGS["vast_metrics_missing"].format(missing=missing_str),
            "\n".join(details_lines),
        )

    assert result["success"], ASSERT_MSGS["vast_metrics_missing"].format(
        missing=", ".join(result["missing"]),
    )


# =========================================================================
# TC_SR_084: Verify VAST logs in VictoriaLogs
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(84)
def test_vast_logs_in_vl(host):
    """Verify VAST logs in VictoriaLogs."""
    _skip_if_vast_disabled(host)
    if not is_logs_enabled(host, "vast"):
        pytest.skip("VAST logs not enabled in config")

    tc = TC["vast_logs_in_vl"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Querying VictoriaLogs for VAST syslog entries")
    result = verify_vast_logs(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["vast_logs_found"].format(count=result["count"]),
            f"Sample: {result['sample_log']}",
        )
    else:
        tl.failed(
            LOG_MSGS["vast_logs_missing"],
            "",
        )

    assert result["success"], ASSERT_MSGS["vast_logs_missing"]
