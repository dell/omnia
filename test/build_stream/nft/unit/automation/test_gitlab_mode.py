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

"""Unit tests of the gitlab_mode-aware execute scenario (needs the FVT toolchain)."""

import importlib.util
import pathlib
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("omnia_auto", reason="FVT toolchain (omnia_auto plugin) is not installed")

# pylint: disable=wrong-import-position
from library.functions import gitlab_mode_func as mode
from library.functions import gitlab_project_func as project_func
from library.functions import prepare_func
from library.functions.config_func import ConfigValidationError, validate_test_config

pytestmark = pytest.mark.unit

MODULE_ROOT = pathlib.Path(__file__).resolve().parents[3]
EXTERNAL_CONFIG = {
    "gitlab_mode": "external",
    "gitlab_host": "",
    "gitlab_external_url": "https://gitlab.example.test/",
    "gitlab_project_namespace": "infra",
    "gitlab_ca_cert_path": "/etc/pki/tls/certs/gitlab-ca.pem",
    "build_stream_host_ip": "10.0.0.1",
    "build_stream_port": 8010,
}
HOSTED_CONFIG = {"gitlab_mode": "hosted", "gitlab_host": "10.0.0.2"}
CREDENTIALS = {"gitlab_api_token": "glpat-x", "gitlab_project_id": 7}


@pytest.fixture(autouse=True)
def _fresh_mode_cache():
    """Every test resolves the mode and connection again."""
    mode.reset_gitlab_mode_cache()
    yield
    mode.reset_gitlab_mode_cache()


def _resolve(config):
    """Resolve the mode of ``config`` with the OIM reads replaced."""
    with patch.object(mode, "domain_input_path", return_value="/data/input/p"), \
            patch.object(mode, "read_remote_yaml", return_value=config):
        return mode.resolve_gitlab_mode(object(), refresh=True)


