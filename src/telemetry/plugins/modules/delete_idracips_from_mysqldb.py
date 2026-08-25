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

#!/usr/bin/python
"""Module to delete iDRAC IPs from MySQL database.
This module connects to a Kubernetes pod running MySQL and deletes iDRAC IPs
that are not present in bmc_data.csv. It handles retries and delays for robustness."""

import time
from ansible.module_utils.basic import AnsibleModule
from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.config.config_exception import ConfigException


def load_kube_context():
    """Load Kubernetes configuration for accessing the cluster."""
    try:
        config.load_kube_config()
    except ConfigException:
        config.load_incluster_config()


def run_mysql_query_in_pod(namespace, pod, container, mysql_user, mysql_password, query):
    """Run a MySQL query in the specified pod.

    Args:
        namespace: Kubernetes namespace
        pod: Pod name
        container: Container name
        mysql_user: MySQL username
        mysql_password: MySQL password
        query: MySQL query to execute

    Returns:
        dict: Result containing return code and output
    """
    core_v1 = client.CoreV1Api()
    mysql_command = [
        "mysql",
        "-u", mysql_user,
        "-N", "-B",
        f"-p{mysql_password}",
        "-e", query
    ]

    try:
        ws = stream(
            core_v1.connect_get_namespaced_pod_exec,
            name=pod,
            namespace=namespace,
            container=container,
            command=mysql_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=False
        )

        stdout = ""
        stderr = ""

        while ws.is_open():
            ws.update(timeout=1)
            if ws.peek_stdout():
                stdout += ws.read_stdout()
            if ws.peek_stderr():
                stderr += ws.read_stderr()
        ws.close()

        rc = ws.returncode

        if rc != 0:
            return {
                "rc": rc,
                "result": stderr.strip() if stderr else "Unknown error"
            }

        query_result = [
            line.strip() for line in stdout.strip().splitlines()
            if line.strip() and not line.strip().startswith("mysql:")
        ]

        return {
            "rc": rc,
            "result": query_result
        }

    except (ConfigException, OSError) as e:
        return {
            "rc": 1,
            "result": str(e)
        }


def delete_idrac_from_mysql(
    namespace,
    pod,
    container,
    mysqldb_name,
    mysql_user,
    mysql_password,
    ip_to_delete,
    retries=3,
    delay=3
):
    """Delete a single iDRAC IP from MySQL database.

    Args:
        namespace: Kubernetes namespace
        pod: Pod name
        container: Container name
        mysqldb_name: MySQL database name
        mysql_user: MySQL username
        mysql_password: MySQL password
        ip_to_delete: IP address to delete
        retries: Number of retry attempts
        delay: Delay between retries in seconds

    Returns:
        dict: Result containing success status and message
    """
    query = (
        f"DELETE FROM {mysqldb_name}.services "
        f"WHERE ip = '{ip_to_delete}';"
    )

    for attempt in range(retries):
        result = run_mysql_query_in_pod(
            namespace=namespace,
            pod=pod,
            container=container,
            mysql_user=mysql_user,
            mysql_password=mysql_password,
            query=query
        )

        if result.get("rc") == 0:
            return {
                "success": True,
                "ip": ip_to_delete,
                "msg": f"Successfully deleted iDRAC IP {ip_to_delete} from MySQL."
            }

        if attempt < retries - 1:
            time.sleep(delay)

    return {
        "success": False,
        "ip": ip_to_delete,
        "msg": f"Failed to delete iDRAC IP {ip_to_delete} after {retries} attempts: {result.get('result')}"
    }


def main():
    """Main function to execute the module logic."""
    module_args = {
        "telemetry_namespace": {"type": "str", "required": True},
        "idrac_podnames": {"type": "list", "required": True},
        "mysqldb_k8s_name": {"type": "str", "required": True},
        "mysqldb_name": {"type": "str", "required": True},
        "mysqldb_user": {"type": "str", "required": True, "no_log": True},
        "mysqldb_password": {"type": "str", "required": True, "no_log": True},
        "ips_to_delete": {"type": "list", "required": True},
        "pod_to_db_idrac_ips": {"type": "dict", "required": True},
        "db_retries": {"type": "int", "default": 3},
        "db_delay": {"type": "int", "default": 3},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    telemetry_namespace = module.params["telemetry_namespace"]
    idrac_podnames = module.params["idrac_podnames"]
    mysqldb_k8s_name = module.params["mysqldb_k8s_name"]
    mysqldb_name = module.params["mysqldb_name"]
    mysqldb_user = module.params["mysqldb_user"]
    mysqldb_password = module.params["mysqldb_password"]
    ips_to_delete = module.params["ips_to_delete"]
    pod_to_db_idrac_ips = module.params["pod_to_db_idrac_ips"]
    db_retries = module.params["db_retries"]
    db_delay = module.params["db_delay"]

    load_kube_context()

    deleted_ips = []
    failed_ips = []
    changed = False

    try:
        for pod in idrac_podnames:
            pod_ips = pod_to_db_idrac_ips.get(pod, [])
            ips_to_delete_from_pod = list(set(pod_ips) & set(ips_to_delete))

            if not ips_to_delete_from_pod:
                module.warn(f"No IPs to delete from pod {pod}. Skipping.")
                continue

            module.warn(f"Deleting IPs from pod {pod}: {ips_to_delete_from_pod}")

            for ip in ips_to_delete_from_pod:
                result = delete_idrac_from_mysql(
                    namespace=telemetry_namespace,
                    pod=pod,
                    container=mysqldb_k8s_name,
                    mysqldb_name=mysqldb_name,
                    mysql_user=mysqldb_user,
                    mysql_password=mysqldb_password,
                    ip_to_delete=ip,
                    retries=db_retries,
                    delay=db_delay
                )

                if result.get("success"):
                    deleted_ips.append(ip)
                    changed = True
                else:
                    failed_ips.append({
                        "pod": pod,
                        "ip": ip,
                        "msg": result.get("msg", "Unknown error")
                    })

        module.exit_json(
            changed=changed,
            deleted_ips=deleted_ips,
            failed_ips=failed_ips,
            msg=f"Deleted {len(deleted_ips)} iDRAC IPs from MySQL database."
        )

    except (OSError, ValueError) as e:
        module.fail_json(
            msg=f"An error occurred while deleting iDRAC IPs from MySQL: {str(e)}",
            deleted_ips=deleted_ips,
            failed_ips=failed_ips
        )


if __name__ == "__main__":
    main()
