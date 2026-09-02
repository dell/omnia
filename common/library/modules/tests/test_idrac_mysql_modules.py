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

"""Unit tests for iDRAC MySQL modules (delete, insert, read).

Verifies that the PyMySQL-based modules use parameterized queries (bound
parameters) to prevent SQL injection, and that retry/delay semantics are
preserved.
"""

import sys
import os
import types
import unittest
from unittest.mock import patch, MagicMock, call

# ---------------------------------------------------------------------------
# Bootstrap: make the module code importable without a full Ansible install
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
MODULES_DIR = os.path.join(REPO_ROOT, "common", "library", "modules")
sys.path.insert(0, MODULES_DIR)

# Stub ansible.module_utils.basic so the modules can be imported
for _name in ("ansible", "ansible.module_utils", "ansible.module_utils.basic"):
    sys.modules.setdefault(_name, types.ModuleType(_name))
_basic = sys.modules["ansible.module_utils.basic"]
_basic.AnsibleModule = MagicMock  # type: ignore[attr-defined]

# Stub pymysql if not installed (CI may not have it)
if "pymysql" not in sys.modules:
    _pymysql = types.ModuleType("pymysql")
    _pymysql_err = types.ModuleType("pymysql.err")
    _pymysql_err.OperationalError = type("OperationalError", (Exception,), {})
    _pymysql_err.MySQLError = type("MySQLError", (Exception,), {})
    _pymysql.err = _pymysql_err
    _pymysql.connect = MagicMock()
    sys.modules["pymysql"] = _pymysql
    sys.modules["pymysql.err"] = _pymysql_err

# Stub kubernetes if not installed
for _name in (
    "kubernetes", "kubernetes.client", "kubernetes.config",
    "kubernetes.config.config_exception", "kubernetes.stream",
):
    if _name not in sys.modules:
        sys.modules[_name] = types.ModuleType(_name)
_k8s_client = sys.modules["kubernetes.client"]
if not hasattr(_k8s_client, "CoreV1Api"):
    _k8s_client.CoreV1Api = MagicMock
_k8s_config = sys.modules["kubernetes.config"]
if not hasattr(_k8s_config, "load_kube_config"):
    _k8s_config.load_kube_config = MagicMock()
if not hasattr(_k8s_config, "load_incluster_config"):
    _k8s_config.load_incluster_config = MagicMock()
_k8s_exc = sys.modules["kubernetes.config.config_exception"]
if not hasattr(_k8s_exc, "ConfigException"):
    _k8s_exc.ConfigException = type("ConfigException", (Exception,), {})
_k8s_stream = sys.modules["kubernetes.stream"]
if not hasattr(_k8s_stream, "stream"):
    _k8s_stream.stream = MagicMock()

# Test-only IP addresses used as fixtures — not real hosts.
TEST_POD_IP = "10.233.64.5"  # NOSONAR — test fixture
TEST_IP_1 = "192.168.1.100"  # NOSONAR — test fixture
TEST_IP_2 = "192.168.1.101"  # NOSONAR — test fixture
MALICIOUS_IP = "x'; DROP TABLE services; --"  # NOSONAR — test fixture


