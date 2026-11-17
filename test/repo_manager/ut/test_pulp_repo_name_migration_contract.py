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

"""Contract tests for no-behavior-change Pulp migration helper catches."""

# pylint: disable=protected-access

import unittest
from types import ModuleType
from unittest.mock import Mock, mock_open, patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from plugins.modules import pulp_repo_name_migration


class PulpRepoNameMigrationContractTests(unittest.TestCase):
    """Verify helper wrappers keep their original safe return contracts."""

    @staticmethod
    def _session():
        session = pulp_repo_name_migration._PulpApiSession.__new__(
            pulp_repo_name_migration._PulpApiSession
        )
        session._logger = Mock()
        session._base_url = None
        session._parsed = None
        session._auth_header = "Basic dGVzdDp0ZXN0"
        return session

    def test_load_config_invalid_cli_section_keeps_session_invalid(self):
        """Malformed CLI config stays a logged, non-raising initialization failure."""
        session = self._session()
        session._auth_header = None

        with patch.object(session, "_read_toml_config", return_value={"cli": None}):
            session._load_config()

        session._logger.error.assert_called_once_with(
            "Failed to process Pulp CLI configuration."
        )
        self.assertFalse(session.is_valid)

    def test_read_toml_config_returns_none_on_parser_type_error(self):
        """Parser type errors keep the ``None`` config contract."""
        fake_toml = ModuleType("toml")

        def boom(_text):
            raise TypeError("boom")

        fake_toml.loads = boom
        with patch.dict("sys.modules", {"toml": fake_toml}), patch.object(
            pulp_repo_name_migration.os.path, "isfile", return_value=True
        ), patch.object(
            pulp_repo_name_migration, "PULP_CLI_CONFIG_PATH", "/tmp/pulp.toml"
        ), patch("builtins.open", mock_open(
            read_data="[cli]\nbase_url='https://localhost'\n"
        )):
            result = pulp_repo_name_migration._PulpApiSession._read_toml_config()

        self.assertIsNone(result)

    def test_http_methods_return_standard_failure_dict_on_type_error(self):
        """POST/GET/PATCH still normalize helper TypeErrors to one failure dict."""
        expected = {
            "ok": False,
            "status": 0,
            "body": {"error": "Pulp API request failed"},
        }
        cases = [
            ("post", ("/pulp/api/v3/remotes/rpm/rpm/", {"name": "repo"}),
             "Pulp API POST %s failed."),
            ("get", ("/pulp/api/v3/remotes/rpm/rpm/",),
             "Pulp API GET %s failed."),
            ("patch", ("/pulp/api/v3/remotes/rpm/rpm/", {"name": "repo"}),
             "Pulp API PATCH %s failed."),
        ]

        for method_name, args, log_message in cases:
            with self.subTest(method=method_name):
                session = self._session()
                conn = Mock()
                conn.request.side_effect = TypeError("boom")
                session._make_connection = Mock(return_value=conn)

                result = getattr(session, method_name)(*args)

                self.assertEqual(result, expected)
                conn.close.assert_called_once()
                session._logger.error.assert_called_once_with(log_message, args[0])


if __name__ == "__main__":
    unittest.main()
