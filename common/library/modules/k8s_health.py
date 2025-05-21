# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

#!/usr/bin/python3.11
"""
Ansible module to check Kubernetes cluster health:
- Verifies node status
- Waits for all pods to be ready
- Optionally updates a success tracker file
"""

import os
import time
import json

from ansible.module_utils.basic import AnsibleModule
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
from prettytable import PrettyTable


def load_k8s_config(config_path=None):
    """
    Load Kubernetes configuration:
    - If `config_path` is provided, expand and load from it.
    - Else try environment variable or default path.
    - If that fails, try in-cluster config.
    """
    try:
        if config_path:
            kubeconfig_path = os.path.expanduser(config_path)
            if not os.path.isfile(kubeconfig_path):
                raise ConfigException(f"Specified kubeconfig path does not exist: {kubeconfig_path}")
            print(f"Trying to load kubeconfig from specified path: {kubeconfig_path}")
            config.load_kube_config(config_file=kubeconfig_path)
            print(f"Kubernetes config loaded successfully from: {kubeconfig_path}")
        else:
            default_path = os.environ.get('KUBECONFIG') or os.path.expanduser("~/.kube/config")
            if not os.path.isfile(default_path):
                print(f"Default kubeconfig not found at: {default_path}, attempting in-cluster config.")
                raise ConfigException("Default kubeconfig not found.")
            print(f"Trying to load default kubeconfig from: {default_path}")
            config.load_kube_config(config_file=default_path)
            print(f"Kubernetes config loaded successfully from: {default_path}")
    except ConfigException as exc:
        print("Failed to load kubeconfig, trying in-cluster config.")
        try:
            config.load_incluster_config()
            print("In-cluster Kubernetes config loaded successfully.")
        except ConfigException as inner_exc:
            raise ConfigException(
                "Kubernetes configuration could not be loaded from any source."
            ) from inner_exc


def get_node_info():
    """
    Collects node health information from the Kubernetes cluster.
    """
    v1 = client.CoreV1Api()
    nodes = v1.list_node().items
    node_info = []
    not_ready = []

    for node in nodes:
        roles = node.metadata.labels.get('kubernetes.io/role', 'worker')
        for label in node.metadata.labels:
            if label.startswith("node-role.kubernetes.io/"):
                roles = label.split("/")[-1]
                break

        internal_ip = next(
            (addr.address for addr in node.status.addresses if addr.type == "InternalIP"), "N/A"
        )
        status = next((c.status for c in node.status.conditions if c.type == "Ready"), "Unknown")
        ready_status = "Ready" if status == "True" else "NotReady"

        node_info.append({
            "name": node.metadata.name,
            "status": ready_status,
            "role": roles,
            "ip": internal_ip
        })

        if ready_status != "Ready":
            not_ready.append(node.metadata.name)

    return node_info, not_ready


def wait_for_pods(namespace, retries, delay):
    """
    Waits for pods in the specified namespace (or all namespaces) to become Ready/Succeeded.
    """
    v1 = client.CoreV1Api()
    available_namespaces = [ns.metadata.name for ns in v1.list_namespace().items]

    if namespace and namespace not in available_namespaces:
        return False, f"Namespace '{namespace}' not found.", [], []

    namespaces = [namespace] if namespace else available_namespaces
    pods_status_info = []

    for _ in range(retries):
        pods = []
        for ns in namespaces:
            pods += v1.list_namespaced_pod(namespace=ns).items

        all_ready = all(pod.status.phase in ['Running', 'Succeeded', 'Completed'] for pod in pods)

        pods_status_info = [{
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node": pod.spec.node_name,
            "ip": pod.status.pod_ip or "N/A"
        } for pod in pods]

        if all_ready:
            return True, "", pods_status_info, []

        time.sleep(delay)

    failed_pods = [
        pod for pod in pods_status_info if pod["status"] not in ['Running', 'Succeeded', 'Completed']
    ]
    return False, "", pods_status_info, failed_pods


def display_table(data, headers):
    """
    Displays a pretty-printed table from dictionary data.
    """
    table = PrettyTable()
    table.field_names = headers
    for row in data:
        table.add_row([row[h.lower()] for h in headers])
    return str(table)


def update_successful_deployments(module_name, file_path):
    """
    Updates the specified JSON file to record a successful module run.
    """
    if not module_name or not file_path:
        return

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = {}
    else:
        existing_data = {}

    existing_data[module_name] = "success"
    cleaned_data = {k: v for k, v in existing_data.items() if v == "success"}

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, indent=4)


def main():
    """
    Main entry point for Ansible module.
    """
    module = AnsibleModule(
        argument_spec={
            "namespace": {"type": "str", "required": False, "default": None},
            "retries": {"type": "int", "required": False, "default": 5},
            "delay": {"type": "int", "required": False, "default": 10},
            "track_module_name": {"type": "str", "required": False, "default": None},
            "track_file_path": {"type": "str", "required": False, "default": None},
            "kubeconfig_path": {"type": "str", "required": False, "default": None}
        }
    )

    try:
        load_k8s_config(module.params.get("kubeconfig_path"))
        nodes, not_ready_nodes = get_node_info()
        success, ns_err, pod_info, failed_pods = wait_for_pods(
            module.params["namespace"],
            module.params["retries"],
            module.params["delay"]
        )

        if success and not not_ready_nodes:
            update_successful_deployments(
                module.params["track_module_name"],
                module.params["track_file_path"]
            )

        node_table = display_table(nodes, ["Name", "Status", "Role", "IP"])
        pod_table = display_table(pod_info, ["Name", "Namespace", "Status", "Node", "IP"])

        module.exit_json(
            changed=False,
            nodes=nodes,
            pods=pod_info,
            not_ready_nodes=not_ready_nodes,
            failed_pods=failed_pods,
            node_table=node_table,
            pod_table=pod_table,
            namespace_error=ns_err,
            k8s_accessible=True
        )
    except ConfigException as ce:
        module.exit_json(changed=False, k8s_accessible=False, msg=str(ce))
    except Exception as e:
        module.exit_json(changed=False, k8s_accessible=False, msg=f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()

