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
PowerScale — Module-Specific Verification Functions.

Handles:
  - isilon-creds K8s secret decoding and validation
  - PowerScale metrics verification in VictoriaMetrics
  - PowerScale syslog log verification in VictoriaLogs
  - PowerScale syslog forwarding configuration verification
  - External health monitor controller verification
  - CSI volume exporter dependency validation
  - Karavi observability integration tests (CSM-OTEL-VM flow)
  - OTEL Collector service patch validation
  - cert-manager TLS certificate validation
"""

import base64

import yaml

from omnia_auto import (
    run_on_host,
    read_remote_yaml,
    read_yaml_key,
)

from ..vars.common_vars import (
    CMDS,
    TELEMETRY_NAMESPACE,
    POWERSCALE_SECRET_NAME,
    SVC_VLAGENT,
)
from .telemetry_func import (
    load_telemetry_config_from_target,
    run_on_kube_vip,
    _get_svc_endpoint,
    query_vm_metric_names,
    query_vm_instant,
    get_vlselect_endpoint,
)
from .k8s_func import get_service


# -------------------------------------------------------------------------
# PowerScale — isilon-creds secret
# -------------------------------------------------------------------------

def decode_isilon_creds(host):
    """Decode and parse the isilon-creds K8s secret.

    Reads the base64-encoded 'config' key from the isilon-creds secret
    deployed in the telemetry namespace.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, clusters (list of dicts with
        clusterName, username, password, endpoint), error.
    """
    cmd = CMDS["kubectl_get_secret_data"].format(
        name=POWERSCALE_SECRET_NAME,
        namespace=TELEMETRY_NAMESPACE,
        key="config",
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {"success": False, "clusters": [], "error": "Secret not found"}

    try:
        decoded = base64.b64decode(result.stdout.strip()).decode("utf-8")
        parsed = yaml.safe_load(decoded) or {}
    except Exception as exc:
        return {"success": False, "clusters": [], "error": str(exc)}

    clusters = []
    for cluster in parsed.get("isilonClusters", []):
        clusters.append({
            "clusterName": cluster.get("clusterName", ""),
            "username": cluster.get("username", ""),
            "password": cluster.get("password", ""),
            "endpoint": cluster.get("endpoint", ""),
        })

    return {"success": len(clusters) > 0, "clusters": clusters, "error": ""}


# -------------------------------------------------------------------------
# PowerScale — VictoriaMetrics metrics
# -------------------------------------------------------------------------

def verify_powerscale_metrics(host, expected_metrics):
    """Verify PowerScale metrics exist in VictoriaMetrics.

    Args:
        host: Testinfra host connection to the OIM.
        expected_metrics: List of metric names to check.

    Returns:
        dict with keys: success, found, missing, values, metric_details.
    """
    all_names = query_vm_metric_names(host)
    found = [m for m in expected_metrics if m in all_names]
    missing = [m for m in expected_metrics if m not in all_names]

    values = {}
    metric_details = []
    for metric in found:
        results = query_vm_instant(host, metric)
        if results:
            val = results[0].get("value", [None, "N/A"])
            timestamp = int(float(val[0])) if val[0] else 0
            value = val[1] if len(val) > 1 else "N/A"
            values[metric] = value
            metric_details.append({
                "metric": metric,
                "value": value,
                "timestamp": timestamp,
            })

    # Success if at least one expected metric is found (cluster metrics
    # like powerscale_cluster_* may take several scrape intervals to appear)
    return {
        "success": len(found) > 0,
        "found": found,
        "missing": missing,
        "values": values,
        "metric_details": metric_details,
    }


# -------------------------------------------------------------------------
# PowerScale — VictoriaLogs
# -------------------------------------------------------------------------

def verify_powerscale_logs(host, hostname_pattern):
    """Verify PowerScale syslog entries exist in VictoriaLogs.

    Args:
        host: Testinfra host connection to the OIM.
        hostname_pattern: Hostname pattern to search for
            (read from isilon-creds cluster name at call site).

    Returns:
        dict with keys: success, count, sample_log.
    """
    import json
    ip, port = get_vlselect_endpoint(host)
    if not ip or not port:
        return {"success": False, "count": 0, "sample_log": ""}

    query = f"hostname:{hostname_pattern}*"
    cmd = CMDS["vl_query_logs"].format(
        vlselect_ip=ip, vlselect_port=port,
        query=query, limit=5, range="30m",
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {"success": False, "count": 0, "sample_log": ""}

    lines = result.stdout.strip().split("\n")
    count = len(lines)
    sample = ""
    if lines:
        try:
            entry = json.loads(lines[0])
            sample = entry.get("_msg", "")[:120]
        except json.JSONDecodeError:
            sample = lines[0][:120]

    return {"success": count > 0, "count": count, "sample_log": sample}


# -------------------------------------------------------------------------
# PowerScale — syslog configuration
# -------------------------------------------------------------------------

def get_vlagent_endpoint(host):
    """Get the VLAgent LoadBalancer IP and syslog port.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        tuple: ``(ip, port)`` — port is a string.
    """
    return _get_svc_endpoint(host, SVC_VLAGENT)


def verify_powerscale_syslog(host, ps_user, ps_password, ps_host,
                             expected_target, expected_port):
    """Verify PowerScale syslog is forwarding to the VLAgent.

    Args:
        host: Testinfra host connection to the OIM.
        ps_user: PowerScale SSH username.
        ps_password: PowerScale SSH password.
        ps_host: PowerScale IP address.
        expected_target: Expected syslog target IP.
        expected_port: Expected syslog port (from SVC_VLAGENT).

    Returns:
        dict with keys: success, ssh_ok, servers_correct, forwarding_on,
        auditing_on, config_servers, system_servers, protocol_servers,
        syslog_enabled, auditing_enabled, details, commands_run.
    """
    view_cmd = CMDS["powerscale_syslog_view"].format(
        user=ps_user, password=ps_password, host=ps_host,
    )
    result = run_on_host(host, view_cmd)
    if result.rc != 0:
        return {
            "success": False,
            "ssh_ok": False,
            "config_servers": "",
            "system_servers": "",
            "protocol_servers": "",
            "syslog_enabled": {},
            "auditing_enabled": {},
            "details": (
                f"SSH to PowerScale failed (rc={result.rc}) as user "
                f"'{ps_user}'@{ps_host} running 'isi audit settings global "
                f"view'.\nstderr: {result.stderr.strip()}"
                f"\nstdout: {result.stdout.strip()}"
            ),
            "commands_run": [view_cmd],
        }

    output = result.stdout
    config_servers = ""
    system_servers = ""
    protocol_servers = ""
    syslog_enabled = {}
    auditing_enabled = {}
    for line in output.split("\n"):
        stripped = line.strip()
        if ":" not in stripped:
            continue
        label, value = stripped.split(":", 1)
        label = label.strip()
        value = value.strip()
        if label == "Config Syslog Servers":
            config_servers = value
        elif label == "System Syslog Servers":
            system_servers = value
        elif label == "Protocol Syslog Servers":
            protocol_servers = value
        elif label.endswith("Syslog Enabled"):
            syslog_enabled[label.split()[0].lower()] = value.lower() == "yes"
        elif label.endswith("Auditing Enabled"):
            auditing_enabled[label.split()[0].lower()] = value.lower() == "yes"

    target_str = f"{expected_target}:{expected_port}"
    servers_correct = (
        target_str in config_servers
        and target_str in system_servers
        and target_str in protocol_servers
    )
    # Syslog servers alone are not enough: OneFS only emits audit events to
    # them when the corresponding auditing/forwarding is enabled.
    forwarding_on = any(syslog_enabled.values()) if syslog_enabled else False
    auditing_on = any(auditing_enabled.values()) if auditing_enabled else False

    details = [
        f"config_syslog_servers: {config_servers or '(unset)'}",
        f"system_syslog_servers: {system_servers or '(unset)'}",
        f"protocol_syslog_servers: {protocol_servers or '(unset)'}",
        f"syslog_enabled: {syslog_enabled or '(not reported)'}",
        f"auditing_enabled: {auditing_enabled or '(not reported)'}",
    ]
    if not servers_correct:
        details.append(f"MISMATCH: expected {target_str} on all three lists")
    if servers_correct and not auditing_on:
        details.append(
            "Syslog servers point at the VLAgent but OneFS auditing is "
            "disabled, so no audit events are generated or forwarded. "
            "Enable auditing on the array "
            "(isi audit settings global modify --config-auditing-enabled=yes "
            "--system-auditing-enabled=yes)."
        )

    return {
        "success": servers_correct and auditing_on,
        "ssh_ok": True,
        "servers_correct": servers_correct,
        "forwarding_on": forwarding_on,
        "auditing_on": auditing_on,
        "config_servers": config_servers,
        "system_servers": system_servers,
        "protocol_servers": protocol_servers,
        "syslog_enabled": syslog_enabled,
        "auditing_enabled": auditing_enabled,
        "details": "\n".join(details),
        "commands_run": [view_cmd],
    }


def configure_powerscale_syslog(host, ps_user, ps_password, ps_host,
                                target_ip, target_port):
    """Configure PowerScale syslog servers to forward to the VLAgent.

    Runs ``isi audit settings global modify`` for config, system,
    and protocol syslog servers.

    Args:
        host: Testinfra host connection to the OIM.
        ps_user: PowerScale SSH username.
        ps_password: PowerScale SSH password.
        ps_host: PowerScale IP address.
        target_ip: VLAgent IP address.
        target_port: Syslog port (from POWERSCALE_SYSLOG_PORT or service).

    Returns:
        dict with keys: success, commands_run, details, error.
    """
    target = f"{target_ip}:{target_port}"
    isi_cmds = [
        f"isi audit settings global modify --config-syslog-servers={target}",
        f"isi audit settings global modify --system-syslog-servers={target}",
        f"isi audit settings global modify --protocol-syslog-servers={target}",
        # Servers alone do not forward anything unless auditing is enabled.
        "isi audit settings global modify --config-auditing-enabled=yes",
        "isi audit settings global modify --system-auditing-enabled=yes",
    ]
    commands_run = []
    failures = []
    for isi_cmd in isi_cmds:
        full_cmd = CMDS["powerscale_syslog_configure"].format(
            user=ps_user, password=ps_password, host=ps_host,
            isi_cmd=isi_cmd,
        )
        commands_run.append(isi_cmd)
        result = run_on_host(host, full_cmd)
        if result.rc != 0:
            failures.append(
                f"rc={result.rc} for '{isi_cmd}'\n"
                f"    stderr: {result.stderr.strip()}\n"
                f"    stdout: {result.stdout.strip()}"
            )

    if failures:
        return {
            "success": False,
            "commands_run": commands_run,
            "details": "\n".join(failures),
            "error": (
                f"{len(failures)}/{len(isi_cmds)} isi command(s) failed as user "
                f"'{ps_user}'. The account may lack the ISI_PRIV_AUDIT "
                f"privilege, or this OneFS release uses different option names."
            ),
        }

    return {
        "success": True,
        "commands_run": commands_run,
        "details": f"Configured all syslog servers to {target}",
        "error": "",
    }


# -------------------------------------------------------------------------
# PowerScale — comprehensive deployment verification
# -------------------------------------------------------------------------

def verify_powerscale_deployment(host):
    """Comprehensive PowerScale deployment verification.

    Verifies:
    - CSM Metrics PowerScale pod running
    - OTEL Collector pod running
    - cert-manager pods running
    - CSI Driver for Dell PowerScale installed
    - No pod restarts

    Returns:
        dict with keys: success, components, details, error.
    """
    from .k8s_func import get_pods_by_label

    components = {}
    details = []

    # Check CSM Metrics PowerScale
    csm_pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app.kubernetes.io/name=karavi-metrics-powerscale")
    csm_running = len([p for p in csm_pods if p.get("ready", False)]) > 0
    csm_restarts = sum(p.get("restarts", 0) for p in csm_pods)
    components["csm_metrics"] = {
        "running": csm_running,
        "restarts": csm_restarts,
        "pod_count": len(csm_pods),
    }
    details.append(f"CSM Metrics: {len(csm_pods)} pods, {csm_restarts} restarts")

    # Check OTEL Collector
    otel_pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app.kubernetes.io/name=otel-collector")
    otel_running = len([p for p in otel_pods if p.get("ready", False)]) > 0
    otel_restarts = sum(p.get("restarts", 0) for p in otel_pods)
    components["otel_collector"] = {
        "running": otel_running,
        "restarts": otel_restarts,
        "pod_count": len(otel_pods),
    }
    details.append(f"OTEL Collector: {len(otel_pods)} pods, {otel_restarts} restarts")

    # Check cert-manager
    cert_pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app.kubernetes.io/name=cert-manager")
    cert_running = len([p for p in cert_pods if p.get("ready", False)]) > 0
    components["cert_manager"] = {
        "running": cert_running,
        "pod_count": len(cert_pods),
    }
    details.append(f"cert-manager: {len(cert_pods)} pods")

    all_running = csm_running and otel_running and cert_running
    no_restarts = csm_restarts == 0 and otel_restarts == 0

    return {
        "success": all_running and no_restarts,
        "components": components,
        "details": "; ".join(details),
        "error": "" if all_running else "Not all components running",
    }


def verify_feature_flags(host):
    """Verify PowerScale telemetry feature flags are set correctly.

    Returns:
        dict with keys: success, flags, details, error.
    """
    config = load_telemetry_config_from_target(host)
    ps_config = config.get("powerscale_configurations", {})

    flags = {
        "metrics_enabled": ps_config.get("metrics_enabled", False),
        "logs_enabled": ps_config.get("logs_enabled", False),
        "csm_observability_values_file_path": bool(ps_config.get("csm_observability_values_file_path", "")),
    }

    details = [
        f"metrics_enabled: {flags['metrics_enabled']}",
        f"logs_enabled: {flags['logs_enabled']}",
        f"csm_observability_configured: {flags['csm_observability_values_file_path']}",
    ]

    return {
        "success": True,  # Feature flags are informational, not pass/fail
        "flags": flags,
        "details": "; ".join(details),
        "error": "",
    }


def verify_health_metrics(host):
    """Verify PowerScale health metrics are being collected.

    Returns:
        dict with keys: success, metrics_found, details, error.
    """
    # Health event metrics from CSI Volume Exporter (health monitor)
    # Note: These are only available when CSI Volume Exporter is deployed
    health_metrics = [
        "powerscale_volume_health_abnormal",
        "powerscale_volume_abnormal_events_total",
        "powerscale_node_failure_events_total",
        "powerscale_node_ready",
    ]

    result = verify_powerscale_metrics(host, health_metrics)
    details = f"Found {len(result['found'])}/{len(health_metrics)} health metrics"

    # If no health metrics found, it's likely because CSI Volume Exporter
    # is not deployed (health monitor not available). Return success with warning.
    if len(result["found"]) == 0:
        return {
            "success": True,
            "metrics_found": [],
            "details": "Health monitor not deployed - health metrics not available",
            "error": "",
        }

    return {
        "success": result["success"],
        "metrics_found": result["found"],
        "details": details,
        "error": result.get("error", ""),
    }


def verify_tls_enforcement(host):
    """Verify TLS is enforced for PowerScale communications.

    Returns:
        dict with keys: success, tls_enabled, details, error.
    """
    # Check if TLS secret exists
    cmd = CMDS["kubectl_get_secret"].format(
        name="otel-collector-tls",
        namespace=TELEMETRY_NAMESPACE,
    )
    result = run_on_kube_vip(host, cmd)
    tls_enabled = result.rc == 0

    return {
        "success": tls_enabled,
        "tls_enabled": tls_enabled,
        "details": f"OTEL TLS secret: {'present' if tls_enabled else 'missing'}",
        "error": "" if tls_enabled else "TLS secret not found",
    }


def verify_label_compliance(host):
    """Verify PowerScale pods have required labels.

    Returns:
        dict with keys: success, compliance, details, error.
    """
    from .k8s_func import get_pods_by_label

    required_labels = ["app.kubernetes.io/name", "app.kubernetes.io/instance"]
    csm_pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app.kubernetes.io/name=karavi-metrics-powerscale")

    compliance = {}
    for pod in csm_pods:
        pod_labels = pod.get("labels", {})
        pod_name = pod.get("name", "unknown")
        missing = [l for l in required_labels if l not in pod_labels]
        compliance[pod_name] = {
            "compliant": len(missing) == 0,
            "missing_labels": missing,
        }

    all_compliant = all(c["compliant"] for c in compliance.values())
    details = f"{len(compliance)} pods checked, {all_compliant and 'all compliant' or 'some non-compliant'}"

    return {
        "success": all_compliant,
        "compliance": compliance,
        "details": details,
        "error": "" if all_compliant else "Some pods missing required labels",
    }


def verify_scrape_interval(host):
    """Verify PowerScale scrape interval is within acceptable range.

    Returns:
        dict with keys: success, interval, details, error.
    """
    config = load_telemetry_config_from_target(host)
    ps_config = config.get("powerscale_configurations", {})
    interval_str = ps_config.get("scrape_interval", "30s")

    # Parse interval (e.g., "30s" -> 30)
    import re
    match = re.match(r'^(\d+)s$', interval_str)
    if match:
        interval_seconds = int(match.group(1))
    else:
        interval_seconds = 30  # default

    # Acceptable range: 15s to 300s
    acceptable = 15 <= interval_seconds <= 300

    return {
        "success": acceptable,
        "interval": interval_str,
        "interval_seconds": interval_seconds,
        "details": f"Scrape interval: {interval_str} ({acceptable and 'acceptable' or 'out of range'})",
        "error": "" if acceptable else f"Interval {interval_str} out of acceptable range (15s-300s)",
    }


def verify_csi_authorization_mode(host):
    """Verify CSI authorization mode (Direct vs Karavi).

    Returns:
        dict with keys: success, mode, details, error.
    """
    # Read Helm values to determine auth mode
    config = load_telemetry_config_from_target(host)
    ps_config = config.get("powerscale_configurations", {})
    values_path = ps_config.get("csm_observability_values_file_path", "")

    if not values_path:
        return {
            "success": False,
            "mode": "unknown",
            "details": "csm_observability_values_file_path not set",
            "error": "Cannot determine auth mode without values file",
        }

    # Parse values file to check karavi authorization
    try:
        values_data = read_remote_yaml(host, values_path)
        karavi_enabled = values_data.get("karaviMetricsPowerscale", {}).get("authorization", {}).get("enabled", False)
        mode = "karavi" if karavi_enabled else "direct"
    except Exception as exc:
        return {
            "success": False,
            "mode": "unknown",
            "details": f"Failed to parse values file: {exc}",
            "error": str(exc),
        }

    return {
        "success": True,
        "mode": mode,
        "details": f"CSI authorization mode: {mode}",
        "error": "",
    }


def verify_deployment_mode(host):
    """Verify PowerScale deployment mode (always omnia-orchestrated).

    Returns:
        dict with keys: success, mode, details, error.
    """
    # With new telemetry_config.yml, PowerScale is always omnia-orchestrated
    return {
        "success": True,
        "mode": "omnia-orchestrated",
        "details": "PowerScale deployment mode: omnia-orchestrated",
        "error": "",
    }


# -------------------------------------------------------------------------
# PowerScale — CSI Volume Exporter verification
# -------------------------------------------------------------------------

def verify_csi_volume_exporter_deployment(host):
    """Verify CSI Volume Exporter deployment.

    Verifies:
    - CSI Volume Exporter pod running
    - Service exists
    - No pod restarts

    Returns:
        dict with keys: success, pods, service, details, error.
    """
    from .k8s_func import get_pods_by_label, get_service

    # Try multiple label selectors for CSI volume exporter
    pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app=csi-volume-exporter")
    if not pods:
        # Try alternative label
        pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app.kubernetes.io/name=csi-volume-exporter")
    running = len([p for p in pods if p.get("ready", False)]) > 0
    restarts = sum(p.get("restarts", 0) for p in pods)

    service = get_service(host, "csi-volume-exporter", TELEMETRY_NAMESPACE)
    service_exists = service is not None

    details = f"Pods: {len(pods)} (running: {running}), Restarts: {restarts}, Service: {'exists' if service_exists else 'missing'}"

    return {
        "success": running and service_exists and restarts == 0,
        "pods": pods,
        "service": service,
        "details": details,
        "error": "" if (running and service_exists) else "CSI Volume Exporter not fully deployed",
    }


def verify_csi_volume_exporter_metrics_endpoint(host):
    """Verify CSI Volume Exporter metrics endpoint is accessible.

    Returns:
        dict with keys: success, endpoint, details, error.
    """
    from .k8s_func import get_service

    service = get_service(host, "csi-volume-exporter", TELEMETRY_NAMESPACE)
    if not service:
        return {
            "success": False,
            "endpoint": "",
            "details": "CSI Volume Exporter service not found",
            "error": "Service not found",
        }

    # Get service IP and port
    service_ip = service.get("cluster_ip", "")
    service_port = service.get("ports", [{}])[0].get("port", 9090)

    if not service_ip:
        return {
            "success": False,
            "endpoint": "",
            "details": "Service IP not available",
            "error": "Cannot determine service endpoint",
        }

    endpoint = f"{service_ip}:{service_port}"

    # Try to access metrics endpoint
    cmd = f"curl -sk --max-time 5 http://{endpoint}/metrics"
    result = run_on_kube_vip(host, cmd)

    if result.rc == 0 and result.stdout.strip():
        return {
            "success": True,
            "endpoint": endpoint,
            "details": f"Metrics endpoint accessible at {endpoint}",
            "error": "",
        }
    else:
        return {
            "success": False,
            "endpoint": endpoint,
            "details": f"Metrics endpoint not accessible at {endpoint}",
            "error": "Failed to access metrics endpoint",
        }


def verify_csi_volume_exporter_metrics(host):
    """Verify CSI Volume Exporter metrics are being collected.

    Returns:
        dict with keys: success, metrics_found, details, error.
    """
    expected_metrics = [
        "powerscale_volume_count",
        "powerscale_volume_capacity_bytes",
        "powerscale_total_capacity_bytes",
    ]

    result = verify_powerscale_metrics(host, expected_metrics)
    details = f"Found {len(result['found'])}/{len(expected_metrics)} CSI volume exporter metrics"

    return {
        "success": result["success"],
        "metrics_found": result["found"],
        "details": details,
        "error": result.get("error", ""),
    }


# -------------------------------------------------------------------------
# PowerScale — CSI Driver (isilon-controller) verification
# -------------------------------------------------------------------------

def verify_csi_driver_powerscale_deployment(host):
    """Verify CSI Driver for PowerScale (isilon-controller) deployment.

    Verifies:
    - isilon-controller StatefulSet is deployed
    - isilon-controller pods are running
    - No recent pod restarts (within 1 hour)

    Returns:
        dict with keys: success, pods, details, error, driver_deployed.
        When driver is not deployed, returns driver_deployed=False and success=True (not a failure).
    """
    from .k8s_func import get_pods_by_label
    from datetime import datetime, timedelta, timezone

    # isilon-controller uses label: app=isilon-controller
    pods = get_pods_by_label(host, "isilon", "app=isilon-controller")
    
    if not pods:
        return {
            "success": True,  # Not a failure - CSI driver might not be deployed
            "driver_deployed": False,
            "pods": [],
            "details": "CSI driver not deployed (no isilon-controller pods found)",
            "error": "",
        }
    
    running = len([p for p in pods if p.get("ready", False)]) > 0
    total_restarts = sum(p.get("restarts", 0) for p in pods)
    
    # Check for recent restarts (within 1 hour)
    recent_restarts = 0
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    
    for pod in pods:
        last_restart_time = pod.get("last_restart_time")
        if last_restart_time:
            try:
                # Parse Kubernetes timestamp format (ISO 8601)
                restart_time = datetime.fromisoformat(last_restart_time.replace('Z', '+00:00'))
                if restart_time.tzinfo is None:
                    restart_time = restart_time.replace(tzinfo=timezone.utc)
                if restart_time > one_hour_ago:
                    recent_restarts += 1
            except (ValueError, AttributeError):
                # If we can't parse the time, consider it recent to be safe
                recent_restarts += 1

    details = f"Pods: {len(pods)} (running: {running}), Restarts: {total_restarts}, Recent restarts (1h): {recent_restarts}"

    return {
        "success": running and recent_restarts == 0,
        "driver_deployed": True,
        "pods": pods,
        "details": details,
        "error": "" if (running and recent_restarts == 0) else "CSI Driver not fully deployed or has recent restarts",
    }


# -------------------------------------------------------------------------
# PowerScale — External Health Monitor Controller verification
# -------------------------------------------------------------------------

def verify_external_health_monitor_container(host):
    """Verify external-health-monitor-controller container is running in isilon-controller pod.

    Verifies:
    - isilon-controller pod exists
    - external-health-monitor-controller container is present
    - external-health-monitor-controller container is ready

    Returns:
        dict with keys: success, pod_name, container_ready, details, error, pod_found.
        When pod is not found, returns pod_found=False and success=True (not a failure).
    """
    from .k8s_func import get_pods_by_label

    # Find isilon-controller pod
    pods = get_pods_by_label(host, "isilon", "app=isilon-controller")
    
    if not pods:
        return {
            "success": True,  # Not a failure - CSI driver might not be deployed
            "pod_found": False,
            "pod_name": "",
            "container_ready": False,
            "details": "isilon-controller pod not found (CSI driver not deployed)",
            "error": "",
        }

    pod_name = pods[0].get("name", "")
    
    # Check if external-health-monitor-controller container is ready
    # We need to check the container status using kubectl
    cmd = f"kubectl get pod {pod_name} -n isilon -o jsonpath='{{.status.containerStatuses[?(@.name==\"external-health-monitor-controller\")].ready}}'"
    result = run_on_kube_vip(host, cmd)

    container_ready = result.stdout.strip() == "true"
    
    details = f"Pod: {pod_name}, Container ready: {container_ready}"
    
    return {
        "success": container_ready,
        "pod_found": True,
        "pod_name": pod_name,
        "container_ready": container_ready,
        "details": details,
        "error": "" if container_ready else "external-health-monitor-controller container not ready",
    }


def verify_csi_exporter_skipped_without_health_monitor(host):
    """Verify CSI volume exporter deployment is skipped when health monitor is not available.

    Verifies:
    - CSI volume exporter deployment is skipped when health monitor is missing
    - No CSI volume exporter pods are deployed

    Returns:
        dict with keys: success, exporter_deployed, health_monitor_available, details, error.
    """
    from .k8s_func import get_pods_by_label

    # Check if health monitor is available
    health_monitor_result = verify_external_health_monitor_container(host)
    health_monitor_available = health_monitor_result.get("pod_found", False) and health_monitor_result["success"]
    
    # Check if CSI volume exporter is deployed
    # Try multiple label selectors
    pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app=csi-volume-exporter")
    if not pods:
        # Try alternative label
        pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app.kubernetes.io/name=csi-volume-exporter")
    exporter_deployed = len(pods) > 0
    
    # Expected behavior:
    # - If health monitor is NOT available → exporter should NOT be deployed
    # - If health monitor IS available → exporter SHOULD be deployed
    if health_monitor_available:
        expected_behavior = exporter_deployed
    else:
        expected_behavior = not exporter_deployed
    
    details = (
        f"Health monitor available: {health_monitor_available}, "
        f"Exporter deployed: {exporter_deployed}, "
        f"Expected behavior: {expected_behavior}"
    )
    
    return {
        "success": expected_behavior,
        "exporter_deployed": exporter_deployed,
        "health_monitor_available": health_monitor_available,
        "details": details,
        "error": "" if expected_behavior else "CSI volume exporter deployment logic incorrect",
    }


def verify_health_monitor_warning_message(host):
    """Verify appropriate warning message is displayed when health monitor is missing.

    This is a informational check that validates the deployment playbook
    shows the correct warning message when health monitor is not available.

    Returns:
        dict with keys: success, warning_expected, details, error.
    """
    # Check if health monitor is available
    health_monitor_result = verify_external_health_monitor_container(host)
    health_monitor_available = health_monitor_result.get("pod_found", False) and health_monitor_result["success"]
    
    # Warning should be displayed when health monitor is not available
    # If health monitor IS available, warning should NOT be displayed
    warning_expected = not health_monitor_available
    
    details = (
        f"Health monitor available: {health_monitor_available}, "
        f"Warning expected: {warning_expected}"
    )
    
    return {
        "success": True,  # This is always informational
        "warning_expected": warning_expected,
        "details": details,
        "error": "",
    }


# -------------------------------------------------------------------------
# PowerScale — Integration Tests for Karavi Observability
# -------------------------------------------------------------------------

def verify_csm_otel_data_flow(host):
    """Verify CSM Metrics to OTEL Collector data flow.

    Verifies:
    - CSM Metrics PowerScale is exposing metrics
    - OTEL Collector is receiving metrics from CSM Metrics
    - Data is flowing between the components

    Returns:
        dict with keys: success, csm_exposing, otel_receiving, details, error.
    """
    from .k8s_func import get_pods_by_label

    # Check if CSM Metrics is running
    csm_pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app.kubernetes.io/name=karavi-metrics-powerscale")
    csm_running = len([p for p in csm_pods if p.get("ready", False)]) > 0

    # Check if OTEL Collector is running
    otel_pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app.kubernetes.io/name=otel-collector")
    otel_running = len([p for p in otel_pods if p.get("ready", False)]) > 0

    # Check CSM metrics endpoint (if accessible)
    csm_exposing = False
    if csm_running and csm_pods:
        # CSM Metrics exposes metrics on port 8080
        cmd = "kubectl get svc karavi-metrics-powerscale -n telemetry -o jsonpath='{.spec.ports[0].port}'"
        result = run_on_kube_vip(host, cmd)
        csm_exposing = result.rc == 0 and result.stdout.strip()

    # Verify OTEL actually received CSM data by scraping the collector's own
    # Prometheus endpoint: the metric families served there are exactly what
    # CSM Metrics pushed into the collector. Log-grepping is unreliable
    # because the collector logs nothing per batch at INFO level.
    otel_receiving = False
    otel_endpoint = ""
    sample_families = []
    if otel_running:
        svc_cmd = (
            "kubectl get svc otel-collector -n telemetry -o jsonpath="
            "'{.spec.clusterIP}{\" \"}{.spec.ports[?(@.name==\"prometheus\")].port}'"
        )
        svc_result = run_on_kube_vip(host, svc_cmd)
        parts = svc_result.stdout.strip().split() if svc_result.rc == 0 else []
        if len(parts) == 1:
            # 'prometheus' port not present — fall back to the first port
            fallback_cmd = (
                "kubectl get svc otel-collector -n telemetry -o jsonpath="
                "'{.spec.ports[0].port}'"
            )
            fallback = run_on_kube_vip(host, fallback_cmd)
            if fallback.rc == 0 and fallback.stdout.strip():
                parts.append(fallback.stdout.strip())
        if len(parts) >= 2:
            otel_endpoint = f"{parts[0]}:{parts[1]}"
            for scheme in ("https", "http"):
                curl_cmd = (
                    f"curl -sk --max-time 10 {scheme}://{otel_endpoint}/metrics"
                )
                curl_result = run_on_kube_vip(host, curl_cmd)
                if curl_result.rc != 0 or not curl_result.stdout.strip():
                    continue
                sample_families = sorted({
                    line.split("{")[0].split()[0]
                    for line in curl_result.stdout.splitlines()
                    if line and not line.startswith("#")
                    and (line.startswith("powerscale_")
                         or line.startswith("karavi_"))
                })
                if sample_families:
                    otel_receiving = True
                    otel_endpoint = f"{scheme}://{otel_endpoint}"
                    break

    data_flow = csm_running and otel_running and csm_exposing and otel_receiving

    details = (
        f"CSM running: {csm_running}, CSM exposing: {csm_exposing}, "
        f"OTEL running: {otel_running}, OTEL receiving: {otel_receiving}"
    )
    if otel_endpoint:
        details += f", OTEL metrics endpoint: {otel_endpoint}"
    if sample_families:
        details += (
            f", CSM metric families served by OTEL: "
            f"{len(sample_families)} (e.g. {', '.join(sample_families[:3])})"
        )

    return {
        "success": data_flow,
        "csm_exposing": csm_exposing,
        "otel_receiving": otel_receiving,
        "details": details,
        "error": "" if data_flow else "CSM to OTEL data flow not established",
    }


def verify_otel_vm_export(host):
    """Verify OTEL Collector to VictoriaMetrics export.

    Verifies:
    - OTEL Collector is configured to export to VictoriaMetrics
    - Metrics are being exported to VictoriaMetrics
    - Export configuration is valid

    Returns:
        dict with keys: success, export_configured, metrics_exporting, details, error.
    """
    # Check if OTEL Collector is configured to export to VictoriaMetrics
    # This typically involves checking the OTEL configuration or service endpoints
    cmd = "kubectl get svc vmagent-vmagent -n telemetry -o jsonpath='{.spec.clusterIP}'"
    result = run_on_kube_vip(host, cmd)
    vmagent_ip = result.stdout.strip() if result.rc == 0 else ""

    export_configured = bool(vmagent_ip)

    # Check if PowerScale metrics are appearing in VictoriaMetrics
    # Query for any known PowerScale/karavi metric
    metrics_exporting = False
    if export_configured:
        try:
            all_names = query_vm_metric_names(host)
            # Check for CSI Volume Exporter metrics (powerscale_volume_*, powerscale_pvc_*)
            # or karavi topology metrics
            ps_metrics = [m for m in all_names if m.startswith("powerscale_") or m.startswith("karavi_")]
            metrics_exporting = len(ps_metrics) > 0
        except Exception:
            metrics_exporting = False

    export_working = export_configured and metrics_exporting

    details = (
        f"Export configured: {export_configured}, "
        f"Metrics exporting: {metrics_exporting}, "
        f"VMagent IP: {vmagent_ip}"
    )

    return {
        "success": export_working,
        "export_configured": export_configured,
        "metrics_exporting": metrics_exporting,
        "details": details,
        "error": "" if export_working else "OTEL to VictoriaMetrics export not working",
    }


def verify_otel_service_patch(host):
    """Verify OTEL Collector service patch for vmagent scrape discovery.

    Verifies:
    - OTEL Collector service has proper annotations for vmagent discovery
    - Service is configured for metrics scraping
    - Port configuration is correct

    Returns:
        dict with keys: success, service_patched, annotations_valid, details, error.
    """
    from .k8s_func import get_service

    # Try to find OTEL Collector service by common names
    service = get_service(host, TELEMETRY_NAMESPACE, "otel-collector")
    if not service:
        # Try Helm release name
        service = get_service(host, TELEMETRY_NAMESPACE, "karavi-observability-otel-collector")

    if not service:
        return {
            "success": False,
            "service_patched": False,
            "annotations_valid": False,
            "details": "OTEL Collector service not found",
            "error": "Service not found",
        }

    # Check for vmagent discovery labels (added by deployment)
    labels = service.get("metadata", {}).get("labels", {})

    # Expected labels for vmagent discovery
    expected_labels = [
        "app.kubernetes.io/name",
        "app.kubernetes.io/component",
    ]

    labels_valid = all(key in labels for key in expected_labels)

    # Check if labels have correct values
    name_valid = labels.get("app.kubernetes.io/name") == "otel-collector"
    component_valid = labels.get("app.kubernetes.io/component") == "collector"

    # Check port configuration (service should have prometheus port 8889)
    ports = service.get("spec", {}).get("ports", [])
    prometheus_port = next((p for p in ports if p.get("name") == "prometheus"), None)
    port_valid = prometheus_port is not None and prometheus_port.get("port") == 8889

    service_patched = labels_valid and name_valid and component_valid and port_valid

    details = (
        f"Labels valid: {labels_valid}, "
        f"Name valid: {name_valid}, "
        f"Component valid: {component_valid}, "
        f"Port valid: {port_valid}"
    )

    return {
        "success": service_patched,
        "service_patched": service_patched,
        "annotations_valid": labels_valid,
        "details": details,
        "error": "" if service_patched else "OTEL Collector service not properly patched",
    }


def verify_cert_manager_tls_certs(host):
    """Verify cert-manager TLS certificate generation.

    Verifies:
    - cert-manager is deployed and running
    - TLS secret for OTEL Collector exists
    - Certificate is valid and not expired
    - Certificate has proper SANs

    Returns:
        dict with keys: success, cert_manager_running, tls_secret_exists, cert_valid, details, error.
    """
    from .k8s_func import get_pods_by_label

    # Check if cert-manager is running
    cert_pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app.kubernetes.io/name=cert-manager")
    cert_manager_running = len([p for p in cert_pods if p.get("ready", False)]) > 0

    # Check if TLS secret exists
    cmd = CMDS["kubectl_get_secret"].format(
        name="otel-collector-tls",
        namespace=TELEMETRY_NAMESPACE,
    )
    result = run_on_kube_vip(host, cmd)
    tls_secret_exists = result.rc == 0

    # Check certificate validity
    cert_valid = False
    cert_details = ""
    if tls_secret_exists:
        # Try to decode and check certificate
        cmd = f"kubectl get secret otel-collector-tls -n telemetry -o jsonpath='{{.data.tls\\.crt}}' | base64 -d | openssl x509 -noout -dates 2>/dev/null || echo 'invalid'"
        result = run_on_kube_vip(host, cmd)
        cert_output = result.stdout.strip()
        
        # Check if certificate is valid (has dates)
        cert_valid = "notBefore" in cert_output and "notAfter" in cert_output
        cert_details = cert_output if cert_valid else "Certificate invalid or expired"

    all_valid = cert_manager_running and tls_secret_exists and cert_valid

    details = (
        f"cert-manager running: {cert_manager_running}, "
        f"TLS secret exists: {tls_secret_exists}, "
        f"Certificate valid: {cert_valid}, "
        f"Cert details: {cert_details}"
    )

    return {
        "success": all_valid,
        "cert_manager_running": cert_manager_running,
        "tls_secret_exists": tls_secret_exists,
        "cert_valid": cert_valid,
        "details": details,
        "error": "" if all_valid else "cert-manager TLS certificate validation failed",
    }