# ---------------------------------------------------------------------------
# Tests for delete_idracips_from_mysqldb
# ---------------------------------------------------------------------------
class TestDeleteModule(unittest.TestCase):
    """Tests for delete_idracips_from_mysqldb PyMySQL-based implementation."""

    def _import_module(self):
        import delete_idracips_from_mysqldb  # pylint: disable=import-outside-toplevel
        return delete_idracips_from_mysqldb

    @patch("delete_idracips_from_mysqldb.resolve_pod_ip", return_value=TEST_POD_IP)
    @patch("delete_idracips_from_mysqldb.pymysql")
    def test_parameterized_delete_query(self, mock_pymysql, _mock_resolve):
        """Verify DELETE uses %s placeholder and bound parameter tuple."""
        mod = self._import_module()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn

        result = mod.run_mysql_delete_in_pod(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret",
            ip_to_delete=TEST_IP_1
        )

        self.assertEqual(result["rc"], 0)
        # Verify the SQL uses a %s placeholder, not string interpolation
        mock_cursor.execute.assert_called_once_with(
            "DELETE FROM services WHERE ip = %s",
            (TEST_IP_1,)
        )
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("delete_idracips_from_mysqldb.resolve_pod_ip", return_value=TEST_POD_IP)
    @patch("delete_idracips_from_mysqldb.pymysql")
    def test_malicious_ip_passed_as_bound_parameter(self, mock_pymysql, _mock_resolve):
        """A malicious IP value is passed as a bound parameter, not interpolated."""
        mod = self._import_module()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn

        # delete_idrac_from_mysql validates IP first, so call run_mysql_delete_in_pod directly
        result = mod.run_mysql_delete_in_pod(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret",
            ip_to_delete=MALICIOUS_IP
        )

        # The SQL string itself never changes — the malicious value is a bound param
        mock_cursor.execute.assert_called_once_with(
            "DELETE FROM services WHERE ip = %s",
            (MALICIOUS_IP,)
        )
        # The SQL text does NOT contain the malicious string
        sql_text = mock_cursor.execute.call_args[0][0]
        self.assertNotIn("DROP TABLE", sql_text)

    def test_invalid_ip_rejected_by_validation(self):
        """delete_idrac_from_mysql rejects garbage IP without a DB round trip."""
        mod = self._import_module()
        result = mod.delete_idrac_from_mysql(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret",
            ip_to_delete="not-an-ip",
            retries=1,
            delay=0
        )
        self.assertFalse(result["success"])
        self.assertIn("Invalid IP", result["msg"])

    @patch("delete_idracips_from_mysqldb.time.sleep")
    @patch("delete_idracips_from_mysqldb.run_mysql_delete_in_pod")
    def test_retry_on_failure(self, mock_run, mock_sleep):
        """Verify retry loop fires the expected number of attempts on failure."""
        mod = self._import_module()
        mock_run.return_value = {"rc": 1, "result": "connection refused"}

        result = mod.delete_idrac_from_mysql(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret",
            ip_to_delete=TEST_IP_1,
            retries=3,
            delay=2
        )

        self.assertFalse(result["success"])
        self.assertEqual(mock_run.call_count, 3)
        # sleep called between attempts (retries-1 times)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("delete_idracips_from_mysqldb.resolve_pod_ip", return_value=TEST_POD_IP)
    @patch("delete_idracips_from_mysqldb.pymysql")
    def test_connection_uses_database_kwarg(self, mock_pymysql, _mock_resolve):
        """Verify pymysql.connect uses database= kwarg (no identifier interpolation)."""
        mod = self._import_module()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn

        mod.run_mysql_delete_in_pod(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret",
            ip_to_delete=TEST_IP_1
        )

        mock_pymysql.connect.assert_called_once_with(
            host=TEST_POD_IP,
            port=3306,
            user="root",
            password="secret",
            database="idrac_telemetrydb",
            connect_timeout=10
        )


