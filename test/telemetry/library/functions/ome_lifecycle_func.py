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

"""OME enable/disable lifecycle helpers used by resilience automation."""

import json
import time
from datetime import datetime, timezone

from omnia_auto import run_on_host

from ..vars.common_vars import TELEMETRY_NAMESPACE
from ..vars.ome_vars import (
    OME_LOG_TOPIC_SUFFIXES,
    OME_METRIC_TOPIC_SUFFIXES,
)
from .ldms_func import get_kafka_bridge_ip, get_kafka_bridge_port
from .ome_func import get_ome_pipeline_context
from .ome_victoria_func import _parse_log_timestamp, _query_log_entries
from .telemetry_func import (
    _get_input_path,
    get_vmselect_endpoint,
    run_on_kube_vip,
)


_OME_DEPLOYMENTS = ("vector-ome", "vmagent-vector", "vlagent-vector")
_OME_RETAINED_RESOURCES = (
    ("deployment", "vector-ome"),
    ("deployment", "vmagent-vector"),
    ("deployment", "vlagent-vector"),
    ("service", "vector-ome"),
    ("service", "vmagent-vector"),
    ("service", "vlagent-vector"),
    ("configmap", "vector-ome-config"),
    ("kafkauser", "vector-ome-user"),
    ("secret", "vector-ome-user"),
)
_SHARED_NAME_MARKERS = (
    "kafka",
    "victoria",
    "vminsert",
    "vmselect",
    "vmstorage",
    "vlinsert",
    "vlselect",
    "vlstorage",
)


def get_ome_telemetry_config_path(host):
    """Return the active project telemetry configuration path."""
    return f"{_get_input_path(host)}/telemetry_config.yml"


def set_ome_channel_state(host, metrics_enabled, logs_enabled):
    """Atomically set matching OME source and Vector bridge channel flags."""
    config_path = get_ome_telemetry_config_path(host)
    script = (
        "import os,sys,tempfile,yaml;"
        "path=sys.argv[1];metrics=sys.argv[2].lower()=='true';"
        "logs=sys.argv[3].lower()=='true';"
        "data=yaml.safe_load(open(path,encoding='utf-8')) or {};"
        "source=data.setdefault('telemetry_sources',{}).setdefault('ome',{});"
        "bridge=data.setdefault('telemetry_bridges',{})"
        ".setdefault('vector_ome',{});"
        "source['metrics_enabled']=metrics;source['logs_enabled']=logs;"
        "bridge['metrics_enabled']=metrics;bridge['logs_enabled']=logs;"
        "fd,tmp=tempfile.mkstemp(prefix='.ome-lifecycle-',"
        "dir=os.path.dirname(path),text=True);"
        "f=os.fdopen(fd,'w',encoding='utf-8');"
        "yaml.safe_dump(data,f,sort_keys=False);f.flush();"
        "os.fsync(f.fileno());f.close();os.replace(tmp,path)"
    )
    result = run_on_host(  # pylint: disable=too-many-function-args
        host,
        "python3 -c %s %s %s %s",
        script,
        config_path,
        "true" if metrics_enabled else "false",
        "true" if logs_enabled else "false",
    )
    return {
        "success": result.rc == 0,
        "path": config_path,
        "error": result.stderr.strip(),
    }


def _get_json(host, resource, name):
    result = run_on_kube_vip(
        host,
        f"kubectl get {resource} {name} -n {TELEMETRY_NAMESPACE} "
        "-o json 2>/dev/null",
    )
    if result.rc != 0 or not result.stdout.strip():
        return {}, result.stderr.strip() or f"{resource}/{name} not found"
    try:
        return json.loads(result.stdout), ""
    except json.JSONDecodeError as exc:
        return {}, f"Invalid JSON for {resource}/{name}: {exc}"


def _deployment_state(host, name):
    document, error = _get_json(host, "deployment", name)
    metadata = document.get("metadata", {})
    spec = document.get("spec", {})
    status = document.get("status", {})
    return {
        "exists": bool(document),
        "uid": metadata.get("uid", ""),
        "replicas": int(spec.get("replicas") or 0),
        "ready_replicas": int(status.get("readyReplicas") or 0),
        "error": error,
    }


def _shared_resource_snapshot(host):
    result = run_on_kube_vip(
        host,
        f"kubectl get deployment,statefulset,pvc "
        f"-n {TELEMETRY_NAMESPACE} -o json 2>/dev/null",
    )
    if result.rc != 0:
        return {}, result.stderr.strip() or "shared resource discovery failed"
    try:
        document = json.loads(result.stdout or '{"items":[]}')
    except json.JSONDecodeError as exc:
        return {}, f"Invalid shared resource JSON: {exc}"

    snapshot = {}
    for item in document.get("items", []):
        metadata = item.get("metadata", {})
        name = metadata.get("name", "")
        if name in _OME_DEPLOYMENTS:
            continue
        if not any(marker in name for marker in _SHARED_NAME_MARKERS):
            continue
        kind = str(item.get("kind", "")).lower()
        key = f"{kind}/{name}"
        value = {"uid": metadata.get("uid", "")}
        if kind == "persistentvolumeclaim":
            value.update({
                "volume_name": item.get("spec", {}).get("volumeName", ""),
                "phase": item.get("status", {}).get("phase", ""),
            })
        snapshot[key] = value
    return snapshot, ""


