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

"""Contract tests: OpenLDAP verification expects the unprivileged-slapd layout.

slapd runs as the ``ldap`` user and reads ``slapd.conf`` and the TLS key
through the ``ldap`` group. The prepare verification must accept that layout
(``root:ldap 0640``), still reject anything looser, and require that slapd does
not run as root.
"""

from types import SimpleNamespace

import pytest

from library.functions import openldap_prepare_func as prepare
from library.vars.prepare_vars import OPENLDAP_SECRET_MODES

BASE = "/opt/omnia"
CONFIG = f"{BASE}/auth/config/slapd.conf"
KEY = f"{BASE}/auth/tls_certs/ldapserver.key"
CERT = f"{BASE}/auth/tls_certs/ldapserver.crt"
QUADLET = "/etc/containers/systemd/omnia_auth.container"
GOOD = {
    CONFIG: ("root", "ldap", 0o640),
    KEY: ("root", "ldap", 0o640),
    CERT: ("root", "root", 0o644),
    QUADLET: ("root", "root", 0o644),
}


class FakeHost:
    """Answer file and command probes from a table of deployed state."""

    def __init__(self, files, slapd_user="ldap"):
        self.files = files
        self.slapd_user = slapd_user

    def file(self, path):
        """Return the deployed file attributes."""
        user, group, mode = self.files[path]
        return SimpleNamespace(is_file=True, user=user, group=group, mode=mode)

    def run(self, cmd, *_args):
        """Return slapd processes for ``ps`` and success for other probes."""
        if cmd.startswith("podman exec") and cmd.endswith("ps -o user,args"):
            line = f"{self.slapd_user}  /usr/sbin/slapd -f /etc/openldap/slapd.conf"
            return SimpleNamespace(rc=0, stdout=f"USER ARGS\n{line}\n", stderr="")
        return SimpleNamespace(rc=0, stdout="", stderr="")


@pytest.fixture(name="patched")
def _patched(monkeypatch):
    monkeypatch.setattr(prepare, "openldap_enabled", lambda host: True)
    monkeypatch.setattr(prepare, "resolve_target_omnia_data_path", lambda host: BASE)


def _check(files, slapd_user="ldap"):
    return prepare.check_prepare_openldap_artifacts(FakeHost(files, slapd_user))


def test_secret_layouts_allow_only_group_read_or_owner_only():
    """Only root:ldap 0640 and root:root 0600 are accepted for secrets."""
    assert set(OPENLDAP_SECRET_MODES) == {("ldap", 0o640), ("root", 0o600)}


@pytest.mark.usefixtures("patched")
def test_unprivileged_layout_passes():
    """The role's root:ldap 0640 layout with slapd as ldap is accepted."""
    result = _check(dict(GOOD))
    assert result["success"], result


@pytest.mark.usefixtures("patched")
def test_slapd_running_as_root_fails():
    """A slapd process owned by root fails the verification."""
    result = _check(dict(GOOD), slapd_user="root")
    assert not result["success"]
    assert "slapd must run as ldap" in result["error"]


@pytest.mark.usefixtures("patched")
@pytest.mark.parametrize(
    "path,state",
    [
        (KEY, ("root", "ldap", 0o644)),
        (CONFIG, ("root", "ldap", 0o660)),
        (KEY, ("root", "users", 0o640)),
        (CONFIG, ("ldap", "ldap", 0o640)),
        (CONFIG, ("root", "root", 0o640)),
    ],
)
def test_looser_or_wrong_owner_layouts_fail(path, state):
    """World-readable, group-writable or wrongly owned secrets are rejected."""
    files = dict(GOOD)
    files[path] = state
    result = _check(files)
    assert not result["success"]
    assert path in result["error"]
