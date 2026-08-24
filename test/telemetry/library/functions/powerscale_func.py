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