def get_ome_lifecycle_state(host):
    """Return OME identities, workload replicas, and shared sink state."""
    deployments = {
        name: _deployment_state(host, name) for name in _OME_DEPLOYMENTS
    }
    retained = {}
    errors = []
    for resource, name in _OME_RETAINED_RESOURCES:
        document, error = _get_json(host, resource, name)
        retained[f"{resource}/{name}"] = (
            document.get("metadata", {}).get("uid", "")
        )
        if error:
            errors.append(error)

    configmap, config_error = _get_json(
        host, "configmap", "vector-ome-config",
    )
    if config_error:
        errors.append(config_error)
    vector_config = configmap.get("data", {}).get("vector.toml", "")

    shared_resources, shared_error = _shared_resource_snapshot(host)
    if shared_error:
        errors.append(shared_error)

    return {
        "success": not errors and all(retained.values()),
        "error": "; ".join(errors),
        "deployments": deployments,
        "retained": retained,
        "vector_config": vector_config,
        "shared_resources": shared_resources,
    }


def wait_for_ome_workloads(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    host,
    vector_replicas,
    metrics_forwarder_replicas,
    logs_forwarder_replicas,
    timeout=600,
    poll_interval=10,
):
    """Wait for OME and forwarding deployments to reach desired replicas."""
    desired = {
        "vector-ome": vector_replicas,
        "vmagent-vector": metrics_forwarder_replicas,
        "vlagent-vector": logs_forwarder_replicas,
    }
    started = time.time()
    last_state = {}
    while time.time() - started < timeout:
        last_state = get_ome_lifecycle_state(host)
        ready = True
        for name, replicas in desired.items():
            state = last_state.get("deployments", {}).get(name, {})
            if not state.get("exists"):
                ready = False
                break
            if state.get("replicas") != replicas:
                ready = False
                break
            if replicas > 0 and state.get("ready_replicas") != replicas:
                ready = False
                break
            if replicas == 0 and state.get("ready_replicas") != 0:
                ready = False
                break
        if ready:
            return {"success": True, "state": last_state, "error": ""}
        time.sleep(poll_interval)
    return {
        "success": False,
        "state": last_state,
        "error": f"OME workloads did not reach {desired} within {timeout}s",
    }


def _record_payloads(identifier, marker):
    now = datetime.now(timezone.utc)
    iso_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    compact_time = now.strftime("%Y%m%dT%H%M%SZ")
    return {
        f"{identifier}.telemetry": {
            "Identifier": marker,
            "Metric": [{
                "MetricId": "Power.NFT_Lifecycle.Value.Avg.1",
                "MetricValue": ["1"],
                "TimeStamp": [iso_time],
                "ComponentId": "NFT",
            }],
        },
        f"{identifier}.inventory": {
            "System": [{
                "Identifier": marker,
                "CollectionTime": iso_time,
                "Component": [{
                    "ComponentType": "NFT",
                    "Data": [{"Properties": {"LifecycleValue": 1}}],
                }],
            }],
        },
        f"{identifier}.health": {
            "System": [{
                "Identifier": marker,
                "CollectionTime": iso_time,
                "LifecycleValue": 1,
            }],
        },
        f"{identifier}.alerts": {
            "Data": [{
                "AlertId": marker,
                "Description": "OME lifecycle NFT marker",
                "Severity": "Info",
                "Timestamp": iso_time,
            }],
        },
        f"{identifier}.auditlogs": {
            "Data": [{
                "Id": marker,
                "Message": "OME lifecycle NFT marker",
                "Category": "Audit",
                "CreateDate": compact_time,
            }],
        },
    }


def publish_ome_lifecycle_records(host, marker):  # pylint: disable=too-many-locals
    """Publish one uniquely marked record to every OME Kafka topic."""
    context = get_ome_pipeline_context(host)
    identifier = context["identifier"]
    bridge_ip = get_kafka_bridge_ip(host)
    bridge_port = get_kafka_bridge_port(host) if bridge_ip else ""
    if not bridge_ip or not bridge_port:
        return {
            "success": False,
            "topics": {},
            "error": "Kafka Bridge endpoint not found",
        }

    topic_results = {}
    for topic, value in _record_payloads(identifier, marker).items():
        payload = json.dumps(
            {"records": [{"value": value}]},
            separators=(",", ":"),
        )
        command = (
            f"curl -kfsS --max-time 15 -X POST "
            f"https://{bridge_ip}:{bridge_port}/topics/{topic} "
            "-H 'Content-Type: application/vnd.kafka.json.v2+json' "
            f"-d '{payload}'"
        )
        result = run_on_kube_vip(host, command)
        response = {}
        parse_error = ""
        if result.rc == 0:
            try:
                response = json.loads(result.stdout or "{}")
            except json.JSONDecodeError as exc:
                parse_error = f"invalid Kafka Bridge response: {exc}"
        offsets = response.get("offsets", [])
        accepted = (
            result.rc == 0
            and isinstance(offsets, list)
            and bool(offsets)
            and all(
                isinstance(offset, dict)
                and offset.get("error_code") is None
                and isinstance(offset.get("offset"), int)
                and offset["offset"] >= 0
                for offset in offsets
            )
        )
        topic_results[topic] = {
            "success": accepted,
            "offsets": offsets,
            "error": result.stderr.strip() or parse_error or (
                "" if accepted else result.stdout.strip()
            ),
        }

    failed = {
        topic: value["error"] or "publish failed"
        for topic, value in topic_results.items()
        if not value["success"]
    }
    return {
        "success": not failed,
        "topics": topic_results,
        "error": "; ".join(
            f"{topic}: {error}" for topic, error in failed.items()
        ),
    }


