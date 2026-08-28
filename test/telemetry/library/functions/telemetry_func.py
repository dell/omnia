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
Telemetry — Common Verification Functions.

Shared utilities used by ALL telemetry source/sink modules:
  - kube_vip resolution and command execution
  - Telemetry config loading and source/sink enablement checks
  - VictoriaMetrics / VictoriaLogs endpoint resolution and queries
  - Target connectivity and environment checks

Module-specific functions live in separate files:
  - powerscale_func.py  — PowerScale isilon-creds, metrics, syslog
  - ufm_func.py         — UFM external service, VMServiceScrape, metrics
"""

import json

import yaml

from omnia_auto import (
    run_on_host,
    log,
    read_remote_env,
    read_yaml_key,
    resolve_domain_input_path,
)

from ..vars.common_vars import (
    CMDS,
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    TELEMETRY_CONFIG_FILE,
    TELEMETRY_NAMESPACE,
    SVC_VMSELECT,
    SVC_VLSELECT,
    SVC_PORT_NAME_HTTP,
    KAFKA_EXTERNAL_BOOTSTRAP_SVC,
)

# Module-level cache for kube_vip IP
_kube_vip_ip_cache = None


# -------------------------------------------------------------------------
# Config & Input Path Resolution
# -------------------------------------------------------------------------

def _get_input_path(host):
    """Resolve the telemetry input directory on the OIM host.

    Returns:
        str: Absolute path to telemetry input directory on the OIM.
    """
    return resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )


def get_output_path(host):
    """Resolve the telemetry output directory on the OIM host.

    Returns ``<OMNIA_DATA_PATH>/telemetry/output/<OMNIA_PROJECT_NAME>``.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        str: Absolute path to telemetry output directory on the OIM.
    """
    data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH)
    project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    output_path = f"{data_path}/{DOMAIN_NAME}/output/{project}"
    log(f"Resolved remote output path: {output_path}", "INFO")
    return output_path


def load_telemetry_config_from_target(host):
    """Read and parse telemetry_config.yml from OIM host.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict: Parsed YAML content, or empty dict on failure.
    """
    input_path = _get_input_path(host)
    file_path = f"{input_path}/{TELEMETRY_CONFIG_FILE}"
    cmd = CMDS["cat_file"].format(path=file_path)
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {}
    try:
        return yaml.safe_load(result.stdout) or {}
    except yaml.YAMLError:
        return {}


# -------------------------------------------------------------------------
# kube_vip Resolution & Remote Execution
# -------------------------------------------------------------------------

def resolve_kube_vip_ip(host):
    """Resolve the kube_vip IP from OIM's telemetry config.

    Reads cluster_inventory path from telemetry_config.yml, then
    parses the orchestrator inventory to extract the kube_vip
    ansible_host IP.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        str: kube_vip IP address, or empty string if not resolvable.
    """
    global _kube_vip_ip_cache  # pylint: disable=global-statement
    if _kube_vip_ip_cache:
        return _kube_vip_ip_cache

    # Step 1: Get cluster_inventory path from telemetry_config.yml
    input_path = _get_input_path(host)
    config_path = f"{input_path}/{TELEMETRY_CONFIG_FILE}"
    cmd = CMDS["read_telemetry_config_field"].format(
        config_path=config_path, field="cluster_inventory",
    )
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        log("Cannot read cluster_inventory from telemetry_config.yml", "WARN")
        return ""

    inventory_path = result.stdout.strip()

    # Step 2: Parse kube_vip_group from the inventory
    cmd = CMDS["read_kube_vip_ip"].format(inventory_path=inventory_path)
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        log(f"Cannot parse kube_vip IP from {inventory_path}", "WARN")
        return ""

    _kube_vip_ip_cache = result.stdout.strip()
    log(f"Resolved kube_vip IP: {_kube_vip_ip_cache}", "INFO")
    return _kube_vip_ip_cache


def get_kube_vip_host(host):
    """Get a testinfra-compatible host that runs commands on the kube_vip.

    Since kubectl must run on the kube_vip node, this wraps commands
    in ssh from OIM to kube_vip. Returns the OIM host with a command
    prefix function that SSHs into kube_vip.

    For local execution on OIM, the kube_vip IP is resolved and commands
    are run via ssh to that IP.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        Testinfra host object connected to the kube_vip node.
    """
    import testinfra
    kube_vip_ip = resolve_kube_vip_ip(host)
    if not kube_vip_ip:
        log("kube_vip IP not resolved; using OIM host directly", "WARN")
        return host

    # Connect to kube_vip via paramiko SSH
    return testinfra.get_host(
        f"paramiko://{kube_vip_ip}",
        ssh_config=None,
    )


def run_on_kube_vip(host, cmd):
    """Run a command on the kube_vip node via SSH from the OIM.

    Uses base64 encoding to transport the command safely over SSH,
    avoiding shell quoting issues with jsonpath expressions and
    other special characters.

    Args:
        host: Testinfra host connection to the OIM.
        cmd: Command string to execute on kube_vip.

    Returns:
        Command result object with .rc, .stdout, .stderr.
    """
    kube_vip_ip = resolve_kube_vip_ip(host)
    if not kube_vip_ip:
        log("kube_vip IP not resolved; running on OIM", "WARN")
        return run_on_host(host, cmd)

    import base64
    b64_cmd = base64.b64encode(cmd.encode("utf-8")).decode("ascii")
    ssh_cmd = (
        f"ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR "
        f"root@{kube_vip_ip} "
        f"\"echo {b64_cmd} | base64 -d | bash\""
    )
    return run_on_host(host, ssh_cmd)


# -------------------------------------------------------------------------
# Source / Sink Enablement Checks
# -------------------------------------------------------------------------

def is_source_enabled(host, source_name):
    """Check if a telemetry source is enabled.

    Uses ``read_yaml_key`` to look up
    ``telemetry_sources.<source_name>.metrics_enabled``.

    Args:
        host: Testinfra host connection to the OIM.
        source_name: Source name (e.g. 'idrac', 'ldms', 'powerscale').

    Returns:
        bool: True if source has metrics_enabled: true.
    """
    config = load_telemetry_config_from_target(host)
    key = f"telemetry_sources.{source_name}.metrics_enabled"
    return read_yaml_key(config, key, default=False)


def is_logs_enabled(host, source_name):
    """Check if a telemetry source has logs collection enabled.

    Uses ``read_yaml_key`` to look up
    ``telemetry_sources.<source_name>.logs_enabled``.

    Args:
        host: Testinfra host connection to the OIM.
        source_name: Source name (e.g. 'powerscale').

    Returns:
        bool: True if source has logs_enabled: true.
    """
    config = load_telemetry_config_from_target(host)
    key = f"telemetry_sources.{source_name}.logs_enabled"
    return read_yaml_key(config, key, default=False)


def is_sink_enabled(host, sink_name):
    """Check if a telemetry sink is implicitly enabled.

    A sink is considered enabled if at least one source targets it.

    Args:
        host: Testinfra host connection to the OIM.
        sink_name: Sink name (e.g. 'victoria_metrics', 'kafka').

    Returns:
        bool: True if at least one source targets this sink.
    """
    config = load_telemetry_config_from_target(host)
    sources = read_yaml_key(config, "telemetry_sources", default={})
    for src_cfg in sources.values():
        if not isinstance(src_cfg, dict):
            continue
        if not src_cfg.get("metrics_enabled", False):
            continue
        targets = src_cfg.get("collection_targets", [])
        if sink_name in targets:
            return True
    return False


def check_target_connectivity(host):
    """Verify OIM target host is reachable.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, details, error.
    """
    result = run_on_host(host, "echo ok")
    if result.rc == 0 and "ok" in result.stdout:
        return {
            "success": True,
            "details": "Target host is reachable",
            "error": "",
        }
    return {
        "success": False,
        "details": "",
        "error": f"Cannot reach target: rc={result.rc}",
    }


# -------------------------------------------------------------------------
# Service Endpoint Resolution (generic)
# -------------------------------------------------------------------------

def _get_svc_endpoint(host, svc_name, port_name=None):
    """Get a K8s service LoadBalancer IP and port dynamically.

    Reads the IP from ``status.loadBalancer.ingress[0].ip`` and the
    port from the named port spec (or the first port if *port_name*
    is ``None``).

    Args:
        host: Testinfra host (OIM).
        svc_name: K8s service name.
        port_name: Port name inside the service spec.  When ``None``
                   the first port is used.

    Returns:
        tuple: ``(ip, port)`` — both strings.  ``("", "")`` on failure.
    """
    ip_cmd = CMDS["kubectl_get_svc_lb_ip"].format(
        name=svc_name, namespace=TELEMETRY_NAMESPACE,
    )
    result = run_on_kube_vip(host, ip_cmd)
    ip = result.stdout.strip() if result.rc == 0 else ""

    if port_name:
        port_cmd = CMDS["kubectl_get_svc_port"].format(
            name=svc_name, namespace=TELEMETRY_NAMESPACE,
            port_name=port_name,
        )
    else:
        port_cmd = CMDS["kubectl_get_svc_first_port"].format(
            name=svc_name, namespace=TELEMETRY_NAMESPACE,
        )
    result = run_on_kube_vip(host, port_cmd)
    port = result.stdout.strip() if result.rc == 0 else ""

    return ip, port


# -------------------------------------------------------------------------
# Kafka — dynamic endpoint resolution
# -------------------------------------------------------------------------

def get_kafka_external_bootstrap(host):
    """Get the Kafka external bootstrap LoadBalancer IP and port.

    Reads from ``kubectl get svc kafka-kafka-external-bootstrap``
    in the telemetry namespace.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        str: ``"<ip>:<port>"`` or empty string if not found.
    """
    ip, port = _get_svc_endpoint(host, KAFKA_EXTERNAL_BOOTSTRAP_SVC, None)
    if ip and port:
        return f"{ip}:{port}"
    return ""


# -------------------------------------------------------------------------
# VictoriaMetrics — dynamic endpoint + queries
# -------------------------------------------------------------------------

def get_vmselect_endpoint(host):
    """Get the VictoriaMetrics vmselect LoadBalancer IP and port.

    Reads from ``kubectl get svc`` — no hardcoded IPs or ports.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        tuple: ``(ip, port)`` or ``("", "")`` if not found.
    """
    return _get_svc_endpoint(host, SVC_VMSELECT, SVC_PORT_NAME_HTTP)


def query_vm_metric_names(host):
    """Query VictoriaMetrics for all metric names.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        list: Metric name strings, or empty list on failure.
    """
    ip, port = get_vmselect_endpoint(host)
    if not ip or not port:
        return []
    cmd = CMDS["vm_query_metric_names"].format(
        vmselect_ip=ip, vmselect_port=port,
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
        return data.get("data", [])
    except (json.JSONDecodeError, KeyError):
        return []


def query_vm_instant(host, query):
    """Run an instant query against VictoriaMetrics.

    Args:
        host: Testinfra host connection to the OIM.
        query: PromQL query string.

    Returns:
        list of result dicts, or empty list on failure.
    """
    ip, port = get_vmselect_endpoint(host)
    if not ip or not port:
        return []
    cmd = CMDS["vm_query_instant"].format(
        vmselect_ip=ip, vmselect_port=port, query=query,
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
        return data.get("data", {}).get("result", [])
    except (json.JSONDecodeError, KeyError):
        return []


# -------------------------------------------------------------------------
# iDRAC data in VictoriaMetrics — per service tag
# -------------------------------------------------------------------------

def verify_idrac_vm_data(host, service_tags):
    """Verify iDRAC telemetry data in VictoriaMetrics for service tags.

    Queries VictoriaMetrics for ``PowerEdge_*`` metrics labelled with
    each service tag to confirm data is flowing end-to-end.

    Args:
        host: Testinfra host connection to the OIM.
        service_tags: list of service tags to check (e.g. ["ABCD123"]).

    Returns:
        dict with keys: success, service_tag_results, found_tags,
        missing_tags, vmselect_ip, vmselect_port.
    """
    import urllib.parse

    ip, port = get_vmselect_endpoint(host)
    if not ip or not port:
        return {"success": False, "error": "vmselect endpoint not found"}

    service_tag_results = []
    found_tags = []
    missing_tags = []

    for stag in service_tags:
        raw_query = f'{{__name__=~"PowerEdge_.*",ServiceTag="{stag}"}}'
        encoded_query = urllib.parse.quote(raw_query)
        curl_cmd = CMDS["vm_query_idrac_service_tag"].format(
            vmselect_ip=ip, vmselect_port=port,
            encoded_query=encoded_query,
        )
        result = run_on_kube_vip(host, curl_cmd)

        try:
            response = json.loads(result.stdout) if result.rc == 0 else {}
            result_data = response.get("data", {}).get("result", [])
        except json.JSONDecodeError:
            result_data = []

        has_data = len(result_data) > 0
        sample_metrics = []
        latest_timestamp = 0

        if has_data:
            for item in result_data[:5]:
                metric = item.get("metric", {})
                value = item.get("value", [])
                metric_name = metric.get("__name__", "")
                ts = int(float(value[0])) if len(value) > 0 else 0
                val = value[1] if len(value) > 1 else ""
                latest_timestamp = max(latest_timestamp, ts)
                sample_metrics.append({
                    "metric_name": metric_name,
                    "value": val,
                    "timestamp": ts,
                })

        service_tag_results.append({
            "service_tag": stag,
            "found": has_data,
            "metric_count": len(result_data),
            "latest_timestamp": latest_timestamp,
            "sample_metrics": sample_metrics,
        })
        if has_data:
            found_tags.append(stag)
        else:
            missing_tags.append(stag)

    return {
        "success": len(missing_tags) == 0 and len(found_tags) > 0,
        "vmselect_ip": ip,
        "vmselect_port": port,
        "service_tag_results": service_tag_results,
        "found_tags": found_tags,
        "missing_tags": missing_tags,
    }


def get_idrac_service_tags(host):
    """Get activated iDRAC service tags from the telemetry status/report.

    Reads the idrac_telemetry_report.yml or queries MySQL in idrac pods
    to retrieve the set of activated service tags.

    Falls back to querying VictoriaMetrics for distinct ServiceTag labels
    on PowerEdge_* metrics.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        list: Service tag strings (e.g. ["ABCD123", "EFGH456"]).
    """
    # Try querying VictoriaMetrics for distinct ServiceTag values
    results = query_vm_instant(host, 'count by (ServiceTag) ({__name__=~"PowerEdge_.*"})')
    tags = []
    for item in results:
        tag = item.get("metric", {}).get("ServiceTag", "")
        if tag:
            tags.append(tag)
    return tags


# -------------------------------------------------------------------------
# VictoriaLogs — dynamic endpoint
# -------------------------------------------------------------------------

def get_vlselect_endpoint(host):
    """Get the VictoriaLogs vlselect LoadBalancer IP and port.

    Reads from ``kubectl get svc`` — no hardcoded IPs or ports.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        tuple: ``(ip, port)`` or ``("", "")`` if not found.
    """
    return _get_svc_endpoint(host, SVC_VLSELECT, SVC_PORT_NAME_HTTP)


# -------------------------------------------------------------------------
# Environment Variable Checks
# -------------------------------------------------------------------------

def check_env_vars_present(host):
    """Verify all required omnia.env variables are set on OIM.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, results (list), details, error.
    """
    required_vars = [
        "OMNIA_DATA_PATH",
        "OMNIA_PROJECT_NAME",
        "SYSTEM_ADMIN_NIC_IPV4",
        "SYSTEM_HOSTNAME",
        "SYSTEM_DOMAIN_NAME",
    ]
    results = []
    missing = []
    for var in required_vars:
        try:
            value = read_remote_env(host, var)
            results.append({"name": var, "found": True, "value": value})
        except ValueError:
            results.append({"name": var, "found": False, "value": ""})
            missing.append(var)

    details = "\n".join(
        f"  {r['name']}: {'set' if r['found'] else 'MISSING'}"
        for r in results
    )
    return {
        "success": len(missing) == 0,
        "results": results,
        "details": details,
        "error": f"Missing: {', '.join(missing)}" if missing else "",
    }
