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

"""Unit tests of the external GitLab checks against a fake GitLab API (no network)."""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("omnia_auto", reason="FVT toolchain (omnia_auto plugin) is not installed")

# pylint: disable=wrong-import-position
from library.functions import gitlab_external_func as ext
from library.functions.gitlab_mode_func import external_settings

pytestmark = pytest.mark.unit

CONFIG = {
    "gitlab_mode": "external",
    "gitlab_external_url": "https://gitlab.example.test",
    "gitlab_project_namespace": "infra",
    "gitlab_ca_cert_path": "/etc/pki/tls/certs/gitlab-ca.pem",
    "build_stream_host_ip": "10.0.0.1",
    "build_stream_port": 8010,
}
PROJECT = "/projects/infra%2Fomnia-catalog"
RUNNERS = "/projects/7/runners?status=online&per_page=100"
GOOD_API = {
    "/version": {"version": "18.2.1"},
    "/personal_access_tokens/self": {"scopes": ["api", "write_repository"],
                                     "expires_at": "2099-01-01"},
    "/user": {"id": 1, "username": "root", "is_admin": True},
    "/groups/infra": {"id": 5},
}


def _in_days(days):
    return (date.today() + timedelta(days=days)).isoformat()


def _connection(**overrides):
    base = {
        "success": True, "error": "", "url": "https://gitlab.example.test",
        "api": "https://gitlab.example.test/api/v4", "tls": object(),
        "headers": {"PRIVATE-TOKEN": "glpat-secret"}, "project_ref": "infra%2Fomnia-catalog",
        "project_id": "7", "config": CONFIG, "input_dir": "/d",
        "settings": external_settings(CONFIG),
    }
    return {**base, **overrides}


def _fake_api(routes):
    def fake(_tls, _method, url, **_options):
        for suffix, data in routes.items():
            if url.endswith(suffix):
                ok = data is not None
                return {"success": ok, "status": 200 if ok else 404, "data": data,
                        "error": "" if ok else "HTTP 404"}
        return {"success": False, "status": 404, "data": None, "error": "HTTP 404"}
    return fake


def _run(function, routes=None, args=(), journal=None,  # pylint: disable=too-many-arguments,too-many-positional-arguments
         stat=None, files=None, connection=None):
    """Run a check with the connection, API, journal, stat and file reads replaced."""
    files = files or {}

    def fake_cmd(_host, _key, path="", **_params):
        return SimpleNamespace(rc=0 if path in files else 1, stdout=files.get(path, ""))

    with patch.object(ext, "external_connection", return_value=connection or _connection()), \
            patch.object(ext, "http_json", side_effect=_fake_api(routes or {})), \
            patch.object(ext, "_journal", return_value=journal or {
                "path": "j", "text": "", "data": {}, "rc": 1}), \
            patch.object(ext, "_stat", return_value=stat or {"owner": "0", "mode": "600"}), \
            patch.object(ext, "run_cmd", side_effect=fake_cmd), \
            patch.object(ext, "domain_output_path", return_value="/out"), \
            patch.object(ext, "data_path", return_value="/data"):
        return function(object(), *args)


