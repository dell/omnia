# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Contracts for external LDAP user provisioning and slapd proxy handling."""

from pathlib import Path

import pytest

from library.functions.external_ldap_func import (
    build_group_ldif,
    build_proxy_slapd_conf,
    build_user_ldif,
    domain_to_dn,
    extract_proxy_identity,
    load_external_ldap_credentials,
    load_external_ldap_settings,
)
from ut.source_loader import TEST_ROOT


pytestmark = pytest.mark.unit


def _settings(**overrides):
    values = {
        "enabled": True,
        "manage_container": False,
        "configure_proxy": True,
        "server_ip": "192.0.2.20",
        "server_port": 1389,
        "secure_port": 1636,
        "domain": "directory.example",
        "admin_username": "admin",
        "container_name": "omnia_external_ldap",
        "volume_name": "omnia_external_ldap_data",
        "proxy_container_name": "omnia_auth",
        "image": "example.invalid/openldap:test",
        "uid_number": 2000,
        "gid_number": 2000,
        "login_shell": "/bin/bash",
        "home_base": "/home",
    }
    values.update(overrides)
    return {"external_ldap": values}


def test_external_ldap_schema_is_explicit_and_fail_closed():
    """ORCH_UT_117: Enabled external LDAP requires endpoint and domain."""
    disabled = load_external_ldap_settings({"external_ldap": {}})
    assert disabled["enabled"] is False
    with pytest.raises(ValueError, match="server_ip"):
        load_external_ldap_settings(_settings(server_ip=""))
    with pytest.raises(ValueError, match="multi-label DNS"):
        load_external_ldap_settings(_settings(domain="localhost"))
    assert domain_to_dn("directory.example") == "dc=directory,dc=example"


def test_external_ldap_secrets_are_complete_and_test_owned():
    """ORCH_UT_118: Setup requires test user and external admin secrets."""
    complete = load_external_ldap_credentials({
        "ldap_username": "omnia-test",
        "ldap_password": "user-secret",
        "external_ldap_admin_password": "admin-secret",
    })
    assert complete["username"] == "omnia-test"
    with pytest.raises(ValueError, match="external_ldap_admin_password"):
        load_external_ldap_credentials({
            "ldap_username": "omnia-test",
            "ldap_password": "user-secret",
        })


def test_posix_ldif_contains_identity_but_no_password():
    """ORCH_UT_119: User passwords are never embedded in staged LDIF."""
    user = build_user_ldif(
        "omnia-test",
        "dc=directory,dc=example",
        2000,
        2000,
        "/bin/bash",
        "/home",
    )
    group = build_group_ldif(
        "omnia-test", "dc=directory,dc=example", 2000
    )
    assert "objectClass: posixAccount" in user
    assert "uidNumber: 2000" in user
    assert "homeDirectory: /home/omnia-test" in user
    assert "userPassword" not in user
    assert "objectClass: posixGroup" in group
    assert "memberUid: omnia-test" in group


def test_proxy_template_matches_automation_v22_contract():
    """ORCH_UT_120: Proxy config carries meta, massage and idassert fields."""
    current = """database mdb
suffix "dc=omnia,dc=test"
rootdn "cn=ldapadmin,dc=omnia,dc=test"
    rootpw {SSHA}local-hash
"""
    identity = extract_proxy_identity(current)
    settings = load_external_ldap_settings(_settings())
    rendered = build_proxy_slapd_conf(
        identity, settings, "external-bind-secret"
    )
    assert "database    meta" in rendered
    assert 'suffix      "dc=omnia,dc=test"' in rendered
    assert (
        'suffixmassage "dc=omnia,dc=test" '
        '"dc=directory,dc=example"'
    ) in rendered
    assert 'binddn="cn=admin,dc=directory,dc=example"' in rendered
    assert 'credentials="external-bind-secret"' in rendered
    assert "moduleload back_ldap.la" in rendered
    assert "moduleload back_meta.la" in rendered


def test_external_ldap_setup_is_explicit_not_a_pytest_side_effect():
    """ORCH_UT_121: State mutation stays behind the utility entry point."""
    test_source = (
        Path(TEST_ROOT) / "fvt/prepare/openldap/test_openldap.py"
    ).read_text(encoding="utf-8")
    utility_source = (
        Path(TEST_ROOT) / "utility/create_ldap_user.py"
    ).read_text(encoding="utf-8")
    assert "reconcile_external_ldap" not in test_source
    assert "reconcile_external_ldap" in utility_source
    assert 'action="store_true"' in utility_source
    assert '"--recreate"' in utility_source


def test_external_ldap_passwords_use_protected_files():
    """ORCH_UT_122: LDAP clients receive secrets through -y/-T files."""
    source = (
        Path(TEST_ROOT) / "library/functions/external_ldap_func.py"
    ).read_text(encoding="utf-8")
    assert '"-y", admin_password_file' in source
    assert '"-T", staged["user_password"]' in source
    assert '"LDAP_ADMIN_PASSWORD=' in source
    assert "chmod %s -- %s" in source
    assert "0o600" in source
    assert "-w {" not in source
    assert "-s {" not in source


def test_external_ldap_proxy_readiness_requires_ldap_probe():
    """ORCH_UT_123: A running proxy container is not sufficient readiness."""
    source = (
        Path(TEST_ROOT) / "library/functions/external_ldap_func.py"
    ).read_text(encoding="utf-8")
    assert '"podman inspect --format \'{{.State.Status}}\' %s"' in source
    assert '"ldapsearch", "-x", "-H", "ldap://127.0.0.1:389"' in source
    assert "and probe.rc == 0" in source
    assert "{{{{.State.Status}}}}" not in source


def test_external_ldap_setup_fails_fast_for_invalid_admin_and_id_conflicts():
    """ORCH_UT_124: Permanent setup errors do not consume readiness timeout."""
    source = (
        Path(TEST_ROOT) / "library/functions/external_ldap_func.py"
    ).read_text(encoding="utf-8")
    assert 'result.rc == 49 or "invalid credentials"' in source
    assert "External LDAP rejected the configured administrator" in source
    assert "_ensure_posix_number_available" in source
    assert "already belongs to" in source
