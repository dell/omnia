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
This module connects to a Kubernetes pod running MySQL and inserts iDRAC IPs with
associated service type and authentication details.
It handles retries and delays for robustness."""

import time
import json
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

def escape_single_quotes(s):
    """Escape single quotes in a string for safe MySQL insertion."""
    return s.replace("'", "\\'")

def run_mysql_insert(
    namespace,
    pod,
    container,
    mysqldb_name,
    mysql_user,
    mysql_password,
    ip,
    service_type,
    auth_type,
    auth_json
):
    """Run a MySQL insert command in the specified pod."""

    query = (
        f"INSERT IGNORE INTO {mysqldb_name}.services "
        f"(ip, serviceType, authType, auth) VALUES ("
        f"'{ip}', "
        f"'{service_type}', "
        f"'{auth_type}', "
        f"'{escape_single_quotes(auth_json)}'"
        f");"
    )

    command = [
        "mysql", "-u", mysql_user, f"-p{mysql_password}",
        "-e", query
    ]

    core_v1 = client.CoreV1Api()
    try:
        ws = stream(
            core_v1.connect_get_namespaced_pod_exec,
            name=pod,
            namespace=namespace,
            container=container,
            command=command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=False  # Allows streaming access
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
                "rc": False,
                "result": stderr.strip() or "Unknown error"
            }
        return {
            "rc": True,
            "result": stdout.strip()
        }

    except Exception as e:
    # Catching all to ensure MySQL errors or stream failures are handled
        return {
            "rc": False, 
            "result": str(e)
        }


def insert_idracs_to_mysql(
    namespace,
    pod,
    container,
    mysqldb_name,
    mysql_user,
    mysql_password,
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
                    container=container,
                    mysqldb_name=mysqldb_name,
                    mysql_user=mysql_user,
                    mysql_password=mysql_password,
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
                results.append({"ip": ip, "changed": False, \
                "msg": f"Failed after {retries} attempts: {msg}"})
        if not results:
            results.append({"ip": "unknown", "changed": False, \
            "msg": "No iDRAC IPs to insert."})
    except Exception as e:
        results.append({"ip": "unknown", "changed": False, \
        "msg": f"An error occurred: {str(e)}"})

    return results

def main():
    """Main function to execute the module logic."""
    module_args = {
        "telemetry_namespace": {"type": "str", "required": True},
        "idrac_podnames_ips": {"type": "dict", "required": True},
        "mysqldb_k8s_name": {"type": "str", "required": True},
        "mysqldb_name": {"type": "str", "required": True},
        "mysql_user": {"type": "str", "required": True, "no_log": True},
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
    mysqldb_k8s_name = module.params['mysqldb_k8s_name']
    mysqldb_name = module.params['mysqldb_name']
    mysql_user = module.params['mysql_user']
    mysqldb_password = module.params['mysqldb_password']
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
                container=mysqldb_k8s_name,
                mysqldb_name=mysqldb_name,
                mysql_user=mysql_user,
                mysql_password=mysqldb_password,
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
