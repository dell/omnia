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

#!/usr/bin/python
"""Module to insert iDRAC IPs into MySQL database.
This module connects to a Kubernetes pod running MySQL via PyMySQL and inserts
iDRAC IPs with associated service type and authentication details.
It uses parameterized queries to prevent SQL injection.
It handles retries and delays for robustness."""

import time
import json
import pymysql
from ansible.module_utils.basic import AnsibleModule
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

DOCUMENTATION = r'''
---
module: insert_idracips_mysqldb
short_description: Insert iDRAC IPs into MySQL database in Kubernetes
version_added: "2.3.0"
description:
  - Connects to MySQL pods running inside Kubernetes and inserts iDRAC IP
    entries into the C(services) table with service type and credentials.
  - Resolves pod IPs via the Kubernetes API and uses PyMySQL with
    parameterized queries (INSERT IGNORE) to prevent SQL injection.
  - Supports configurable retry count and delay for transient failures.
options:
  telemetry_namespace:
    description: Kubernetes namespace where the MySQL pods are running.
    type: str
    required: true
  idrac_podnames_ips:
    description: >
      Dictionary mapping pod names to lists of iDRAC IPs owned by that pod.
    type: dict
    required: true
  mysqldb_container_port:
    description: TCP port of the MySQL container inside the pod.
    type: int
    required: true
  mysqldb_name:
    description: Name of the MySQL database.
    type: str
    required: true
  mysqldb_user:
    description: MySQL username for authentication.
    type: str
    required: true
  mysqldb_password:
    description: MySQL password for authentication.
    type: str
    required: true
  bmc_username:
    description: BMC username stored with each iDRAC IP entry.
    type: str
    required: true
  bmc_password:
    description: BMC password stored with each iDRAC IP entry.
    type: str
    required: true
  telemetry_idrac:
    description: List of iDRAC IPs eligible for insertion (working set).
    type: list
    elements: str
    required: true
  service_type:
    description: Service type value to store in the database.
    type: str
    required: true
  auth_type:
    description: Authentication type value to store in the database.
    type: str
    required: true
  db_retries:
    description: Number of retry attempts per IP on failure.
    type: int
    default: 3
  db_delay:
    description: Delay in seconds between retries.
    type: int
    default: 3
author:
  - Dell Technologies (@dell)
'''

EXAMPLES = r'''
- name: Insert iDRAC IPs into MySQL for each pod
  omnia.telemetry.insert_idracips_mysqldb:
    telemetry_namespace: telemetry
    idrac_podnames_ips: "{{ idrac_podname_ips }}"
    mysqldb_container_port: 3306
    mysqldb_name: idrac_telemetry_db
    mysqldb_user: "{{ mysqldb_user }}"
    mysqldb_password: "{{ mysqldb_password }}"
    bmc_username: "{{ bmc_username }}"
    bmc_password: "{{ bmc_password }}"
    telemetry_idrac: "{{ telemetry_idrac }}"
    service_type: iDRAC
    auth_type: basic
'''

RETURN = r'''
changed:
  description: Whether any IPs were inserted.
  type: bool
  returned: always
inserted_ips:
  description: >
    Dictionary mapping pod names to per-IP insertion results.
  type: dict
  returned: always
  sample:
    idrac-pod-0:
      - ip: "192.168.1.10"
        changed: true
        msg: "Successfully inserted iDRAC IP 192.168.1.10 into MySQL."
failed_ips:
  description: List of dicts for IPs that could not be inserted.
  type: list
  elements: dict
  returned: always
  sample:
    - pod: idrac-pod-0
      ip: "192.168.1.11"
      msg: "Failed after 3 attempts: Connection refused"
'''

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

def run_mysql_insert(
    namespace,
    pod,
    container_port,
    db_name,
    db_user,
    db_password,
    ip,
    service_type,
    auth_type,
    auth_json
):
    """Run a MySQL insert using a PyMySQL parameterized query.

    Connects directly to the MySQL pod over TCP (resolved via the K8s API)
    and executes an INSERT IGNORE with bound parameters, eliminating SQL injection.

    Args:
        namespace: Kubernetes namespace
        pod: Pod name
        container_port: MySQL container port
        db_name: MySQL database name
        db_user: MySQL username
        db_password: MySQL password
        ip: iDRAC IP address to insert
        service_type: Service type value
        auth_type: Authentication type value
        auth_json: JSON string of authentication credentials

    Returns:
        dict: Result containing rc (bool) and result message
    """
    pod_ip = resolve_pod_ip(namespace, pod)

    conn = None
    try:
        conn = pymysql.connect(
            host=pod_ip,
            port=container_port,
            user=db_user,
            password=db_password,
            database=db_name,
            connect_timeout=10
        )
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT IGNORE INTO services (ip, serviceType, authType, auth) "
                "VALUES (%s, %s, %s, %s)",
                (ip, service_type, auth_type, auth_json)
            )
        conn.commit()
        return {
            "rc": True,
            "result": f"Inserted IP {ip}"
        }
    except (pymysql.err.OperationalError, pymysql.err.MySQLError) as e:
        return {
            "rc": False,
            "result": str(e)
        }
    finally:
        if conn:
            conn.close()


