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
VAST — Module-Specific Verification Functions.

Handles:
  - VAST external headless service verification
  - VAST VMServiceScrape CR verification
  - VAST credentials K8s secret verification
  - VAST storage metrics in VictoriaMetrics
  - VAST logs in VictoriaLogs
"""

import json

from omnia_auto import read_yaml_key

from ..vars.common_vars import (
    TELEMETRY_NAMESPACE,
    VAST_SVC_NAME,
    VAST_VMSCRAPE_NAME,
    VAST_SECRET_NAME,
    CFG_KEY_VAST_ENDPOINT,
    CFG_KEY_VAST_PORT,
    CMDS,
)
from .telemetry_func import (
    load_telemetry_config_from_target,
    run_on_kube_vip,
    query_vm_metric_names,
    query_vm_instant,
    get_vlselect_endpoint,
)


def verify_vast_external_service(host):
    """Verify VAST external headless service exists and has correct endpoint.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, service_name, endpoint_ip, endpoint_port,
        expected_endpoint, expected_port.
    """
    svc_cmd = (
        f"kubectl get svc {VAST_SVC_NAME} -n {TELEMETRY_NAMESPACE}"
        " -o json 2>/dev/null"
    )
    result = run_on_kube_vip(host, svc_cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "service_name": VAST_SVC_NAME,
            "error": "Service not found",
        }

    try:
        svc = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "service_name": VAST_SVC_NAME,
            "error": "JSON parse error",
        }

    svc_port = ""
    for p in svc.get("spec", {}).get("ports", []):
        svc_port = str(p.get("port", ""))
        break

    # Get endpoints
    ep_cmd = (
        f"kubectl get endpoints {VAST_SVC_NAME} -n {TELEMETRY_NAMESPACE}"
        " -o json 2>/dev/null"
    )
    ep_result = run_on_kube_vip(host, ep_cmd)
    endpoint_ip = ""
    endpoint_port = ""
    if ep_result.rc == 0 and ep_result.stdout.strip():
        try:
            ep_data = json.loads(ep_result.stdout)
            for subset in ep_data.get("subsets", []):
                for addr in subset.get("addresses", []):
                    endpoint_ip = addr.get("ip", "")
                    break
                for port in subset.get("ports", []):
                    endpoint_port = str(port.get("port", ""))
                    break
        except json.JSONDecodeError:
            pass

    # Get expected from config
    config = load_telemetry_config_from_target(host)
    expected_endpoint = read_yaml_key(config, CFG_KEY_VAST_ENDPOINT, default="")
    expected_port = str(read_yaml_key(config, CFG_KEY_VAST_PORT, default="443"))

    match = endpoint_ip == expected_endpoint

    return {
        "success": match and bool(endpoint_ip),
        "service_name": VAST_SVC_NAME,
        "endpoint_ip": endpoint_ip,
        "endpoint_port": endpoint_port,
        "svc_port": svc_port,
        "expected_endpoint": expected_endpoint,
        "expected_port": expected_port,
    }


def verify_vast_vmscrape(host):
    """Verify VAST VMServiceScrape CR exists.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, name, scrape_interval, port, path.
    """
    cmd = (
        f"kubectl get vmservicescrape {VAST_VMSCRAPE_NAME} -n {TELEMETRY_NAMESPACE}"
        " -o json 2>/dev/null"
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "name": VAST_VMSCRAPE_NAME,
            "error": "Not found",
        }

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "name": VAST_VMSCRAPE_NAME,
            "error": "JSON parse error",
        }

    endpoints = data.get("spec", {}).get("endpoints", [])
    interval = ""
    port = ""
    path = ""
    if endpoints:
        interval = endpoints[0].get("interval", "")
        port = endpoints[0].get("port", "")
        path = endpoints[0].get("path", "/api/prometheusmetrics/all")

    return {
        "success": True,
        "name": VAST_VMSCRAPE_NAME,
        "scrape_interval": interval,
        "port": port,
        "path": path,
    }


def verify_vast_credentials_secret(host):
    """Verify VAST credentials K8s secret exists.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, secret_name, keys_found.
    """
    cmd = (
        f"kubectl get secret {VAST_SECRET_NAME} -n {TELEMETRY_NAMESPACE}"
        " -o json 2>/dev/null"
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "secret_name": VAST_SECRET_NAME,
            "error": "Not found",
        }

    try:
        data = json.loads(result.stdout)
        keys_found = list(data.get("data", {}).keys())
    except json.JSONDecodeError:
        return {
            "success": False,
            "secret_name": VAST_SECRET_NAME,
            "error": "JSON parse",
        }

    return {
        "success": len(keys_found) > 0,
        "secret_name": VAST_SECRET_NAME,
        "keys_found": keys_found,
    }


def verify_vast_metrics(host, expected_metrics):
    """Verify VAST storage metrics exist in VictoriaMetrics.

    Args:
        host: Testinfra host connection to the OIM.
        expected_metrics: List of metric names to check.

    Returns:
        dict with keys: success, found, missing, metric_details.
    """
    all_names = query_vm_metric_names(host)
    found = [m for m in expected_metrics if m in all_names]
    missing = [m for m in expected_metrics if m not in all_names]

    metric_details = []
    for metric in found:
        results = query_vm_instant(host, metric)
        if results:
            val = results[0].get("value", [None, "N/A"])
            timestamp = int(float(val[0])) if val[0] else 0
            value = val[1] if len(val) > 1 else "N/A"
            metric_details.append({
                "metric": metric,
                "value": value,
                "timestamp": timestamp,
            })

    return {
        "success": len(missing) == 0,
        "found": found,
        "missing": missing,
        "metric_details": metric_details,
    }


def verify_vast_logs(host, hostname_pattern=None):
    """Verify VAST syslog entries exist in VictoriaLogs.

    Args:
        host: Testinfra host connection to the OIM.
        hostname_pattern: Optional hostname pattern to search for.
            If None, searches for any VAST-related logs.

    Returns:
        dict with keys: success, count, sample_log.
    """
    ip, port = get_vlselect_endpoint(host)
    if not ip or not port:
        return {"success": False, "count": 0, "sample_log": ""}

    # Search for VAST-related logs by hostname or source
    if hostname_pattern:
        query = f"hostname:{hostname_pattern}*"
    else:
        # Search for logs from VAST appliance (typically contains "vast" in hostname)
        query = "hostname:*vast* OR _msg:*VAST*"

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


def get_vast_endpoint_from_config(host):
    """Get VAST endpoint from telemetry config.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, endpoint, port, metrics_path.
    """
    config = load_telemetry_config_from_target(host)
    endpoint = read_yaml_key(config, CFG_KEY_VAST_ENDPOINT, default="")
    port = read_yaml_key(config, CFG_KEY_VAST_PORT, default=443)
    metrics_path = read_yaml_key(
        config, "vast_configuration.metrics_path",
        default="/api/prometheusmetrics/all"
    )

    return {
        "success": bool(endpoint),
        "endpoint": endpoint,
        "port": str(port),
        "metrics_path": metrics_path,
    }
