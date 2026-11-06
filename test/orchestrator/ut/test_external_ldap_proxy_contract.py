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

"""Contract tests: the external LDAP proxy keeps omnia_auth hardened.

slapd runs as an unprivileged user that reads ``slapd.conf`` through its group,
and password binds must stay TLS-protected. The proxy configuration that the
test automation installs must therefore keep the deployed file's ownership and
mode, and must carry the same ``security simple_bind=128`` directive.
"""

# pylint: disable=protected-access

from types import SimpleNamespace

from library.functions import external_ldap_func as ldap_func
from library.vars.openldap_vars import LDAP_PROXY_SLAPD_TEMPLATE

CONFIG_PATH = "/opt/omnia/auth/config/slapd.conf"


class FakeHost:
    """Record commands and answer ``stat`` with a root:ldap 0640 file."""

    def __init__(self):
        self.commands = []

    def run(self, cmd, *args):
        """Record the rendered command and return a successful result."""
        self.commands.append(cmd % tuple(args))
        if cmd.startswith("stat -c"):
            return SimpleNamespace(rc=0, stdout="root ldap 640\n", stderr="")
        return SimpleNamespace(rc=0, stdout="", stderr="")

    def starting_with(self, prefix):
        """Return the recorded commands that begin with ``prefix``."""
        return [cmd for cmd in self.commands if cmd.startswith(prefix)]


def _directive_index(text, directive):
    return next(
        index
        for index, line in enumerate(text.splitlines())
        if line.strip().startswith(directive)
    )


def test_proxy_template_enforces_tls_for_password_binds():
    """Password binds must be TLS-protected before the database definition."""
    lines = LDAP_PROXY_SLAPD_TEMPLATE.splitlines()
    assert lines.count("security simple_bind=128") == 1
    database = _directive_index(LDAP_PROXY_SLAPD_TEMPLATE, "database")
    assert lines.index("security simple_bind=128") < database


def test_proxy_template_tls_material_is_global():
    """TLS directives are global, so they precede the database definition."""
    database = _directive_index(LDAP_PROXY_SLAPD_TEMPLATE, "database")
    for directive in (
        "TLSCACertificateFile",
        "TLSCertificateFile",
        "TLSCertificateKeyFile",
    ):
        assert _directive_index(LDAP_PROXY_SLAPD_TEMPLATE, directive) < database


def test_ownership_of_deployed_config_is_read_from_the_file():
    """Ownership and mode come from the deployed slapd.conf."""
    host = FakeHost()
    assert ldap_func._config_ownership(host, CONFIG_PATH) == ("root", "ldap", "640")
    assert host.commands == [f"stat -c '%U %G %a' -- {CONFIG_PATH}"]


def test_rollback_restores_the_deployed_ownership(monkeypatch):
    """A rollback keeps the group that lets slapd read the file."""
    monkeypatch.setattr(ldap_func, "_wait_for_proxy", lambda host: True)
    host = FakeHost()
    ldap_func._restore_proxy_config(host, "/tmp/backup", CONFIG_PATH)
    installs = host.starting_with("install ")
    assert len(installs) == 1
    assert "-o root -g ldap -m 640" in installs[0]
    assert "-g root" not in installs[0]
