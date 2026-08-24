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

Test cases:
    TC_SR_030: Verify CSM Metrics PowerScale deployment ready
    TC_SR_031: Verify OTEL Collector deployment ready
    TC_SR_032: Verify isilon-creds secret has correct endpoint
    TC_SR_033: Verify PowerScale metrics in VictoriaMetrics
    TC_SR_034: Verify PowerScale logs in VictoriaLogs
    TC_SR_035: Verify PowerScale syslog forwarding configured
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
            ts_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
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
    """TC_SR_030: Verify CSM Metrics PowerScale deployment ready."""
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
    """TC_SR_031: Verify OTEL Collector deployment ready."""
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
    """TC_SR_032: Verify isilon-creds secret has correct endpoint."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_secret_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    # Read expected values from config-referenced secret file
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
        pytest.fail(f"Cannot read PowerScale secret file: {cfg_result['error']}")

    expected = cfg_result["clusters"][0]

    # Read deployed K8s secret
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
        pytest.fail(f"isilon-creds K8s secret decode failed: {k8s_result['error']}")

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
    """TC_SR_033: Verify PowerScale metrics in VictoriaMetrics."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_metrics_in_vm"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Querying VictoriaMetrics for PowerScale metrics")
    result = verify_powerscale_metrics(host, POWERSCALE_EXPECTED_METRICS)

    metric_lines = _format_metric_lines(result.get("metric_details", []))

    if result["success"]:
        details_lines = [
            f"Found: {len(result['found'])}/{len(POWERSCALE_EXPECTED_METRICS)} metrics",
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
            f"Found: {len(result['found'])}/{len(POWERSCALE_EXPECTED_METRICS)} metrics",
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
# TC_SR_034: Verify PowerScale logs in VictoriaLogs
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(64)
def test_powerscale_logs_in_vl(host):
    """TC_SR_034: Verify PowerScale logs in VictoriaLogs."""
    _skip_if_powerscale_disabled(host)
    if not is_logs_enabled(host, "powerscale"):
        pytest.skip("PowerScale logs not enabled in config")

    tc = TC["powerscale_logs_in_vl"]
    tl = TestLogger(tc["title"], tc["id"])

    cfg_result = load_powerscale_secret_from_config(host)
    if not cfg_result["success"]:
        tl.failed("Cannot read PowerScale secret for cluster name", "")
        pytest.fail("Cannot determine PowerScale cluster name")

    hostname = cfg_result["clusters"][0]["clusterName"]

    tl.check(f"Querying VictoriaLogs for PowerScale syslog (hostname: {hostname})")
    result = verify_powerscale_logs(host, hostname_pattern=hostname)

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
# TC_SR_035: Verify PowerScale syslog forwarding configured
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(65)
def test_powerscale_syslog_config(host):
    """TC_SR_035: Verify PowerScale syslog forwarding configured.

    If syslog is not correctly configured, this test will reconfigure
    it automatically and report the commands executed.
    """
    _skip_if_powerscale_disabled(host)
    if not is_logs_enabled(host, "powerscale"):
        pytest.skip("PowerScale logs not enabled in config")

    tc = TC["powerscale_syslog_config"]
    tl = TestLogger(tc["title"], tc["id"])

    cfg_result = load_powerscale_secret_from_config(host)
    if not cfg_result["success"]:
        tl.failed("Cannot read PowerScale credentials from config", "")
        pytest.fail("PowerScale secret not available in config")

    cluster = cfg_result["clusters"][0]
    ps_host = cluster["endpoint"]
    ps_user = cluster["username"]
    ps_password = cluster["password"]

    # Get VLAgent service IP and port dynamically
    vlagent_ip, vlagent_port = get_vlagent_endpoint(host)
    if not vlagent_ip:
        tl.failed("Cannot get VLAgent LoadBalancer IP from service", "")
        pytest.fail("VLAgent service not found")
    syslog_port = vlagent_port or str(POWERSCALE_SYSLOG_PORT)

    target_str = f"{vlagent_ip}:{syslog_port}"
    tl.check(f"Checking PowerScale syslog config -> {target_str}")

    result = verify_powerscale_syslog(
        host, ps_user, ps_password, ps_host,
        vlagent_ip, syslog_port,
    )

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

    # Syslog not configured correctly — reconfigure it
    tl.check(f"Syslog misconfigured — reconfiguring to {target_str}")
    cfg_result2 = configure_powerscale_syslog(
        host, ps_user, ps_password, ps_host,
        vlagent_ip, syslog_port,
    )

    cmds_detail = "\n".join(
        f"  > {cmd}" for cmd in cfg_result2["commands_run"]
    )
    if not cfg_result2["success"]:
        tl.failed(
            LOG_MSGS["syslog_not_configured"].format(target=target_str),
            f"Commands run:\n{cmds_detail}\nError: {cfg_result2['error']}",
        )
        assert False, ASSERT_MSGS["syslog_not_configured"].format(
            target=vlagent_ip,
        )

    # Verify again after reconfiguration
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
            LOG_MSGS["syslog_not_configured"].format(target=target_str),
            (
                f"Reconfiguration attempted but verification failed.\n"
                f"Commands run:\n{cmds_detail}\n"
                f"config: {verify_result['config_servers']}, "
                f"system: {verify_result['system_servers']}, "
                f"protocol: {verify_result['protocol_servers']}"
            ),
        )

    assert verify_result["success"], ASSERT_MSGS["syslog_not_configured"].format(
        target=vlagent_ip,
    )
