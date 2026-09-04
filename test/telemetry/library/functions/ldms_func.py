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
LDMS Telemetry — Verification Functions.

Functions for verifying LDMS data in Kafka and VictoriaMetrics:
  - Get LDMS node hostnames from orchestrator inventory
  - Get sampler plugins from telemetry_config.yml
  - Verify LDMS data in Kafka ldms topic
"""

import json
import time
from typing import Any, Dict, List
from uuid import uuid4

from omnia_auto import (
    run_on_host,
    read_yaml_key,
    read_remote_yaml,
    get_inventory_hosts,
)

from .telemetry_func import (
    load_telemetry_config_from_target,
    run_on_kube_vip,
    _get_input_path,
)
from ..vars.common_vars import (
    CMDS,
    TELEMETRY_CONFIG_FILE,
    TELEMETRY_NAMESPACE,
    LDMS_KAFKA_LATEST_TIMEOUT_SECONDS,
    LDMS_KAFKA_EARLIEST_TIMEOUT_SECONDS,
    LDMS_KAFKA_CLOCK_SKEW_SECONDS,
    LDMS_KAFKA_LATEST_POLL_INTERVAL_SECONDS,
    LDMS_KAFKA_EARLIEST_POLL_INTERVAL_SECONDS,
    LDMS_KAFKA_OFFSET_LATEST,
    LDMS_KAFKA_OFFSET_EARLIEST,
    LDMS_KAFKA_CONSUMER_GROUP_TEMPLATE,
    LDMS_KAFKA_CONSUMER_NAME_TEMPLATE,
)
from ..vars.ome_vars import KAFKA_BRIDGE_SERVICE
from ..vars.ldms_vars import (
    LDMS_KAFKA_TOPIC,
    LDMS_FUNCTIONAL_GROUPS,
    LDMS_SAMPLER_SERVICE,
    LDMS_SAMPLER_CONF_PATH,
    LDMS_BINARY_PATH,
    LDMS_CMD_TEMPLATES,
)
from ..vars.ome_vars import KAFKA_BRIDGE_DEFAULT_PORT


# =========================================================================
# LDMS Configuration Functions
# =========================================================================

def get_ldms_sampler_plugins(host) -> List[str]:
    """Get list of LDMS sampler plugin names from telemetry_config.yml.

    Reads from ldms_configurations.sampler_plugins list.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        List of plugin names (e.g., ['meminfo', 'procstat2', 'vmstat']).
    """
    config = load_telemetry_config_from_target(host)
    if not config:
        return []

    ldms_cfg = read_yaml_key(config, "ldms_configurations", default={})
    sampler_configs = ldms_cfg.get("sampler_plugins", [])
    plugins = []

    for sampler in sampler_configs:
        plugin_name = sampler.get("plugin_name", "")
        if plugin_name:
            plugins.append(plugin_name)

    return plugins


def get_ldms_sampler_config(host) -> Dict[str, Any]:
    """Get full LDMS sampler configuration from telemetry_config.yml.

    Returns all sampler plugin configs including offset, interval, etc.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        Dict with keys: success, plugins (list of plugin configs), error.
    """
    input_path = _get_input_path(host)
    config_path = f"{input_path}/{TELEMETRY_CONFIG_FILE}"
    config = read_remote_yaml(host, config_path)

    if not config:
        return {
            "success": False,
            "plugins": [],
            "error": f"Could not read {config_path}",
        }

    ldms_cfg = read_yaml_key(config, "ldms_configurations", default={})
    sampler_configs = ldms_cfg.get("sampler_plugins", [])

    plugins = []
    for sampler in sampler_configs:
        plugin_name = sampler.get("plugin_name", "")
        if plugin_name:
            plugins.append({
                "plugin_name": plugin_name,
                "offset": sampler.get("offset", 0),
                "interval": sampler.get("interval", 30000000),
                "perm": sampler.get("perm", "0777"),
                "config": sampler.get("config", {}),
            })

    return {
        "success": True,
        "plugins": plugins,
        "plugin_names": [p["plugin_name"] for p in plugins],
    }


def get_domain_name_from_config(host) -> str:
    """Get domain name from environment on target host.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        Domain name string or empty string if not found.
    """
    result = run_on_host(host, "echo $SYSTEM_DOMAIN_NAME")
    if result.rc == 0 and result.stdout.strip():
        return result.stdout.strip()
    return ""


def get_cluster_inventory_path(host) -> str:
    """Get the cluster_inventory path from telemetry_config.yml.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        Path to orchestrator inventory file.
    """
    input_path = _get_input_path(host)
    config_path = f"{input_path}/{TELEMETRY_CONFIG_FILE}"
    cmd = CMDS["read_telemetry_config_field"].format(
        config_path=config_path, field="cluster_inventory",
    )
    result = run_on_host(host, cmd)
    if result.rc == 0 and result.stdout.strip():
        return result.stdout.strip()
    return ""


def get_ldms_hostnames_from_inventory(host) -> Dict[str, Any]:
    """Get LDMS node hostnames from orchestrator inventory.

    LDMS runs on the following functional groups (with architecture suffixes):
      - slurm_control_node_x86_64
      - slurm_node_x86_64, slurm_node_aarch64
      - login_node_x86_64, login_node_aarch64
      - login_compiler_node_x86_64, login_compiler_node_aarch64

    Uses the omnia_auto.get_inventory_hosts() function to parse the
    Ansible inventory file.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        Dict with keys: success, hostnames, by_group, error.
    """
    inventory_path = get_cluster_inventory_path(host)
    if not inventory_path:
        return {
            "success": False,
            "hostnames": [],
            "by_group": {},
            "error": "cluster_inventory path not found in telemetry_config.yml",
        }

    # Use omnia_auto.get_inventory_hosts() with exact matching
    # since LDMS_FUNCTIONAL_GROUPS already has full architecture suffixes
    return get_inventory_hosts(
        host, inventory_path, LDMS_FUNCTIONAL_GROUPS, prefix_match=False
    )


def get_ldms_nodes_with_ips(host) -> Dict[str, Any]:
    """Get LDMS nodes with their ansible_host IPs from inventory.

    Returns:
        Dict with success, nodes (list of {hostname, ansible_host, group}), error.
    """
    from omnia_auto import get_inventory_host_var

    inventory_path = get_cluster_inventory_path(host)
    if not inventory_path:
        return {
            "success": False,
            "nodes": [],
            "error": "cluster_inventory path not found in telemetry_config.yml",
        }

    # Get hostnames by group
    inv_result = get_inventory_hosts(host, inventory_path, LDMS_FUNCTIONAL_GROUPS)
    if not inv_result.get("success"):
        return {
            "success": False,
            "nodes": [],
            "error": inv_result.get("error", "Failed to get inventory hosts"),
        }

    nodes = []
    for group, hostnames in inv_result.get("by_group", {}).items():
        for hostname in hostnames:
            ansible_host = get_inventory_host_var(
                host, inventory_path, group, hostname, "ansible_host"
            )
            nodes.append({
                "hostname": hostname,
                "ansible_host": ansible_host or "",
                "group": group,
            })

    return {
        "success": len(nodes) > 0,
        "nodes": nodes,
        "error": "" if nodes else "No LDMS nodes found",
    }


def run_on_slurm_node(host, admin_ip: str, cmd: str):
    """Run command on remote slurm node via SSH from OIM.

    Args:
        host: Testinfra host connected to OIM.
        admin_ip: Admin IP (ansible_host) of the slurm node.
        cmd: Command to execute on remote node.

    Returns:
        Result with stdout, stderr, rc attributes.
    """
    escaped_cmd = cmd.replace('"', '\\"')
    ssh_cmd = (
        f'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '
        f'-o ConnectTimeout=10 root@{admin_ip} "{escaped_cmd}" 2>/dev/null'
    )
    return run_on_host(host, ssh_cmd)


# =========================================================================
# LDMS Sampler Service and Config Verification
# =========================================================================

def verify_ldms_sampler_service(host) -> Dict[str, Any]:
    """Verify ldmsd.sampler.service is running on all Slurm nodes.

    Checks systemctl is-active for LDMS sampler service on each node
    found in the cluster_inventory.

    Returns:
        Dict with success, total, running, failed, node_results, failed_nodes.
    """
    results = {
        "success": True,
        "total": 0,
        "running": 0,
        "failed": 0,
        "node_results": [],
        "failed_nodes": [],
    }

    # Get all LDMS nodes with IPs
    nodes_result = get_ldms_nodes_with_ips(host)
    if not nodes_result.get("success"):
        results["error"] = nodes_result.get("error", "Failed to get LDMS nodes")
        results["success"] = False
        return results

    nodes = nodes_result.get("nodes", [])
    results["total"] = len(nodes)

    for node in nodes:
        hostname = node.get("hostname", "")
        admin_ip = node.get("ansible_host", "")
        group = node.get("group", "")

        if not admin_ip:
            node_result = {
                "hostname": hostname,
                "admin_ip": "",
                "group": group,
                "service": LDMS_SAMPLER_SERVICE,
                "active": False,
                "status": "no ansible_host IP",
                "error": "Missing ansible_host in inventory",
            }
            results["node_results"].append(node_result)
            results["failed"] += 1
            results["failed_nodes"].append(hostname)
            results["success"] = False
            continue

        # Check service status
        cmd = LDMS_CMD_TEMPLATES["check_service_active"].format(
            service=LDMS_SAMPLER_SERVICE
        )
        result = run_on_slurm_node(host, admin_ip, cmd)
        is_active = result.rc == 0 and "active" in result.stdout.strip()

        node_result = {
            "hostname": hostname,
            "admin_ip": admin_ip,
            "group": group,
            "service": LDMS_SAMPLER_SERVICE,
            "active": is_active,
            "status": result.stdout.strip() if result.rc == 0 else "unknown",
        }

        results["node_results"].append(node_result)

        if is_active:
            results["running"] += 1
        else:
            results["failed"] += 1
            results["failed_nodes"].append(hostname)
            results["success"] = False

    return results


def verify_ldms_sampler_plugins(host) -> Dict[str, Any]:
    """Verify LDMS sampler plugins on nodes match telemetry_config.yml.

    Reads ldms_configurations.sampler_plugins from telemetry_config.yml and
    verifies /opt/ovis-ldms/etc/ldms/sampler.conf on each node has those plugins.

    Returns:
        Dict with success, expected_plugins, node_results.
    """
    results = {
        "success": True,
        "expected_plugins": [],
        "node_results": [],
    }

    # Get expected plugins from telemetry_config.yml
    plugins = get_ldms_sampler_plugins(host)
    if not plugins:
        results["error"] = "No ldms_configurations.sampler_plugins in telemetry_config.yml"
        results["success"] = False
        return results

    results["expected_plugins"] = plugins

    # Get all LDMS nodes with IPs
    nodes_result = get_ldms_nodes_with_ips(host)
    if not nodes_result.get("success"):
        results["error"] = nodes_result.get("error", "Failed to get LDMS nodes")
        results["success"] = False
        return results

    nodes = nodes_result.get("nodes", [])

    for node in nodes:
        hostname = node.get("hostname", "")
        admin_ip = node.get("ansible_host", "")
        group = node.get("group", "")

        node_result = {
            "hostname": hostname,
            "group": group,
            "success": True,
            "configured_plugins": [],
            "missing_plugins": [],
            "extra_plugins": [],
        }

        if not admin_ip:
            node_result["success"] = False
            node_result["error"] = "Missing ansible_host in inventory"
            results["node_results"].append(node_result)
            results["success"] = False
            continue

        # Read sampler.conf from node
        cmd = LDMS_CMD_TEMPLATES["read_sampler_conf"].format(
            conf_path=LDMS_SAMPLER_CONF_PATH
        )
        result = run_on_slurm_node(host, admin_ip, cmd)

        if result.rc != 0:
            node_result["success"] = False
            node_result["error"] = "Failed to read sampler.conf"
            results["node_results"].append(node_result)
            results["success"] = False
            continue

        # Parse sampler.conf to extract configured plugins
        configured_plugins = []
        lines = result.stdout.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("load name="):
                plugin_name = line.replace("load name=", "").strip()
                configured_plugins.append(plugin_name)

        node_result["configured_plugins"] = configured_plugins

        # Compare expected vs configured
        for plugin in plugins:
            if plugin not in configured_plugins:
                node_result["missing_plugins"].append(plugin)
                node_result["success"] = False

        # Check for extra plugins not in config
        for plugin in configured_plugins:
            if plugin not in plugins:
                node_result["extra_plugins"].append(plugin)

        results["node_results"].append(node_result)
        if not node_result["success"]:
            results["success"] = False

    return results


def verify_ldms_package_installed(host) -> Dict[str, Any]:
    """Verify LDMS package (ovis-ldms) is installed on all Slurm nodes.

    Checks if ldmsd binary exists at /opt/ovis-ldms/sbin/ldmsd on each node.

    Returns:
        Dict with success, total, installed, failed, node_results, failed_nodes.
    """
    results = {
        "success": True,
        "total": 0,
        "installed": 0,
        "failed": 0,
        "node_results": [],
        "failed_nodes": [],
    }

    # Get all LDMS nodes with IPs
    nodes_result = get_ldms_nodes_with_ips(host)
    if not nodes_result.get("success"):
        results["error"] = nodes_result.get("error", "Failed to get LDMS nodes")
        results["success"] = False
        return results

    nodes = nodes_result.get("nodes", [])
    results["total"] = len(nodes)

    for node in nodes:
        hostname = node.get("hostname", "")
        admin_ip = node.get("ansible_host", "")
        group = node.get("group", "")

        if not admin_ip:
            node_result = {
                "hostname": hostname,
                "admin_ip": "",
                "group": group,
                "installed": False,
                "error": "Missing ansible_host in inventory",
            }
            results["node_results"].append(node_result)
            results["failed"] += 1
            results["failed_nodes"].append(hostname)
            results["success"] = False
            continue

        # Check if ldmsd binary exists
        cmd = LDMS_CMD_TEMPLATES["check_ldms_binary"].format(
            binary_path=LDMS_BINARY_PATH
        )
        result = run_on_slurm_node(host, admin_ip, cmd)
        is_installed = result.rc == 0 and "installed" in result.stdout.strip()

        # Also check ldmsd version if installed
        version = ""
        if is_installed:
            ver_cmd = LDMS_CMD_TEMPLATES["get_ldms_version"].format(
                binary_path=LDMS_BINARY_PATH
            )
            ver_result = run_on_slurm_node(host, admin_ip, ver_cmd)
            if ver_result.rc == 0:
                version = ver_result.stdout.strip()

        node_result = {
            "hostname": hostname,
            "admin_ip": admin_ip,
            "group": group,
            "installed": is_installed,
            "version": version,
        }

        results["node_results"].append(node_result)

        if is_installed:
            results["installed"] += 1
        else:
            results["failed"] += 1
            results["failed_nodes"].append(hostname)
            results["success"] = False

    return results


# =========================================================================
# Kafka Bridge Functions (shared with OME)
# =========================================================================

def get_kafka_bridge_ip(host) -> str:
    """Get the Kafka bridge LoadBalancer IP.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        Bridge IP address or empty string.
    """
    cmd = LDMS_CMD_TEMPLATES["get_bridge_lb_ip"].format(
        service=KAFKA_BRIDGE_SERVICE,
        namespace=TELEMETRY_NAMESPACE,
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc == 0 and result.stdout.strip():
        return result.stdout.strip()
    return ""


def get_kafka_bridge_port(host) -> str:
    """Get the Kafka bridge LoadBalancer port.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        Port number as string.
    """
    cmd = LDMS_CMD_TEMPLATES["get_bridge_lb_port"].format(
        service=KAFKA_BRIDGE_SERVICE,
        namespace=TELEMETRY_NAMESPACE,
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc == 0 and result.stdout.strip():
        return result.stdout.strip()
    return KAFKA_BRIDGE_DEFAULT_PORT


# =========================================================================
# LDMS Kafka Data Verification
# =========================================================================

def verify_ldms_data_in_kafka(
    host,
    timeout_seconds: int = LDMS_KAFKA_LATEST_TIMEOUT_SECONDS,
    clock_skew_seconds: int = LDMS_KAFKA_CLOCK_SKEW_SECONDS,
) -> Dict[str, Any]:
    """Verify fresh LDMS data is flowing to the Kafka ldms topic.

    Gets expected hostnames from orchestrator inventory and sampler plugins
    from telemetry_config.yml. A unique consumer starts at the end of the
    topic and waits for a fresh record from every expected hostname/plugin
    instance. Historical records cannot satisfy this verification.

    Expected LDMS instance format: hostname.domain/plugin

    Args:
        host: Testinfra host connection to the OIM.
        timeout_seconds: Maximum time to wait for fresh data.
        clock_skew_seconds: Allowed LDMS node clock lag.

    Returns:
        Dict with keys: success, found_instances, missing_instances,
        hostname_results, error.
    """
    # Get expected hostnames
    inv_result = get_ldms_hostnames_from_inventory(host)
    if not inv_result["success"]:
        return {
            "success": False,
            "skipped": True,
            "reason": inv_result["error"],
        }

    hostnames = inv_result["hostnames"]
    by_group = inv_result["by_group"]

    # Get expected plugins
    plugins = get_ldms_sampler_plugins(host)
    if not plugins:
        return {
            "success": False,
            "skipped": True,
            "reason": "No LDMS sampler plugins configured",
        }

    # Get domain name
    domain_name = get_domain_name_from_config(host)
    if not domain_name:
        return {
            "success": False,
            "error": "Could not get domain name from environment",
        }

    # Get Kafka bridge endpoint
    bridge_ip = get_kafka_bridge_ip(host)
    if not bridge_ip:
        return {
            "success": False,
            "error": "Kafka bridge IP not found",
        }
    port = get_kafka_bridge_port(host)

    # Build expected instances: hostname.domain/plugin
    expected_instances = set()
    for hostname in hostnames:
        for plugin in plugins:
            instance = f"{hostname}.{domain_name}/{plugin}"
            expected_instances.add(instance)

    consumer_suffix = uuid4().hex
    consumer_group = LDMS_KAFKA_CONSUMER_GROUP_TEMPLATE.format(
        offset=LDMS_KAFKA_OFFSET_LATEST,
        suffix=consumer_suffix,
    )
    consumer_name = LDMS_KAFKA_CONSUMER_NAME_TEMPLATE.format(
        consumer_group=consumer_group,
    )

    found_instances = set()
    found_records = {}  # Store the newest fresh record per expected instance
    ignored_stale_records = 0
    invalid_timestamp_records = 0
    verification_started_at = time.time()
    fresh_after = verification_started_at - clock_skew_seconds

    try:
        # Step 1: Create a unique consumer at the current end of the topic.
        create_cmd = LDMS_CMD_TEMPLATES["rest_create_consumer"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
            offset=LDMS_KAFKA_OFFSET_LATEST,
        )
        result = run_on_kube_vip(host, create_cmd)
        if result.rc != 0 or "error_code" in result.stdout:
            return {
                "success": False,
                "bridge_ip": bridge_ip,
                "error": f"Failed to create consumer: {result.stdout}",
            }

        # Step 2: Subscribe to ldms topic
        subscribe_cmd = LDMS_CMD_TEMPLATES["rest_subscribe_topic"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
            topic=LDMS_KAFKA_TOPIC,
        )
        result = run_on_kube_vip(host, subscribe_cmd)
        if result.rc != 0 or "error_code" in result.stdout:
            return {
                "success": False,
                "bridge_ip": bridge_ip,
                "error": f"Failed to subscribe consumer: {result.stdout}",
            }

        # Step 3: Consume records with timeout
        consume_cmd = LDMS_CMD_TEMPLATES["rest_consume_records"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
        )

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            result = run_on_kube_vip(host, consume_cmd)

            if result.stdout.strip() and result.stdout.strip().startswith("["):
                try:
                    records = json.loads(result.stdout)
                    for record in records:
                        value = record.get("value", {})
                        # LDMS record format: {"instance": "hostname.domain/plugin", ...}
                        instance = value.get("instance", "")
                        if instance not in expected_instances:
                            continue

                        try:
                            record_timestamp = float(value.get("timestamp"))
                        except (TypeError, ValueError):
                            invalid_timestamp_records += 1
                            continue

                        if record_timestamp < fresh_after:
                            ignored_stale_records += 1
                            continue

                        previous_record = found_records.get(instance, {})
                        previous_value = previous_record.get("value", {})
                        try:
                            previous_timestamp = float(
                                previous_value.get("timestamp")
                            )
                        except (TypeError, ValueError):
                            previous_timestamp = float("-inf")

                        if record_timestamp >= previous_timestamp:
                            found_records[instance] = record
                            found_instances.add(instance)
                except json.JSONDecodeError:
                    pass

            # Break when all expected instances found
            if found_instances >= expected_instances:
                break

            time.sleep(LDMS_KAFKA_LATEST_POLL_INTERVAL_SECONDS)

    finally:
        # Step 4: Delete consumer (cleanup)
        delete_cmd = LDMS_CMD_TEMPLATES["rest_delete_consumer"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
        )
        run_on_kube_vip(host, delete_cmd)

    # Analyze results
    missing_instances = expected_instances - found_instances

    # Build per-hostname summary
    found_hostnames = set()
    for inst in found_instances:
        if "/" in inst:
            host_part = inst.split("/")[0]
            if "." in host_part:
                found_hostnames.add(host_part.split(".")[0])

    missing_hostnames = set(hostnames) - found_hostnames

    # Build detailed results per hostname
    hostname_results = []
    for hostname in hostnames:
        host_plugins_found = []
        host_plugins_missing = []
        for plugin in plugins:
            expected_inst = f"{hostname}.{domain_name}/{plugin}"
            if expected_inst in found_instances:
                record = found_records.get(expected_inst, {})
                host_plugins_found.append({
                    "plugin": plugin,
                    "record": record,
                })
            else:
                host_plugins_missing.append(plugin)

        # Find which group this hostname belongs to
        host_group = "unknown"
        for grp, grp_hosts in by_group.items():
            if hostname in grp_hosts:
                host_group = grp
                break

        hostname_results.append({
            "hostname": hostname,
            "functional_group": host_group,
            "found": len(host_plugins_found) > 0,
            "all_plugins_found": len(host_plugins_missing) == 0,
            "plugins_found": host_plugins_found,
            "plugins_missing": host_plugins_missing,
            "plugins_expected": plugins,
        })

    # Build results grouped by functional_group
    results_by_group = {}
    for hr in hostname_results:
        fg = hr.get("functional_group", "unknown")
        if fg not in results_by_group:
            results_by_group[fg] = []
        results_by_group[fg].append(hr)

    # Build error message
    success = len(missing_instances) == 0
    if success:
        error_msg = ""
    elif missing_hostnames:
        error_msg = (
            "Fresh LDMS data missing from hostnames: "
            f"{sorted(missing_hostnames)}"
        )
    else:
        # Some hosts have partial data
        missing_details = []
        for hr in hostname_results:
            if hr.get("plugins_missing"):
                missing_details.append(
                    f"{hr['hostname']}: missing {hr['plugins_missing']}"
                )
        error_msg = f"Fresh LDMS plugins missing: {'; '.join(missing_details)}"

    return {
        "success": success,
        "skipped": False,
        "bridge_ip": bridge_ip,
        "domain_name": domain_name,
        "expected_hostnames": hostnames,
        "expected_plugins": plugins,
        "expected_instance_count": len(expected_instances),
        "verification_started_at": verification_started_at,
        "fresh_after": fresh_after,
        "ignored_stale_record_count": ignored_stale_records,
        "invalid_timestamp_record_count": invalid_timestamp_records,
        "found_instances": sorted(found_instances),
        "found_instance_count": len(found_instances),
        "missing_instances": sorted(missing_instances),
        "found_hostnames": sorted(found_hostnames),
        "missing_hostnames": sorted(missing_hostnames),
        "hostname_results": hostname_results,
        "results_by_group": results_by_group,
        "error": error_msg,
    }


def verify_ldms_earliest_data_in_kafka(
    host,
    timeout_seconds: int = LDMS_KAFKA_EARLIEST_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Get earliest LDMS data from Kafka for every expected instance.

    Uses a unique consumer group with the earliest offset. Kafka group
    subscription assigns all topic partitions dynamically, so this remains
    correct if the LDMS topic partition count changes.

    Args:
        host: Testinfra host connection to the OIM.
        timeout_seconds: Maximum time to search for all instances.

    Returns:
        Dict with keys: success, earliest_records, hostname_results, error.
    """
    # Get expected hostnames
    inv_result = get_ldms_hostnames_from_inventory(host)
    if not inv_result["success"]:
        return {
            "success": False,
            "skipped": True,
            "reason": inv_result["error"],
        }

    hostnames = inv_result["hostnames"]
    by_group = inv_result["by_group"]

    # Get expected plugins
    plugins = get_ldms_sampler_plugins(host)
    if not plugins:
        return {
            "success": False,
            "skipped": True,
            "reason": "No LDMS sampler plugins configured",
        }

    # Get domain name
    domain_name = get_domain_name_from_config(host)
    if not domain_name:
        return {
            "success": False,
            "error": "Could not get domain name from environment",
        }

    # Get Kafka bridge endpoint
    bridge_ip = get_kafka_bridge_ip(host)
    if not bridge_ip:
        return {
            "success": False,
            "error": "Kafka bridge IP not found",
        }
    port = get_kafka_bridge_port(host)

    expected_instances = {
        f"{hostname}.{domain_name}/{plugin}"
        for hostname in hostnames
        for plugin in plugins
    }
    consumer_suffix = uuid4().hex
    consumer_group = LDMS_KAFKA_CONSUMER_GROUP_TEMPLATE.format(
        offset=LDMS_KAFKA_OFFSET_EARLIEST,
        suffix=consumer_suffix,
    )
    consumer_name = LDMS_KAFKA_CONSUMER_NAME_TEMPLATE.format(
        consumer_group=consumer_group,
    )

    found_records = {}  # Store first record per instance
    total_records = 0

    try:
        # Step 1: Create a unique group whose uncommitted offsets start earliest.
        create_cmd = LDMS_CMD_TEMPLATES["rest_create_consumer"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
            offset=LDMS_KAFKA_OFFSET_EARLIEST,
        )
        result = run_on_kube_vip(host, create_cmd)
        if result.rc != 0 or "error_code" in result.stdout:
            return {
                "success": False,
                "bridge_ip": bridge_ip,
                "error": f"Failed to create consumer: {result.stdout}",
            }

        # Step 2: Subscribe so Kafka dynamically assigns every topic partition.
        subscribe_cmd = LDMS_CMD_TEMPLATES["rest_subscribe_topic"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
            topic=LDMS_KAFKA_TOPIC,
        )
        result = run_on_kube_vip(host, subscribe_cmd)
        if result.rc != 0 or "error_code" in result.stdout:
            return {
                "success": False,
                "bridge_ip": bridge_ip,
                "error": f"Failed to subscribe consumer: {result.stdout}",
            }

        # Step 3: Consume until every expected hostname/plugin is represented.
        consume_cmd = LDMS_CMD_TEMPLATES["rest_consume_records"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
        )

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            result = run_on_kube_vip(host, consume_cmd)

            if result.stdout.strip() and result.stdout.strip().startswith("["):
                try:
                    records = json.loads(result.stdout)
                    for record in records:
                        total_records += 1
                        value = record.get("value", {})
                        instance = value.get("instance", "")
                        if (
                            instance in expected_instances
                            and instance not in found_records
                        ):
                            found_records[instance] = record
                except json.JSONDecodeError:
                    pass

            # Stop only after all expected hostname/plugin instances are found.
            if set(found_records) >= expected_instances:
                break

            time.sleep(LDMS_KAFKA_EARLIEST_POLL_INTERVAL_SECONDS)

    finally:
        # Cleanup consumer
        delete_cmd = LDMS_CMD_TEMPLATES["rest_delete_consumer"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
        )
        run_on_kube_vip(host, delete_cmd)

    found_instances = set(found_records)
    missing_instances = expected_instances - found_instances
    found_hostnames = {
        instance.split("/", maxsplit=1)[0].split(".", maxsplit=1)[0]
        for instance in found_instances
    }
    missing_hostnames = set(hostnames) - found_hostnames

    # Build results per hostname
    hostname_results = []
    for hostname in hostnames:
        host_plugins_found = []
        host_plugins_missing = []
        for plugin in plugins:
            expected_inst = f"{hostname}.{domain_name}/{plugin}"
            if expected_inst in found_records:
                host_plugins_found.append({
                    "plugin": plugin,
                    "record": found_records[expected_inst],
                })
            else:
                host_plugins_missing.append(plugin)

        # Find which group this hostname belongs to
        host_group = "unknown"
        for grp, grp_hosts in by_group.items():
            if hostname in grp_hosts:
                host_group = grp
                break

        hostname_results.append({
            "hostname": hostname,
            "functional_group": host_group,
            "found": len(host_plugins_found) > 0,
            "all_plugins_found": len(host_plugins_missing) == 0,
            "plugins_found": host_plugins_found,
            "plugins_missing": host_plugins_missing,
            "plugins_expected": plugins,
        })

    # Build results grouped by functional_group
    results_by_group = {}
    for hr in hostname_results:
        fg = hr.get("functional_group", "unknown")
        if fg not in results_by_group:
            results_by_group[fg] = []
        results_by_group[fg].append(hr)

    # Success requires every configured plugin from every expected hostname.
    success = not missing_instances
    if success:
        error_msg = ""
    elif missing_hostnames:
        error_msg = f"Missing hostnames: {sorted(missing_hostnames)}"
    else:
        error_msg = f"Missing instances: {sorted(missing_instances)}"

    return {
        "success": success,
        "skipped": False,
        "bridge_ip": bridge_ip,
        "domain_name": domain_name,
        "expected_hostnames": hostnames,
        "expected_plugins": plugins,
        "expected_instance_count": len(expected_instances),
        "total_records_read": total_records,
        "found_instances": sorted(found_instances),
        "found_instance_count": len(found_instances),
        "missing_instances": sorted(missing_instances),
        "found_hostnames": sorted(found_hostnames),
        "missing_hostnames": sorted(missing_hostnames),
        "hostname_results": hostname_results,
        "results_by_group": results_by_group,
        "error": error_msg,
    }