def insert_idracs_to_mysql(
    namespace,
    pod,
    container_port,
    db_name,
    db_user,
    db_password,
    telemetry_idrac_list,
    service_type,
    auth_type,
    bmc_username,
    bmc_password,
    retries=3,
    delay=3,
):
    """Insert iDRAC IPs into MySQL database."""

    # Load Kubernetes context to access the cluster
    load_kube_context()
    auth_dict = {"username": bmc_username, "password": bmc_password}
    auth_json = json.dumps(auth_dict)
    results = []

    try:
        for ip in telemetry_idrac_list:
            for _ in range(retries):
                result = run_mysql_insert(
                    namespace=namespace,
                    pod=pod,
                    container_port=container_port,
                    db_name=db_name,
                    db_user=db_user,
                    db_password=db_password,
                    ip=ip,
                    service_type=service_type,
                    auth_type=auth_type,
                    auth_json=auth_json
                )
                if result.get("rc"):
                    msg = f"Successfully inserted iDRAC IP {ip} into MySQL."
                    results.append({"ip": ip, "changed": True, "msg": msg})
                    break
                time.sleep(delay)
            else:
                results.append({"ip": ip, "changed": False,
                               "msg": f"Failed after {retries} attempts: {result.get('result')}"})
        if not results:
            results.append({"ip": "unknown", "changed": False,
                           "msg": "No iDRAC IPs to insert."})
    except Exception as e:
        results.append({"ip": "unknown", "changed": False,
                       "msg": f"An error occurred: {str(e)}"})

    return results

def main():
    """Main function to execute the module logic."""
    module_args = {
        "telemetry_namespace": {"type": "str", "required": True},
        "idrac_podnames_ips": {"type": "dict", "required": True},
        "mysqldb_container_port": {"type": "int", "required": True},
        "mysqldb_name": {"type": "str", "required": True},
        "mysqldb_user": {"type": "str", "required": True, "no_log": True},
        "mysqldb_password": {"type": "str", "required": True, "no_log": True},
        "bmc_username": {"type": "str", "required": True, "no_log": True},
        "bmc_password": {"type": "str", "required": True, "no_log": True},
        "telemetry_idrac": {"type": "list", "elements": "str", "required": True},
        "service_type": {"type": "str", "required": True},
        "auth_type": {"type": "str", "required": True},
        "db_retries": {"type": "int", "required": False, "default": 3},
        "db_delay": {"type": "int", "required": False, "default": 3},
    }

    result = {
        "changed": False,
        "inserted_ips": {},
        "failed_ips": []
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    telemetry_namespace = module.params['telemetry_namespace']
    idrac_podnames_ips = module.params['idrac_podnames_ips']
    container_port = module.params['mysqldb_container_port']
    db_name = module.params['mysqldb_name']
    db_user = module.params['mysqldb_user']
    db_password = module.params['mysqldb_password']
    bmc_username = module.params['bmc_username']
    bmc_password = module.params['bmc_password']
    telemetry_idrac = module.params['telemetry_idrac']
    service_type = module.params['service_type']
    auth_type = module.params['auth_type']
    db_retries = module.params['db_retries']
    db_delay = module.params['db_delay']

    # For each pod in idrac_podnames,
    # fetch the working IP's from telemetry_idrac,
    # then insert them into the mysqldb
    try:
        for pod in idrac_podnames_ips:
            idrac_ips_of_pod = idrac_podnames_ips.get(pod, [])
            if not idrac_ips_of_pod:
                module.warn(f"No iDRAC IPs found for pod {pod}. Skipping.")
                continue
            working_idrac_ips = list(set(telemetry_idrac) & set(idrac_ips_of_pod))
            pod_results = insert_idracs_to_mysql(
                namespace=telemetry_namespace,
                pod=pod,
                container_port=container_port,
                db_name=db_name,
                db_user=db_user,
                db_password=db_password,
                telemetry_idrac_list=working_idrac_ips,
                service_type=service_type,
                auth_type=auth_type,
                bmc_username=bmc_username,
                bmc_password=bmc_password,
                retries=db_retries,
                delay=db_delay
            )
            result['inserted_ips'][pod] = pod_results
            success = False
            for r in pod_results:
                if r.get('changed'):
                    success = True
                else:
                    result['failed_ips'].append({
                        "pod": pod,
                        "ip": r.get("ip", "unknown"),
                        "msg": r.get("msg", "No message")
                    })

            if success:
                result['changed'] = True

        module.exit_json(**result)
    except Exception as e:
        module.fail_json(
            msg=f"An error occurred while inserting iDRAC IPs into MySQL: {str(e)}",
            results=result['inserted_ips'],
            failed_ips=result['failed_ips']
        )

if __name__ == '__main__':
    main()