class TestGitlabApi:
    """Version, token and group role."""

    def test_passes_for_supported_version_scopes_and_admin(self):
        """GIVEN GitLab 18, full scopes, valid token and an admin THEN the check passes."""
        assert _run(ext.check_external_gitlab_api, GOOD_API, (30,))["success"]

    @pytest.mark.parametrize("version,scopes,reason", [
        ("16.9.0", ["api", "write_repository"], "GitLab version"),
        ("18.2.1", ["api"], "Token scopes"),
    ])
    def test_unsupported_version_or_scope_fails(self, version, scopes, reason):
        """GIVEN an unsupported version or missing scope THEN the check names it."""
        routes = {**GOOD_API, "/version": {"version": version},
                  "/personal_access_tokens/self": {"scopes": scopes, "expires_at": "2099-01-01"}}
        result = _run(ext.check_external_gitlab_api, routes, (0,))
        assert not result["success"] and reason in result["error"]

    def test_expired_token_fails_even_without_a_threshold(self):
        """GIVEN an expired token THEN the check fails with a minimum of 0 days."""
        routes = {**GOOD_API, "/personal_access_tokens/self": {
            "scopes": ["api", "write_repository"], "expires_at": "2000-01-01"}}
        assert not _run(ext.check_external_gitlab_api, routes, (0,))["success"]

    def test_token_below_the_minimum_days_fails(self):
        """GIVEN 10 days left and a minimum of 30 THEN the check fails; a minimum of 5 passes."""
        soon = _in_days(10)
        routes = {**GOOD_API, "/personal_access_tokens/self": {
            "scopes": ["api", "write_repository"], "expires_at": soon}}
        assert not _run(ext.check_external_gitlab_api, routes, (30,))["success"]
        assert _run(ext.check_external_gitlab_api, routes, (5,))["success"]

    def test_non_admin_needs_maintainer_on_the_group(self):
        """GIVEN a non-admin THEN access level 40 passes and 30 fails."""
        routes = {**GOOD_API, "/user": {"id": 9, "is_admin": False},
                  "/groups/5/members/all/9": {"access_level": 40}}
        assert _run(ext.check_external_gitlab_api, routes, (0,))["success"]
        routes["/groups/5/members/all/9"] = {"access_level": 30}
        assert not _run(ext.check_external_gitlab_api, routes, (0,))["success"]

    def test_unreadable_token_user_is_reported_clearly(self):
        """GIVEN /user fails THEN the role probe says so instead of calling members/None."""
        routes = {key: value for key, value in GOOD_API.items() if key != "/user"}
        result = _run(ext.check_external_gitlab_api, routes, (0,))
        assert not result["success"] and "TOKEN USER NOT READABLE" in result["error"]


class TestProjectAndRunner:
    """Project, runner and CI token."""

    PROJECT_DATA = {"id": 7, "path_with_namespace": "infra/omnia-catalog",
                    "description": "Omnia (managed-by:omnia-buildstream)",
                    "visibility": "private", "default_branch": "main"}

    def test_project_check(self):
        """GIVEN an Omnia-marked project in the namespace THEN the check passes."""
        routes = {PROJECT: dict(self.PROJECT_DATA),
                  "/protected_branches/main": {"name": "main"}}
        assert _run(ext.check_external_project, routes)["success"]
        routes[PROJECT] = {**self.PROJECT_DATA, "description": "someone else"}
        result = _run(ext.check_external_project, routes)
        assert not result["success"] and "Ownership marker" in result["error"]

    def test_missing_project_fails(self):
        """GIVEN no project THEN the check fails."""
        assert not _run(ext.check_external_project, {PROJECT: None})["success"]

    def test_runner_needs_an_online_user_provided_runner(self):
        """GIVEN an online runner and a user_provided journal entry THEN the check passes."""
        journal = {"path": "j", "text": "", "rc": 0,
                   "data": {"resources": [{"type": "runner", "action": "user_provided"}]}}
        routes = {PROJECT: {"id": 7}, RUNNERS: [{"id": 1}]}
        assert _run(ext.check_external_runner, routes, journal=journal)["success"]
        assert not _run(ext.check_external_runner, {**routes, RUNNERS: []},
                        journal=journal)["success"]

    def test_runner_registered_by_omnia_fails(self):
        """GIVEN a journal runner entry that is not user_provided THEN the check fails."""
        journal = {"path": "j", "text": "", "rc": 0,
                   "data": {"resources": [{"type": "runner", "action": "created"}]}}
        assert not _run(ext.check_external_runner, {PROJECT: {"id": 7}, RUNNERS: [{"id": 1}]},
                        journal=journal)["success"]

    def test_ci_token_check(self):
        """GIVEN one valid omnia-ci token recorded in the journal THEN the check passes."""
        token = {"id": 3, "name": "omnia-ci", "scopes": ["api"], "access_level": 40,
                 "expires_at": "2099-01-01"}
        journal = {"path": "j", "text": "", "rc": 0,
                   "data": {"resources": [{"type": "access_token", "token_id": 3}]}}
        url = "/projects/7/access_tokens?state=active&per_page=100"
        routes = {PROJECT: {"id": 7}, url: [token]}
        assert not _run(ext.check_external_ci_token, routes, journal=journal)["success"], \
            "an expiry beyond 360 days must fail"
        token["expires_at"] = _in_days(300)
        assert _run(ext.check_external_ci_token, routes, journal=journal)["success"]
        routes[url] = [token, dict(token, id=4)]
        assert not _run(ext.check_external_ci_token, routes, journal=journal)["success"]


