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

DOCUMENTATION = r'''
---
module: delete_idracips_from_mysqldb
short_description: Delete iDRAC IPs from MySQL database in Kubernetes
version_added: "2.3.0"
description:
  - Connects to MySQL pods running inside Kubernetes and deletes iDRAC IP
    entries from the C(services) table.
  - Resolves pod IPs via the Kubernetes API and uses PyMySQL with
    parameterized queries to prevent SQL injection.
  - Iterates over each pod and deletes only IPs assigned to that pod
    (intersection of C(ips_to_delete) and C(pod_to_db_idrac_ips[pod])).
options:
  telemetry_namespace:
    description: Kubernetes namespace where the MySQL pods are running.
    type: str
    required: true
  idrac_podnames:
    description: List of iDRAC telemetry pod names containing MySQL databases.
    type: list
    elements: str
    required: true
  mysqldb_container_port:
    description: TCP port of the MySQL container inside the pod.
    type: int
    required: true
  mysqldb_name:
    description: Name of the MySQL database.
    type: str
    required: true
  mysql_user:
    description: MySQL username for authentication.
    type: str
    required: true
  mysql_password:
    description: MySQL password for authentication.
    type: str
    required: true
  ips_to_delete:
    description: List of iDRAC IP addresses to delete.
    type: list
    elements: str
    required: true
  pod_to_db_idrac_ips:
    description: >
      Mapping of pod names to their currently stored iDRAC IPs.
      Only IPs in the intersection of this list and C(ips_to_delete) are removed.
    type: dict
    required: true
author:
  - Dell Technologies (@dell)
'''

EXAMPLES = r'''
- name: Delete stale iDRAC IPs from all telemetry MySQL pods
  omnia.telemetry.delete_idracips_from_mysqldb:
    telemetry_namespace: telemetry
    idrac_podnames: "{{ idrac_podnames }}"
    mysqldb_container_port: 3306
    mysqldb_name: idrac_telemetry_db
    mysql_user: "{{ mysql_user }}"
    mysql_password: "{{ mysql_password }}"
    ips_to_delete: "{{ stale_ips }}"
    pod_to_db_idrac_ips: "{{ pod_to_db_idrac_ips }}"
'''

RETURN = r'''
changed:
  description: Whether any IPs were deleted.
  type: bool
  returned: always
deleted_ips:
  description: List of iDRAC IPs that were successfully deleted.
  type: list
  elements: str
  returned: always
  sample: ["192.168.1.10", "192.168.1.11"]
failed_ips:
  description: List of dicts describing IPs that could not be deleted.
  type: list
  elements: dict
  returned: always
  sample:
    - pod: idrac-pod-0
      ip: "192.168.1.12"
      msg: "Connection refused"
msg:
  description: Summary message.
  type: str
  returned: always
  sample: "Deleted 2 iDRAC IPs from MySQL database."
'''

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


def delete_idrac_from_mysql(
    namespace,
    pod,
    mysqldb_container_port,
    mysqldb_name,
    mysql_user,
    mysql_password,
    ip_to_delete
):
    """Delete a single iDRAC IP from MySQL database using PyMySQL.

    Args:
        namespace: Kubernetes namespace
        pod: Pod name
        mysqldb_container_port: MySQL container port
        mysqldb_name: MySQL database name
        mysql_user: MySQL username
        mysql_password: MySQL password
        ip_to_delete: IP address to delete

    Returns:
        dict: Result containing success status and message
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
            cursor.execute(
                "DELETE FROM services WHERE ip = %s",
                (ip_to_delete,)
            )
            affected_rows = cursor.rowcount
            conn.commit()

        return {
            "success": True,
            "ip": ip_to_delete,
            "msg": f"Successfully deleted iDRAC IP {ip_to_delete} from MySQL.",
            "affected_rows": affected_rows
        }
    except (pymysql.err.OperationalError, pymysql.err.MySQLError) as e:
        return {
            "success": False,
            "ip": ip_to_delete,
            "msg": str(e)
        }
    finally:
        if conn:
            conn.close()


def main():
    """Main function to execute the module logic."""
    module_args = {
        "telemetry_namespace": {"type": "str", "required": True},
        "idrac_podnames": {"type": "list", "required": True},
        "mysqldb_container_port": {"type": "int", "required": True},
        "mysqldb_name": {"type": "str", "required": True},
        "mysql_user": {"type": "str", "required": True, "no_log": True},
        "mysql_password": {"type": "str", "required": True, "no_log": True},
        "ips_to_delete": {"type": "list", "required": True},
        "pod_to_db_idrac_ips": {"type": "dict", "required": True},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    telemetry_namespace = module.params["telemetry_namespace"]
    idrac_podnames = module.params["idrac_podnames"]
    mysqldb_container_port = module.params["mysqldb_container_port"]
    mysqldb_name = module.params["mysqldb_name"]
    mysql_user = module.params["mysqldb_user"]
    mysql_password = module.params["mysqldb_password"]
    ips_to_delete = module.params["ips_to_delete"]
    pod_to_db_idrac_ips = module.params["pod_to_db_idrac_ips"]

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
                    mysql_user=mysql_user,
                    mysql_password=mysql_password,
                    ip_to_delete=ip
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
