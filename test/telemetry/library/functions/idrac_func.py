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

import json
import re
import shlex
import time
from uuid import uuid4

from omnia_auto import run_on_host

from .ldms_func import get_kafka_bridge_ip, get_kafka_bridge_port

from ..vars.common_vars import (
    IDRAC_KAFKA_TOPIC,
    IDRAC_POD_PREFIX,
    IDRAC_STS_NAME,
    TELEMETRY_NAMESPACE,
)
from .telemetry_func import (
    _get_input_path,
    get_output_path,
    get_vmselect_endpoint,
    load_telemetry_config_from_target,
    read_remote_env,
    run_on_kube_vip,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
)

_IDRAC_PVC_PREFIX = "mysqldb-pvc-idrac-telemetry-"
_IDRAC_VM_MATCH = '{__name__=~"PowerEdge_.*"}'


def get_idrac_telemetry_config_path(host):
    """Return the active project telemetry_config.yml path on the OIM."""
    return f"{_get_input_path(host)}/telemetry_config.yml"


def set_idrac_metrics_enabled(host, enabled):  # pylint: disable=too-many-function-args
    """Atomically update only the active iDRAC metrics flag on the OIM."""
    config_path = get_idrac_telemetry_config_path(host)
    script = (
        "import os,sys,tempfile,yaml;"
        "path=sys.argv[1];enabled=sys.argv[2].lower()=='true';"
        "data=yaml.safe_load(open(path,encoding='utf-8')) or {};"
        "data.setdefault('telemetry_sources',{})"
        ".setdefault('idrac',{})['metrics_enabled']=enabled;"
        "fd,tmp=tempfile.mkstemp(prefix='.idrac-lifecycle-',"
        "dir=os.path.dirname(path),text=True);"
        "f=os.fdopen(fd,'w',encoding='utf-8');"
        "yaml.safe_dump(data,f,sort_keys=False);f.flush();"
        "os.fsync(f.fileno());f.close();os.replace(tmp,path)"
    )
    result = run_on_host(  # pylint: disable=too-many-function-args
        host, "python3 -c %s %s %s", script, config_path,
        "true" if enabled else "false",
    )
    return {
        "success": result.rc == 0,
        "path": config_path,
        "error": result.stderr.strip(),
    }


def get_idrac_lifecycle_state(host):  # pylint: disable=too-many-locals
    """Return StatefulSet, pod, and PVC identity for lifecycle assertions.

    PVC UID and ``spec.volumeName`` are retained so a lifecycle test can
    distinguish reuse from creation of a same-named replacement.
    """
    sts_result = run_on_kube_vip(
        host,
        f"kubectl get statefulset {IDRAC_STS_NAME} "
        f"-n {TELEMETRY_NAMESPACE} -o json 2>/dev/null",
    )
    if sts_result.rc != 0 or not sts_result.stdout.strip():
        return {
            "success": False,
            "error": "iDRAC StatefulSet not found",
            "statefulset": {},
            "pods": [],
            "pvcs": {},
        }

    pods_result = run_on_kube_vip(
        host,
        f"kubectl get pods -n {TELEMETRY_NAMESPACE} "
        f"-l app={IDRAC_STS_NAME} -o json 2>/dev/null",
    )
    pvc_result = run_on_kube_vip(
        host,
        f"kubectl get pvc -n {TELEMETRY_NAMESPACE} -o json 2>/dev/null",
    )
    topic_result = run_on_kube_vip(
        host,
        f"kubectl get kafkatopic {IDRAC_KAFKA_TOPIC} "
        f"-n {TELEMETRY_NAMESPACE} -o json 2>/dev/null",
    )

    try:
        sts = json.loads(sts_result.stdout)
        pods_doc = json.loads(pods_result.stdout or '{"items": []}')
        pvc_doc = json.loads(pvc_result.stdout or '{"items": []}')
        topic_doc = json.loads(topic_result.stdout or '{}')
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "error": f"Failed to parse iDRAC lifecycle resources: {exc}",
            "statefulset": {},
            "pods": [],
            "pvcs": {},
        }

    pods = []
    for item in pods_doc.get("items", []):
        statuses = item.get("status", {}).get("containerStatuses", [])
        pods.append({
            "name": item.get("metadata", {}).get("name", ""),
            "uid": item.get("metadata", {}).get("uid", ""),
            "phase": item.get("status", {}).get("phase", ""),
            "ready": bool(statuses) and all(
                status.get("ready", False) for status in statuses
            ),
        })

    pvcs = {}
    for item in pvc_doc.get("items", []):
        metadata = item.get("metadata", {})
        name = metadata.get("name", "")
        if not name.startswith(_IDRAC_PVC_PREFIX):
            continue
        pvcs[name] = {
            "uid": metadata.get("uid", ""),
            "volume_name": item.get("spec", {}).get("volumeName", ""),
            "phase": item.get("status", {}).get("phase", ""),
            "capacity": (
                item.get("status", {}).get("capacity", {}).get("storage", "")
            ),
        }

    metadata = sts.get("metadata", {})
    spec = sts.get("spec", {})
    status = sts.get("status", {})
    annotation = (
        metadata.get("annotations", {})
        .get("telemetry.omnia.dell.com/desired-replicas", "")
    )
    command_ok = (
        pods_result.rc == 0
        and pvc_result.rc == 0
        and topic_result.rc == 0
    )
    return {
        "success": command_ok,
        "error": "" if command_ok else (
            pods_result.stderr.strip()
            or pvc_result.stderr.strip()
            or topic_result.stderr.strip()
        ),
        "statefulset": {
            "uid": metadata.get("uid", ""),
            "replicas": int(spec.get("replicas") or 0),
            "ready_replicas": int(status.get("readyReplicas") or 0),
            "desired_replicas_annotation": int(annotation or 0),
        },
        "pods": pods,
        "pvcs": pvcs,
        "kafka_topic": {
            "uid": topic_doc.get("metadata", {}).get("uid", ""),
            "topic_id": topic_doc.get("status", {}).get("topicId", ""),
        },
    }