class TestTriggerAndVariables:
    """Pipeline trigger, token file and CI/CD variables."""

    @staticmethod
    def _variables(**changes):
        base = {
            "GITLAB_API_TOKEN": {"masked": True, "protected": True, "value": "s"},
            "BSM_API_URL": {"masked": False, "protected": False, "value": "https://10.0.0.1:8010"},
            "BSM_API_USERNAME": {"masked": False, "protected": True, "value": "u"},
            "BSM_API_PASSWORD": {"masked": True, "protected": True, "value": "p"},
            "BSM_API_CERT": {"masked": False, "protected": False, "value": "CERT"},
            "BSM_LOG_TAIL_LINES": {"masked": False, "protected": False, "value": "50"},
        }
        base.update(changes)
        return [{"key": key, **value} for key, value in base.items()]

    def _routes(self, variables):
        return {PROJECT: {"id": 7},
                "/projects/7/triggers": [{"description": "Omnia Software Catalog Webhook"}],
                "/projects/7/variables?per_page=100": variables}

    def _check(self, variables):
        return _run(ext.check_external_trigger_and_variables, self._routes(variables),
                    files={"/data/build_stream/ssl/bs_cert.pem": "CERT\n"})

    def test_all_flags_and_values_match(self):
        """GIVEN the six variables with the product flags THEN the check passes."""
        assert self._check(self._variables())["success"]

    @pytest.mark.parametrize("key,flags", [
        ("GITLAB_API_TOKEN", {"masked": False, "protected": True, "value": "s"}),
        ("BSM_API_PASSWORD", {"masked": True, "protected": False, "value": "p"}),
    ])
    def test_wrong_masked_or_protected_flag_fails(self, key, flags):
        """GIVEN a secret variable that is not masked and protected THEN the check fails."""
        assert not self._check(self._variables(**{key: flags}))["success"]

    def test_missing_variable_fails(self):
        """GIVEN a missing variable THEN the check fails."""
        variables = [item for item in self._variables() if item["key"] != "BSM_API_CERT"]
        assert not self._check(variables)["success"]

    def test_ca_path_in_a_variable_fails(self):
        """GIVEN the CA path injected into a variable THEN the check fails."""
        leaked = {"masked": False, "protected": False, "value": "/etc/pki/tls/certs/gitlab-ca.pem"}
        result = self._check(self._variables(BSM_LOG_TAIL_LINES=leaked))
        assert not result["success"] and "CA path injected" in result["error"]

    def test_cert_must_equal_bs_cert(self):
        """GIVEN a BSM_API_CERT that differs from bs_cert.pem THEN the check fails."""
        other = {"masked": False, "protected": False, "value": "OTHER"}
        assert not self._check(self._variables(BSM_API_CERT=other))["success"]


