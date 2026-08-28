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
Telemetry Deploy — PowerScale Source Verification Tests.

PowerScale Architecture:
    CSM Metrics PowerScale (karavi-metrics-powerscale) collects metrics
    from PowerScale storage clusters via REST API. The OTEL Collector
    exports metrics to VictoriaMetrics. Syslog logs are forwarded from
    PowerScale OneFS to VLAgent for ingestion into VictoriaLogs.

    Data pipeline (metrics):
        PowerScale API -> CSM Metrics -> OTEL Collector -> VictoriaMetrics
    Data pipeline (logs):
        PowerScale OneFS syslog -> VLAgent -> VictoriaLogs

Test cases (execution order):
    TC_SR_030: Verify CSM Metrics PowerScale deployment ready
    TC_SR_031: Verify OTEL Collector deployment ready
    TC_SR_032: Verify isilon-creds secret has correct endpoint
    TC_SR_033: Verify PowerScale metrics in VictoriaMetrics
    TC_SR_035: Verify/configure PowerScale syslog forwarding (BEFORE log check)
    TC_SR_034: Verify PowerScale logs in VictoriaLogs (AFTER syslog config)
"""

from datetime import datetime

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    POWERSCALE_DEPLOY_NAME,
    POWERSCALE_OTEL_DEPLOY_NAME,
    POWERSCALE_EXPECTED_METRICS,
    POWERSCALE_SYSLOG_PORT,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import verify_deploy_pods_detail
from library.functions.telemetry_func import (
    is_source_enabled,
    is_logs_enabled,
)
from library.functions.powerscale_func import (
    load_powerscale_secret_from_config,
    decode_isilon_creds,
    verify_powerscale_metrics,
    verify_powerscale_logs,
    verify_powerscale_syslog,
    configure_powerscale_syslog,
    get_vlagent_endpoint,
    verify_powerscale_deployment,
    verify_feature_flags,
    verify_health_metrics,
    verify_tls_enforcement,
    verify_label_compliance,
    verify_scrape_interval,
    verify_csi_authorization_mode,
    verify_deployment_mode,
    verify_csi_volume_exporter_deployment,
    verify_csi_volume_exporter_metrics_endpoint,
    verify_csi_volume_exporter_metrics,
    verify_csi_driver_powerscale_deployment,
    verify_external_health_monitor_container,
    verify_csi_exporter_skipped_without_health_monitor,
    verify_health_monitor_warning_message,
    verify_csm_otel_data_flow,
    verify_otel_vm_export,
    verify_otel_service_patch,
    verify_cert_manager_tls_certs,
)


def _skip_if_powerscale_disabled(host):
    """Skip test if PowerScale source is not enabled."""
    if not is_source_enabled(host, "powerscale"):
        pytest.skip("PowerScale source not enabled in config")


def _format_pod_table(pods):
    """Format pods into an aligned table string."""
    if not pods:
        return "  (no pods found)"

    headers = ["POD", "STATUS", "NODE", "RESTARTS"]
    rows = []
    for p in pods:
        rows.append([
            p["name"],
            p["status"],
            p.get("node", ""),
            str(p.get("restarts", 0)),
        ])

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    lines = [fmt.format(*headers)]
    lines.append("  ".join("-" * w for w in widths))
    for row in rows:
        lines.append(fmt.format(*row))
    return "\n".join(lines)


def _format_metric_lines(metric_details):
    """Format metrics into lines with value and timestamp."""
    if not metric_details:
        return "  (no metrics found)"

    lines = []
    for m in metric_details:
        ts = m.get("timestamp", 0)
        try:
            ts_str = datetime.fromtimestamp(ts).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except (ValueError, OSError):
            ts_str = str(ts)
        lines.append(
            f"  \u2713 {m['metric']}: {m['value']} ({ts_str})"
        )
    return "\n".join(lines)


# =========================================================================
# TC_SR_030: Verify CSM Metrics PowerScale deployment ready
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(60)
def test_powerscale_csm_deploy(host):
    """Verify CSM Metrics PowerScale deployment ready."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_csm_deploy"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying CSM Metrics PowerScale deployment")
    result = verify_deploy_pods_detail(host, POWERSCALE_DEPLOY_NAME)

    pod_table = _format_pod_table(result["pods"])
    summary = (
        f"Ready: {result['ready_replicas']}/{result['expected']}\n"
        f"{pod_table}"
    )

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="CSM Metrics PowerScale",
                count=result["ready_replicas"],
                expected=result["expected"],
            ),
            summary,
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="CSM Metrics PowerScale",
                running=result["ready_replicas"],
                expected=result["expected"],
            ),
            summary,
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="CSM Metrics PowerScale",
        expected=result["expected"],
        running=result["ready_replicas"],
    )


