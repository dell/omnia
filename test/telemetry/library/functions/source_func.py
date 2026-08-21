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
Telemetry — Source Verification Functions.

Functions for verifying iDRAC, LDMS, and OME source deployments
via SSH to kube_vip.
"""

from omnia_auto import run_on_host

from library.vars.common_vars import (
    CMDS,
    IDRAC_CONTAINERS,
    IDRAC_KAFKA_TOPIC,
    IDRAC_POD_PREFIX,
    IDRAC_STS_NAME,
    IDRAC_SERVICE_NAME,
    LDMS_AGG_STS_NAME,
    LDMS_KAFKA_TOPIC,
    LDMS_STORE_NAME,
    OME_KAFKA_USER,
    TELEMETRY_NAMESPACE,
    VECTOR_LDMS_APP_NAME,
    VECTOR_OME_APP_NAME,
)
from library.functions.k8s_func import get_pods_by_prefix


# =============================================================================
# iDRAC Verification
# =============================================================================

def verify_idrac_sts_ready(host, namespace=None):
    """Verify iDRAC telemetry StatefulSet has ready replicas.

    Returns:
        dict with keys: success, ready_replicas, expected
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_sts_ready"].format(
        name=IDRAC_STS_NAME, namespace=ns,
    )
    result = run_on_host(host, cmd)
    ready = 0
    if result.rc == 0 and result.stdout.strip():
        try:
            ready = int(result.stdout.strip())
        except ValueError:
            pass
    return {
        "success": ready >= 1,
        "ready_replicas": ready,
        "expected": 1,
    }


def verify_idrac_containers(host, namespace=None):
    """Verify all containers in the iDRAC pod are running.

    Checks: mysqldb, activemq, idrac-telemetry-receiver, kafka-pump, victoria-pump

    Returns:
        dict with keys: success, pod_name, containers (list), not_ready (list)
    """
    ns = namespace or TELEMETRY_NAMESPACE
    # Get pod name
    cmd = CMDS["kubectl_get_idrac_pod_name"].format(
        namespace=ns, label=IDRAC_STS_NAME,
    )
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "pod_name": "",
            "containers": [],
            "not_ready": IDRAC_CONTAINERS,
            "error": "Could not find iDRAC pod",
        }

    pod_name = result.stdout.strip()

    # Get container statuses
    cmd = CMDS["kubectl_get_idrac_container_status"].format(
        pod_name=pod_name, namespace=ns,
    )
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "pod_name": pod_name,
            "containers": [],
            "not_ready": IDRAC_CONTAINERS,
            "error": "Could not get container status",
        }

    containers = []
    not_ready = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip() or "=" not in line:
            continue
        name, ready_str = line.strip().split("=", 1)
        ready = ready_str.lower() == "true"
        containers.append({"name": name, "ready": ready})
        if not ready:
            not_ready.append(name)

    return {
        "success": len(not_ready) == 0 and len(containers) > 0,
        "pod_name": pod_name,
        "containers": containers,
        "not_ready": not_ready,
    }


def verify_idrac_kafka_topic(host, namespace=None):
    """Verify Kafka topic 'idrac' exists.

    Returns:
        dict with keys: success, topic_name
    """
    from library.functions.sink_func import verify_kafka_topics
    result = verify_kafka_topics(host, [IDRAC_KAFKA_TOPIC], namespace)
    return {
        "success": IDRAC_KAFKA_TOPIC in result.get("found", []),
        "topic_name": IDRAC_KAFKA_TOPIC,
        "all_topics": result.get("all_topics", []),
    }


def verify_idrac_victoriapump(host, namespace=None):
    """Verify VictoriaPump metrics endpoint is active in iDRAC pod.

    Returns:
        dict with keys: success, metrics_available
    """
    ns = namespace or TELEMETRY_NAMESPACE
    # Get pod name first
    cmd = CMDS["kubectl_get_idrac_pod_name"].format(
        namespace=ns, label=IDRAC_STS_NAME,
    )
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {"success": False, "metrics_available": False}

    pod_name = result.stdout.strip()
    cmd = CMDS["victoriapump_metrics"].format(
        namespace=ns, pod_name=pod_name,
    )
    result = run_on_host(host, cmd)
    return {
        "success": result.rc == 0,
        "metrics_available": result.rc == 0,
    }


