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

"""Contract tests: LDAP clients bind as a read-only account; anonymous reads are denied.

The directory ACL used to grant ``read`` to everyone, so any unauthenticated
client could enumerate users. Anonymous clients may now only authenticate,
``deploy_openldap`` maintains a read-only bind account from the credential
vault, and ``sssd`` on every node binds with that account in both TLS and SSL
modes instead of the admin account.
"""

import json
import re
from pathlib import Path

import yaml

SRC = Path(__file__).resolve().parents[3] / "src"
ORCH = SRC / "orchestrator"
ROLE = ORCH / "roles" / "deploy_openldap"
SLAPD_CONF = (ROLE / "templates" / "slapd.conf.j2").read_text(encoding="utf-8")
LDIF = (ROLE / "templates" / "bind_account.ldif.j2").read_text(encoding="utf-8")
SSSD = (ORCH / "roles" / "provision_common" / "templates" / "openldap" / "sssd.conf.j2").read_text(
    encoding="utf-8"
)
METADATA_SVC = (
    ORCH / "roles" / "provision_common" / "tasks" / "configure_metadata_svc.yml"
).read_text(encoding="utf-8")
OPENLDAP_ROLE = (ORCH / "roles" / "openldap" / "tasks" / "main.yml").read_text(encoding="utf-8")
BIND_KEYS = ("openldap_bind_username", "openldap_bind_password")


def _yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _walk(tasks):
    for task in tasks:
        yield task
        for key in ("block", "rescue", "always"):
            yield from _walk(task.get(key, []))


def _task(tasks, name):
    return next(t for t in _walk(tasks) if t.get("name") == name)


def _acl_rules():
    """Return slapd access rules as (target, [by clauses]) in file order."""
    rules = []
    for line in SLAPD_CONF.splitlines():
        if line.startswith("access to "):
            rules.append((line[len("access to ") :].strip(), []))
        elif line.strip().startswith("by ") and rules:
            rules[-1][1].append(line.strip())
    return rules


def test_anonymous_clients_cannot_read_directory_entries():
    """Only authenticated clients read entries; anonymous clients may only authenticate."""
    rules = dict(_acl_rules())
    assert rules["*"] == ["by self write", "by users read", "by * none"]
    assert rules["attrs=userPassword"] == ["by self write", "by anonymous auth", "by * none"]


def test_root_dse_and_schema_stay_readable_before_bind():
    """Server metadata stays public and is declared globally, before the database."""
    rules = dict(_acl_rules())
    assert rules['dn.base=""'] == ["by * read"]
    assert rules['dn.base="cn=Subschema"'] == ["by * read"]
    database = SLAPD_CONF.index("\ndatabase ")
    assert SLAPD_CONF.index('access to dn.base=""') < database
    assert SLAPD_CONF.index("access to attrs=userPassword") > database


def test_bind_credentials_are_prompted_and_validated():
    """The bind account credentials follow the vault, template, and rule flow."""
    defs = _yaml(ORCH / "roles" / "orchestrator_credentials" / "vars" / "main.yml")
    pairs = defs["orchestrator_credentials_definitions"]["openldap"]["mandatory"]
    assert {"username": BIND_KEYS[0], "password": BIND_KEYS[1]} in pairs

    template = (
        ORCH / "roles" / "orchestrator_credentials" / "templates" / "orchestrator_credentials.j2"
    ).read_text(encoding="utf-8")
    for key in BIND_KEYS:
        assert f'{key}: ""' in template

    flat = json.loads(
        (
            ORCH
            / "plugins"
            / "module_utils"
            / "orchestrator_validation"
            / "schema"
            / "credential_rules.json"
        ).read_text(encoding="utf-8")
    )
    username = re.compile(flat[BIND_KEYS[0]]["pattern"])
    assert username.fullmatch("svc-sssd-ro")
    for unsafe in ("svc,ou=x", "svc=1", "1svc", "svc user", "svc+a"):
        assert not username.fullmatch(unsafe)
    assert flat[BIND_KEYS[1]]["pattern"] == flat["openldap_db_password"]["pattern"]

    masking = (
        SRC
        / "repo_manager"
        / "plugins"
        / "module_utils"
        / "input_validation"
        / "core"
        / "config.py"
    ).read_text(encoding="utf-8")
    assert '"openldap_bind_password"' in masking


def test_deploy_requires_distinct_bind_password():
    """The role fails fast when bind credentials are missing or reuse the admin password."""
    main = _yaml(ROLE / "tasks" / "main.yml")
    check = _task(main, "Validate OpenLDAP credentials are available")
    that = check["ansible.builtin.assert"]["that"]
    assert "openldap_bind_username | default('') | length > 0" in that
    assert "openldap_bind_password | default('') | length > 0" in that
    assert "openldap_bind_password | default('') != openldap_db_password" in that
    assert check["no_log"] is True