def _load(name, relative):
    """Import a script of the suite by path."""
    spec = importlib.util.spec_from_file_location(name, MODULE_ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestModeResolution:
    """gitlab_mode is read from the input file and validated."""

    @pytest.mark.parametrize("config,expected", [
        (HOSTED_CONFIG, "hosted"), (EXTERNAL_CONFIG, "external"),
        ({"gitlab_mode": " External "}, "external"),
    ])
    def test_supported_modes_resolve(self, config, expected):
        """GIVEN a supported gitlab_mode THEN it resolves."""
        result = _resolve(config)
        assert result["success"] and result["mode"] == expected

    @pytest.mark.parametrize("config", [{}, {"gitlab_mode": ""}, {"gitlab_mode": "self_hosted"}])
    def test_missing_or_unsupported_mode_fails(self, config):
        """GIVEN no or an old gitlab_mode THEN resolution fails with the supported values."""
        result = _resolve(config)
        assert not result["success"] and result["mode"] == ""
        assert "hosted, external" in result["error"]

    def test_unreadable_input_file_is_reported(self):
        """GIVEN an unreadable input file THEN the error names the file."""
        with patch.object(mode, "domain_input_path", return_value="/data/input/p"), \
                patch.object(mode, "read_remote_yaml", side_effect=RuntimeError("no file")):
            result = mode.resolve_gitlab_mode(object(), refresh=True)
        assert not result["success"] and "build_stream_config.yml" in result["error"]

    def test_mode_is_cached_until_reset(self):
        """GIVEN a resolved mode THEN a second call does not read the file again."""
        with patch.object(mode, "domain_input_path", return_value="/d"), \
                patch.object(mode, "read_remote_yaml", return_value=HOSTED_CONFIG) as read:
            mode.resolve_gitlab_mode(object())
            mode.resolve_gitlab_mode(object())
        assert read.call_count == 1


class TestModeApplies:
    """hosted_only / external_only tests are skipped only for the other mode."""

    @pytest.mark.parametrize("config,required,applies", [
        (HOSTED_CONFIG, "hosted", True), (HOSTED_CONFIG, "external", False),
        (EXTERNAL_CONFIG, "external", True), (EXTERNAL_CONFIG, "hosted", False),
    ])
    def test_decision(self, config, required, applies):
        """GIVEN the resolved mode THEN only the matching tests apply."""
        _resolve(config)
        decision = mode.mode_applies(object(), required)
        assert decision["applies"] is applies
        assert applies or required in decision["reason"]

    def test_unresolvable_mode_never_skips(self):
        """GIVEN an unreadable mode THEN the test runs and reports the problem itself."""
        unresolved = {"success": False, "mode": "", "config": {}, "path": "p", "error": "e"}
        with patch.object(mode, "resolve_gitlab_mode", return_value=unresolved):
            assert mode.mode_applies(object(), "external")["applies"] is True


class TestExternalConnection:
    """The external connection uses the PAT, the CA bundle and the project path."""

    @staticmethod
    def _connect(config=None, credentials=None):
        credentials = CREDENTIALS if credentials is None else credentials
        _resolve(config or EXTERNAL_CONFIG)
        with patch.object(mode, "domain_input_path", return_value="/data/input/p"), \
                patch.object(mode, "read_vault_mapping", return_value=credentials) as vault, \
                patch.object(mode, "external_tls", return_value=object()):
            return mode.external_connection(object()), vault

    def test_connection_fields(self):
        """GIVEN valid inputs THEN URL, API base, token header and project ref are built."""
        connection, _ = self._connect()
        assert connection["success"]
        assert connection["api"] == "https://gitlab.example.test/api/v4"
        assert connection["headers"] == {"PRIVATE-TOKEN": "glpat-x"}
        assert connection["project_ref"] == "infra%2Fomnia-catalog"
        assert connection["project_id"] == "7"

    def test_connection_is_built_once(self):
        """GIVEN a built connection THEN the vault is not decrypted again."""
        _, vault = self._connect()
        with patch.object(mode, "read_vault_mapping") as again:
            mode.external_connection(object())
        assert vault.call_count == 1 and again.call_count == 0

    def test_failed_connection_is_not_cached(self):
        """GIVEN an empty token THEN the failure is reported and retried next time."""
        connection, _ = self._connect(credentials={"gitlab_api_token": ""})
        assert not connection["success"] and "gitlab_api_token" in connection["error"]
        assert "result" not in mode._CONNECTION_CACHE  # pylint: disable=protected-access

    def test_hosted_mode_is_rejected(self):
        """GIVEN gitlab_mode hosted THEN no external connection is built."""
        connection, _ = self._connect(config=HOSTED_CONFIG)
        assert not connection["success"] and "not external" in connection["error"]

    def test_empty_ca_uses_system_trust_store(self):
        """GIVEN no CA path THEN a default TLS context verifies the server."""
        assert mode.external_tls(object(), "").verify_mode.name == "CERT_REQUIRED"

    def test_unreadable_ca_bundle_fails_closed(self):
        """GIVEN an unreadable CA bundle THEN TLS setup raises."""
        with patch.object(mode, "run_cmd", return_value=SimpleNamespace(rc=1, stdout="")), \
                pytest.raises(RuntimeError):
            mode.external_tls(object(), "/missing.pem")


class TestModeInputsCheck:
    """check_gitlab_mode_inputs reports the resolved mode and its inputs."""

    @staticmethod
    def _check(config, expected=""):
        resolved = _resolve(config)
        with patch.object(mode, "resolve_gitlab_mode", return_value=resolved):
            return mode.check_gitlab_mode_inputs(object(), expected)

    def test_modes_pass_with_valid_inputs(self):
        """GIVEN valid hosted and external inputs THEN the check passes."""
        assert self._check(HOSTED_CONFIG)["mode"] == "hosted"
        assert self._check(EXTERNAL_CONFIG)["success"]

    def test_invalid_inputs_and_expected_mode_fail(self):
        """GIVEN a broken input or a different expected mode THEN the check fails."""
        assert not self._check({**EXTERNAL_CONFIG, "gitlab_external_url": "http://x"})["success"]
        assert not self._check(EXTERNAL_CONFIG, "hosted")["success"]

    def test_unresolvable_mode_fails_with_empty_mode(self):
        """GIVEN no gitlab_mode THEN the check fails with the mode empty."""
        result = self._check({})
        assert not result["success"] and result["mode"] == ""


class TestProjectFunctionsExternalBranch:
    """gitlab_project_func uses the external connection only in external mode."""

    CONNECTION = {
        "success": True, "error": "", "api": "https://gl/api/v4", "tls": object(),
        "headers": {"PRIVATE-TOKEN": "t"}, "project_ref": "infra%2Fomnia-catalog",
        "settings": {"project_path": "infra/omnia-catalog", "branch": "dev",
                     "visibility": "internal"},
    }

    def _patch(self, mode_name, connection=None):
        resolved = {"success": True, "mode": mode_name, "config": {}, "path": "p", "error": ""}
        return (patch.object(project_func, "resolve_gitlab_mode", return_value=resolved),
                patch.object(project_func, "external_connection",
                             return_value=connection or self.CONNECTION))

    def test_hosted_mode_has_no_external_connection(self):
        """GIVEN hosted THEN the SSH-derived hosted path is kept."""
        first, second = self._patch("hosted")
        with first, second as connect:
            assert project_func._external_connection(object()) == {}  # pylint: disable=protected-access
        assert connect.call_count == 0

    def test_external_api_context(self):
        """GIVEN external THEN the API context carries the PAT header, project ref and branch."""
        first, second = self._patch("external")
        with first, second:
            context = project_func._api_context(object(), {})  # pylint: disable=protected-access
        assert context["api_url"] == "https://gl/api/v4" and context["branch"] == "dev"
        assert context["project_id"] == "infra%2Fomnia-catalog" and not context["error"]

    def test_external_connection_error_is_returned(self):
        """GIVEN a failed external connection THEN the context carries the error."""
        first, second = self._patch("external", {"success": False, "error": "no token"})
        with first, second:
            context = project_func._api_context(object(), {})  # pylint: disable=protected-access
        assert context == {"error": "no token"}

    def test_expected_visibility_follows_the_mode(self):
        """GIVEN external THEN the configured visibility is the expectation."""
        first, second = self._patch("external")
        with first, second:
            value = project_func._expected_project_setting(  # pylint: disable=protected-access
                object(), "project_visibility", "visibility", "private")
        assert value == "internal"


class TestPrepareStatusFile:
    """build_stream_status.yml is checked per mode."""

    STATUS = {"overall_status": "prepared", "build_stream_host": "h", "build_stream_port": 1,
              "gitlab_host": "", "gitlab_url": "https://gl", "bsm_api_url": "https://b",
              "gitlab_mode": "external"}

    def _run(self, mode_name, status):
        resolved = {"success": True, "mode": mode_name, "config": {}, "path": "p", "error": ""}
        with patch.object(prepare_func, "domain_output_path", return_value="/out"), \
                patch.object(prepare_func, "read_remote_yaml", return_value=status), \
                patch.object(prepare_func, "resolve_gitlab_mode", return_value=resolved):
            return prepare_func.check_prepare_status_file(object())

    def test_external_accepts_an_empty_gitlab_host(self):
        """GIVEN external THEN an empty gitlab_host passes."""
        assert self._run("external", self.STATUS)["success"]

    def test_external_requires_the_mode_key(self):
        """GIVEN external without gitlab_mode in the status file THEN the check fails."""
        status = {key: value for key, value in self.STATUS.items() if key != "gitlab_mode"}
        assert not self._run("external", status)["success"]

    def test_hosted_still_requires_gitlab_host(self):
        """GIVEN hosted THEN an empty gitlab_host fails as before."""
        assert not self._run("hosted", self.STATUS)["success"]
        assert self._run("hosted", {**self.STATUS, "gitlab_host": "10.0.0.2"})["success"]


class TestConftestModeSkip:  # pylint: disable=too-few-public-methods
    """The conftest hook skips tests of the other gitlab_mode."""

    @staticmethod
    def _item(marker):
        return SimpleNamespace(name="test_x", get_closest_marker=lambda name: name == marker)

    @pytest.fixture(name="conf")
    def _conf(self):
        return _load("fvt_conftest", "conftest.py")

    @pytest.mark.parametrize("marker,mode_name,skipped", [
        ("hosted_only", "external", True), ("hosted_only", "hosted", False),
        ("external_only", "hosted", True), ("external_only", "external", False),
        (None, "external", False),
    ])
    def test_skip_decision(self, conf, marker, mode_name, skipped):
        """GIVEN a mode marker and the resolved mode THEN only the other mode is skipped."""
        resolved = {"success": True, "mode": mode_name, "config": {}, "path": "p", "error": ""}
        with patch.object(mode, "resolve_gitlab_mode", return_value=resolved), \
                patch.object(conf, "get_testinfra_host", return_value=object()):
            if skipped:
                with pytest.raises(pytest.skip.Exception):
                    conf._skip_for_gitlab_mode(self._item(marker))  # pylint: disable=protected-access
            else:
                conf._skip_for_gitlab_mode(self._item(marker))  # pylint: disable=protected-access


class TestDatasetGenerator:  # pylint: disable=too-few-public-methods
    """The dataset generator asks for the fields of the selected mode."""

    @pytest.mark.parametrize("document,fields", [
        ({"gitlab_mode": "external"},
         ("build_stream_host_ip", "gitlab_external_url", "gitlab_project_namespace")),
        ({"gitlab_mode": "hosted"}, ("build_stream_host_ip", "gitlab_host")),
        ({}, ("build_stream_host_ip", "gitlab_host")),
    ])
    def test_review_fields(self, document, fields):
        """GIVEN the document mode THEN the review fields follow it."""
        pytest.importorskip("jinja2")
        generator = _load("generate_dataset", "datasets/generator/generate_dataset.py")
        assert generator._review_fields(document) == fields  # pylint: disable=protected-access


class TestConfigIntegration:
    """test_config.yml validation wires the gitlab block."""

    BASE = {"report_path": "/tmp/r", "report_name": "n", "installation": {"catalog": 1}}

    def test_invalid_block_raises_config_error(self):
        """GIVEN an invalid gitlab block THEN validation raises ConfigValidationError."""
        with pytest.raises(ConfigValidationError):
            validate_test_config({**self.BASE, "gitlab": {"expected_mode": "cloud"}})

    def test_valid_block_is_accepted(self):
        """GIVEN a valid gitlab block THEN validation passes."""
        validate_test_config({**self.BASE, "gitlab": {"expected_mode": "external"}})
