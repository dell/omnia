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


pytestmark = [pytest.mark.openldap, pytest.mark.functional]


def _require_openldap(host):
    """Skip only when persisted Orchestrator state says OpenLDAP is disabled."""
    paths = target_paths()
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
def test_openldap_accepts_anonymous_health_request(host):
    """ORCH_FVT_PREPARE_V011: OpenLDAP answers the same LDAP health request used by Quadlet."""
    _require_openldap(host)
    result = host.run(
        "podman exec omnia_auth ldapwhoami -x -H ldap://127.0.0.1:389"
    )
    assert result.rc == 0, result.stderr


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