# ---------------------------------------------------------------------------
# Tests for insert_idracips_mysqldb
# ---------------------------------------------------------------------------
class TestInsertModule(unittest.TestCase):
    """Tests for insert_idracips_mysqldb PyMySQL-based implementation."""

    def _import_module(self):
        import insert_idracips_mysqldb  # pylint: disable=import-outside-toplevel
        return insert_idracips_mysqldb

    @patch("insert_idracips_mysqldb.resolve_pod_ip", return_value=TEST_POD_IP)
    @patch("insert_idracips_mysqldb.pymysql")
    def test_parameterized_insert_query(self, mock_pymysql, _mock_resolve):
        """Verify INSERT uses %s placeholders and bound parameter tuple."""
        mod = self._import_module()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn

        result = mod.run_mysql_insert(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret",
            ip=TEST_IP_1,
            service_type="3",
            auth_type="1",
            auth_json='{"username": "admin", "password": "pass"}'
        )

        self.assertTrue(result["rc"])
        mock_cursor.execute.assert_called_once_with(
            "INSERT IGNORE INTO services (ip, serviceType, authType, auth) "
            "VALUES (%s, %s, %s, %s)",
            (TEST_IP_1, "3", "1", '{"username": "admin", "password": "pass"}')
        )
        mock_conn.commit.assert_called_once()

    @patch("insert_idracips_mysqldb.resolve_pod_ip", return_value=TEST_POD_IP)
    @patch("insert_idracips_mysqldb.pymysql")
    def test_malicious_ip_as_bound_parameter(self, mock_pymysql, _mock_resolve):
        """A malicious IP in insert is passed as a bound parameter."""
        mod = self._import_module()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn

        mod.run_mysql_insert(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret",
            ip=MALICIOUS_IP,
            service_type="3",
            auth_type="1",
            auth_json='{"username": "admin", "password": "pass"}'
        )

        # SQL text itself is constant — never contains the malicious string
        sql_text = mock_cursor.execute.call_args[0][0]
        self.assertNotIn("DROP TABLE", sql_text)
        self.assertIn("%s", sql_text)

        # The malicious value is in the params tuple
        params = mock_cursor.execute.call_args[0][1]
        self.assertEqual(params[0], MALICIOUS_IP)

    @patch("insert_idracips_mysqldb.load_kube_context")
    @patch("insert_idracips_mysqldb.time.sleep")
    @patch("insert_idracips_mysqldb.run_mysql_insert")
    def test_retry_on_insert_failure(self, mock_run, mock_sleep, _mock_kube):
        """Verify retry loop on insert failure."""
        mod = self._import_module()
        mock_run.return_value = {"rc": False, "result": "connection refused"}

        results = mod.insert_idracs_to_mysql(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret",
            telemetry_idrac_list=[TEST_IP_1],
            service_type="3",
            auth_type="1",
            bmc_username="admin",
            bmc_password="pass",
            retries=3,
            delay=1
        )

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["changed"])
        self.assertEqual(mock_run.call_count, 3)

    @patch("insert_idracips_mysqldb.load_kube_context")
    @patch("insert_idracips_mysqldb.run_mysql_insert")
    def test_invalid_ip_skipped_in_insert(self, mock_run, _mock_kube):
        """Invalid IP is rejected by validation without calling run_mysql_insert."""
        mod = self._import_module()

        results = mod.insert_idracs_to_mysql(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret",
            telemetry_idrac_list=["not-an-ip"],
            service_type="3",
            auth_type="1",
            bmc_username="admin",
            bmc_password="pass",
            retries=1,
            delay=0
        )

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["changed"])
        self.assertIn("Invalid IP", results[0]["msg"])
        mock_run.assert_not_called()

    @patch("insert_idracips_mysqldb.resolve_pod_ip", return_value=TEST_POD_IP)
    @patch("insert_idracips_mysqldb.pymysql")
    def test_escape_single_quotes_no_longer_needed(self, mock_pymysql, _mock_resolve):
        """Auth JSON with single quotes is handled by parameterized query."""
        mod = self._import_module()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn

        auth_with_quotes = '{"username": "admin", "password": "it\'s a test"}'
        mod.run_mysql_insert(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret",
            ip=TEST_IP_1,
            service_type="3",
            auth_type="1",
            auth_json=auth_with_quotes
        )

        # The auth_json is passed as a bound parameter — no escaping needed
        params = mock_cursor.execute.call_args[0][1]
        self.assertEqual(params[3], auth_with_quotes)


