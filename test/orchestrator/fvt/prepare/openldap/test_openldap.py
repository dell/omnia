# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Live verification of the catalog-driven OpenLDAP deployment."""

import json
import posixpath
import re
import shlex

import pytest

from fvt.check.feature_helpers import read_remote_yaml, target_paths
from library.functions.external_ldap_func import (
    domain_to_dn,
    load_external_ldap_settings,
    resolve_proxy_config_path,
    verify_external_ldap_user_bind,
)


pytestmark = [pytest.mark.openldap, pytest.mark.functional]


def _require_openldap(host):
    """Skip only when persisted Orchestrator state says OpenLDAP is disabled."""
    paths = target_paths(host)
    state = read_remote_yaml(
        host, posixpath.join(paths["output"], "orchestrator_state.yml")
    )
    enabled = state.get("openldap_support")
    assert isinstance(enabled, bool), (
        "orchestrator_state.yml must contain boolean openldap_support"
    )
    if not enabled:
        pytest.skip("OpenLDAP is disabled by the selected catalog")
    return paths


def _require_external_ldap(host):
    """Return validated settings or skip when the opt-in setup is disabled."""
    _require_openldap(host)
    settings = load_external_ldap_settings()
    if not settings["enabled"]:
        pytest.skip(
            "External LDAP verification is disabled in test_config.yml"
        )
    return settings


@pytest.mark.sanity
@pytest.mark.order(8)
def test_openldap_service_active_and_enabled(host):
    """ORCH_FVT_PREPARE_V008: Enabled OpenLDAP has an active and enabled Quadlet service."""
    _require_openldap(host)
    service = host.service("omnia_auth")
    assert service.is_running, "omnia_auth.service is not active"
    assert service.is_enabled, "omnia_auth.service is not enabled"


@pytest.mark.sanity
@pytest.mark.order(9)
def test_openldap_container_running_and_healthy(host):
    """ORCH_FVT_PREPARE_V009: Enabled OpenLDAP container is running and healthy."""
    _require_openldap(host)
    result = host.run("podman inspect omnia_auth")
    assert result.rc == 0, result.stderr
    try:
        inspection = json.loads(result.stdout)[0]
    except (IndexError, KeyError, TypeError, json.JSONDecodeError) as exc:
        pytest.fail(f"Invalid podman inspection output for omnia_auth: {exc}")
    state = inspection.get("State", {})
    assert state.get("Status") == "running", state
    assert state.get("Health", {}).get("Status") == "healthy", state


@pytest.mark.order(10)
def test_openldap_configuration_and_secret_modes(host):
    """ORCH_FVT_PREPARE_V010: OpenLDAP config, key, certificate and Quadlet modes are safe."""
    paths = _require_openldap(host)
    expected = {
        posixpath.join(paths["data"], "auth/config/slapd.conf"): 0o600,
        posixpath.join(paths["data"], "auth/tls_certs/ldapserver.key"): 0o600,
        posixpath.join(paths["data"], "auth/tls_certs/ldapserver.crt"): 0o644,
        "/etc/containers/systemd/omnia_auth.container": 0o644,
    }
    for path, mode in expected.items():
        deployed = host.file(path)
        assert deployed.is_file, f"OpenLDAP artifact is missing: {path}"
        assert deployed.user == "root" and deployed.group == "root", path
        actual_mode = deployed.mode
        assert actual_mode == mode, (
            f"Unsafe mode for {path}: {actual_mode!r} != {oct(mode)}"
        )


@pytest.mark.order(11)
def test_openldap_requires_starttls_for_health_request(host):
    """ORCH_FVT_PREPARE_V011: LDAP health succeeds only over verified STARTTLS."""
    _require_openldap(host)
    result = host.run(
        "podman exec -e LDAPTLS_CACERT=/etc/openldap/certs/ldapserver.crt "
        "omnia_auth ldapwhoami -x -ZZ -H ldap://127.0.0.1:389"
    )
    assert result.rc == 0, result.stderr

    cleartext = host.run(
        "podman exec omnia_auth ldapsearch -x -H ldap://127.0.0.1:389 "
        "-b '' -s base namingContexts"
    )
    assert cleartext.rc != 0, "OpenLDAP unexpectedly allowed a cleartext query"