def _query_marker_metrics(host, marker, start_epoch, end_epoch, identifier):
    vmselect_ip, vmselect_port = get_vmselect_endpoint(host)
    if not vmselect_ip or not vmselect_port:
        return {}, "vmselect endpoint not found"
    selector = (
        f'{{source_subsystem="{identifier}",identifier="{marker}"}}'
    )
    command = (
        f"curl -kfsS --max-time 30 -G "
        f"'https://{vmselect_ip}:{vmselect_port}"
        "/select/0/prometheus/api/v1/export' "
        f"--data-urlencode 'match[]={selector}' "
        f"--data-urlencode 'start={float(start_epoch)}' "
        f"--data-urlencode 'end={float(end_epoch)}'"
    )
    result = run_on_kube_vip(host, command)
    if result.rc != 0:
        return {}, result.stderr.strip() or "VictoriaMetrics export failed"

    counts = {}
    for line in result.stdout.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        topic = item.get("metric", {}).get("source_topic", "")
        counts[topic] = counts.get(topic, 0) + len(item.get("timestamps", []))
    return counts, ""


def query_ome_lifecycle_data(host, marker, start_epoch, end_epoch=None):  # pylint: disable=too-many-locals
    """Count one lifecycle marker in every OME Victoria destination."""
    context = get_ome_pipeline_context(host)
    identifier = context["identifier"]
    end_epoch = end_epoch or time.time()
    metric_counts, metric_error = _query_marker_metrics(
        host, marker, start_epoch, end_epoch, identifier,
    )

    # Import here to avoid exposing endpoint discovery through this module.
    from .telemetry_func import get_vlselect_endpoint  # pylint: disable=import-outside-toplevel

    vlselect_ip, vlselect_port = get_vlselect_endpoint(host)
    log_counts = {}
    log_error = ""
    if not vlselect_ip or not vlselect_port:
        log_error = "vlselect endpoint not found"
    else:
        endpoint = {"ip": vlselect_ip, "port": vlselect_port}
        for suffix in OME_LOG_TOPIC_SUFFIXES:
            topic = f"{identifier}.{suffix}"
            try:
                _, entries = _query_log_entries(
                    host, endpoint, topic, identifier,
                )
            except (RuntimeError, ValueError) as exc:
                log_error = str(exc)
                entries = []
            log_counts[topic] = sum(
                1
                for entry in entries
                if marker in str(entry.get("_msg", ""))
                and (_parse_log_timestamp(entry.get("_time")) or 0)
                >= start_epoch
            )

    metric_topics = [
        f"{identifier}.{suffix}" for suffix in OME_METRIC_TOPIC_SUFFIXES
    ]
    log_topics = [
        f"{identifier}.{suffix}" for suffix in OME_LOG_TOPIC_SUFFIXES
    ]
    return {
        "success": not metric_error and not log_error,
        "metric_counts": {
            topic: metric_counts.get(topic, 0) for topic in metric_topics
        },
        "log_counts": {
            topic: log_counts.get(topic, 0) for topic in log_topics
        },
        "error": metric_error or log_error,
    }


def wait_for_ome_lifecycle_data(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    host,
    marker,
    start_epoch,
    expect_metrics,
    expect_logs,
    timeout=120,
    poll_interval=5,
):
    """Wait until every enabled OME topic marker reaches its Victoria sink."""
    started = time.time()
    last_result = {}
    while time.time() - started < timeout:
        last_result = query_ome_lifecycle_data(
            host, marker, start_epoch, time.time(),
        )
        metrics_ready = (
            not expect_metrics
            or all(last_result.get("metric_counts", {}).values())
        )
        logs_ready = (
            not expect_logs
            or all(last_result.get("log_counts", {}).values())
        )
        if last_result.get("success") and metrics_ready and logs_ready:
            return last_result
        time.sleep(poll_interval)
    last_result["success"] = False
    last_result["error"] = (
        last_result.get("error")
        or f"OME marker {marker} did not reach all enabled sinks"
    )
    return last_result
