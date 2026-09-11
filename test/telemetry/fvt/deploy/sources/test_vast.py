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
    TC_SR_088: Verify VAST external service exists with correct endpoint
    TC_SR_089: Verify VAST VMServiceScrape CR exists
    TC_SR_090: Verify VAST credentials K8s secret exists
    TC_SR_091: Verify VAST storage metrics in VictoriaMetrics
    TC_SR_092: Configure VAST syslog and trigger a test event
    TC_SR_093: Verify that fresh VAST event in VictoriaLogs
"""

from datetime import datetime, timezone

import pytest

from library.functions import (
    TestLogger,
    configure_vast_syslog_and_trigger,
    get_vast_endpoint_from_config,
    is_logs_enabled,
    is_source_enabled,
    verify_vast_credentials_secret,
    verify_vast_external_service,
    verify_fresh_vast_test_event,
    verify_vast_metrics,
    verify_vast_vmscrape,
)
from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)


def _skip_if_vast_metrics_disabled(host):
    """Skip metric-path tests if VAST metrics are disabled."""
    if not is_source_enabled(host, "vast"):
        pytest.skip("VAST metrics not enabled in config")


def _skip_if_vast_logs_disabled(host):
    """Skip the log-path test if VAST logs are disabled."""
    if not is_logs_enabled(host, "vast"):
        pytest.skip("VAST logs not enabled in config")


def _format_metric_lines(metric_details):
    """Format metrics into lines with value and timestamp."""
    if not metric_details:
        return "  (no metrics found)"

    lines = []
    for m in metric_details:
        ts = m.get("timestamp", 0)
        try:
            ts_str = datetime.fromtimestamp(
                ts, tz=timezone.utc,
            ).strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, OSError):
            ts_str = str(ts)
        lines.append(
            f"  \u2713 {m['metric']} ({ts_str})"
        )
    return "\n".join(lines)


def _format_vast_event_lines(details):
    """Render bounded VAST RFC5424 event summaries for TestLogger."""
    lines = []
    for index, event in enumerate(details.get("event_summaries", []), start=1):
        lines.extend([
            f"    \u2713 Event {index}",
            f"        Timestamp : {event.get('timestamp_utc', '')}",
            f"        Hostname  : {event.get('hostname', '')}",
            f"        App name  : {event.get('app_name', '')}",
            f"        Process   : {event.get('process', '')}",
            f"        Severity  : {event.get('severity', '')}",
            f"        Facility  : {event.get('facility', '')}",
            f"        Format    : {event.get('format', '')}",
        ])
    remaining = details.get("remaining_events", 0)
    if remaining:
        lines.append(f"    ... {remaining} more event(s)")
    return lines


def _format_vast_log_details(result):
    """Render an OME-style VAST VictoriaLogs result."""
    details = result.get("details", {})
    source_hosts = ", ".join(details.get("source_hosts", [])) or "unavailable"
    lines = [
        f"VictoriaLogs : {result['vlselect_ip']}:{result['vlselect_port']}",
        "Application  : vast_event",
        f"Records found: {details.get('matched_events', 0)}",
        f"Source hosts : {source_hosts}",
        f"Trigger time : {details.get('trigger_time_utc', '')}",
        f"Query start  : {details.get('query_start_utc', '')}",
        f"Earliest     : {details.get('earliest_event_utc', '')}",
        f"Latest       : {details.get('latest_event_utc', '')}",
        f"Latest age   : {details.get('latest_event_age_seconds', 0):.1f}s",
        f"Poll attempt : {details.get('poll_attempt', '')}",
        "",
        "Event records:",
    ]
    if details.get("query_limit_reached"):
        lines.insert(3, "Query limit  : reached; displayed count may be partial")
    lines.extend(_format_vast_event_lines(details))
    return "\n".join(lines)


# =========================================================================
# TC_SR_088: Verify VAST external service exists with correct endpoint
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.vast
@pytest.mark.order(80)
def test_vast_external_service(host):
    """Verify VAST external service exists with correct endpoint."""
    _skip_if_vast_metrics_disabled(host)
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
# TC_SR_089: Verify VAST VMServiceScrape CR exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.vast
@pytest.mark.order(81)
def test_vast_vmscrape(host):
    """Verify VAST VMServiceScrape CR exists."""
    _skip_if_vast_metrics_disabled(host)
    tc = TC["vast_vmscrape"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking VAST VMServiceScrape CR")
    result = verify_vast_vmscrape(host)

    if result["success"]:
        detail = (
            f"port={result.get('port', '')}, "
            f"path={result.get('path', '')}, "
            f"expected_path={result.get('expected_path', '')}, "
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
# TC_SR_090: Verify VAST credentials K8s secret exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.vast
@pytest.mark.order(82)
def test_vast_credentials_secret(host):
    """Verify VAST credentials K8s secret exists."""
    _skip_if_vast_metrics_disabled(host)
    tc = TC["vast_credentials_secret"]
    tl = TestLogger(tc["title"], tc["id"])

    cfg_result = get_vast_endpoint_from_config(host)
    if not cfg_result["success"]:
        tl.failed("VAST endpoint is not configured", "")
        pytest.fail("VAST metrics are enabled but vast_endpoint is empty")
    if cfg_result["auth_mode"] != "basic":
        tl.skipped(
            f"VAST auth_mode is '{cfg_result['auth_mode']}'; secret not required"
        )
        pytest.skip("VAST credentials secret is required only for basic auth")

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
# TC_SR_091: Verify VAST storage metrics in VictoriaMetrics
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.vast
@pytest.mark.order(83)
def test_vast_metrics_in_vm(host):
    """Verify VAST storage metrics in VictoriaMetrics."""
    _skip_if_vast_metrics_disabled(host)
    tc = TC["vast_metrics_in_vm"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Querying VictoriaMetrics for VAST storage metrics")
    result = verify_vast_metrics(host)

    metric_lines = _format_metric_lines(result.get("metric_details", []))

    if result["success"]:
        details_lines = [
            f"VictoriaMetrics: {result['vmselect_ip']}:{result['vmselect_port']}",
            f"Healthy scrape targets: {result['healthy_targets']}",
            f"Samples per scrape: {result['scraped_samples']}",
            f"Attributed series: {result['series_count']}",
            f"Distinct VAST metrics: {result['metric_count']}",
            f"Latest sample: {result['latest_timestamp_utc']}",
            f"Latest sample age: {result['latest_age_seconds']:.1f}s",
            "Metric examples:",
            metric_lines,
        ]
        tl.passed(
            LOG_MSGS["vast_metrics_found"].format(
                count=result["metric_count"],
            ),
            "\n".join(details_lines),
        )
    else:
        details_lines = [
            f"VictoriaMetrics: {result.get('vmselect_ip', '')}:"
            f"{result.get('vmselect_port', '')}",
            f"Healthy scrape targets: {result.get('healthy_targets', 0)}",
            f"Samples per scrape: {result.get('scraped_samples', 0)}",
            f"Reason: {result.get('error', 'verification failed')}",
        ]
        tl.failed(
            LOG_MSGS["vast_metrics_missing"],
            "\n".join(details_lines),
        )

    assert result["success"], ASSERT_MSGS["vast_metrics_missing"].format(
        error=result.get("error", "verification failed"),
    )


# =========================================================================
# TC_SR_093: Configure VAST syslog and trigger a test event
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.vast
@pytest.mark.order(84)
def test_vast_syslog_configuration(host):
    """Configure VAST syslog and trigger a test notification."""
    _skip_if_vast_logs_disabled(host)

    tc = TC["vast_syslog_configuration"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Configuring VAST syslog and sending a test event")
    result = configure_vast_syslog_and_trigger(host)
    details = result.get("details", {})

    if result["success"]:
        output = [
            f"VAST endpoint: {details.get('vast_endpoint', '')}",
            f"VLAgent target: {details.get('syslog_target', '')} "
            f"({details.get('syslog_protocol', '')})",
            f"Configuration: {details.get('configuration', '')}; "
            f"readback HTTP {details.get('readback_http_status', '')}",
            f"Test event: HTTP {details.get('trigger_http_status', '')} at "
            f"{details.get('trigger_time_utc', '')}",
        ]
        tl.passed(LOG_MSGS["vast_syslog_configured"], "\n".join(output))
    else:
        tl.failed(
            LOG_MSGS["vast_syslog_configuration_failed"],
            result.get("error", "VAST syslog configuration failed"),
        )

    assert result["success"], ASSERT_MSGS[
        "vast_syslog_configuration_failed"
    ].format(error=result.get("error", "verification failed"))


# =========================================================================
# TC_SR_092: Verify the fresh VAST test event in VictoriaLogs
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.vast
@pytest.mark.order(85)
def test_vast_test_event_in_victoria_logs(host):
    """Verify the VAST test event from this run reached VictoriaLogs."""
    _skip_if_vast_logs_disabled(host)

    tc = TC["vast_test_event_in_victoria_logs"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Waiting for the triggered VAST event in VictoriaLogs")
    result = verify_fresh_vast_test_event(host)
    details = result.get("details", {})

    if result.get("skipped"):
        reason = details.get("reason", "No VAST test event was triggered")
        tl.skipped(reason)
        pytest.skip(reason)

    if result["success"]:
        tl.passed(
            LOG_MSGS["vast_logs_found"].format(count=result["count"]),
            _format_vast_log_details(result),
        )
    else:
        output = [
            f"VictoriaLogs: {result.get('vlselect_ip', '')}:"
            f"{result.get('vlselect_port', '')}",
            f"Triggered: {details.get('trigger_time_utc', '')}",
            f"Query start: {details.get('query_start_utc', '')}",
            f"Poll attempts: {details.get('poll_attempts', 0)}",
            f"Reason: {result.get('error', 'verification failed')}",
        ]
        tl.failed(
            LOG_MSGS["vast_logs_missing"],
            "\n".join(output),
        )

    assert result["success"], ASSERT_MSGS["vast_logs_missing"].format(
        error=result.get("error", "verification failed"),
    )
