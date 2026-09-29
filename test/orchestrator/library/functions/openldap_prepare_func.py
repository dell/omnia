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

"""OpenLDAP postcondition helpers for the prepare lifecycle."""

import ipaddress
import posixpath
import re
import time
from typing import Any

from omnia_auto import run_on_host

from ..vars.openldap_vars import (
    LDAP_READY_DELAY_SECONDS,
    LDAP_READY_RETRIES,
)
from ..vars.prepare_vars import (
    OPENLDAP_CERT_PATH_SUFFIX,
    OPENLDAP_CONFIG_PATH_SUFFIX,
    OPENLDAP_CONTAINER,
    OPENLDAP_KEY_PATH_SUFFIX,
    OPENLDAP_PORTS,
    OPENLDAP_QUADLET_PATH,
    OPENLDAP_SERVICE,
    PREPARE_COMMANDS,
)
from ._prepare_helpers import prepare_result, read_yaml_mapping
from .external_ldap_func import (
    configure_external_ldap_proxy,
    domain_to_dn,
    load_external_ldap_settings,
    resolve_proxy_config_path,
    verify_external_ldap_backend,
)
from .project_func import (
    resolve_target_omnia_data_path,
    resolve_target_output_project_path,
)


def _openldap_enabled(host) -> bool:
    """Read the authoritative catalog decision from Orchestrator state."""
    state_path = posixpath.join(
        resolve_target_output_project_path(host), "orchestrator_state.yml"
    )
    state = read_yaml_mapping(host, state_path)
    enabled = state.get("openldap_support")
    if not isinstance(enabled, bool):
        raise TypeError("orchestrator_state.yml must contain boolean openldap_support")
    return enabled


def _openldap_skip(component: str) -> dict[str, Any]:
    """Return a consistent expected skip for catalog-disabled OpenLDAP."""
    return prepare_result(
        True,
        "OpenLDAP is disabled by the active catalog",
        [("Component", component), ("openldap_support", False)],
        skipped=True,
    )


def reconcile_prepare_external_ldap_proxy(host) -> dict[str, Any]:
    """Reconcile and verify the opt-in external LDAP proxy configuration."""
    try:
        if not _openldap_enabled(host):
            return _openldap_skip("External LDAP proxy")
    except (TypeError, ValueError) as exc:
        return prepare_result(False, "Unable to resolve OpenLDAP state", [], str(exc))

    try:
        settings = load_external_ldap_settings()
        if not settings["validation_enabled"]:
            return prepare_result(
                True,
                "External LDAP validation is not requested",
                [("validate_external_ldap", False)],
                skipped=True,
            )
    except (TypeError, ValueError) as exc:
        return prepare_result(False, "External LDAP settings are invalid", [], str(exc))

    reconciliation = configure_external_ldap_proxy(host)
    fields = [
        ("Configuration changed", reconciliation.get("changed", False)),
        ("Reconciliation", reconciliation["details"]),
    ]
    if not reconciliation["success"]:
        return prepare_result(
            False,
            reconciliation["details"],
            fields,
            reconciliation["error"],
        )

    verification = check_prepare_external_ldap_proxy(host)
    return prepare_result(
        verification["success"],
        "External LDAP proxy reconciled and verified",
        [*fields, *verification["fields"]],
        verification["error"],
    )