class TestCredentialsAndCaBundle:
    """Credential store and CA bundle."""

    @staticmethod
    def _credentials(values):
        resolved = {"success": True, "mode": "external", "config": CONFIG, "path": "p",
                    "error": ""}
        with patch.object(ext, "resolve_gitlab_mode", return_value=resolved), \
                patch.object(ext, "domain_input_path", return_value="/d"), \
                patch.object(ext, "read_vault_mapping", return_value=values):
            return ext.check_external_credentials(object())

    def test_token_and_project_id_are_required(self):
        """GIVEN a token and a numeric project ID THEN the check passes, else it fails."""
        assert self._credentials({"gitlab_api_token": "t", "gitlab_project_id": 7})["success"]
        assert not self._credentials({"gitlab_api_token": "", "gitlab_project_id": 7})["success"]
        assert not self._credentials({"gitlab_api_token": "t"})["success"]

    def test_token_value_is_never_reported(self):
        """GIVEN a token THEN no report field carries its value."""
        result = self._credentials({"gitlab_api_token": "glpat-secret", "gitlab_project_id": 7})
        assert "glpat-secret" not in str(result["fields"])

    def _ca(self, config, text, stat):
        resolved = {"success": True, "mode": "external", "config": config, "path": "p",
                    "error": ""}
        with patch.object(ext, "resolve_gitlab_mode", return_value=resolved), \
                patch.object(ext, "run_cmd",
                             return_value=SimpleNamespace(rc=0 if text is not None else 1,
                                                          stdout=text or "")), \
                patch.object(ext, "_stat", return_value=stat):
            return ext.check_external_ca_bundle(object())

    def test_ca_bundle_rules(self):
        """GIVEN a root-owned certificate bundle THEN it passes; a key, bad mode or owner fails."""
        good = "-----BEGIN CERTIFICATE-----\nx\n"
        assert self._ca(CONFIG, good, {"owner": "0", "mode": "644"})["success"]
        assert not self._ca(CONFIG, good + "PRIVATE KEY", {"owner": "0", "mode": "644"})["success"]
        assert not self._ca(CONFIG, good, {"owner": "0", "mode": "666"})["success"]
        assert not self._ca(CONFIG, good, {"owner": "1000", "mode": "644"})["success"]
        assert not self._ca(CONFIG, None, {})["success"]

    def test_empty_ca_path_uses_the_system_trust_store(self):
        """GIVEN no gitlab_ca_cert_path THEN the check passes."""
        assert self._ca({**CONFIG, "gitlab_ca_cert_path": ""}, None, {})["success"]


class TestJournal:
    """Setup journal."""

    DATA = {"schema_version": 1, "gitlab_url": "https://gitlab.example.test", "project_id": "7",
            "resources": [{"type": name} for name in (
                "project", "runner", "access_token", "trigger", "variable")]}

    def _check(self, text, trigger_token=""):
        journal = {"path": "j", "text": text, "rc": 0, "data": self.DATA}
        files = {"/out/.gitlab_trigger_token": trigger_token} if trigger_token else {}
        return _run(ext.check_external_journal, journal=journal, files=files)

    def test_clean_journal_passes(self):
        """GIVEN a journal without secrets THEN the check passes."""
        assert self._check("{}")["success"]

    @pytest.mark.parametrize("text,trigger", [
        ("glpat-secret", ""), ("token glptt-abcdefghij1234567890", ""),
        ("glrt-abcdefghij1234567890", ""), ("abc trig-123 def", "trig-123"),
    ])
    def test_any_token_in_the_journal_fails(self, text, trigger):
        """GIVEN the PAT, the trigger token or a token-shaped value THEN the check fails."""
        assert not self._check(text, trigger)["success"]

    def test_missing_resource_type_fails(self):
        """GIVEN a journal without a trigger entry THEN the check fails."""
        data = {**self.DATA, "resources": self.DATA["resources"][:3]}
        journal = {"path": "j", "text": "{}", "rc": 0, "data": data}
        assert not _run(ext.check_external_journal, journal=journal)["success"]

    def test_connection_failure_is_a_failed_result(self):
        """GIVEN no connection THEN the check fails with the reason."""
        result = _run(ext.check_external_project,
                      connection={"success": False, "error": "no token"})
        assert not result["success"] and "no token" in result["error"]
