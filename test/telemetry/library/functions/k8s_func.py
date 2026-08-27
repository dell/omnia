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
Telemetry — K8s Verification Functions.

Functions for verifying Kubernetes resources (pods, deployments,
statefulsets, services, Kafka CRs) on the kube_vip node.

All commands run on kube_vip via SSH from the OIM.
"""

import json

from .telemetry_func import run_on_kube_vip

from ..vars.common_vars import (
    CMDS,
    TELEMETRY_NAMESPACE,
    KAFKA_CR_NAME,
)


def verify_all_pods_running(host, namespace=None):
    """Verify all pods in telemetry namespace are running.

    Matches the 2.2 automation output: shows ``kubectl get pods -o wide``
    and lists every pod with running/not-running status.

    Args:
        host: Testinfra host (OIM).
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, total_pods, running_count,
        not_running_count, running_pods, not_running_pods, output.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    valid_statuses = ["Running", "Completed", "Succeeded"]

    # Get pods JSON for structured parsing
    cmd_json = CMDS["kubectl_get_pods_json_all"].format(namespace=ns)
    result = run_on_kube_vip(host, cmd_json)
    running_pods = []
    not_running_pods = []

    if result.rc == 0 and result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            for item in data.get("items", []):
                name = item["metadata"]["name"]
                phase = item["status"].get("phase", "Unknown")
                node = item["spec"].get("nodeName", "")
                restarts = 0
                ready_count = 0
                total_count = 0
                for cs in item["status"].get("containerStatuses", []):
                    total_count += 1
                    if cs.get("ready", False):
                        ready_count += 1
                    restarts += cs.get("restartCount", 0)
                ready_str = f"{ready_count}/{total_count}"
                pod_info = {
                    "name": name,
                    "status": phase,
                    "ready": ready_str,
                    "node": node,
                    "restarts": restarts,
                    "running": phase in valid_statuses and ready_count == total_count,
                }
                if pod_info["running"]:
                    running_pods.append(pod_info)
                else:
                    not_running_pods.append(pod_info)
        except (json.JSONDecodeError, KeyError):
            pass

    # Get wide output for display
    cmd_wide = CMDS["kubectl_get_pods_wide"].format(namespace=ns)
    wide_result = run_on_kube_vip(host, cmd_wide)
    output = wide_result.stdout if wide_result.rc == 0 else ""

    total = len(running_pods) + len(not_running_pods)
    return {
        "success": len(not_running_pods) == 0 and total > 0,
        "total_pods": total,
        "running_count": len(running_pods),
        "not_running_count": len(not_running_pods),
        "running_pods": running_pods,
        "not_running_pods": not_running_pods,
        "output": output,
    }


def verify_pods_by_prefix(host, prefix, namespace=None, min_count=1):
    """Verify pods matching a prefix are running.

    Args:
        host: Testinfra host (OIM).
        prefix: Pod name prefix to grep.
        namespace: K8s namespace (default: telemetry).
        min_count: Minimum required running pods.

    Returns:
        dict with keys: success, running_count, pods.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_pods_by_prefix"].format(
        namespace=ns, prefix=prefix,
    )
    result = run_on_kube_vip(host, cmd)
    pods = []
    if result.rc == 0 and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                pods.append({
                    "name": parts[0],
                    "status": parts[1],
                    "running": parts[1] == "Running",
                })
    running = [p for p in pods if p["running"]]
    return {
        "success": len(running) >= min_count,
        "running_count": len(running),
        "total_count": len(pods),
        "pods": pods,
    }


def verify_sts_ready(host, name, namespace=None, expected=1):
    """Verify StatefulSet has expected ready replicas.

    Args:
        host: Testinfra host (OIM).
        name: StatefulSet name.
        namespace: K8s namespace (default: telemetry).
        expected: Expected ready replicas.

    Returns:
        dict with keys: success, ready_replicas, expected.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_sts_ready"].format(name=name, namespace=ns)
    result = run_on_kube_vip(host, cmd)
    # Check if STS exists by trying to get it (separate check without 2>/dev/null)
    exists_cmd = (
        f"kubectl get statefulset {name} -n {ns}"
        " -o name 2>&1 | head -1"
    )
    exists_result = run_on_kube_vip(host, exists_cmd)
    not_found = (
        exists_result.rc != 0
        or "NotFound" in exists_result.stdout
        or "NotFound" in getattr(exists_result, "stderr", "")
    )
    ready = 0
    if result.rc == 0 and result.stdout.strip():
        try:
            ready = int(result.stdout.strip())
        except ValueError:
            pass
    return {
        "success": ready >= expected,
        "ready_replicas": ready,
        "expected": expected,
        "not_found": not_found,
    }


