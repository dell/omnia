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
Telemetry — iDRAC Source Verification Functions.

Functions for verifying iDRAC telemetry pods, MySQL data,
and receiver metrics collection.
"""

import re
import shlex

from omnia_auto import run_on_host

from ..vars.common_vars import (
    IDRAC_POD_PREFIX,
    TELEMETRY_NAMESPACE,
)
from .telemetry_func import (
    _get_input_path,
    get_output_path,
    load_telemetry_config_from_target,
    run_on_kube_vip,
)

# -------------------------------------------------------------------------
# BMC Group Data — pod count scaling
# -------------------------------------------------------------------------

def get_bmc_group_data_path(host):
    """Resolve the deployed BMC inventory path on the OIM.

    ``telemetry_config.yml`` is loaded from the environment-derived project
    input directory. An explicit ``bmc_group_data_path`` wins; otherwise the
    CSV is resolved alongside that deployed configuration.

    Args:
        host: Testinfra host (OIM).

    Returns:
        Absolute path to bmc_group_data.csv on the OIM.
    """
    config = load_telemetry_config_from_target(host)
    idrac_config = config.get("idrac_telemetry_configurations", {})
    if not isinstance(idrac_config, dict):
        idrac_config = {}

    configured_path = str(
        idrac_config.get("bmc_group_data_path", "")
    ).strip()
    if configured_path:
        if configured_path.startswith("/"):
            return configured_path
        return f"{_get_input_path(host)}/{configured_path}"

    return f"{_get_input_path(host)}/bmc_group_data.csv"


def get_bmc_group_data(host, csv_path=None):
    """Read bmc_group_data.csv from the telemetry input on the OIM.

    The deployed telemetry configuration and the environment-derived project
    input directory determine the default path.

    Args:
        host: Testinfra host (OIM).

    Returns:
        list of dicts with bmc_ip, group_name, parent keys.
        Empty list if the file is not found.
    """
    path = csv_path or get_bmc_group_data_path(host)
    result = run_on_host(host, "cat -- %s", path)
    if result.rc != 0 or not result.stdout.strip():
        return []

    entries = []
    for line in result.stdout.strip().split("\n"):
        if line.startswith(("BMC_IP", "#")):
            continue
        parts = line.split(",")
        if parts:
            entries.append({
                "bmc_ip": parts[0].strip() if len(parts) > 0 else "",
                "group_name": parts[1].strip() if len(parts) > 1 else "",
                "parent": parts[2].strip() if len(parts) > 2 else "",
            })

    return entries


def get_idrac_pod_inventory(host):
    """Map StatefulSet pod ordinals to the BMCs assigned at deployment."""
    bmc_data = get_bmc_group_data(host)
    inventory = {f"{IDRAC_POD_PREFIX}-0": []}
    parent_ips = {}

    for entry in bmc_data:
        bmc_ip = entry.get("bmc_ip", "")
        parent = entry.get("parent", "")
        if not bmc_ip:
            continue
        if parent:
            parent_ips.setdefault(parent, []).append(bmc_ip)
        else:
            inventory[f"{IDRAC_POD_PREFIX}-0"].append(bmc_ip)

    for ordinal, parent in enumerate(sorted(parent_ips), start=1):
        inventory[f"{IDRAC_POD_PREFIX}-{ordinal}"] = parent_ips[parent]

    return inventory


def _parse_report_ip_section(report, heading):
    """Return list items immediately following an iDRAC report heading."""
    lines = report.splitlines()
    try:
        start = next(
            index for index, line in enumerate(lines)
            if line.strip() == heading
        )
    except StopIteration:
        return []

    ips = []
    for line in lines[start + 1:]:
        stripped = line.strip()
        if not stripped:
            if ips:
                break
            continue
        match = re.fullmatch(r"-\s*(\S+)", stripped)
        if not match:
            break
        ips.append(match.group(1))
    return ips


def get_idrac_report_ips(host):
    """Read activated and unsupported BMC IPs from the project report."""
    report_path = f"{get_output_path(host)}/idrac_telemetry_report.yml"
    quoted_path = shlex.quote(report_path)
    stat_result = run_on_host(
        host, f"stat -c %Y {quoted_path} 2>/dev/null",
    )
    if stat_result.rc != 0 or not stat_result.stdout.strip():
        return {"activated": [], "unsupported": []}

    result = run_on_host(host, f"cat {quoted_path} 2>/dev/null")
    if result.rc != 0 or not result.stdout.strip():
        return {"activated": [], "unsupported": []}

    return {
        "activated": _parse_report_ip_section(
            result.stdout, "Telemetry activated IPs List:",
        ),
        "unsupported": _parse_report_ip_section(
            result.stdout, "Telemetry not supported IPs List:",
        ),
    }


def _expected_idle_pods(host):
    """Return intentionally idle pods and their assigned inventory."""
    inventory = get_idrac_pod_inventory(host)
    unsupported = set(get_idrac_report_ips(host)["unsupported"])
    expected = {
        pod_name
        for pod_name, assigned_ips in inventory.items()
        if assigned_ips and set(assigned_ips).issubset(unsupported)
    }
    return expected, inventory


def get_idrac_expected_pod_count(host):
    """Calculate expected iDRAC StatefulSet replica count.

    Expected count = number of unique parent service tags + 1 (for MGMT pod).
    If bmc_group_data.csv is not found, returns 0 (skip test).

    Args:
        host: Testinfra host (OIM).

    Returns:
        dict with expected_count, parents, bmc_data_found.
    """
    bmc_data_path = get_bmc_group_data_path(host)
    bmc_data = get_bmc_group_data(host, bmc_data_path)
    if not bmc_data:
        return {
            "expected_count": 0,
            "parents": [],
            "bmc_entries": 0,
            "bmc_data_found": False,
            "bmc_data_path": bmc_data_path,
        }

    # Count unique non-empty parent service tags
    parents = list(set(
        e["parent"] for e in bmc_data if e.get("parent")
    ))
    # Expected = parent nodes + 1 (for MGMT layer pod-0)
    expected = len(parents) + 1

    return {
        "expected_count": expected,
        "parents": parents,
        "bmc_entries": len(bmc_data),
        "bmc_data_found": True,
        "bmc_data_path": bmc_data_path,
    }


def verify_idrac_pod_count(host):
    """Verify iDRAC telemetry pod count matches expected from bmc_group_data.csv.

    Args:
        host: Testinfra host (OIM).

    Returns:
        dict with success, expected_count, actual_count, pods, bmc_data_found.
    """
    count_info = get_idrac_expected_pod_count(host)
    if not count_info["bmc_data_found"]:
        return {
            "success": False,
            "bmc_data_found": False,
            "expected_count": 0,
            "actual_count": 0,
            "pods": [],
            "skip": True,
            "skip_reason": (
                "bmc_group_data.csv not found or empty at "
                f"{count_info['bmc_data_path']}"
            ),
        }

    # Count actual iDRAC pods
    cmd = (
        f"kubectl get pods -n {TELEMETRY_NAMESPACE}"
        f" --no-headers -o custom-columns='NAME:.metadata.name'"
        f" | grep '^{IDRAC_POD_PREFIX}'"
    )
    result = run_on_kube_vip(host, cmd)
    pods = []
    if result.rc == 0 and result.stdout.strip():
        pods = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]

    actual = len(pods)
    expected = count_info["expected_count"]
    return {
        "success": actual == expected,
        "bmc_data_found": True,
        "expected_count": expected,
        "actual_count": actual,
        "parents": count_info["parents"],
        "bmc_entries": count_info["bmc_entries"],
        "bmc_data_path": count_info["bmc_data_path"],
        "pods": pods,
    }


# -------------------------------------------------------------------------
# MySQL Data Verification
# -------------------------------------------------------------------------

def get_mysql_ips_from_pod(host, pod_name):
    """Get IPs from MySQL services table in an iDRAC telemetry pod.

    Args:
        host: Testinfra host (OIM).
        pod_name: Pod name (e.g. idrac-telemetry-0).

    Returns:
        dict with success, mysql_ips, and error.
    """
    cmd = (
        f"kubectl exec {pod_name} -n {TELEMETRY_NAMESPACE}"
        " -c mysqldb -- sh -c '"
        "MYSQL_PWD=\"$MYSQL_PASSWORD\" "
        "mysql -N -u\"$MYSQL_USER\" \"$MYSQL_DATABASE\" "
        "-e \"SELECT ip FROM services\"'"
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0:
        error = result.stderr.strip() or result.stdout.strip()
        return {
            "success": False,
            "mysql_ips": [],
            "error": error or f"MySQL query failed with rc={result.rc}",
        }

    mysql_ips = [
        ip.strip() for ip in result.stdout.strip().split("\n")
        if ip.strip() and not ip.startswith("mysql:")
    ]
    return {
        "success": True,
        "mysql_ips": mysql_ips,
        "error": "",
    }


def verify_mysql_data_in_pods(host):
    """Verify MySQL data in all iDRAC telemetry pods.

    For each pod, retrieves IPs from the MySQL services table
    and reports them. Useful for verifying that BMC IPs from
    bmc_group_data.csv have been registered.

    Args:
        host: Testinfra host (OIM).

    Returns:
        dict with success, pod_results list, each containing
        pod_name, mysql_ips, ip_count.
    """
    # Get all iDRAC pods
    cmd = (
        f"kubectl get pods -n {TELEMETRY_NAMESPACE}"
        f" --no-headers -o custom-columns='NAME:.metadata.name'"
        f" | grep '^{IDRAC_POD_PREFIX}'"
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "pod_results": [],
            "error": "No iDRAC telemetry pods found",
        }

    pods = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
    expected_idle_pods, pod_inventory = _expected_idle_pods(host)
    pod_results = []
    all_have_data = True

    # Check if any BMC IPs are configured at all
    total_assigned_ips = sum(len(ips) for ips in pod_inventory.values())
    if total_assigned_ips == 0:
        return {
            "success": False,
            "pod_results": [],
            "total_pods": len(pods),
            "error": "No BMC IPs configured in bmc_group_data.csv - iDRAC telemetry requires at least one BMC IP",
        }

    for pod_name in sorted(pods):
        query_result = get_mysql_ips_from_pod(host, pod_name)
        mysql_ips = query_result["mysql_ips"]
        has_data = query_result["success"] and len(mysql_ips) > 0
        expected_idle = (
            query_result["success"]
            and not has_data
            and pod_name in expected_idle_pods
        )
        if not (has_data or expected_idle):
            all_have_data = False
        pod_results.append({
            "pod_name": pod_name,
            "mysql_ips": mysql_ips,
            "ip_count": len(mysql_ips),
            "has_data": has_data,
            "expected_idle": expected_idle,
            "assigned_ips": pod_inventory.get(pod_name, []),
            "query_success": query_result["success"],
            "error": query_result["error"],
        })

    return {
        "success": all_have_data,
        "pod_results": pod_results,
        "total_pods": len(pods),
    }


# -------------------------------------------------------------------------
# Receiver Metrics Collection
# -------------------------------------------------------------------------

def verify_receiver_collecting(host):
    """Verify idrac-telemetry-receiver containers are collecting metrics.

    Checks the receiver container logs in each iDRAC pod for
    ``Got new report for /redfish/v1/TelemetryService/MetricReports``
    entries indicating active SSE connections.

    Args:
        host: Testinfra host (OIM).

    Returns:
        dict with success, pod_results list.
    """
    # Get all iDRAC pods
    cmd = (
        f"kubectl get pods -n {TELEMETRY_NAMESPACE}"
        f" --no-headers -o custom-columns='NAME:.metadata.name'"
        f" | grep '^{IDRAC_POD_PREFIX}'"
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "pod_results": [],
            "error": "No iDRAC telemetry pods found",
        }

    pods = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
    expected_idle_pods, pod_inventory = _expected_idle_pods(host)
    pod_results = []
    all_collecting = True

    # Check if any BMC IPs are configured at all
    total_assigned_ips = sum(len(ips) for ips in pod_inventory.values())
    if total_assigned_ips == 0:
        return {
            "success": False,
            "pod_results": [],
            "total_pods": len(pods),
            "error": "No BMC IPs configured in bmc_group_data.csv - iDRAC telemetry requires at least one BMC IP",
        }

    for pod_name in sorted(pods):
        # Get last 200 lines of receiver logs
        log_cmd = (
            f"kubectl logs {pod_name} -n {TELEMETRY_NAMESPACE}"
            f" -c idrac-telemetry-receiver --tail=200 2>/dev/null"
        )
        log_result = run_on_kube_vip(host, log_cmd)

        reports = []
        service_tags = set()
        if log_result.rc == 0 and log_result.stdout:
            for line in log_result.stdout.split("\n"):
                if "Got new report for" in line and "MetricReports" in line:
                    # Extract metric report name
                    if "/MetricReports/" in line:
                        report_name = line.split("/MetricReports/")[-1].strip()
                        reports.append(report_name)
                # Look for service tag connections
                if "SSE connected" in line or "ServiceTag" in line:
                    # Extract service tag if present
                    tag_match = re.search(r'ServiceTag[=: ]+(\w+)', line)
                    if tag_match:
                        service_tags.add(tag_match.group(1))

        collecting = len(reports) > 0
        expected_idle = (
            log_result.rc == 0
            and not collecting
            and pod_name in expected_idle_pods
        )
        if not (collecting or expected_idle):
            all_collecting = False

        pod_results.append({
            "pod_name": pod_name,
            "collecting": collecting,
            "expected_idle": expected_idle,
            "assigned_ips": pod_inventory.get(pod_name, []),
            "report_count": len(reports),
            "sample_reports": reports[:3],
            "service_tags": list(service_tags),
        })

    return {
        "success": all_collecting,
        "pod_results": pod_results,
        "total_pods": len(pods),
    }