def check_prepare_openldap_runtime(host) -> dict[str, Any]:
    """Verify enabled OpenLDAP has a healthy service and container."""
    try:
        if not _openldap_enabled(host):
            return _openldap_skip("OpenLDAP runtime")
    except (TypeError, ValueError) as exc:
        return prepare_result(False, "Unable to resolve OpenLDAP state", [], str(exc))

    active = run_on_host(host, PREPARE_COMMANDS["unit_active"], OPENLDAP_SERVICE)
    enabled = run_on_host(host, PREPARE_COMMANDS["unit_enabled"], OPENLDAP_SERVICE)
    state = run_on_host(host, PREPARE_COMMANDS["container_state"], OPENLDAP_CONTAINER)
    health = run_on_host(host, PREPARE_COMMANDS["container_health"], OPENLDAP_CONTAINER)
    health_state = health.stdout.strip()
    if state.stdout.strip() == "running" and health_state == "starting":
        for _ in range(LDAP_READY_RETRIES):
            time.sleep(LDAP_READY_DELAY_SECONDS)
            health = run_on_host(
                host,
                PREPARE_COMMANDS["container_health"],
                OPENLDAP_CONTAINER,
            )
            health_state = health.stdout.strip()
            if health_state != "starting":
                break
    values = {
        "Service active": active.stdout.strip(),
        "Service enabled": enabled.stdout.strip(),
        "Container state": state.stdout.strip(),
        "Container health": health_state,
    }
    valid_states = {
        "Service active": {"active"},
        "Service enabled": {"enabled", "generated"},
        "Container state": {"running"},
        "Container health": {"healthy"},
    }
    failures = []
    for name, value in values.items():
        if value not in valid_states[name]:
            failures.append(f"{name}={value or 'unavailable'}")
    return prepare_result(
        not failures,
        "OpenLDAP Quadlet service and container health checked",
        list(values.items()),
        "; ".join(failures),
    )


def check_prepare_openldap_artifacts(host) -> dict[str, Any]:
    """Verify OpenLDAP secret modes, certificate lifetime and slapd syntax."""
    try:
        if not _openldap_enabled(host):
            return _openldap_skip("OpenLDAP artifacts")
    except (TypeError, ValueError) as exc:
        return prepare_result(False, "Unable to resolve OpenLDAP state", [], str(exc))

    base = resolve_target_omnia_data_path(host).rstrip("/")
    artifacts = (
        (posixpath.join(base, OPENLDAP_CONFIG_PATH_SUFFIX), 0o600),
        (posixpath.join(base, OPENLDAP_KEY_PATH_SUFFIX), 0o600),
        (posixpath.join(base, OPENLDAP_CERT_PATH_SUFFIX), 0o644),
        (OPENLDAP_QUADLET_PATH, 0o644),
    )
    fields = []
    failures = []
    for path, mode in artifacts:
        deployed = host.file(path)
        state = "valid"
        if not deployed.is_file:
            state = "missing"
        elif deployed.user != "root" or deployed.group != "root":
            state = "invalid owner"
        elif deployed.mode != mode:
            state = f"mode {oct(deployed.mode)}"
        fields.append((path, state))
        if state != "valid":
            failures.append(f"{path}: {state}")

    certificate = posixpath.join(base, OPENLDAP_CERT_PATH_SUFFIX)
    cert = run_on_host(host, PREPARE_COMMANDS["certificate_valid"], certificate)
    fields.append(("TLS certificate", "valid" if cert.rc == 0 else "invalid"))
    if cert.rc != 0:
        failures.append("TLS certificate expires within 24 hours or is invalid")

    slapd = run_on_host(
        host,
        PREPARE_COMMANDS["slapd_validate"],
        OPENLDAP_CONTAINER,
    )
    fields.append(("slapd.conf syntax", "valid" if slapd.rc == 0 else "invalid"))
    if slapd.rc != 0:
        failures.append("slapd.conf syntax")

    return prepare_result(
        not failures,
        "OpenLDAP configuration, permissions and TLS checked",
        fields,
        "; ".join(failures),
    )