def verify_deploy_ready(host, name, namespace=None, expected=1):
    """Verify Deployment has expected ready replicas.

    Args:
        host: Testinfra host (OIM).
        name: Deployment name.
        namespace: K8s namespace (default: telemetry).
        expected: Expected ready replicas.

    Returns:
        dict with keys: success, ready_replicas, expected.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_deploy_ready"].format(name=name, namespace=ns)
    result = run_on_kube_vip(host, cmd)
    ready = 0
    if result.rc == 0 and result.stdout.strip():
        try:
            ready = int(result.stdout.strip())
        except ValueError:
            pass
    return {
        "success": ready >= expected,
        "ready_replicas": ready,
        "expected": expected,
    }


def verify_pod_containers(host, pod_name, namespace=None):
    """Verify all containers in a pod are ready.

    Args:
        host: Testinfra host (OIM).
        pod_name: Pod name.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, pod_name, containers, not_ready.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_pod_containers"].format(
        pod_name=pod_name, namespace=ns,
    )
    result = run_on_kube_vip(host, cmd)
    containers = []
    not_ready = []
    if result.rc == 0 and result.stdout.strip():
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


def verify_kafka_ready(host, namespace=None):
    """Verify Kafka cluster has Ready condition.

    Args:
        host: Testinfra host (OIM).
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, status.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kafka_wait_ready"].format(
        kafka_cr=KAFKA_CR_NAME, namespace=ns,
    )
    result = run_on_kube_vip(host, cmd)
    is_ready = result.rc == 0 and "ready" in result.stdout.lower()
    return {
        "success": is_ready,
        "status": result.stdout.strip() if result.rc == 0 else "error",
    }


def verify_kafka_topics(host, expected_topics, namespace=None):
    """Verify Kafka topics exist via Strimzi CRD.

    Args:
        host: Testinfra host (OIM).
        expected_topics: List of topic names to check.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, found, missing, all_topics.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kafka_get_topics_cr"].format(namespace=ns)
    result = run_on_kube_vip(host, cmd)
    all_topics = []
    if result.rc == 0 and result.stdout.strip():
        all_topics = [
            t.strip() for t in result.stdout.strip().split("\n") if t.strip()
        ]
    found = [t for t in expected_topics if t in all_topics]
    missing = [t for t in expected_topics if t not in all_topics]
    return {
        "success": len(missing) == 0,
        "found": found,
        "missing": missing,
        "all_topics": all_topics,
    }


def verify_kafka_topic_ready(host, topic, namespace=None):
    """Verify a specific Kafka topic has Ready=True status.

    Args:
        host: Testinfra host (OIM).
        topic: Topic name.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, topic, status.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kafka_topic_ready"].format(topic=topic, namespace=ns)
    result = run_on_kube_vip(host, cmd)
    status = result.stdout.strip() if result.rc == 0 else ""
    return {
        "success": status == "True",
        "topic": topic,
        "status": status,
    }


def verify_services_exist(host, service_names, namespace=None):
    """Verify K8s services exist.

    Args:
        host: Testinfra host (OIM).
        service_names: List of service names to check.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, found, missing.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_svc"].format(namespace=ns)
    result = run_on_kube_vip(host, cmd)
    existing = result.stdout.strip() if result.rc == 0 else ""
    found = [s for s in service_names if s in existing]
    missing = [s for s in service_names if s not in existing]
    return {
        "success": len(missing) == 0,
        "found": found,
        "missing": missing,
    }