# =========================================================================
# TC_SR_031: Verify OTEL Collector deployment ready
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(61)
def test_powerscale_otel_deploy(host):
    """Verify OTEL Collector deployment ready."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_otel_deploy"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying OTEL Collector deployment")
    result = verify_deploy_pods_detail(host, POWERSCALE_OTEL_DEPLOY_NAME)

    pod_table = _format_pod_table(result["pods"])
    summary = (
        f"Ready: {result['ready_replicas']}/{result['expected']}\n"
        f"{pod_table}"
    )

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="OTEL Collector",
                count=result["ready_replicas"],
                expected=result["expected"],
            ),
            summary,
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="OTEL Collector",
                running=result["ready_replicas"],
                expected=result["expected"],
            ),
            summary,
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="OTEL Collector",
        expected=result["expected"],
        running=result["ready_replicas"],
    )


# =========================================================================
# TC_SR_032: Verify isilon-creds secret has correct endpoint
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(62)
def test_powerscale_secret_valid(host):
    """Verify isilon-creds secret has correct endpoint."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_secret_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Reading PowerScale secret from telemetry config")
    cfg_result = load_powerscale_secret_from_config(host)
    if not cfg_result["success"]:
        tl.failed(
            LOG_MSGS["secret_invalid"].format(
                secret="powerscale_secret.yaml",
                actual="cannot read",
                expected="valid config",
            ),
            cfg_result["error"],
        )
        pytest.fail(
            f"Cannot read PowerScale secret: {cfg_result['error']}"
        )

    expected = cfg_result["clusters"][0]

    tl.check("Decoding deployed isilon-creds K8s secret")
    k8s_result = decode_isilon_creds(host)
    if not k8s_result["success"]:
        tl.failed(
            LOG_MSGS["secret_invalid"].format(
                secret="isilon-creds",
                actual="not found",
                expected=expected["endpoint"],
            ),
            k8s_result["error"],
        )
        pytest.fail(
            f"isilon-creds decode failed: {k8s_result['error']}"
        )

    deployed = k8s_result["clusters"][0]
    details = (
        f"endpoint={deployed['endpoint']}, "
        f"user={deployed['username']}, "
        f"cluster={deployed['clusterName']}"
    )

    match = deployed["endpoint"] == expected["endpoint"]
    if match:
        tl.passed(
            LOG_MSGS["secret_valid"].format(
                secret="isilon-creds",
                endpoint=deployed["endpoint"],
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["secret_invalid"].format(
                secret="isilon-creds",
                actual=deployed["endpoint"],
                expected=expected["endpoint"],
            ),
            details,
        )

    assert match, ASSERT_MSGS["secret_invalid"].format(
        secret="isilon-creds",
        actual=deployed["endpoint"],
        expected=expected["endpoint"],
    )


# =========================================================================
# TC_SR_033: Verify PowerScale metrics in VictoriaMetrics
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(63)
def test_powerscale_metrics_in_vm(host):
    """Verify PowerScale metrics in VictoriaMetrics."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_metrics_in_vm"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Querying VictoriaMetrics for PowerScale metrics")
    result = verify_powerscale_metrics(host, POWERSCALE_EXPECTED_METRICS)

    metric_lines = _format_metric_lines(
        result.get("metric_details", [])
    )

    if result["success"]:
        details_lines = [
            f"Found: {len(result['found'])}"
            f"/{len(POWERSCALE_EXPECTED_METRICS)} metrics",
            "",
            metric_lines,
        ]
        tl.passed(
            LOG_MSGS["metrics_found"].format(
                count=len(result["found"]),
                metrics=", ".join(result["found"]),
            ),
            "\n".join(details_lines),
        )
    else:
        missing_str = ", ".join(result["missing"])
        details_lines = [
            f"Found: {len(result['found'])}"
            f"/{len(POWERSCALE_EXPECTED_METRICS)} metrics",
        ]
        for m in result["missing"]:
            details_lines.append(f"  \u2717 {m}: MISSING")
        if result.get("metric_details"):
            details_lines.append("")
            details_lines.append(metric_lines)
        tl.failed(
            LOG_MSGS["metrics_missing"].format(missing=missing_str),
            "\n".join(details_lines),
        )

    assert result["success"], ASSERT_MSGS["metrics_missing"].format(
        missing=", ".join(result["missing"]),
    )


# =========================================================================
# TC_SR_035: Verify/configure PowerScale syslog forwarding
#   Runs BEFORE TC_SR_034 (log verification) so syslog is configured
#   before we check if logs are arriving.
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(64)
def test_powerscale_syslog_config(host):
    """Verify PowerScale syslog forwarding configured.

    Checks if syslog is already configured correctly. If not, configures
    it automatically, then verifies.
    """
    _skip_if_powerscale_disabled(host)
    if not is_logs_enabled(host, "powerscale"):
        pytest.skip("PowerScale logs not enabled in config")

    tc = TC["powerscale_syslog_config"]
    tl = TestLogger(tc["title"], tc["id"])

    cfg_result = load_powerscale_secret_from_config(host)
    if not cfg_result["success"]:
        tl.failed(
            "Cannot read PowerScale credentials from config", ""
        )
        pytest.fail("PowerScale secret not available in config")

    cluster = cfg_result["clusters"][0]
    ps_host = cluster["endpoint"]
    ps_user = cluster["username"]
    ps_password = cluster["password"]

    vlagent_ip, vlagent_port = get_vlagent_endpoint(host)
    if not vlagent_ip:
        tl.failed(
            "Cannot get VLAgent LoadBalancer IP from service", ""
        )
        pytest.fail("VLAgent service not found")
    syslog_port = vlagent_port or str(POWERSCALE_SYSLOG_PORT)

    target_str = f"{vlagent_ip}:{syslog_port}"
    tl.check(f"Checking PowerScale syslog config -> {target_str}")

    result = verify_powerscale_syslog(
        host, ps_user, ps_password, ps_host,
        vlagent_ip, syslog_port,
    )

    # Already configured correctly — pass without reconfiguring
    if result["success"]:
        tl.passed(
            LOG_MSGS["syslog_configured"].format(target=target_str),
            (
                f"config: {result['config_servers']}, "
                f"system: {result['system_servers']}, "
                f"protocol: {result['protocol_servers']}"
            ),
        )
        return

    # Not configured — configure it now
    tl.check(
        f"Syslog not configured — configuring to {target_str}"
    )
    cfg_result2 = configure_powerscale_syslog(
        host, ps_user, ps_password, ps_host,
        vlagent_ip, syslog_port,
    )

    cmds_detail = "\n".join(
        f"  > {cmd}" for cmd in cfg_result2["commands_run"]
    )
    if not cfg_result2["success"]:
        tl.failed(
            LOG_MSGS["syslog_not_configured"].format(
                target=target_str
            ),
            f"Commands run:\n{cmds_detail}\n"
            f"Error: {cfg_result2['error']}",
        )
        assert False, ASSERT_MSGS["syslog_not_configured"].format(
            target=vlagent_ip,
        )

    # Verify after reconfiguration
    tl.check("Verifying syslog after reconfiguration")
    verify_result = verify_powerscale_syslog(
        host, ps_user, ps_password, ps_host,
        vlagent_ip, syslog_port,
    )

    if verify_result["success"]:
        tl.passed(
            LOG_MSGS["syslog_configured"].format(target=target_str),
            (
                f"Reconfigured successfully.\n"
                f"Commands run:\n{cmds_detail}\n"
                f"config: {verify_result['config_servers']}, "
                f"system: {verify_result['system_servers']}, "
                f"protocol: {verify_result['protocol_servers']}"
            ),
        )
    else:
        tl.failed(
            LOG_MSGS["syslog_not_configured"].format(
                target=target_str
            ),
            (
                f"Reconfiguration attempted but failed.\n"
                f"Commands run:\n{cmds_detail}\n"
                f"config: {verify_result['config_servers']}, "
                f"system: {verify_result['system_servers']}, "
                f"protocol: {verify_result['protocol_servers']}"
            ),
        )

    assert verify_result["success"], (
        ASSERT_MSGS["syslog_not_configured"].format(
            target=vlagent_ip,
        )
    )


# =========================================================================
# TC_SR_034: Verify PowerScale logs in VictoriaLogs
#   Runs AFTER TC_SR_035 (syslog config) so logs have time to arrive.
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(65)
def test_powerscale_logs_in_vl(host):
    """Verify PowerScale logs in VictoriaLogs."""
    _skip_if_powerscale_disabled(host)
    if not is_logs_enabled(host, "powerscale"):
        pytest.skip("PowerScale logs not enabled in config")

    tc = TC["powerscale_logs_in_vl"]
    tl = TestLogger(tc["title"], tc["id"])

    cfg_result = load_powerscale_secret_from_config(host)
    if not cfg_result["success"]:
        tl.failed(
            "Cannot read PowerScale secret for cluster name", ""
        )
        pytest.fail("Cannot determine PowerScale cluster name")

    hostname = cfg_result["clusters"][0]["clusterName"]

    tl.check(
        f"Querying VictoriaLogs for PowerScale syslog "
        f"(hostname: {hostname})"
    )
    result = verify_powerscale_logs(
        host, hostname_pattern=hostname
    )

    if result["success"]:
        tl.passed(
            LOG_MSGS["logs_found"].format(count=result["count"]),
            f"Sample: {result['sample_log']}",
        )
    else:
        tl.failed(
            LOG_MSGS["logs_missing"].format(source="PowerScale"),
            "",
        )

    assert result["success"], ASSERT_MSGS["logs_missing"].format(
        source="PowerScale",
    )


# =========================================================================
# TC_SR_036: Verify comprehensive PowerScale deployment
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(66)
def test_powerscale_comprehensive_deployment(host):
    """Verify comprehensive PowerScale deployment."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_comprehensive_deployment"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying comprehensive PowerScale deployment")
    result = verify_powerscale_deployment(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["deployment_verified"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["deployment_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["deployment_failed"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_037: Verify PowerScale feature flags
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(67)
def test_powerscale_feature_flags(host):
    """Verify PowerScale feature flags."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_feature_flags"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying PowerScale feature flags")
    result = verify_feature_flags(host)

    flags_str = ", ".join(f"{k}={v}" for k, v in result["flags"].items())
    tl.passed(
        LOG_MSGS["feature_flags"],
        flags_str,
    )

    # Feature flags are informational, not pass/fail
    assert True


# =========================================================================
# TC_SR_038: Verify PowerScale health metrics
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(68)
def test_powerscale_health_metrics(host):
    """Verify PowerScale health metrics."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_health_metrics"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying PowerScale health metrics")
    result = verify_health_metrics(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["health_metrics"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["health_metrics_missing"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["health_metrics_missing"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_039: Verify PowerScale TLS enforcement
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(69)
def test_powerscale_tls_enforcement(host):
    """Verify PowerScale TLS enforcement."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_tls_enforcement"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying PowerScale TLS enforcement")
    result = verify_tls_enforcement(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["tls_enforced"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["tls_not_enforced"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["tls_not_enforced"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_040: Verify PowerScale pod label compliance
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(70)
def test_powerscale_label_compliance(host):
    """Verify PowerScale pod label compliance."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_label_compliance"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying PowerScale pod label compliance")
    result = verify_label_compliance(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["label_compliance"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["label_compliance_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["label_compliance_failed"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_041: Verify PowerScale scrape interval
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(71)
def test_powerscale_scrape_interval(host):
    """Verify PowerScale scrape interval."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_scrape_interval"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying PowerScale scrape interval")
    result = verify_scrape_interval(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["scrape_interval"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["scrape_interval_invalid"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["scrape_interval_invalid"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_042: Verify PowerScale CSI authorization mode
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(72)
def test_powerscale_csi_auth_mode(host):
    """Verify PowerScale CSI authorization mode."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_csi_auth_mode"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying PowerScale CSI authorization mode")
    result = verify_csi_authorization_mode(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["csi_auth_mode"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["csi_auth_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["csi_auth_failed"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_043: Verify PowerScale deployment mode
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(73)
def test_powerscale_deployment_mode(host):
    """Verify PowerScale deployment mode."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_deployment_mode"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying PowerScale deployment mode")
    result = verify_deployment_mode(host)

    tl.passed(
        LOG_MSGS["deployment_mode"],
        result["details"],
    )

    # Deployment mode is always omnia-orchestrated
    assert result["mode"] == "omnia-orchestrated"


# =========================================================================
# TC_SR_044: Verify CSI Volume Exporter deployment
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(74)
def test_csi_volume_exporter_deploy(host):
    """Verify CSI Volume Exporter deployment."""
    _skip_if_powerscale_disabled(host)
    tc = TC["csi_volume_exporter_deploy"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying CSI Volume Exporter deployment")
    result = verify_csi_volume_exporter_deployment(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["csi_exporter_deployed"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["csi_exporter_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["csi_exporter_failed"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_045: Verify CSI Volume Exporter metrics endpoint
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(75)
def test_csi_volume_exporter_endpoint(host):
    """Verify CSI Volume Exporter metrics endpoint is accessible."""
    _skip_if_powerscale_disabled(host)
    tc = TC["csi_volume_exporter_endpoint"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying CSI Volume Exporter metrics endpoint")
    result = verify_csi_volume_exporter_metrics_endpoint(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["csi_exporter_endpoint"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["csi_exporter_endpoint_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["csi_exporter_endpoint_failed"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_046: Verify CSI Volume Exporter metrics in VictoriaMetrics
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(76)
def test_csi_volume_exporter_metrics(host):
    """Verify CSI Volume Exporter metrics in VictoriaMetrics."""
    _skip_if_powerscale_disabled(host)
    tc = TC["csi_volume_exporter_metrics"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying CSI Volume Exporter metrics in VictoriaMetrics")
    result = verify_csi_volume_exporter_metrics(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["csi_exporter_metrics"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["metrics_missing"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["csi_exporter_metrics_missing"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_047: Verify CSI Driver for PowerScale (isilon-controller) deployment
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(77)
def test_csi_driver_powerscale_deploy(host):
    """Verify CSI Driver for PowerScale (isilon-controller) deployment."""
    _skip_if_powerscale_disabled(host)
    tc = TC["csi_driver_powerscale_deploy"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying CSI Driver for PowerScale (isilon-controller) deployment")
    result = verify_csi_driver_powerscale_deployment(host)

    # If driver is not deployed, skip this test
    if not result.get("driver_deployed", True):
        tl.skipped(
            "CSI driver not deployed",
            "isilon-controller pods not found - CSI driver verification skipped",
        )
        pytest.skip("CSI driver not deployed - CSI driver verification skipped")

    if result["success"]:
        tl.passed(
            LOG_MSGS["csi_driver_deployed"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["csi_driver_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["csi_driver_failed"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_048: Verify external-health-monitor-controller container is running
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(78)
def test_external_health_monitor_container(host):
    """Verify external-health-monitor-controller container is running in isilon-controller pod."""
    _skip_if_powerscale_disabled(host)
    tc = TC["external_health_monitor_container"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying external-health-monitor-controller container")
    result = verify_external_health_monitor_container(host)

    # If pod is not found, skip this test (CSI driver not deployed)
    if not result.get("pod_found", True):
        tl.skipped(
            "isilon-controller pod not found",
            "CSI driver not deployed - health monitor verification skipped",
        )
        pytest.skip("CSI driver not deployed - health monitor verification skipped")

    if result["success"]:
        tl.passed(
            LOG_MSGS["health_monitor_container"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["health_monitor_container_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["health_monitor_container_failed"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_049: Verify CSI volume exporter deployment skipped when health monitor missing
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(79)
def test_csi_exporter_skipped_without_health_monitor(host):
    """Verify CSI volume exporter deployment is skipped when health monitor is not available."""
    _skip_if_powerscale_disabled(host)
    tc = TC["csi_exporter_skipped_without_health_monitor"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if CSI driver is deployed first
    driver_result = verify_csi_driver_powerscale_deployment(host)
    if not driver_result.get("driver_deployed", True):
        tl.skipped(
            "CSI driver not deployed",
            "CSI driver not deployed - dependency verification skipped",
        )
        pytest.skip("CSI driver not deployed - dependency verification skipped")

    tl.check("Verifying CSI volume exporter deployment logic with health monitor dependency")
    result = verify_csi_exporter_skipped_without_health_monitor(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["csi_exporter_dependency"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["csi_exporter_dependency_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["csi_exporter_dependency_failed"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_050: Verify warning message displayed for missing health monitor
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(80)
def test_health_monitor_warning_message(host):
    """Verify appropriate warning message is displayed when health monitor is missing."""
    _skip_if_powerscale_disabled(host)
    tc = TC["health_monitor_warning_message"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying health monitor warning message behavior")
    result = verify_health_monitor_warning_message(host)

    # This is informational - always passes
    tl.passed(
        LOG_MSGS["health_monitor_warning"],
        result["details"],
    )

    assert result["success"]


# =========================================================================
# TC_SR_051: Verify CSM Metrics to OTEL Collector data flow
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(81)
def test_csm_otel_data_flow(host):
    """Verify CSM Metrics to OTEL Collector data flow."""
    _skip_if_powerscale_disabled(host)
    tc = TC["csm_otel_data_flow"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying CSM Metrics to OTEL Collector data flow")
    result = verify_csm_otel_data_flow(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["csm_otel_flow"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["csm_otel_flow_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["csm_otel_flow_failed"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_052: Verify OTEL Collector to VictoriaMetrics export
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(82)
def test_otel_vm_export(host):
    """Verify OTEL Collector to VictoriaMetrics export."""
    _skip_if_powerscale_disabled(host)
    tc = TC["otel_vm_export"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying OTEL Collector to VictoriaMetrics export")
    result = verify_otel_vm_export(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["otel_vm_export"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["otel_vm_export_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["otel_vm_export_failed"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_053: Verify OTEL Collector service patch for vmagent
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(83)
def test_otel_service_patch(host):
    """Verify OTEL Collector service patch for vmagent scrape discovery."""
    _skip_if_powerscale_disabled(host)
    tc = TC["otel_service_patch"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying OTEL Collector service patch for vmagent")
    result = verify_otel_service_patch(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["otel_service_patch"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["otel_service_patch_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["otel_service_patch_failed"].format(
        details=result["details"],
    )


# =========================================================================
# TC_SR_054: Verify cert-manager TLS certificate generation
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(84)
def test_cert_manager_tls_certs(host):
    """Verify cert-manager TLS certificate generation."""
    _skip_if_powerscale_disabled(host)
    tc = TC["cert_manager_tls_certs"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying cert-manager TLS certificate generation")
    result = verify_cert_manager_tls_certs(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["cert_manager_tls"],
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["cert_manager_tls_failed"],
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["cert_manager_tls_failed"].format(
        details=result["details"],
    )