# ---------------------------------------------------------------------------
# Tests for read_idracips_from_mysqldb
# ---------------------------------------------------------------------------
class TestReadModule(unittest.TestCase):
    """Tests for read_idracips_from_mysqldb PyMySQL-based implementation."""

    def _import_module(self):
        import read_idracips_from_mysqldb  # pylint: disable=import-outside-toplevel
        return read_idracips_from_mysqldb

    @patch("read_idracips_from_mysqldb.resolve_pod_ip", return_value=TEST_POD_IP)
    @patch("read_idracips_from_mysqldb.pymysql")
    def test_read_uses_database_kwarg_no_interpolation(self, mock_pymysql, _mock_resolve):
        """Verify read connects with database= kwarg (no SHOW TABLES FROM {db} interpolation)."""
        mod = self._import_module()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [("services",)],  # SHOW TABLES result
            [(TEST_IP_1,), (TEST_IP_2,)]  # SELECT ip result
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn

        result = mod.run_mysql_read_in_pod(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret"
        )

        self.assertEqual(result["rc"], 0)
        self.assertEqual(result["ip_list"], [TEST_IP_1, TEST_IP_2])

        # Verify database= kwarg is used instead of identifier interpolation
        mock_pymysql.connect.assert_called_once_with(
            host=TEST_POD_IP,
            port=3306,
            user="root",
            password="secret",
            database="idrac_telemetrydb",
            connect_timeout=10
        )

        # Verify SQL statements are constant (no user input in them)
        calls = mock_cursor.execute.call_args_list
        self.assertEqual(calls[0], call("SHOW TABLES"))
        self.assertEqual(calls[1], call("SELECT ip FROM services"))

    @patch("read_idracips_from_mysqldb.resolve_pod_ip", return_value=TEST_POD_IP)
    @patch("read_idracips_from_mysqldb.pymysql")
    def test_no_services_table(self, mock_pymysql, _mock_resolve):
        """When the services table doesn't exist, return empty IP list."""
        mod = self._import_module()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("other_table",)]  # no 'services'
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn

        result = mod.run_mysql_read_in_pod(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret"
        )

        self.assertEqual(result["rc"], 0)
        self.assertIsNone(result["tables_found"])
        self.assertEqual(result["ip_list"], [])
        # Only SHOW TABLES should have been called
        mock_cursor.execute.assert_called_once_with("SHOW TABLES")

    @patch("read_idracips_from_mysqldb.resolve_pod_ip", return_value=TEST_POD_IP)
    @patch("read_idracips_from_mysqldb.pymysql")
    def test_connection_error_returns_rc_1(self, mock_pymysql, _mock_resolve):
        """Connection error returns rc=1 with error message."""
        mod = self._import_module()

        mock_pymysql.connect.side_effect = Exception("Connection refused")
        mock_pymysql.err.OperationalError = type("OperationalError", (Exception,), {})
        mock_pymysql.err.MySQLError = type("MySQLError", (Exception,), {})

        # Need to re-raise as one of the expected types
        mock_pymysql.connect.side_effect = mock_pymysql.err.OperationalError("Connection refused")

        result = mod.run_mysql_read_in_pod(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name="idrac_telemetrydb",
            mysql_user="root",
            mysql_password="secret"
        )

        self.assertEqual(result["rc"], 1)
        self.assertIn("Connection refused", result.get("result", ""))

    @patch("read_idracips_from_mysqldb.resolve_pod_ip", return_value=TEST_POD_IP)
    @patch("read_idracips_from_mysqldb.pymysql")
    def test_no_sql_contains_user_controlled_identifiers(self, mock_pymysql, _mock_resolve):
        """No SQL statement contains user-controlled identifiers (mysqldb_name etc)."""
        mod = self._import_module()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [("services",)],
            [(TEST_IP_1,)]
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn

        malicious_db_name = "db; DROP TABLE services; --"
        mod.run_mysql_read_in_pod(
            namespace="telemetry",
            pod="idrac-pod-0",
            mysqldb_container_port=3306,
            mysqldb_name=malicious_db_name,
            mysql_user="root",
            mysql_password="secret"
        )

        # Verify the malicious db name only appears in the connect() call
        # (as the database= kwarg, which PyMySQL handles safely), never in SQL text
        for c in mock_cursor.execute.call_args_list:
            sql = c[0][0]
            self.assertNotIn("DROP TABLE", sql)
            self.assertNotIn(malicious_db_name, sql)


# ---------------------------------------------------------------------------
# Tests for resolve_pod_ip (shared helper)
# ---------------------------------------------------------------------------
class TestResolvePodIP(unittest.TestCase):
    """Tests for the resolve_pod_ip helper function."""

    @patch("delete_idracips_from_mysqldb.client.CoreV1Api")
    def test_resolve_returns_pod_ip(self, mock_api_class):
        """Verify resolve_pod_ip returns the pod's IP from the K8s API."""
        import delete_idracips_from_mysqldb as mod

        mock_api = MagicMock()
        mock_pod = MagicMock()
        mock_pod.status.pod_ip = TEST_POD_IP
        mock_api.read_namespaced_pod.return_value = mock_pod
        mock_api_class.return_value = mock_api

        result = mod.resolve_pod_ip("telemetry", "idrac-pod-0")
        self.assertEqual(result, TEST_POD_IP)
        mock_api.read_namespaced_pod.assert_called_once_with(
            name="idrac-pod-0", namespace="telemetry"
        )

    @patch("delete_idracips_from_mysqldb.client.CoreV1Api")
    def test_resolve_raises_on_no_ip(self, mock_api_class):
        """Verify resolve_pod_ip raises RuntimeError when pod has no IP."""
        import delete_idracips_from_mysqldb as mod

        mock_api = MagicMock()
        mock_pod = MagicMock()
        mock_pod.status.pod_ip = None
        mock_api.read_namespaced_pod.return_value = mock_pod
        mock_api_class.return_value = mock_api

        with self.assertRaises(RuntimeError):
            mod.resolve_pod_ip("telemetry", "idrac-pod-0")


if __name__ == "__main__":
    unittest.main()