def verify_idrac_service(host, namespace=None):
    """Verify iDRAC telemetry service exists.

    Returns:
        dict with keys: success, service_name
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_svc"].format(namespace=ns)
    result = run_on_host(host, cmd)
    svc_found = IDRAC_SERVICE_NAME in (result.stdout or "")
    return {
        "success": svc_found,
        "service_name": IDRAC_SERVICE_NAME,
    }


# =============================================================================
# LDMS Verification
# =============================================================================

def verify_ldms_aggregator(host, namespace=None):
    """Verify LDMS aggregator StatefulSet is ready.

    Returns:
        dict with keys: success, ready_replicas
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_sts_ready"].format(
        name=LDMS_AGG_STS_NAME, namespace=ns,
    )
    result = run_on_host(host, cmd)
    ready = 0
    if result.rc == 0 and result.stdout.strip():
        try:
            ready = int(result.stdout.strip())
        except ValueError:
            pass
    return {"success": ready >= 1, "ready_replicas": ready}


def verify_ldms_store(host, namespace=None):
    """Verify LDMS store daemon pod is Running.

    Returns:
        dict with keys: success, phase
    """
    ns = namespace or TELEMETRY_NAMESPACE
    pods = get_pods_by_prefix(host, LDMS_STORE_NAME, ns)
    if not pods:
        return {"success": False, "phase": "NotFound"}
    running = [p for p in pods if p["running"]]
    return {
        "success": len(running) > 0,
        "phase": pods[0]["status"],
    }


def verify_vector_ldms(host, namespace=None):
    """Verify Vector-LDMS bridge deployment is ready.

    Returns:
        dict with keys: success, ready_replicas
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_deploy_ready"].format(
        name=VECTOR_LDMS_APP_NAME, namespace=ns,
    )
    result = run_on_host(host, cmd)
    ready = 0
    if result.rc == 0 and result.stdout.strip():
        try:
            ready = int(result.stdout.strip())
        except ValueError:
            pass
    return {"success": ready >= 1, "ready_replicas": ready}


def verify_ldms_kafka_topic(host, namespace=None):
    """Verify Kafka topic 'ldms' exists.

    Returns:
        dict with keys: success, topic_name
    """
    from library.functions.sink_func import verify_kafka_topics
    result = verify_kafka_topics(host, [LDMS_KAFKA_TOPIC], namespace)
    return {
        "success": LDMS_KAFKA_TOPIC in result.get("found", []),
        "topic_name": LDMS_KAFKA_TOPIC,
    }


def verify_ldms_sampler_config(host, share_path):
    """Verify LDMS sampler configuration file exists on NFS.

    Args:
        host: testinfra host connection.
        share_path: NFS share path (cluster_mount/telemetry/ldms).

    Returns:
        dict with keys: success, path
    """
    cmd = CMDS["ldms_sampler_conf_exists"].format(share_path=share_path)
    result = run_on_host(host, cmd)
    exists = result.rc == 0 and "exists" in result.stdout
    return {
        "success": exists,
        "path": f"{share_path}/samplers/sampler.conf",
    }


# =============================================================================
# OME Verification
# =============================================================================

def verify_vector_ome(host, namespace=None):
    """Verify Vector-OME bridge deployment is ready.

    Returns:
        dict with keys: success, ready_replicas
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_deploy_ready"].format(
        name=VECTOR_OME_APP_NAME, namespace=ns,
    )
    result = run_on_host(host, cmd)
    ready = 0
    if result.rc == 0 and result.stdout.strip():
        try:
            ready = int(result.stdout.strip())
        except ValueError:
            pass
    return {"success": ready >= 1, "ready_replicas": ready}


def verify_ome_kafka_user(host, namespace=None):
    """Verify OME KafkaUser CR exists.

    Returns:
        dict with keys: success, user_name
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_kafkauser"].format(
        name=OME_KAFKA_USER, namespace=ns,
    )
    result = run_on_host(host, cmd)
    exists = result.rc == 0 and "exists" in result.stdout
    return {
        "success": exists,
        "user_name": OME_KAFKA_USER,
    }


def verify_ome_sink_prerequisites(host, namespace=None):
    """Verify OME bridge sink prerequisites (Kafka Ready).

    Returns:
        dict with keys: success, kafka_ready
    """
    from library.functions.sink_func import verify_kafka_ready
    result = verify_kafka_ready(host, namespace)
    return {
        "success": result["success"],
        "kafka_ready": result["success"],
        "status": result.get("status", "Unknown"),
    }
