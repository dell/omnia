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
This module connects to a Kubernetes pod running MySQL via PyMySQL and deletes
iDRAC IPs that are not present in bmc_data.csv. It uses parameterized queries
to prevent SQL injection. It handles retries and delays for robustness."""

import time
import ipaddress
import pymysql
from ansible.module_utils.basic import AnsibleModule
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


def load_kube_context():
    """Load Kubernetes configuration for accessing the cluster."""
    try:
        config.load_kube_config()
    except ConfigException:
        config.load_incluster_config()


def resolve_pod_ip(namespace, pod):
    """Resolve the IP address of a Kubernetes pod via the K8s API.

    Args:
        namespace: Kubernetes namespace
        pod: Pod name

    Returns:
        str: Pod IP address

    Raises:
        RuntimeError: If the pod IP cannot be resolved
    """
    core_v1 = client.CoreV1Api()
    pod_obj = core_v1.read_namespaced_pod(name=pod, namespace=namespace)
    pod_ip = pod_obj.status.pod_ip
    if not pod_ip:
        raise RuntimeError(f"Pod {pod} in namespace {namespace} has no IP assigned")
    return pod_ip


def run_mysql_delete_in_pod(
    namespace, pod, mysqldb_container_port, mysqldb_name,
    mysql_user, mysql_password, ip_to_delete
):
    """Delete an iDRAC IP from MySQL using a PyMySQL parameterized query.

    Connects directly to the MySQL pod over TCP (resolved via the K8s API)
    and executes a DELETE with a bound parameter, eliminating SQL injection.

    Args:
        namespace: Kubernetes namespace
        pod: Pod name
        mysqldb_container_port: MySQL container port (default 3306)
        mysqldb_name: MySQL database name
        mysql_user: MySQL username
        mysql_password: MySQL password
        ip_to_delete: IP address to delete

    Returns:
        dict: Result containing return code and output
    """
    pod_ip = resolve_pod_ip(namespace, pod)

    conn = None
    try:
        conn = pymysql.connect(
            host=pod_ip,
            port=mysqldb_container_port,
            user=mysql_user,
            password=mysql_password,
            database=mysqldb_name,
            connect_timeout=10
        )
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM services WHERE ip = %s", (ip_to_delete,))
            affected_rows = cursor.rowcount
        conn.commit()
        return {
            "rc": 0,
            "result": f"Deleted {affected_rows} row(s)"
        }
    except (pymysql.err.OperationalError, pymysql.err.MySQLError) as e:
        return {
            "rc": 1,
            "result": str(e)
        }
    finally:
        if conn:
            conn.close()


def delete_idrac_from_mysql(
    namespace,
    pod,
    mysqldb_container_port,
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
        mysqldb_container_port: MySQL container port
        mysqldb_name: MySQL database name
        mysql_user: MySQL username
        mysql_password: MySQL password
        ip_to_delete: IP address to delete
        retries: Number of retry attempts
        delay: Delay between retries in seconds

    Returns:
        dict: Result containing success status and message
    """
    # Defense-in-depth: validate IP before attempting DB operation
    try:
        ipaddress.ip_address(ip_to_delete)
    except ValueError:
        return {
            "success": False,
            "ip": ip_to_delete,
            "msg": f"Invalid IP address format: {ip_to_delete}"
        }

    result = {}
    for attempt in range(retries):
        result = run_mysql_delete_in_pod(
            namespace=namespace,
            pod=pod,
            mysqldb_container_port=mysqldb_container_port,
            mysqldb_name=mysqldb_name,
            mysql_user=mysql_user,
            mysql_password=mysql_password,
            ip_to_delete=ip_to_delete
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
        "mysqldb_container_port": {"type": "int", "default": 3306},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    telemetry_namespace = module.params["telemetry_namespace"]
    idrac_podnames = module.params["idrac_podnames"]
    mysqldb_name = module.params["mysqldb_name"]
    mysqldb_user = module.params["mysqldb_user"]
    mysqldb_password = module.params["mysqldb_password"]
    ips_to_delete = module.params["ips_to_delete"]
    pod_to_db_idrac_ips = module.params["pod_to_db_idrac_ips"]
    db_retries = module.params["db_retries"]
    db_delay = module.params["db_delay"]
    mysqldb_container_port = module.params["mysqldb_container_port"]

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
                    mysqldb_container_port=mysqldb_container_port,
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
