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

"""Contract tests: slapd must refuse cleartext credential binds in every mode.

The OpenLDAP container listens on cleartext port 389 (``ldap:///``) in both TLS
and SSL modes. ``security simple_bind=128`` makes slapd reject username/password
binds unless the connection is TLS-protected (StartTLS or LDAPS). The directive
must be global, so it applies regardless of ``ldap_connection_type``.
"""

from pathlib import Path

TEMPLATE = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "orchestrator"
    / "roles"
    / "deploy_openldap"
    / "templates"
    / "slapd.conf.j2"
)
DIRECTIVE = "security simple_bind=128"


def _lines():
    return TEMPLATE.read_text(encoding="utf-8").splitlines()


def test_simple_bind_directive_is_present_once():
    assert _lines().count(DIRECTIVE) == 1


def test_simple_bind_directive_is_global_and_unconditional():
    lines = _lines()
    index = lines.index(DIRECTIVE)
    depth = 0
    for line in lines[:index]:
        stripped = line.strip()
        if stripped.startswith("{% if"):
            depth += 1
        elif stripped.startswith("{% endif"):
            depth -= 1
    assert depth == 0, "directive must not sit inside a connection-type conditional"
    database = next(i for i, line in enumerate(lines) if line.startswith("database"))
    assert index < database, "security is a global option and must precede the database block"
