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
This module connects to a Kubernetes pod running MySQL via PyMySQL and retrieves
iDRAC IPs from the 'services' table. It uses parameterized queries (database
selected via connection kwarg) to prevent SQL injection.
It handles retries and delays for robustness."""
import time
import pymysql
from ansible.module_utils.basic import AnsibleModule
from kubernetes import client, config

def load_kube_context():
    """Load Kubernetes configuration for accessing the cluster."""
    try:
        config.load_kube_config()
    except Exception:
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


# Function to check for the services table and read IPs via PyMySQL
def run_mysql_read_in_pod(
    namespace, pod, mysqldb_container_port, mysqldb_name,
    mysql_user, mysql_password
):
    """Read iDRAC IPs from MySQL using a PyMySQL connection.

    Connects directly to the MySQL pod over TCP (resolved via the K8s API)
    with the database selected via connection kwarg (no identifier interpolation).

    Args:
        namespace: Kubernetes namespace
        pod: Pod name
        mysqldb_container_port: MySQL container port
        mysqldb_name: MySQL database name
        mysql_user: MySQL username
        mysql_password: MySQL password

    Returns:
        dict: Result with 'tables_found' (bool or result), 'ip_list' (list), 'rc' (int)
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
            # Check for services table (schema already selected via connection)
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            if "services" not in tables:
                return {
                    "rc": 0,
                    "tables_found": None,
                    "ip_list": []
                }

            # Fetch iDRAC IPs
            cursor.execute("SELECT ip FROM services")
            ip_list = [row[0] for row in cursor.fetchall()]

        return {
            "rc": 0,
            "tables_found": tables,
            "ip_list": ip_list
        }
    except (pymysql.err.OperationalError, pymysql.err.MySQLError) as e:
        return {
            "rc": 1,
            "tables_found": None,
            "ip_list": [],
            "result": str(e)
        }
    finally:
        if conn:
            conn.close()


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
        "mysqldb_container_port": {"type": "int", "default": 3306},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    telemetry_namespace = module.params["telemetry_namespace"]
    idrac_podnames = module.params["idrac_podnames"]
    mysqldb_name = module.params["mysqldb_name"]
    mysqldb_user = module.params["mysqldb_user"]
    mysqldb_password = module.params["mysqldb_password"]
    db_retries = module.params["db_retries"]
    db_delay = module.params["db_delay"]
    mysqldb_container_port = module.params["mysqldb_container_port"]

    load_kube_context()

    services_table_exists = {}
    db_idrac_ips = {}
    mysqldb_idrac_ips = []

    try:
        for idrac_podname in idrac_podnames:
            found = None
            ip_list = []

            for _ in range(db_retries):
                read_result = run_mysql_read_in_pod(
                    namespace=telemetry_namespace,
                    pod=idrac_podname,
                    mysqldb_container_port=mysqldb_container_port,
                    mysqldb_name=mysqldb_name,
                    mysql_user=mysqldb_user,
                    mysql_password=mysqldb_password
                )

                if read_result.get("rc") == 0:
                    found = read_result.get("tables_found")
                    ip_list = read_result.get("ip_list", [])
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
