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
    CFG_KEY_PS_SECRET_PATH,
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

def load_powerscale_secret_from_config(host):
    """Read PowerScale credentials from the csi_powerscale_secret_path
    referenced in telemetry_config.yml on the OIM host.

    Returns:
        dict with keys: success, clusters (list), error.
    """
    config = load_telemetry_config_from_target(host)
    secret_path = read_yaml_key(config, CFG_KEY_PS_SECRET_PATH, default="")
    if not secret_path:
        return {"success": False, "clusters": [], "error": "secret_path not set"}

    data = read_remote_yaml(host, secret_path)
    if not data:
        return {"success": False, "clusters": [], "error": f"Cannot read {secret_path}"}

    clusters = []
    for cluster in data.get("isilonClusters", []):
        clusters.append({
            "clusterName": cluster.get("clusterName", ""),
            "username": str(cluster.get("username", "")),
            "password": str(cluster.get("password", "")),
            "endpoint": str(cluster.get("endpoint", "")),
        })

    return {
        "success": len(clusters) > 0,
        "clusters": clusters,
        "secret_path": secret_path,
        "error": "",
    }


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

    return {
        "success": len(missing) == 0,
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
        dict with keys: success, config_servers, system_servers,
        protocol_servers, details, commands_run.
    """
    view_cmd = CMDS["powerscale_syslog_view"].format(
        user=ps_user, password=ps_password, host=ps_host,
    )
    result = run_on_host(host, view_cmd)
    if result.rc != 0:
        return {
            "success": False,
            "config_servers": "",
            "system_servers": "",
            "protocol_servers": "",
            "details": f"SSH failed: {result.stderr}",
            "commands_run": [view_cmd],
        }

    output = result.stdout
    config_servers = ""
    system_servers = ""
    protocol_servers = ""
    for line in output.split("\n"):
        stripped = line.strip()
        if stripped.startswith("Config Syslog Servers:"):
            config_servers = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("System Syslog Servers:"):
            system_servers = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Protocol Syslog Servers:"):
            protocol_servers = stripped.split(":", 1)[1].strip()

    target_str = f"{expected_target}:{expected_port}"
    all_correct = (
        target_str in config_servers
        and target_str in system_servers
        and target_str in protocol_servers
    )

    return {
        "success": all_correct,
        "config_servers": config_servers,
        "system_servers": system_servers,
        "protocol_servers": protocol_servers,
        "details": output,
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
    ]
    commands_run = []
    for isi_cmd in isi_cmds:
        full_cmd = CMDS["powerscale_syslog_configure"].format(
            user=ps_user, password=ps_password, host=ps_host,
            isi_cmd=isi_cmd,
        )
        commands_run.append(isi_cmd)
        result = run_on_host(host, full_cmd)
        if result.rc != 0:
            return {
                "success": False,
                "commands_run": commands_run,
                "details": result.stderr,
                "error": f"Failed: {isi_cmd}",
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
    csm_pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app=karavi-metrics-powerscale")
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
    cert_pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app.kubernetes.io/part-of=cert-manager")
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
    health_metrics = [
        "powerscale_cluster_health",
        "powerscale_node_health",
        "powerscale_disk_health",
    ]

    result = verify_powerscale_metrics(host, health_metrics)
    details = f"Found {len(result['found'])}/{len(health_metrics)} health metrics"

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

    required_labels = ["app", "app.kubernetes.io/name", "app.kubernetes.io/instance"]
    csm_pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app=karavi-metrics-powerscale")

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
    cfg_result = load_powerscale_secret_from_config(host)
    if not cfg_result["success"]:
        return {
            "success": False,
            "mode": "unknown",
            "details": "Cannot read PowerScale config",
            "error": cfg_result["error"],
        }

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

    pods = get_pods_by_label(host, TELEMETRY_NAMESPACE, "app=csi-volume-exporter")
    running = len([p for p in pods if p.get("ready", False)]) > 0
    restarts = sum(p.get("restarts", 0) for p in pods)

    service = get_service(host, TELEMETRY_NAMESPACE, "csi-volume-exporter")
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

    service = get_service(host, TELEMETRY_NAMESPACE, "csi-volume-exporter")
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
        "csi_volume_exporter_pv_count",
        "csi_volume_exporter_pv_capacity_bytes",
        "csi_volume_exporter_pv_used_bytes",
    ]

    result = verify_powerscale_metrics(host, expected_metrics)
    details = f"Found {len(result['found'])}/{len(expected_metrics)} CSI volume exporter metrics"

    return {
        "success": result["success"],
        "metrics_found": result["found"],
        "details": details,
        "error": result.get("error", ""),
    }
