from ansible.module_utils.basic import AnsibleModule
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
import time
from prettytable import PrettyTable

def get_node_info():
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

        internal_ip = next((addr.address for addr in node.status.addresses if addr.type == "InternalIP"), "N/A")
        status = next((c.status for c in node.status.conditions if c.type == "Ready"), "Unknown")
        ready_status = "Ready" if status == "True" else "NotReady"

        node_info.append({
            'name': node.metadata.name,
            'status': ready_status,
            'role': roles,
            'ip': internal_ip
        })

        if ready_status != "Ready":
            not_ready.append(node.metadata.name)

    return node_info, not_ready

def wait_for_pods(namespace, retries, delay):
    v1 = client.CoreV1Api()
    available_namespaces = [ns.metadata.name for ns in v1.list_namespace().items]

    if namespace and namespace not in available_namespaces:
        return False, f"Namespace '{namespace}' not found.", [], []

    namespaces = [namespace] if namespace else available_namespaces
    pods_status_info = []

    for attempt in range(retries):
        pods = []
        for ns in namespaces:
            pods += v1.list_namespaced_pod(namespace=ns).items

        all_ready = all(pod.status.phase in ['Running', 'Succeeded', 'Completed'] for pod in pods)
        pods_status_info = [dict(
            name=pod.metadata.name,
            namespace=pod.metadata.namespace,
            status=pod.status.phase,
            node=pod.spec.node_name,
            ip=pod.status.pod_ip or "N/A"
        ) for pod in pods]

        if all_ready:
            return True, "", pods_status_info, []

        time.sleep(delay)

    failed_pods = [pod for pod in pods_status_info if pod['status'] not in ['Running', 'Succeeded', 'Completed']]
    return False, "", pods_status_info, failed_pods

def display_table(data, headers):
    table = PrettyTable()
    table.field_names = headers
    for row in data:
        table.add_row([row[h.lower()] for h in headers])
    return str(table)

def main():
    module = AnsibleModule(
        argument_spec=dict(
            namespace=dict(type='str', required=False, default=None),
            retries=dict(type='int', required=False, default=5),
            delay=dict(type='int', required=False, default=10),
        )
    )

    try:
        config.load_kube_config()
        nodes, not_ready_nodes = get_node_info()
        success, ns_err, pod_info, failed_pods = wait_for_pods(module.params['namespace'], module.params['retries'], module.params['delay'])

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
        module.exit_json(changed=False, k8s_accessible=False, msg="Kubernetes not found or not configured")
    except Exception as e:
        module.exit_json(changed=False, k8s_accessible=False, msg=f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