def check_prepare_openldap_endpoint(host) -> dict[str, Any]:
    """Verify local LDAP health and both published listeners."""
    try:
        if not _openldap_enabled(host):
            return _openldap_skip("OpenLDAP endpoint")
    except (TypeError, ValueError) as exc:
        return prepare_result(False, "Unable to resolve OpenLDAP state", [], str(exc))

    fields = []
    failures = []
    identity = run_on_host(host, PREPARE_COMMANDS["ldap_identity"], OPENLDAP_CONTAINER)
    fields.append(("Anonymous LDAP health", "passed" if identity.rc == 0 else "failed"))
    if identity.rc != 0:
        failures.append("anonymous ldapwhoami")
    for port in OPENLDAP_PORTS:
        listener = run_on_host(
            host,
            PREPARE_COMMANDS["ldap_listener"],
            str(port),
        )
        listening = listener.rc == 0 and bool(listener.stdout.strip())
        fields.append((f"TCP {port}", "listening" if listening else "not listening"))
        if not listening:
            failures.append(f"TCP {port}")
    return prepare_result(
        not failures,
        "OpenLDAP local health and published listeners checked",
        fields,
        "; ".join(failures),
    )


def check_prepare_external_ldap_proxy(host) -> dict[str, Any]:
    """Verify the deployed external LDAP meta-proxy configuration."""
    try:
        if not _openldap_enabled(host):
            return _openldap_skip("External LDAP proxy")
        settings = load_external_ldap_settings()
        if not settings["validation_enabled"]:
            return prepare_result(
                True,
                "External LDAP validation is not requested",
                [("validate_external_ldap", False)],
                skipped=True,
            )
        path = resolve_proxy_config_path(host, settings)
        deployed = host.file(path)
        if not deployed.is_file:
            return prepare_result(
                False,
                "External LDAP proxy config missing",
                [("Path", path)],
                path,
            )
        content = deployed.content_string
        external_dn = domain_to_dn(str(settings["domain"]))
        endpoint_host = str(settings["server_ip"])
        try:
            if ipaddress.ip_address(endpoint_host).version == 6:
                endpoint_host = f"[{endpoint_host}]"
        except ValueError:
            pass
        expected = {
            "database meta": bool(
                re.search(r"^database\s+meta\s*$", content, re.MULTILINE)
            ),
            "back_ldap module": "back_ldap" in content,
            "back_meta module": "back_meta" in content,
            "external endpoint": (
                f"ldap://{endpoint_host}:{settings['server_port']}/" in content
            ),
            "suffix massage": external_dn in content,
            "idassert bind": bool(
                re.search(r"^idassert-bind\s*$", content, re.MULTILINE)
            ),
        }
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(
            False, "External LDAP proxy verification failed", [], str(exc)
        )

    fields = [
        (name, "present" if value else "missing") for name, value in expected.items()
    ]
    failures = [name for name, value in expected.items() if not value]
    fields.extend(
        [
            ("Config owner", f"{deployed.user}:{deployed.group}"),
            ("Config mode", oct(deployed.mode)),
        ]
    )
    if deployed.user != "root" or deployed.group != "root":
        failures.append("config owner")
    if deployed.mode != 0o600:
        failures.append("config mode")
    return prepare_result(
        not failures,
        "External LDAP meta-proxy configuration checked",
        fields,
        "; ".join(failures),
    )


def check_prepare_external_ldap_backend(host) -> dict[str, Any]:
    """Verify external LDAP is reachable from the omnia_auth container."""
    try:
        if not _openldap_enabled(host):
            return _openldap_skip("External LDAP backend")
        settings = load_external_ldap_settings()
        if not settings["validation_enabled"]:
            return prepare_result(
                True,
                "External LDAP validation is not requested",
                [("validate_external_ldap", False)],
                skipped=True,
            )
    except (TypeError, ValueError) as exc:
        return prepare_result(False, "External LDAP settings are invalid", [], str(exc))

    probe = verify_external_ldap_backend(host)
    return prepare_result(
        probe["success"],
        probe["details"],
        [
            ("Endpoint", probe.get("endpoint", "unavailable")),
            (
                "LDAP protocol reachability",
                "passed" if probe["success"] else "failed",
            ),
        ],
        probe["error"],
    )
