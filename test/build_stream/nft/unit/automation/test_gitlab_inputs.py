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

"""Unit tests of the dependency-free GitLab mode inputs (run in the GitHub unit job)."""

import pytest

from library import gitlab_inputs as gi

pytestmark = pytest.mark.unit

EXTERNAL = {
    "gitlab_mode": "external",
    "gitlab_host": "",
    "gitlab_external_url": "https://gitlab.example.test/",
    "gitlab_project_namespace": "infra",
    "gitlab_ca_cert_path": "/etc/pki/tls/certs/gitlab-ca.pem",
}
HOSTED = {"gitlab_mode": "hosted", "gitlab_host": "10.0.0.2"}


@pytest.mark.parametrize("config,expected", [
    (HOSTED, "hosted"), (EXTERNAL, "external"), ({"gitlab_mode": " External "}, "external"),
    ({}, ""), (None, ""),
])
def test_gitlab_mode_of(config, expected):
    """GIVEN a parsed input file THEN the mode is normalized."""
    assert gi.gitlab_mode_of(config) == expected


class TestExternalSettings:
    """Defaults and normalization of the external inputs."""

    def test_defaults_and_trailing_slash(self):
        """GIVEN the minimal external inputs THEN defaults are applied."""
        settings = gi.external_settings(EXTERNAL)
        assert settings["url"] == "https://gitlab.example.test"
        assert settings["project_path"] == "infra/omnia-catalog"
        assert (settings["branch"], settings["visibility"]) == ("main", "private")

    def test_explicit_values(self):
        """GIVEN explicit inputs THEN they are used."""
        settings = gi.external_settings({
            **EXTERNAL, "gitlab_project_namespace": "/a/b/", "gitlab_project_name": "cat",
            "gitlab_default_branch": "dev", "gitlab_project_visibility": "internal",
            "gitlab_ca_cert_path": "",
        })
        assert settings["project_path"] == "a/b/cat"
        assert (settings["branch"], settings["visibility"], settings["ca_path"]) == (
            "dev", "internal", "")


@pytest.mark.parametrize("url,valid", [
    ("https://gitlab.example.test", True), ("https://10.0.0.5:8443/group", True),
    ("https://host:70000", False), ("http://gitlab.example.test", False), ("", False),
])
def test_url(url, valid):
    """URL syntax matches the product validator."""
    assert gi.is_valid_external_url(url) is valid


@pytest.mark.parametrize("value,valid", [("infra", True), ("infra/omnia-builds", True),
                                         ("/infra", False), ("in fra", False), ("", False)])
def test_namespace(value, valid):
    """Group path syntax matches the product validator."""
    assert gi.is_valid_namespace(value) is valid


class TestModeInputProbes:
    """mode_input_probes validates the inputs of the resolved mode."""

    @staticmethod
    def _ok(mode, config, expected=""):
        return all(ok for _, _, ok in gi.mode_input_probes(mode, config, expected))

    def test_hosted_needs_ipv4_host(self):
        """GIVEN hosted THEN gitlab_host must be an IPv4 address."""
        assert self._ok("hosted", HOSTED)
        assert not self._ok("hosted", {"gitlab_host": "name"})
        assert not self._ok("hosted", {})

    def test_hosted_reports_ignored_external_inputs(self):
        """GIVEN hosted with external inputs set THEN they are reported as ignored."""
        labels = [label for label, _, _ in gi.mode_input_probes("hosted", {**HOSTED, **EXTERNAL})]
        assert "External-only inputs set" in labels

    def test_external_needs_url_and_namespace(self):
        """GIVEN external THEN URL and namespace are validated."""
        assert self._ok("external", EXTERNAL)
        assert not self._ok("external", {**EXTERNAL, "gitlab_external_url": "http://x"})
        assert not self._ok("external", {**EXTERNAL, "gitlab_project_namespace": ""})

    def test_expected_mode_must_match(self):
        """GIVEN gitlab.expected_mode THEN a different mode fails."""
        assert self._ok("external", EXTERNAL, "external")
        assert not self._ok("external", EXTERNAL, "hosted")


class TestGitlabBlock:
    """test_config.yml gitlab block."""

    def test_defaults(self):
        """GIVEN no gitlab block THEN defaults apply."""
        gi.validate_gitlab_block(None)
        assert gi.gitlab_settings({}) == {"expected_mode": "", "token_min_days_remaining": 30}

    @pytest.mark.parametrize("block", [
        {"expected_mode": "cloud"}, {"token_min_days_remaining": -1},
        {"token_min_days_remaining": True}, {"unknown": 1}, ["list"],
    ])
    def test_invalid_blocks_are_rejected(self, block):
        """GIVEN an invalid gitlab block THEN validation fails."""
        with pytest.raises(ValueError):
            gi.validate_gitlab_block(block)

    def test_valid_block(self):
        """GIVEN a valid gitlab block THEN it is accepted."""
        config = {"gitlab": {"expected_mode": "external", "token_min_days_remaining": 0}}
        gi.validate_gitlab_block(config["gitlab"])
        assert gi.gitlab_settings(config) == {"expected_mode": "external",
                                              "token_min_days_remaining": 0}
