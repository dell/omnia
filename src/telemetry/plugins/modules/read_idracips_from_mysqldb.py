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
"""Module to read iDRAC IPs from MySQL database.
This module connects to a Kubernetes pod running MySQL and retrieves iDRAC IPs
from the 'services' table. It handles retries and delays for robustness."""
import time
from ansible.module_utils.basic import AnsibleModule
from kubernetes import client, config
from kubernetes.stream import stream

def load_kube_context():
    """Load Kubernetes configuration for accessing the cluster."""
    try:
        config.load_kube_config()
    except Exception:
        config.load_incluster_config()


# Function to execute a MySQL command inside a pod using the Kubernetes client
def run_mysql_query_in_pod(namespace, pod, container, mysql_user, mysql_password, query):
    """Run a MySQL query in the specified pod."""
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
            _preload_content=False  # Allow access to return code and streaming output
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
              }  # Or return stderr if you want to inspect/log errors

        # Clean and filter result
        query_result = [
            line.strip() for line in stdout.strip().splitlines()
            if line.strip() and not line.strip().startswith("mysql:")
        ]

        return {
            "rc": rc,
            "result": query_result
        }

    except Exception as e:
        return {
         "rc": 1,
         "result": str(e)   
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
        "db_retries": {"type": "int", "default": 5},
        "db_delay": {"type": "int", "default": 3},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    telemetry_namespace = module.params["telemetry_namespace"]
    idrac_podnames = module.params["idrac_podnames"]
    mysqldb_k8s_name = module.params["mysqldb_k8s_name"]
    mysqldb_name = module.params["mysqldb_name"]
    mysqldb_user = module.params["mysqldb_user"]
    mysqldb_password = module.params["mysqldb_password"]
    db_retries = module.params["db_retries"]
    db_delay = module.params["db_delay"]

    load_kube_context()

    services_table_exists = {}
    db_idrac_ips = {}
    mysqldb_idrac_ips = []

    try:
        for idrac_podname in idrac_podnames:
            found = None
            ip_output = None
            ip_list = []

            for _ in range(db_retries):
                # Check for services table
                query_tables = f"SHOW TABLES FROM {mysqldb_name}"
                tables_output = run_mysql_query_in_pod(
                    telemetry_namespace,
                    idrac_podname,
                    mysqldb_k8s_name,
                    mysqldb_user,
                    mysqldb_password,
                    query_tables
                )
                if tables_output and not found:
                    found = tables_output

                # Fetch iDRAC IPs if table exists
                if found and not ip_output:
                    query_ips = f"SELECT ip FROM {mysqldb_name}.services"
                    ip_output = run_mysql_query_in_pod(
                        telemetry_namespace,
                        idrac_podname,
                        mysqldb_k8s_name,
                        mysqldb_user,
                        mysqldb_password,
                        query_ips
                    )
                    module.warn(f"iDRAC IPs output from {idrac_podname}: {ip_output}")
                if ip_output.get("rc") == 0:
                    ip_list = ip_output.get("result", [])
                    module.warn(f"iDRAC IPs found in {idrac_podname}: {ip_list}")
                    break

                time.sleep(db_delay)

            services_table_exists[idrac_podname] = found

            # Parse iDRAC IPs
            if ip_list:
                db_idrac_ips[idrac_podname] = ip_list
                mysqldb_idrac_ips.extend(ip_list)
            else:
                db_idrac_ips[idrac_podname] = []

        if not any(services_table_exists.values()):
            module.warn("Failed to find 'services' table in any of the MySQL pods.")

        if not any(db_idrac_ips.values()):
            module.warn("Failed to fetch iDRAC IPs from any pod.")

        module.exit_json(
            changed=False,
            mysqldb_idrac_ips=mysqldb_idrac_ips,
            pod_to_db_idrac_ips=db_idrac_ips,
            services_table_check=services_table_exists
        )
    except Exception as e:
        module.fail_json(
            msg=f"An error occurred while reading iDRAC IPs from MySQL: {str(e)}",
            mysqldb_idrac_ips=[],
            services_table_check=services_table_exists,
            pod_to_db_idrac_ips=db_idrac_ips
        )


if __name__ == "__main__":
    main()
