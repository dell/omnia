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

"""Unit tests of the gitlab_mode-aware execute scenario (hosted / external)."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("omnia_auto", reason="FVT toolchain (omnia_auto plugin) is not installed")

# pylint: disable=wrong-import-position
from library.functions import gitlab_external_func as ext
from library.functions import gitlab_mode_func as mode
from library.functions.config_func import (
    ConfigValidationError,
    gitlab_settings,
    validate_test_config,
)

pytestmark = pytest.mark.unit

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


@pytest.fixture(autouse=True)
def _fresh_mode_cache():
    """Every test resolves the mode again."""
    mode.reset_gitlab_mode_cache()
    yield
    mode.reset_gitlab_mode_cache()


def _resolve(config):
    """Resolve the mode of ``config`` with the OIM reads replaced."""
    with patch.object(mode, "domain_input_path", return_value="/data/input/p"), \
            patch.object(mode, "read_remote_yaml", return_value=config):
        return mode.resolve_gitlab_mode(object(), refresh=True)


class TestModeResolution:
    """gitlab_mode is read from the input file and validated."""

    @pytest.mark.parametrize("config,expected", [
        (HOSTED_CONFIG, "hosted"),
        (EXTERNAL_CONFIG, "external"),
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
        (HOSTED_CONFIG, "hosted", True),
        (HOSTED_CONFIG, "external", False),
        (EXTERNAL_CONFIG, "external", True),
        (EXTERNAL_CONFIG, "hosted", False),
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


class TestExternalSettings:
    """Defaults and normalization of the external inputs."""

    def test_defaults_and_trailing_slash(self):
        """GIVEN the minimal external inputs THEN defaults are applied."""
        settings = mode.external_settings(EXTERNAL_CONFIG)
        assert settings["url"] == "https://gitlab.example.test"
        assert settings["project_path"] == "infra/omnia-catalog"
        assert (settings["branch"], settings["visibility"]) == ("main", "private")

    def test_explicit_values(self):
        """GIVEN explicit inputs THEN they are used."""
        settings = mode.external_settings({
            **EXTERNAL_CONFIG, "gitlab_project_namespace": "/a/b/",
            "gitlab_project_name": "cat", "gitlab_default_branch": "dev",
            "gitlab_project_visibility": "internal", "gitlab_ca_cert_path": "",
        })
        assert settings["project_path"] == "a/b/cat"
        assert (settings["branch"], settings["visibility"], settings["ca_path"]) == (
            "dev", "internal", "")


class TestExternalConnection:
    """The external connection uses the PAT, the CA bundle and the project path."""

    def _connect(self, config=None, credentials=None, tls=object()):
        credentials = {"gitlab_api_token": "glpat-x", "gitlab_project_id": 7} \
            if credentials is None else credentials
        _resolve(config or EXTERNAL_CONFIG)
        with patch.object(mode, "domain_input_path", return_value="/data/input/p"), \
                patch.object(mode, "read_vault_mapping", return_value=credentials), \
                patch.object(mode, "external_tls", return_value=tls):
            return mode.external_connection(object())

    def test_connection_fields(self):
        """GIVEN valid inputs THEN URL, API base, token header and project ref are built."""
        connection = self._connect()
        assert connection["success"]
        assert connection["api"] == "https://gitlab.example.test/api/v4"
        assert connection["headers"] == {"PRIVATE-TOKEN": "glpat-x"}
        assert connection["project_ref"] == "infra%2Fomnia-catalog"
        assert connection["project_id"] == "7"

    def test_missing_token_fails_without_echoing_secrets(self):
        """GIVEN an empty token THEN the connection fails."""
        connection = self._connect(credentials={"gitlab_api_token": ""})
        assert not connection["success"] and "gitlab_api_token" in connection["error"]

    def test_hosted_mode_is_rejected(self):
        """GIVEN gitlab_mode hosted THEN no external connection is built."""
        connection = self._connect(config=HOSTED_CONFIG)
        assert not connection["success"] and "not external" in connection["error"]

    def test_empty_ca_uses_system_trust_store(self):
        """GIVEN no CA path THEN a default TLS context verifies the server."""
        context = mode.external_tls(object(), "")
        assert context.verify_mode.name == "CERT_REQUIRED"

    def test_unreadable_ca_bundle_fails_closed(self):
        """GIVEN an unreadable CA bundle THEN TLS setup raises."""
        failed = SimpleNamespace(rc=1, stdout="")
        with patch.object(mode, "run_cmd", return_value=failed), pytest.raises(RuntimeError):
            mode.external_tls(object(), "/missing.pem")


class TestPureHelpers:
    """Syntax, version, expiry and mode helpers of the external checks."""

    @pytest.mark.parametrize("url,valid", [
        ("https://gitlab.example.test", True),
        ("https://10.0.0.5:8443/group", True),
        ("https://host:70000", False),
        ("http://gitlab.example.test", False),
        ("", False),
    ])
    def test_url(self, url, valid):
        """URL syntax matches the product validator."""
        assert ext.is_valid_external_url(url) is valid

    @pytest.mark.parametrize("value,valid", [("infra", True), ("infra/omnia-builds", True),
                                             ("/infra", False), ("in fra", False), ("", False)])
    def test_namespace(self, value, valid):
        """Group path syntax matches the product validator."""
        assert ext.is_valid_namespace(value) is valid

    @pytest.mark.parametrize("version,major", [("17.4.1-ee", 17), ("19.0", 19), ("x", None)])
    def test_major_version(self, version, major):
        """The major GitLab version is parsed."""
        assert ext.gitlab_major_version(version) == major

    def test_days_until(self):
        """Token expiry is counted in whole days."""
        assert ext.days_until("2026-12-24", date(2026, 11, 24)) == 30
        assert ext.days_until("", date(2026, 11, 24)) is None
        assert ext.days_until("garbage") is None

    @pytest.mark.parametrize("value,safe", [("644", True), ("600", True), ("444", True),
                                            ("664", False), ("755", False), ("x", False)])
    def test_ca_mode(self, value, safe):
        """The CA bundle must be 0644 or stricter without execute bits."""
        assert ext.mode_is_ca_safe(value) is safe


class TestModeInputsCheck:
    """check_gitlab_mode_inputs validates the inputs of the resolved mode."""

    @staticmethod
    def _check(config, expected=""):
        resolved = _resolve(config)
        with patch.object(ext, "resolve_gitlab_mode", return_value=resolved):
            return ext.check_gitlab_mode_inputs(object(), expected)

    def test_hosted_needs_ipv4_host(self):
        """GIVEN hosted with an IPv4 gitlab_host THEN the check passes."""
        result = self._check(HOSTED_CONFIG)
        assert result["success"] and result["mode"] == "hosted"
        assert not self._check({"gitlab_mode": "hosted", "gitlab_host": "name"})["success"]

    def test_external_needs_url_and_namespace(self):
        """GIVEN external inputs THEN URL and namespace are validated."""
        assert self._check(EXTERNAL_CONFIG)["success"]
        broken = {**EXTERNAL_CONFIG, "gitlab_external_url": "http://x"}
        assert not self._check(broken)["success"]
        assert not self._check({**EXTERNAL_CONFIG, "gitlab_project_namespace": ""})["success"]

    def test_expected_mode_must_match(self):
        """GIVEN gitlab.expected_mode THEN a different input mode fails."""
        assert self._check(EXTERNAL_CONFIG, "external")["success"]
        assert not self._check(EXTERNAL_CONFIG, "hosted")["success"]

    def test_unresolvable_mode_fails(self):
        """GIVEN no gitlab_mode THEN the check fails with the mode empty."""
        result = self._check({})
        assert not result["success"] and result["mode"] == ""


class TestExternalChecks:
    """External checks against a fake GitLab API (no network)."""

    CONNECTION = {
        "success": True, "error": "", "url": "https://gitlab.example.test",
        "api": "https://gitlab.example.test/api/v4", "tls": object(),
        "headers": {"PRIVATE-TOKEN": "glpat-secret"}, "project_ref": "infra%2Fomnia-catalog",
        "project_id": "7", "config": EXTERNAL_CONFIG, "input_dir": "/d",
        "settings": mode.external_settings(EXTERNAL_CONFIG),
    }

    @staticmethod
    def _api(routes):
        def fake(_tls, _method, url, **_options):
            for suffix, data in routes.items():
                if url.endswith(suffix):
                    ok = data is not None
                    return {"success": ok, "status": 200 if ok else 404, "data": data,
                            "error": "" if ok else "HTTP 404"}
            return {"success": False, "status": 404, "data": None, "error": "HTTP 404"}
        return fake

    def _run(self, function, routes, *args, journal=None, stat=None):
        with patch.object(ext, "external_connection", return_value=dict(self.CONNECTION)), \
                patch.object(ext, "http_json", side_effect=self._api(routes)), \
                patch.object(ext, "_journal", return_value=journal or {
                    "path": "j", "text": "", "data": {}, "rc": 1}), \
                patch.object(ext, "_stat", return_value=stat or {"owner": "0", "mode": "600"}):
            return function(object(), *args)

    def test_api_check_passes_for_supported_version_and_scopes(self):
        """GIVEN GitLab 18, full scopes, valid token and an admin THEN the check passes."""
        routes = {
            "/version": {"version": "18.2.1"},
            "/personal_access_tokens/self": {"scopes": ["api", "write_repository"],
                                             "expires_at": "2099-01-01"},
            "/user": {"id": 1, "username": "root", "is_admin": True},
            "/groups/infra": {"id": 5},
        }
        assert self._run(ext.check_external_gitlab_api, routes, 30)["success"]

    @pytest.mark.parametrize("version,scopes,reason", [
        ("16.9.0", ["api", "write_repository"], "GitLab version"),
        ("18.2.1", ["api"], "Token scopes"),
    ])
    def test_api_check_fails(self, version, scopes, reason):
        """GIVEN an unsupported version or missing scope THEN the check names it."""
        routes = {
            "/version": {"version": version},
            "/personal_access_tokens/self": {"scopes": scopes, "expires_at": "2099-01-01"},
            "/user": {"id": 1, "is_admin": True},
            "/groups/infra": {"id": 5},
        }
        result = self._run(ext.check_external_gitlab_api, routes, 0)
        assert not result["success"] and reason in result["error"]

    def test_expiring_token_fails_the_threshold(self):
        """GIVEN a token that expires too soon THEN the check fails."""
        routes = {
            "/version": {"version": "18.0"},
            "/personal_access_tokens/self": {"scopes": ["api", "write_repository"],
                                             "expires_at": "2000-01-01"},
            "/user": {"id": 1, "is_admin": True},
            "/groups/infra": {"id": 5},
        }
        assert not self._run(ext.check_external_gitlab_api, routes, 0)["success"]

    def test_project_check(self):
        """GIVEN an Omnia-marked project in the namespace THEN the check passes."""
        project = {"id": 7, "path_with_namespace": "infra/omnia-catalog",
                   "description": "Omnia (managed-by:omnia-buildstream)",
                   "visibility": "private", "default_branch": "main"}
        routes = {"/projects/infra%2Fomnia-catalog": project,
                  "/protected_branches/main": {"name": "main"}}
        assert self._run(ext.check_external_project, routes)["success"]
        project["description"] = "someone else"
        result = self._run(ext.check_external_project, routes)
        assert not result["success"] and "Ownership marker" in result["error"]

    def test_runner_check_needs_online_runner_and_user_provided(self):
        """GIVEN an online runner and a user_provided journal entry THEN the check passes."""
        journal = {"path": "j", "text": "", "rc": 0,
                   "data": {"resources": [{"type": "runner", "action": "user_provided"}]}}
        routes = {"/projects/infra%2Fomnia-catalog": {"id": 7},
                  "/projects/7/runners?status=online&per_page=100": [{"id": 1}]}
        assert self._run(ext.check_external_runner, routes, journal=journal)["success"]
        routes["/projects/7/runners?status=online&per_page=100"] = []
        assert not self._run(ext.check_external_runner, routes, journal=journal)["success"]

    def test_journal_never_contains_the_token(self):
        """GIVEN the PAT in the journal text THEN the check fails."""
        data = {"schema_version": 1, "gitlab_url": "https://gitlab.example.test",
                "project_id": "7", "resources": [{"type": name} for name in (
                    "project", "runner", "access_token", "trigger", "variable")]}
        clean = {"path": "j", "text": "{}", "rc": 0, "data": data}
        leaky = {**clean, "text": "glpat-secret"}
        connection = dict(self.CONNECTION)
        with patch.object(ext, "external_connection", return_value=connection), \
                patch.object(ext, "_stat", return_value={"owner": "0", "mode": "600"}):
            with patch.object(ext, "_journal", return_value=clean):
                assert ext.check_external_journal(object())["success"]
            with patch.object(ext, "_journal", return_value=leaky):
                assert not ext.check_external_journal(object())["success"]

    def test_connection_failure_is_a_failed_result(self):
        """GIVEN no connection THEN every check fails with the reason."""
        with patch.object(ext, "external_connection",
                          return_value={"success": False, "error": "no token"}):
            result = ext.check_external_project(object())
        assert not result["success"] and "no token" in result["error"]


class TestGitlabConfig:
    """test_config.yml gitlab block."""

    BASE = {"report_path": "/tmp/r", "report_name": "n", "installation": {"catalog": 1}}

    def test_defaults(self):
        """GIVEN no gitlab block THEN defaults apply."""
        validate_test_config(self.BASE)
        assert gitlab_settings(self.BASE) == {"expected_mode": "",
                                              "token_min_days_remaining": 30}

    @pytest.mark.parametrize("block", [
        {"expected_mode": "cloud"}, {"token_min_days_remaining": -1},
        {"token_min_days_remaining": True}, {"unknown": 1},
    ])
    def test_invalid_blocks_are_rejected(self, block):
        """GIVEN an invalid gitlab block THEN validation fails."""
        with pytest.raises(ConfigValidationError):
            validate_test_config({**self.BASE, "gitlab": block})

    def test_valid_block(self):
        """GIVEN a valid gitlab block THEN it is accepted."""
        config = {**self.BASE, "gitlab": {"expected_mode": "external",
                                          "token_min_days_remaining": 0}}
        validate_test_config(config)
        assert gitlab_settings(config)["expected_mode"] == "external"
