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

"""External LDAP meta-proxy reconciliation and verification after PXE boot.

The prepare lifecycle only starts the local omnia_auth container. Pointing it
at an external directory is a test-side configuration step, so it runs in the
pxeboot slurm_ldap suite immediately before the LDAP login checks.
"""

import ipaddress
import re
from typing import Any

from ._pxeboot_helpers import runtime_result
from .external_ldap_func import (
    configure_external_ldap_proxy,
    domain_to_dn,
    load_external_ldap_settings,
    resolve_proxy_config_path,
    verify_external_ldap_backend,
)
from .openldap_prepare_func import openldap_enabled


def _openldap_skip(component: str) -> dict[str, Any]:
    """Return a consistent expected skip for catalog-disabled OpenLDAP."""
    return runtime_result(
        True,
        "OpenLDAP is disabled by the active catalog",
        [
            ("Reason", "OpenLDAP is disabled by the active catalog"),
            ("Component", component),
            ("openldap_support", False),
        ],
        skipped=True,
    )


def reconcile_external_ldap_proxy(host) -> dict[str, Any]:
    """Reconcile and verify the opt-in external LDAP proxy configuration."""
    try:
        if not openldap_enabled(host):
            return _openldap_skip("External LDAP proxy")
    except (TypeError, ValueError) as exc:
        return runtime_result(False, "Unable to resolve OpenLDAP state", [], str(exc))

    try:
        settings = load_external_ldap_settings()
        if not settings["validation_enabled"]:
            return runtime_result(
                True,
                "External LDAP validation is not requested",
                [
                    ("Reason", "validate_external_ldap is false"),
                    ("validate_external_ldap", False),
                ],
                skipped=True,
            )
    except (TypeError, ValueError) as exc:
        return runtime_result(False, "External LDAP settings are invalid", [], str(exc))

    reconciliation = configure_external_ldap_proxy(host)
    fields = [
        ("Configuration changed", reconciliation.get("changed", False)),
        ("Reconciliation", reconciliation["details"]),
    ]
    if not reconciliation["success"]:
        return runtime_result(
            False,
            reconciliation["details"],
            fields,
            reconciliation["error"],
        )

    verification = check_external_ldap_proxy(host)
    return runtime_result(
        verification["success"],
        "External LDAP proxy reconciled and verified",
        [*fields, *verification["details"]["fields"]],
        verification["error"],
    )


def check_external_ldap_proxy(host) -> dict[str, Any]:
    """Verify the deployed external LDAP meta-proxy configuration."""
    try:
        if not openldap_enabled(host):
            return _openldap_skip("External LDAP proxy")
        settings = load_external_ldap_settings()
        if not settings["validation_enabled"]:
            return runtime_result(
                True,
                "External LDAP validation is not requested",
                [
                    ("Reason", "validate_external_ldap is false"),
                    ("validate_external_ldap", False),
                ],
                skipped=True,
            )
        path = resolve_proxy_config_path(host, settings)
        deployed = host.file(path)
        if not deployed.is_file:
            return runtime_result(
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
        return runtime_result(
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
    return runtime_result(
        not failures,
        "External LDAP meta-proxy configuration checked",
        fields,
        "; ".join(failures),
    )


def check_external_ldap_backend(host) -> dict[str, Any]:
    """Verify external LDAP is reachable from the omnia_auth container."""
    try:
        if not openldap_enabled(host):
            return _openldap_skip("External LDAP backend")
        settings = load_external_ldap_settings()
        if not settings["validation_enabled"]:
            return runtime_result(
                True,
                "External LDAP validation is not requested",
                [
                    ("Reason", "validate_external_ldap is false"),
                    ("validate_external_ldap", False),
                ],
                skipped=True,
            )
    except (TypeError, ValueError) as exc:
        return runtime_result(False, "External LDAP settings are invalid", [], str(exc))

    probe = verify_external_ldap_backend(host)
    return runtime_result(
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