def verify_deploy_pods_detail(host, deploy_name, namespace=None):
    """Get detailed pod info for a Deployment (name, status, node, restarts, age).

    Reads the deployment's matchLabels selector and uses it to find pods.

    Args:
        host: Testinfra host (OIM).
        deploy_name: Deployment name.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, ready_replicas, expected, pods (list of dicts).
    """
    ns = namespace or TELEMETRY_NAMESPACE

    # Get the deployment's selector labels
    sel_cmd = CMDS["kubectl_get_deploy_selector"].format(
        name=deploy_name, namespace=ns,
    )
    sel_result = run_on_kube_vip(host, sel_cmd)
    if sel_result.rc != 0 or not sel_result.stdout.strip():
        return {"success": False, "ready_replicas": 0, "expected": 1, "pods": []}

    try:
        labels = json.loads(sel_result.stdout)
    except json.JSONDecodeError:
        return {"success": False, "ready_replicas": 0, "expected": 1, "pods": []}

    # Build label selector string: key1=val1,key2=val2
    label_selector = ",".join(f"{k}={v}" for k, v in labels.items())

    cmd = CMDS["kubectl_get_pods_json_by_selector"].format(
        namespace=ns, label_selector=label_selector,
    )
    result = run_on_kube_vip(host, cmd)
    pods = []
    if result.rc != 0 or not result.stdout.strip():
        return {"success": False, "ready_replicas": 0, "expected": 1, "pods": []}

    try:
        data = json.loads(result.stdout)
        items = data.get("items", [])
    except json.JSONDecodeError:
        return {"success": False, "ready_replicas": 0, "expected": 1, "pods": []}

    running_count = 0
    for pod in items:
        meta = pod.get("metadata", {})
        status = pod.get("status", {})
        phase = status.get("phase", "Unknown")
        node = pod.get("spec", {}).get("nodeName", "")
        restarts = 0
        for cs in status.get("containerStatuses", []):
            restarts += cs.get("restartCount", 0)
        creation = meta.get("creationTimestamp", "")

        is_running = phase == "Running"
        if is_running:
            running_count += 1

        pods.append({
            "name": meta.get("name", ""),
            "status": phase,
            "node": node,
            "restarts": restarts,
            "created": creation,
            "running": is_running,
        })

    # Get expected replicas from the deployment
    deploy_cmd = CMDS["kubectl_get_deploy_ready"].format(
        name=deploy_name, namespace=ns,
    )
    result = run_on_kube_vip(host, deploy_cmd)
    expected = 1
    try:
        expected = int(result.stdout.strip()) if result.rc == 0 else 1
    except ValueError:
        pass

    return {
        "success": running_count >= expected and running_count > 0,
        "ready_replicas": running_count,
        "expected": max(expected, 1),
        "pods": pods,
    }


def verify_services_detail(host, service_names, namespace=None):
    """Get detailed service info (name, type, clusterIP, externalIP, ports).

    Args:
        host: Testinfra host (OIM).
        service_names: List of service names to check.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, found, missing, services (list of dicts).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_svc_json"].format(namespace=ns)
    result = run_on_kube_vip(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False, "found": [], "missing": service_names,
            "services": [],
        }

    try:
        data = json.loads(result.stdout)
        items = data.get("items", [])
    except json.JSONDecodeError:
        return {
            "success": False, "found": [], "missing": service_names,
            "services": [],
        }

    svc_map = {}
    for svc in items:
        name = svc.get("metadata", {}).get("name", "")
        svc_type = svc.get("spec", {}).get("type", "")
        cluster_ip = svc.get("spec", {}).get("clusterIP", "")

        # External IP from LoadBalancer
        ingress = svc.get("status", {}).get("loadBalancer", {}).get("ingress", [])
        external_ip = ingress[0].get("ip", "") if ingress else ""

        # Ports
        ports = []
        for p in svc.get("spec", {}).get("ports", []):
            port_name = p.get("name", "")
            port_num = p.get("port", "")
            target_port = p.get("targetPort", "")
            protocol = p.get("protocol", "TCP")
            ports.append({
                "name": port_name,
                "port": port_num,
                "targetPort": target_port,
                "protocol": protocol,
            })

        svc_map[name] = {
            "name": name,
            "type": svc_type,
            "clusterIP": cluster_ip,
            "externalIP": external_ip,
            "ports": ports,
        }

    found = [s for s in service_names if s in svc_map]
    missing = [s for s in service_names if s not in svc_map]
    services = [svc_map[s] for s in found]

    return {
        "success": len(missing) == 0,
        "found": found,
        "missing": missing,
        "services": services,
    }