@pytest.mark.order(12)
def test_openldap_tls_and_listener_contract(host):
    """ORCH_FVT_PREPARE_V012: LDAP/LDAPS listen and the deployed certificate is not expired."""
    paths = _require_openldap(host)
    listeners = host.run(
        "ss -H -ltn '( sport = :389 or sport = :636 )'"
    )
    assert listeners.rc == 0, listeners.stderr
    for port in (389, 636):
        assert re.search(rf":{port}\b", listeners.stdout), (
            f"OpenLDAP TCP port {port} is not listening: {listeners.stdout}"
        )
    certificate = posixpath.join(
        paths["data"], "auth/tls_certs/ldapserver.crt"
    )
    cert_check = host.run(
        "openssl x509 -checkend 86400 -noout -in %s",
        shlex.quote(certificate),
    )
    assert cert_check.rc == 0, cert_check.stderr


@pytest.mark.order(13)
def test_external_ldap_proxy_configuration(host):
    """ORCH_FVT_PREPARE_V013: omnia_auth uses the configured, valid meta proxy."""
    settings = _require_external_ldap(host)
    config_path = resolve_proxy_config_path(host, settings)
    deployed = host.file(config_path)
    assert deployed.is_file, f"External LDAP proxy config is missing: {config_path}"
    assert deployed.user == "root" and deployed.group == "root", config_path
    assert deployed.mode == 0o600, (
        f"External LDAP proxy config mode must be 0600: {deployed.mode!r}"
    )

    content = deployed.content_string
    external_dn = domain_to_dn(settings["domain"])
    expected_uri = (
        f"ldap://{settings['server_ip']}:{settings['server_port']}/"
    )
    assert re.search(r"^database\s+meta\s*$", content, re.MULTILINE)
    assert "moduleload back_ldap" in content
    assert "moduleload back_meta" in content
    assert expected_uri in content
    assert re.search(
        rf'^suffixmassage\s+"[^"]+"\s+"{re.escape(external_dn)}"\s*$',
        content,
        re.MULTILINE,
    )
    assert re.search(r"^idassert-bind\s*$", content, re.MULTILINE)
    validation = host.run(
        "podman exec %s slaptest -u -f /etc/openldap/slapd.conf",
        settings["proxy_container_name"],
    )
    assert validation.rc == 0, validation.stderr or validation.stdout


@pytest.mark.order(14)
def test_external_ldap_backend_reachable_from_proxy(host):
    """ORCH_FVT_PREPARE_V014: External LDAP is reachable from omnia_auth."""
    settings = _require_external_ldap(host)
    endpoint = f"ldap://{settings['server_ip']}:{settings['server_port']}"
    result = host.run(
        "podman exec %s ldapsearch -x -H %s -b '' -s base "
        "'(objectClass=*)' dn",
        settings["proxy_container_name"],
        endpoint,
    )
    assert result.rc == 0, (
        "External LDAP backend is unreachable from omnia_auth: "
        f"{result.stderr or result.stdout}"
    )


@pytest.mark.order(15)
def test_external_ldap_posix_account_binds_through_proxy(host):
    """ORCH_FVT_PREPARE_V015: Test POSIX account binds through omnia_auth."""
    _require_external_ldap(host)
    result = verify_external_ldap_user_bind(host)
    assert result["username"], "LDAP bind returned no configured username"
    assert result["dn"], "LDAP bind returned no configured user DN"


@pytest.mark.order(16)
def test_external_ldap_secrets_are_not_in_public_test_config(host):
    """ORCH_FVT_PREPARE_V016: External LDAP secrets stay in test_creds.yml."""
    _require_external_ldap(host)
    module_root = posixpath.dirname(
        posixpath.dirname(posixpath.dirname(posixpath.dirname(__file__)))
    )
    # This check executes where pytest runs; it intentionally verifies the
    # public framework input rather than reading or logging any secret value.
    public_config = posixpath.join(module_root, "test_config.yml")
    with open(public_config, encoding="utf-8") as config_file:
        content = config_file.read()
    assert not re.search(
        r"^\s*(?:ldap_password|external_ldap_admin_password)\s*:",
        content,
        re.MULTILINE,
    ), "LDAP secret fields must not be stored in test_config.yml"
