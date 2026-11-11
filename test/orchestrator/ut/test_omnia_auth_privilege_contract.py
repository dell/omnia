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

"""Contract tests: omnia_auth runs slapd unprivileged and rolls out image changes.

``slapd`` must drop to the ``ldap`` user, which needs read access to
``slapd.conf`` and the TLS key through a fixed numeric group shared by the image
and the role. The entrypoint must verify a CA-signed certificate against an
explicit CA (``LDAP_TLS_CA_FILE``), and the role must replace a running
container whose image differs from the desired one.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

SRC = Path(__file__).resolve().parents[3] / "src" / "orchestrator"
ROLE = SRC / "roles" / "deploy_openldap"
CONTAINER = SRC / "containers" / "omnia_auth"
ENTRYPOINT = (CONTAINER / "entrypoint.sh").read_text(encoding="utf-8")
CONTAINERFILE = (CONTAINER / "Containerfile").read_text(encoding="utf-8")
QUADLET = (ROLE / "templates" / "omnia_auth.container.j2").read_text(encoding="utf-8")
SLAPD_CONF = (ROLE / "templates" / "slapd.conf.j2").read_text(encoding="utf-8")


def _yaml(name):
    return yaml.safe_load((ROLE / name).read_text(encoding="utf-8"))


def _walk_tasks(tasks):
    for task in tasks:
        yield task
        for key in ("block", "rescue", "always"):
            yield from _walk_tasks(task.get(key, []))


def _task(tasks, name):
    return next(t for t in _walk_tasks(tasks) if t.get("name") == name)


def test_image_pins_ldap_ids_matching_role_defaults():
    """The image and the role agree on fixed numeric ldap ids."""
    role_vars = _yaml("vars/main.yml")
    uid = re.search(r"^ARG LDAP_UID=(\d+)$", CONTAINERFILE, re.MULTILINE)
    gid = re.search(r"^ARG LDAP_GID=(\d+)$", CONTAINERFILE, re.MULTILINE)
    assert uid and gid
    assert int(uid.group(1)) == role_vars["auth_ldap_uid"]
    assert int(gid.group(1)) == role_vars["auth_ldap_gid"]
    assert role_vars["auth_ldap_gid"] >= 1 and role_vars["auth_ldap_gid"] != 100
    assert '-g "${LDAP_GID}" ldap' in CONTAINERFILE
    assert '-u "${LDAP_UID}"' in CONTAINERFILE


def test_slapd_drops_privileges_after_setup():
    """slapd starts with -u ldap -g ldap after the root-only setup."""
    exec_line = [ln for ln in ENTRYPOINT.splitlines() if ln.startswith("exec /usr/sbin/slapd")]
    assert len(exec_line) == 1
    assert "-u ldap -g ldap" in exec_line[0]
    assert ENTRYPOINT.index("update-ca-certificates") < ENTRYPOINT.index(exec_line[0])


def test_data_ownership_repaired_on_every_start():
    """Data ownership is repaired on every start, not only on first run."""
    chown = "chown -R ldap:ldap /var/lib/openldap /run/openldap"
    assert chown in ENTRYPOINT
    assert ENTRYPOINT.index(chown) < ENTRYPOINT.index("__initialized")


def test_entrypoint_checks_ldap_user_can_read_tls_material():
    """The entrypoint reports files the ldap user cannot read."""
    assert "su -s /bin/sh ldap" in ENTRYPOINT
    assert "cannot read" in ENTRYPOINT


def test_ca_signed_certificate_requires_explicit_ca():
    """A CA-signed certificate is verified only against an explicit CA."""
    assert '-CAfile "$TLS_CA_FILE" "$TLS_CERT"' in ENTRYPOINT
    assert 'TLS_CA_FILE="${LDAP_TLS_CA_FILE:-}"' in ENTRYPOINT
    assert 'LDAP_TLS_CA_FILE is not set' in ENTRYPOINT
    assert '-CAfile "$TLS_CERT" "$TLS_CERT"' in ENTRYPOINT
    assert '[ "$cert_subject" = "$cert_issuer" ]' in ENTRYPOINT


def test_role_grants_group_read_on_config_and_key():
    """slapd.conf and the key are group-readable by the ldap group."""
    main = _yaml("tasks/main.yml")
    conf = _task(main, "Template slapd.conf")["ansible.builtin.template"]
    assert (conf["owner"], conf["group"], conf["mode"]) == ("root", "{{ auth_ldap_group }}", "0640")

    certs = _yaml("tasks/generate_tls_certs.yml")
    perms = next(t for t in certs if t.get("name") == "Set certificate file permissions")
    loop = {item["name"]: item for item in perms["loop"]}
    assert loop["{{ tls_key_file }}"]["mode"] == "0640"
    assert loop["{{ tls_key_file }}"]["group"] == "{{ auth_ldap_group }}"
    assert loop["{{ tls_cert_file }}"]["mode"] == "0644"
    assert "when" not in perms


def test_role_directories_are_traversable_by_ldap():
    """The certs and data directories are usable by the ldap user."""
    main = _yaml("tasks/main.yml")
    loop = _task(main, "Create OpenLDAP directories")["loop"]
    by_name = {Path(item["path"]).name.rstrip("}").rstrip(" "): item for item in loop}
    certs = next(i for i in loop if "auth_certs_dir" in i["path"])
    data = next(i for i in loop if "auth_data_dir" in i["path"])
    assert certs["mode"] == "0750" and certs["group"] == "{{ auth_ldap_group }}"
    assert data["owner"] == "{{ auth_ldap_uid }}" and data["group"] == "{{ auth_ldap_gid }}"
    assert by_name


def test_group_is_created_before_any_file_uses_it():
    """The host group exists before any file is given to it."""
    main = _yaml("tasks/main.yml")
    names = [t.get("name") for t in _walk_tasks(main)]
    group = "Create the group that grants slapd read access to its configuration and key"
    assert names.index(group) < names.index("Create OpenLDAP directories")
    task = _task(main, group)["ansible.builtin.group"]
    assert task["gid"] == "{{ auth_ldap_gid }}"


def test_reconcile_preserves_group_read_permissions():
    """Reconciling slapd.conf keeps the group read access."""
    reconcile = _yaml("tasks/reconcile_slapd_conf.yml")
    installs = [
        t["ansible.builtin.copy"]
        for t in _walk_tasks(reconcile)
        if "ansible.builtin.copy" in t
        and t["ansible.builtin.copy"].get("dest", "").endswith("/slapd.conf")
    ]
    assert len(installs) == 2
    for copy in installs:
        assert copy["group"] == "{{ auth_ldap_group }}"
        assert copy["mode"] == "0640"


def test_running_container_with_other_image_is_replaced():
    """A running container with another image is redeployed."""
    main = _yaml("tasks/main.yml")
    fact = _task(main, "Decide whether omnia_auth must be deployed or redeployed")
    expression = fact["ansible.builtin.set_fact"]["omnia_auth_needs_deploy"]
    assert "ImageName" in expression
    assert "omnia_auth_image ~ ':' ~ omnia_auth_tag" in expression

    deploy = _task(main, "Deploy OpenLDAP when container is not running or runs a different image")
    assert deploy["when"] == "omnia_auth_needs_deploy | bool"
    verify = "Verify TLS certificate when container is already running the desired image"
    assert _task(main, verify)["when"] == "not (omnia_auth_needs_deploy | bool)"
    reconcile = "Reconcile slapd.conf when container is already running the desired image"
    assert "not (omnia_auth_needs_deploy | bool)" in _task(main, reconcile)["when"]

    stop = _task(main, "Stop omnia_auth service before replacing the container")
    names = [t.get("name") for t in _walk_tasks(main)]
    assert names.index(stop["name"]) < names.index("Stop existing omnia_auth container if present")


DEPLOY_BLOCK = "Deploy OpenLDAP when container is not running or runs a different image"
PROXY_CHECK = "Detect an external LDAP proxy slapd.conf"


def test_permissions_are_enforced_when_container_keeps_running():
    """Directory and slapd.conf ownership do not depend on a redeploy."""
    main = _yaml("tasks/main.yml")
    deploy = [t.get("name") for t in _walk_tasks(_task(main, DEPLOY_BLOCK)["block"])]
    names = [t.get("name") for t in _walk_tasks(main)]
    enforce = "Enforce slapd.conf ownership so the unprivileged slapd can read it"
    for name in ("Create OpenLDAP directories", "Check deployed slapd.conf", enforce):
        assert name not in deploy
        assert "omnia_auth_needs_deploy" not in str(_task(main, name).get("when", ""))
        assert names.index(name) < names.index(DEPLOY_BLOCK)

    task = _task(main, enforce)
    perms = task["ansible.builtin.file"]
    assert (perms["owner"], perms["group"], perms["mode"]) == ("root", "{{ auth_ldap_group }}", "0640")
    assert "state" not in perms
    assert task["when"] == "_slapd_conf_stat.stat.exists"


def test_external_proxy_slapd_conf_is_not_overwritten():
    """A proxy slapd.conf is neither templated nor reconciled unless forced."""
    main = _yaml("tasks/main.yml")
    assert _yaml("vars/main.yml")["openldap_force_reconcile"] is False
    fact = _task(main, "Record whether slapd.conf is managed outside this role")
    expression = fact["ansible.builtin.set_fact"]["omnia_auth_external_proxy"]
    assert "not openldap_force_reconcile | bool" in expression
    assert "_slapd_conf_stat.stat.exists" in expression

    check = _task(main, PROXY_CHECK)
    assert check["check_mode"] is False
    assert check["failed_when"] == "_slapd_proxy_check.rc > 1"

    template = _task(main, "Template slapd.conf")
    assert template["when"] == "not (omnia_auth_external_proxy | bool)"
    reconcile = _task(main, "Reconcile slapd.conf when container is already running the desired image")
    assert "not (omnia_auth_external_proxy | bool)" in reconcile["when"]


@pytest.mark.skipif(shutil.which("grep") is None, reason="grep is required")
@pytest.mark.parametrize(
    ("content", "is_proxy"),
    [
        ("database meta\n", True),
        ("  database\tldap\n", True),
        ("database mdb\n", False),
        ("# database meta\n", False),
        ("database metadata\n", False),
    ],
)
def test_external_proxy_detection_pattern(tmp_path, content, is_proxy):
    """The detection pattern matches only active meta or ldap databases."""
    pattern = _task(_yaml("tasks/main.yml"), PROXY_CHECK)["ansible.builtin.command"]["argv"][2]
    conf = tmp_path / "slapd.conf"
    conf.write_text("include /etc/openldap/schema/core.schema\n" + content, encoding="utf-8")
    result = subprocess.run(["grep", "-Eq", pattern, str(conf)], check=False)
    assert (result.returncode == 0) is is_proxy


def test_tls_trust_inputs_are_wired_and_default_unset():
    """The CA file and fingerprint pin are wired and default to unset."""
    role_vars = _yaml("vars/main.yml")
    assert role_vars["ldap_tls_ca_file"] == ""
    assert role_vars["ldap_tls_cert_sha256"] == ""
    assert "Environment=LDAP_TLS_CA_FILE=/etc/openldap/certs/{{ ldap_tls_ca_file }}" in QUADLET
    assert "Environment=LDAP_TLS_CERT_SHA256={{ ldap_tls_cert_sha256 }}" in QUADLET
    assert "{% if ldap_tls_ca_file | length > 0 %}" in QUADLET
    assert "{% if ldap_tls_cert_sha256 | length > 0 %}" in QUADLET
    assert "ldap_tls_ca_file if ldap_tls_ca_file | length > 0 else tls_cert_file" in SLAPD_CONF
    assert role_vars["ldap_tls_ca_missing_msg"]