def wait_for_idrac_replicas(host, replicas, timeout=600, poll_interval=10):
    """Wait until iDRAC reaches the requested replica state."""
    started = time.time()
    last_state = {}
    while time.time() - started < timeout:
        last_state = get_idrac_lifecycle_state(host)
        sts = last_state.get("statefulset", {})
        pods = last_state.get("pods", [])
        if replicas == 0:
            ready = sts.get("replicas") == 0 and not pods
        else:
            ready = (
                sts.get("replicas") == replicas
                and sts.get("ready_replicas") == replicas
                and len(pods) == replicas
                and all(pod.get("ready") for pod in pods)
            )
        if ready:
            return {"success": True, "state": last_state, "error": ""}
        time.sleep(poll_interval)
    return {
        "success": False,
        "state": last_state,
        "error": f"iDRAC did not reach {replicas} replicas within {timeout}s",
    }


def probe_fresh_idrac_kafka_records(host, timeout_seconds=90):  # pylint: disable=too-many-locals
    """Consume only iDRAC records produced after this probe starts.

    A unique Kafka Bridge consumer starts at ``latest`` with auto-commit
    disabled. It is always removed, and only record metadata is returned.
    """
    bridge_ip = get_kafka_bridge_ip(host)
    bridge_port = get_kafka_bridge_port(host) if bridge_ip else ""
    if not bridge_ip or not bridge_port:
        return {
            "success": False,
            "records": [],
            "error": "Kafka Bridge endpoint not found",
        }

    consumer_group = f"idrac-lifecycle-{uuid4().hex}"
    consumer_name = "fresh-record-check"
    base_uri = (
        f"https://{bridge_ip}:{bridge_port}/consumers/{consumer_group}"
        f"/instances/{consumer_name}"
    )
    create_payload = json.dumps({
        "name": consumer_name,
        "format": "binary",
        "auto.offset.reset": "latest",
        "enable.auto.commit": False,
    }, separators=(",", ":"))
    create_cmd = (
        f"curl -kfsS --max-time 15 -X POST "
        f"https://{bridge_ip}:{bridge_port}/consumers/{consumer_group} "
        "-H 'Content-Type: application/vnd.kafka.v2+json' "
        f"-d '{create_payload}'"
    )
    subscribe_cmd = (
        f"curl -kfsS --max-time 15 -X POST {base_uri}/subscription "
        "-H 'Content-Type: application/vnd.kafka.v2+json' "
        f"-d '{{\"topics\":[\"{IDRAC_KAFKA_TOPIC}\"]}}'"
    )
    consume_cmd = (
        f"curl -kfsS --max-time 15 -X GET {base_uri}/records "
        "-H 'Accept: application/vnd.kafka.binary.v2+json'"
    )
    delete_cmd = f"curl -kfsS --max-time 15 -X DELETE {base_uri}"

    records = []
    error = ""
    try:
        create = run_on_kube_vip(host, create_cmd)
        if create.rc != 0:
            return {
                "success": False,
                "records": [],
                "error": create.stderr.strip() or "consumer creation failed",
            }
        subscribe = run_on_kube_vip(host, subscribe_cmd)
        if subscribe.rc != 0:
            return {
                "success": False,
                "records": [],
                "error": subscribe.stderr.strip() or "subscription failed",
            }

        started = time.time()
        while time.time() - started < timeout_seconds:
            result = run_on_kube_vip(host, consume_cmd)
            if result.rc != 0:
                error = result.stderr.strip() or "Kafka record read failed"
                break
            try:
                batch = json.loads(result.stdout or "[]")
            except json.JSONDecodeError:
                batch = []
            for record in batch:
                if record.get("topic") != IDRAC_KAFKA_TOPIC:
                    continue
                records.append({
                    "topic": record.get("topic"),
                    "partition": record.get("partition"),
                    "offset": record.get("offset"),
                    "timestamp": record.get("timestamp"),
                    "value_bytes": len(record.get("value") or ""),
                })
            if records:
                break
            time.sleep(2)
    finally:
        run_on_kube_vip(host, delete_cmd)

    return {
        "success": bool(records),
        "records": records,
        "error": error,
    }