def test_bind_account_is_ensured_on_every_run_except_proxy():
    """The account is maintained after deploy or reconcile, but not for an external proxy."""
    main = _yaml(ROLE / "tasks" / "main.yml")
    names = [t.get("name") for t in _walk(main)]
    ensure = _task(main, "Ensure the read-only account that LDAP clients bind with")
    assert ensure["ansible.builtin.include_tasks"] == "ensure_bind_account.yml"
    assert ensure["when"] == "not (omnia_auth_external_proxy | bool)"
    assert names.index(ensure["name"]) > names.index(
        "Reconcile slapd.conf when container is already running the desired image"
    )
    report = _task(main, "Report that the bind account is managed by the external directory")
    assert report["when"] == "omnia_auth_external_proxy | bool"


def test_bind_account_secrets_never_reach_argv_logs_or_disk():
    """Passwords travel through private tmpfs files that are always removed."""
    role_vars = _yaml(ROLE / "vars" / "main.yml")
    assert role_vars["bind_secret_container_dir"].startswith("/dev/shm/")
    assert role_vars["slapd_candidate_container_path"].startswith("/dev/shm/")
    assert role_vars["slapd_reconcile_tmp_dir"] == "/dev/shm"

    tasks = _yaml(ROLE / "tasks" / "ensure_bind_account.yml")
    write = _task(tasks, "Write admin and bind account password files")
    assert write["no_log"] is True
    assert write["ansible.builtin.copy"]["mode"] == "0600"

    text = (ROLE / "tasks" / "ensure_bind_account.yml").read_text(encoding="utf-8")
    assert "-w" not in re.findall(r"'(-[a-zA-Z])'", text)
    assert "'-y'" in text and "'-T'" in text

    cleanup = [t.get("name") for t in tasks[0]["always"]]
    assert cleanup == [
        "Remove password files from the container",
        "Remove the private temp directory",
    ]


def test_bind_account_uses_verified_starttls_and_is_idempotent():
    """Every LDAP call verifies the server certificate; nothing changes when the password works."""
    tasks = _yaml(ROLE / "tasks" / "ensure_bind_account.yml")
    block_vars = tasks[0]["vars"]
    assert block_vars["_bind_ldap_conn"] == ["-x", "-ZZ", "-H", "ldap://{{ ldap_server_ip }}"]
    assert "LDAPTLS_REQCERT=demand" in block_vars["_bind_ldap_env"]
    assert any(
        str(v).startswith("LDAPTLS_CACERT=/etc/openldap/certs/")
        for v in block_vars["_bind_ldap_env"]
    )

    check = _task(tasks, "Check whether the bind account accepts the stored password")
    assert check["changed_when"] is False
    assert check["failed_when"] == "_bind_check.rc not in [0, 49]"
    reset = _task(tasks, "Create or reset the bind account")
    assert reset["when"] == "_bind_check.rc != 0"
    add = _task(tasks, "Create the service account container and bind account entry")
    assert add["failed_when"] == "_bind_add.rc not in [0, 68]"
    assert "ldappasswd" in str(
        _task(tasks, "Set the bind account password")["ansible.builtin.command"]["argv"]
    )


def test_bind_account_entry_holds_no_password():
    """The LDIF creates the entry locked; slapd hashes the password set by ldappasswd."""
    assert "dn: {{ bind_account_ou }},{{ ldap_search_base }}" in LDIF
    assert (
        "dn: cn={{ openldap_bind_username }},{{ bind_account_ou }},{{ ldap_search_base }}" in LDIF
    )
    assert "objectClass: simpleSecurityObject" in LDIF
    assert "userPassword: {CRYPT}*" in LDIF
    assert "openldap_bind_password" not in LDIF
    assert _yaml(ROLE / "vars" / "main.yml")["bind_account_ou"] == "ou=ServiceAccounts"


def test_sssd_binds_as_read_only_account_in_both_modes():
    """Both sssd branches bind; the admin account is no longer written to nodes."""
    tls, ssl = SSSD.split("{% else %}")
    for branch in (tls, ssl):
        assert "ldap_default_bind_dn = {{ ldap_default_bind_dn }}" in branch
        assert "ldap_default_authtok = {{ password }}" in branch
        assert "ldap_tls_reqcert = demand" in branch

    for source in (METADATA_SVC, OPENLDAP_ROLE):
        assert "openldap_db_password" not in source
        assert "openldap_db_username" not in source
        assert "openldap_bind_password" in source
        assert "ou=ServiceAccounts," in source
    assert METADATA_SVC.count("hostvars['localhost']['openldap_bind_username']") == 3


def test_provision_fails_fast_without_bind_credentials():
    """Node configuration stops when OpenLDAP is enabled but the bind account is unknown."""
    tasks = _yaml(ORCH / "roles" / "provision_common" / "tasks" / "configure_metadata_svc.yml")
    check = _task(tasks, "Validate the read-only LDAP bind credentials for client configuration")
    assert check["when"] == "hostvars['localhost']['openldap_support'] | default(false) | bool"
    assert (
        check["ansible.builtin.assert"]["fail_msg"] == "{{ openldap_bind_credentials_missing_msg }}"
    )
    assert check["no_log"] is True
    messages = _yaml(ORCH / "roles" / "provision_common" / "vars" / "main.yml")
    assert "openldap_bind_username" in messages["openldap_bind_credentials_missing_msg"]