def query_idrac_vm_samples(host, start_epoch, end_epoch):
    """Return raw iDRAC samples stored in a VictoriaMetrics time window."""
    vmselect_ip, vmselect_port = get_vmselect_endpoint(host)
    if not vmselect_ip or not vmselect_port:
        return {
            "success": False,
            "sample_count": 0,
            "latest_timestamp": 0,
            "series": [],
            "error": "vmselect endpoint not found",
        }

    cmd = (
        f"curl -kfsS --max-time 30 -G "
        f"'https://{vmselect_ip}:{vmselect_port}"
        "/select/0/prometheus/api/v1/export' "
        f"--data-urlencode 'match[]={_IDRAC_VM_MATCH}' "
        f"--data-urlencode 'start={float(start_epoch)}' "
        f"--data-urlencode 'end={float(end_epoch)}'"
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "sample_count": 0,
            "latest_timestamp": 0,
            "series": [],
            "error": result.stderr.strip() or "VictoriaMetrics export failed",
        }

    series = []
    sample_count = 0
    latest_timestamp = 0
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamps = item.get("timestamps", [])
        sample_count += len(timestamps)
        if timestamps:
            latest_timestamp = max([latest_timestamp, *timestamps])
        metric = item.get("metric", {})
        series.append({
            "name": metric.get("__name__", ""),
            "service_tag": metric.get("ServiceTag", ""),
            "samples": len(timestamps),
        })

    return {
        "success": result.rc == 0,
        "sample_count": sample_count,
        "latest_timestamp": latest_timestamp,
        "series": series,
        "error": "",
    }


def wait_for_fresh_idrac_vm_samples(
    host, start_epoch, timeout_seconds=90, poll_interval=5,
):
    """Wait for raw VictoriaMetrics iDRAC samples newer than start_epoch."""
    started = time.time()
    last_result = {}
    while time.time() - started < timeout_seconds:
        last_result = query_idrac_vm_samples(host, start_epoch, time.time())
        if last_result.get("success") and last_result.get("sample_count", 0) > 0:
            return last_result
        time.sleep(poll_interval)
    if not last_result:
        last_result = {
            "success": False,
            "sample_count": 0,
            "latest_timestamp": 0,
            "series": [],
            "error": "No query attempted",
        }
    last_result["success"] = False
    last_result["error"] = (
        last_result.get("error")
        or f"No fresh iDRAC VictoriaMetrics samples within {timeout_seconds}s"
    )
    return last_result


# -------------------------------------------------------------------------
# BMC Group Data — pod count scaling
# -------------------------------------------------------------------------

def get_bmc_group_data_path(host):
    """Resolve the deployed BMC inventory path on the OIM.

    ``telemetry_config.yml`` is loaded from the environment-derived project
    input directory. An explicit ``bmc_group_data_path`` wins; otherwise the
    CSV is resolved from the orchestrator output directory.

    Default: $OMNIA_DATA_PATH/orchestrator/output/$OMNIA_PROJECT_NAME/bmc_group_data.csv

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

    # Default: $OMNIA_DATA_PATH/orchestrator/output/$OMNIA_PROJECT_NAME/bmc_group_data.csv
    omnia_data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH) or "/opt/omnia"
    project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME) or "project_default"
    return f"{omnia_data_path}/orchestrator/output/{project}/bmc_group_data.csv"


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
