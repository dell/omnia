# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""External LDAP proxy configuration and verification helpers.

The OpenLDAP prepare verification may reconcile ``omnia_auth`` only when
explicitly enabled in ``test_config.yml``. External-directory operations stay
read-only. Secrets are loaded from the encrypted test credential store and are
transferred only through protected temporary files.
"""

import ipaddress
import os
import posixpath
import re
import secrets
import tempfile
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from omnia_auto import (
    connection_params,
    load_test_config,
    load_test_credentials,
    read_remote_env,
    run_on_host,
    sync_files,
    vault_decrypt_to_dict,
)

from ..vars.openldap_vars import (
    LDAP_DEFAULT_PORT,
    LDAP_PROXY_CONTAINER,
    LDAP_PROXY_SERVICE,
    LDAP_PROXY_SLAPD_TEMPLATE,
    LDAP_READY_DELAY_SECONDS,
    LDAP_READY_RETRIES,
)
from .project_func import resolve_target_input_project_path

_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_DOMAIN = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
    r"[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
    r"[A-Za-z0-9])?))+$"
)
_HOSTNAME = re.compile(
    r"^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$"
)


def _ldap_host(value: str) -> str:
    """Validate a server address and bracket IPv6 for LDAP URIs."""
    address = value.strip()
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        if not _HOSTNAME.fullmatch(address) or ".." in address:
            raise ValueError("external_ldap_server_ip is invalid") from None
        return address
    return f"[{address}]" if parsed.version == 6 else address


def domain_to_dn(domain: str) -> str:
    """Convert a validated DNS domain into an LDAP base DN."""
    value = str(domain).strip().lower()
    if not _DOMAIN.fullmatch(value):
        raise ValueError("external_ldap_domain must be a multi-label DNS name")
    return ",".join(f"dc={label}" for label in value.split("."))


def _integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    """Return a bounded integer while rejecting booleans."""
    if isinstance(value, bool):
        raise ValueError(  # noqa: TRY004 - public config validation error
            f"{field} must be an integer"
        )
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if not minimum <= parsed <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return parsed


def load_external_ldap_settings(
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load and validate the explicit external LDAP proxy settings."""
    source = dict(config if config is not None else load_test_config())
    if "external_ldap" in source:
        raise ValueError(
            "external_ldap is not a supported mapping; use "
            "validate_external_ldap, configure_external_ldap, "
            "external_ldap_server_ip, "
            "external_ldap_server_port, external_ldap_domain, and "
            "external_ldap_bind_username"
        )

    validation_enabled = source.get("validate_external_ldap", False)
    if not isinstance(validation_enabled, bool):
        raise ValueError(  # noqa: TRY004 - public config validation error
            "validate_external_ldap must be true or false"
        )
    configuration_enabled = source.get("configure_external_ldap", False)
    if not isinstance(configuration_enabled, bool):
        raise ValueError(  # noqa: TRY004 - public config validation error
            "configure_external_ldap must be true or false"
        )

    server_ip = str(source.get("external_ldap_server_ip", "")).strip()
    server_port = source.get("external_ldap_server_port", "")
    domain = str(source.get("external_ldap_domain", "")).strip().lower()
    bind_username = str(source.get("external_ldap_bind_username", "")).strip()

    if validation_enabled:
        missing = [
            field
            for field, value in (
                ("external_ldap_server_ip", server_ip),
                ("external_ldap_server_port", str(server_port).strip()),
                ("external_ldap_domain", domain),
                ("external_ldap_bind_username", bind_username),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "External LDAP configuration is incomplete; missing "
                + ", ".join(missing)
            )

    settings: dict[str, Any] = {
        "validation_enabled": validation_enabled,
        "configuration_enabled": configuration_enabled,
        "server_ip": server_ip,
        "server_port": (
            _integer(
                server_port,
                "external_ldap_server_port",
                1,
                65535,
            )
            if validation_enabled
            else LDAP_DEFAULT_PORT
        ),
        "domain": domain,
        "bind_username": bind_username,
        "proxy_container_name": LDAP_PROXY_CONTAINER,
        "proxy_config_path": "",
    }
    if validation_enabled:
        _ldap_host(server_ip)
        domain_to_dn(domain)
        if not _SAFE_NAME.fullmatch(bind_username):
            raise ValueError(
                "external_ldap_bind_username contains unsupported characters"
            )
    return settings


def load_external_ldap_credentials(
    credentials: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Load the LDAP test identity used by login verification."""
    source = dict(credentials if credentials is not None else load_test_credentials())
    values = {
        "username": source.get("ldap_username", ""),
        "password": source.get("ldap_password", ""),
    }
    if not all(isinstance(value, str) for value in values.values()):
        raise ValueError("LDAP test credentials must be strings")
    if not _SAFE_NAME.fullmatch(values["username"]):
        raise ValueError("ldap_username is missing or contains unsupported characters")
    if not values["password"]:
        raise ValueError("ldap_password is required in test_creds.yml")
    if any(character in values["password"] for character in "\r\n\x00"):
        raise ValueError("ldap_password must be a single-line value")
    return values


def load_external_ldap_bind_credentials(
    credentials: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Load credentials used by the omnia_auth external-directory bind."""
    source = dict(credentials if credentials is not None else load_test_credentials())
    values = {"password": source.get("external_ldap_bind_password", "")}
    if not isinstance(values["password"], str):
        raise TypeError("External LDAP bind password must be a string")
    if not values["password"]:
        raise ValueError("external_ldap_bind_password is required in test_creds.yml")
    if any(character in values["password"] for character in "\r\n\x00"):
        raise ValueError("external_ldap_bind_password must be a single-line value")
    return values


def extract_proxy_identity(current_config: str) -> dict[str, str]:
    """Preserve the Omnia-local suffix and root identity from slapd.conf."""
    patterns = {
        "suffix": r'^\s*suffix\s+"?([^"\s]+)"?\s*$',
        "rootdn": r'^\s*rootdn\s+"?([^"\n]+)"?\s*$',
        "rootpw": r"^\s*rootpw\s+(\S+)\s*$",
    }
    identity: dict[str, str] = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, current_config, re.MULTILINE)
        if not match:
            raise ValueError(f"Existing slapd.conf does not define {field}")
        identity[field] = match.group(1).strip()
    return identity


def load_local_proxy_identity(host) -> dict[str, str]:
    """Resolve the Omnia-local LDAP identity from authoritative inputs.

    The local suffix comes from the OIM FQDN. The local administrator identity
    comes from the encrypted Orchestrator credential store. Existing proxy
    content is deliberately not used because it may already contain a prior
    external-directory mapping.
    """
    hostname_result = _checked(
        run_on_host(host, "hostname -f"),
        "Resolve OIM FQDN",
    )
    fqdn = hostname_result.stdout.strip().lower().rstrip(".")
    if not _HOSTNAME.fullmatch(fqdn) or "." not in fqdn:
        raise ValueError("OIM hostname must be a fully qualified domain name")
    labels = fqdn.split(".")
    local_domain = ".".join(labels[1:]) if len(labels) > 2 else fqdn
    local_dn = domain_to_dn(local_domain)

    input_path = resolve_target_input_project_path(host)
    remote_paths = {
        "credentials": posixpath.join(input_path, "orchestrator_credentials.yml"),
        "key": posixpath.join(input_path, ".orchestrator_credentials_key"),
    }
    remote_files = {name: host.file(path) for name, path in remote_paths.items()}
    missing = [
        remote_paths[name]
        for name, remote_file in remote_files.items()
        if not remote_file.is_file
    ]
    if missing:
        raise ValueError(
            "Required Orchestrator credential artifact is missing: "
            + ", ".join(missing)
        )

    with tempfile.TemporaryDirectory(prefix="omnia_local_ldap_identity_") as local_dir:
        os.chmod(local_dir, 0o700)
        local_paths = {
            name: os.path.join(local_dir, posixpath.basename(path))
            for name, path in remote_paths.items()
        }
        for name, local_path in local_paths.items():
            with open(local_path, "wb") as handle:
                handle.write(remote_files[name].content)
            os.chmod(local_path, 0o600)
        decrypted = vault_decrypt_to_dict(
            local_paths["credentials"],
            local_paths["key"],
        )
    if not decrypted["success"]:
        raise ValueError(
            "Unable to read the encrypted Orchestrator credential store: "
            + decrypted["error"]
        )

    values = decrypted["data"]
    username = values.get("openldap_db_username", "")
    password = values.get("openldap_db_password", "")
    if not isinstance(username, str) or not _SAFE_NAME.fullmatch(username):
        raise ValueError(
            "openldap_db_username is missing or invalid in orchestrator_credentials.yml"
        )
    if (
        not isinstance(password, str)
        or not password
        or any(character in password for character in "\r\n\x00")
    ):
        raise ValueError(
            "openldap_db_password is missing or invalid in orchestrator_credentials.yml"
        )
    return {
        "suffix": local_dn,
        "rootdn": f"cn={username},{local_dn}",
        "rootpw": password,
    }


def resolve_proxy_config_path(
    host,
    settings: Mapping[str, Any] | None = None,
) -> str:
    """Resolve the mounted slapd.conf from the execution OIM environment."""
    values = dict(settings or load_external_ldap_settings())
    explicit = str(values.get("proxy_config_path", "")).strip()
    if explicit:
        return explicit
    data_path = read_remote_env(host, "OMNIA_DATA_PATH", required=False) or "/opt/omnia"
    return posixpath.join(data_path.rstrip("/"), "auth/config/slapd.conf")


def build_proxy_slapd_conf(
    local_identity: Mapping[str, str],
    settings: Mapping[str, Any],
    bind_username: str,
    bind_password: str,
) -> str:
    """Render the desired external-directory meta-proxy configuration."""
    if not _SAFE_NAME.fullmatch(bind_username):
        raise ValueError("Invalid external LDAP bind username")
    if not bind_password or any(character in bind_password for character in "\r\n\x00"):
        raise ValueError("Invalid external LDAP bind password")

    external_dn = domain_to_dn(str(settings["domain"]))
    local_dn = str(local_identity["suffix"])
    bind_dn = f"cn={bind_username},{external_dn}"
    server_uri = (
        f"ldap://{_ldap_host(str(settings['server_ip']))}:"
        f"{settings['server_port']}/{local_dn}"
    )
    escaped_password = bind_password.replace("\\", "\\\\").replace('"', '\\"')
    return LDAP_PROXY_SLAPD_TEMPLATE.format(
        ldap_suffix=local_dn,
        ldap_rootdn=local_identity["rootdn"],
        ldap_rootpw=local_identity["rootpw"],
        ldap_uri=server_uri,
        ldap_suffixmassage_local=local_dn,
        ldap_suffixmassage_remote=external_dn,
        ldap_bind_dn=bind_dn,
        ldap_bind_credentials=escaped_password,
    )


def _checked(result, action: str):
    """Raise a safe, actionable error for a failed target command."""
    if result.rc != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        raise RuntimeError(f"{action} failed: {detail}")
    return result


@contextmanager
def _target_files(
    host,
    files: Mapping[str, tuple[str, int]],
) -> Iterator[dict[str, str]]:
    """Copy protected temporary files to the execution OIM."""
    token = secrets.token_hex(8)
    remote_dir = posixpath.join(tempfile.gettempdir(), f"omnia_external_ldap_{token}")
    local_dir = tempfile.mkdtemp(prefix="omnia_external_ldap_")
    remote_paths: dict[str, str] = {}
    local_paths = []
    try:
        _checked(
            run_on_host(host, "install -d -m 0700 -- %s", remote_dir),
            "Create protected LDAP staging directory",
        )
        connection = connection_params()
        for name, (content, mode) in files.items():
            local_path = os.path.join(local_dir, name)
            with open(local_path, "w", encoding="utf-8") as handle:
                handle.write(content)
            os.chmod(local_path, mode)
            remote_path = posixpath.join(remote_dir, name)
            transfer = sync_files(
                mode=connection["mode"],
                src=local_path,
                dest=remote_path,
                ip=connection["ip"],
                user=connection["user"],
                port=connection["port"],
                auth_secret=connection["auth_secret"],
                ssh_opts=connection["ssh_opts"],
            )
            if not transfer["success"]:
                raise RuntimeError(
                    f"Unable to stage protected LDAP file: {transfer['error']}"
                )
            _checked(
                run_on_host(host, "chmod %s -- %s", oct(mode)[2:], remote_path),
                "Secure staged LDAP file",
            )
            remote_paths[name] = remote_path
            local_paths.append(local_path)
        yield remote_paths
    finally:
        if remote_paths:
            run_on_host(
                host,
                "rm -f -- " + " ".join("%s" for _ in remote_paths),
                *remote_paths.values(),
            )
        run_on_host(host, "rmdir -- %s 2>/dev/null || true", remote_dir)
        for local_path in local_paths:
            try:
                os.unlink(local_path)
            except FileNotFoundError:
                pass
        try:
            os.rmdir(local_dir)
        except OSError:
            pass


def _verify_external_directory_reachability(
    host,
    settings: Mapping[str, Any],
) -> None:
    """Prove LDAP protocol reachability from the omnia_auth container."""
    base_dn = domain_to_dn(str(settings["domain"]))
    endpoint = (
        f"ldap://{_ldap_host(str(settings['server_ip']))}:{settings['server_port']}"
    )
    command = [
        "podman",
        "exec",
        LDAP_PROXY_CONTAINER,
        "ldapsearch",
        "-x",
        "-LLL",
        "-o",
        "nettimeout=5",
        "-H",
        endpoint,
        "-b",
        "",
        "-s",
        "base",
        "namingContexts",
    ]
    last_detail = ""
    for _ in range(LDAP_READY_RETRIES):
        result = run_on_host(
            host,
            " ".join("%s" for _ in command),
            *command,
        )
        if result.rc == 0:
            naming_contexts = {
                line.split(":", 1)[1].strip().lower()
                for line in result.stdout.splitlines()
                if line.lower().startswith("namingcontexts:")
            }
            if base_dn.lower() not in naming_contexts:
                raise RuntimeError(
                    f"External LDAP does not advertise {base_dn} as a naming context"
                )
            return
        last_detail = (result.stderr or result.stdout or "").strip()
        if result.rc == 127 or "not found" in last_detail.lower():
            raise RuntimeError(
                "ldapsearch is unavailable inside the omnia_auth container"
            )
        time.sleep(LDAP_READY_DELAY_SECONDS)
    suffix = f": {last_detail}" if last_detail else ""
    raise RuntimeError(
        "External LDAP endpoint did not become reachable from the "
        f"omnia_auth container{suffix}"
    )


def _proxy_running(host, container: str) -> bool:
    """Return whether the exact proxy container is running."""
    state = run_on_host(
        host,
        "podman inspect --format '{{.State.Status}}' %s",
        container,
    )
    return state.rc == 0 and state.stdout.strip() == "running"


def _proxy_health(host, container: str) -> str:
    """Return the exact container health state without raising."""
    health = run_on_host(
        host,
        "podman inspect --format "
        "'{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' %s",
        container,
    )
    return health.stdout.strip() if health.rc == 0 else "unavailable"


def _wait_for_proxy(host) -> bool:
    """Wait for running, healthy, and LDAP-responsive proxy state."""
    for _ in range(LDAP_READY_RETRIES):
        if _proxy_running(host, LDAP_PROXY_CONTAINER):
            probe = run_on_host(
                host,
                "%s %s %s %s %s %s %s",
                "podman",
                "exec",
                LDAP_PROXY_CONTAINER,
                "ldapwhoami",
                "-x",
                "-H",
                "ldap://127.0.0.1:389",
            )
            if _proxy_health(host, LDAP_PROXY_CONTAINER) == "healthy" and probe.rc == 0:
                return True
        time.sleep(LDAP_READY_DELAY_SECONDS)
    return False


def _restore_proxy_config(host, backup: str, config_path: str) -> None:
    """Atomically restore the most recent configuration and its readiness."""
    rollback = f"{config_path}.rollback-{secrets.token_hex(8)}.tmp"
    _checked(
        run_on_host(
            host,
            "install -o root -g root -m 0600 -- %s %s",
            backup,
            rollback,
        ),
        "Stage LDAP proxy rollback",
    )
    _checked(
        run_on_host(host, "mv -f -- %s %s", rollback, config_path),
        "Restore LDAP proxy configuration",
    )
    run_on_host(host, "restorecon -F -- %s 2>/dev/null || true", config_path)
    _checked(
        run_on_host(host, "systemctl restart %s", LDAP_PROXY_SERVICE),
        "Restart omnia_auth after rollback",
    )
    if not _wait_for_proxy(host):
        raise RuntimeError("omnia_auth did not become ready after slapd.conf rollback")


def _install_proxy_config(
    host,
    settings: Mapping[str, Any],
    bind_credentials: Mapping[str, str],
) -> dict[str, Any]:
    """Install changed content atomically and roll back failed restarts."""
    config_path = resolve_proxy_config_path(host, settings)
    current = _checked(
        run_on_host(host, "cat -- %s", config_path),
        "Read deployed slapd.conf",
    ).stdout
    identity = load_local_proxy_identity(host)
    desired = build_proxy_slapd_conf(
        identity,
        settings,
        str(settings["bind_username"]),
        bind_credentials["password"],
    )
    if not _proxy_running(host, LDAP_PROXY_CONTAINER):
        raise RuntimeError(
            "omnia_auth container is not running; run the prepare playbook "
            "and inspect omnia_auth.service"
        )
    if current == desired:
        return {
            "path": config_path,
            "local_dn": identity["suffix"],
            "changed": False,
        }

    _verify_external_directory_reachability(host, settings)

    backup = f"{config_path}.pre-external-ldap"
    candidate = f"{config_path}.omnia-test-{secrets.token_hex(8)}.tmp"
    installed = False
    try:
        with _target_files(host, {"slapd.conf": (desired, 0o600)}) as staged:
            _checked(
                run_on_host(
                    host,
                    "install -o root -g root -m 0600 -- %s %s",
                    staged["slapd.conf"],
                    candidate,
                ),
                "Stage generated slapd.conf",
            )
            container_candidate = f"/run/omnia-test-slapd-{secrets.token_hex(8)}.conf"
            try:
                _checked(
                    run_on_host(
                        host,
                        "podman cp %s %s",
                        candidate,
                        f"{LDAP_PROXY_CONTAINER}:{container_candidate}",
                    ),
                    "Copy candidate slapd.conf into omnia_auth",
                )
                _checked(
                    run_on_host(
                        host,
                        "podman exec %s slaptest -u -f %s",
                        LDAP_PROXY_CONTAINER,
                        container_candidate,
                    ),
                    "Validate candidate slapd.conf",
                )
            finally:
                run_on_host(
                    host,
                    "podman exec %s rm -f -- %s",
                    LDAP_PROXY_CONTAINER,
                    container_candidate,
                )

            _checked(
                run_on_host(host, "cp -a -- %s %s", config_path, backup),
                "Back up deployed slapd.conf",
            )
            _checked(
                run_on_host(host, "mv -f -- %s %s", candidate, config_path),
                "Install generated slapd.conf",
            )
            installed = True
            run_on_host(
                host,
                "restorecon -F -- %s 2>/dev/null || true",
                config_path,
            )

        _checked(
            run_on_host(host, "systemctl restart %s", LDAP_PROXY_SERVICE),
            "Restart omnia_auth service",
        )
        if not _wait_for_proxy(host):
            raise RuntimeError(
                "omnia_auth did not become ready after applying slapd.conf"
            )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        if installed:
            _restore_proxy_config(host, backup, config_path)
            raise RuntimeError(f"{exc}; previous slapd.conf restored") from exc
        raise
    finally:
        run_on_host(host, "rm -f -- %s", candidate)

    return {
        "path": config_path,
        "local_dn": identity["suffix"],
        "changed": True,
    }


def configure_external_ldap_proxy(host) -> dict[str, Any]:
    """Validate inputs and idempotently reconcile the omnia_auth proxy."""
    try:
        settings = load_external_ldap_settings()
        if not settings["validation_enabled"]:
            return {
                "success": True,
                "changed": False,
                "skipped": True,
                "details": (
                    "validate_external_ldap is false; omnia_auth was not modified"
                ),
                "error": "",
            }
        if not settings["configuration_enabled"]:
            return {
                "success": True,
                "changed": False,
                "skipped": True,
                "details": (
                    "configure_external_ldap is false; omnia_auth was not modified"
                ),
                "error": "",
            }
        bind_credentials = load_external_ldap_bind_credentials()
        result = _install_proxy_config(host, settings, bind_credentials)
        action = "updated" if result["changed"] else "already matched"
        return {
            "success": True,
            "changed": result["changed"],
            "skipped": False,
            "details": (f"omnia_auth slapd.conf {action}; container is running"),
            "error": "",
        }
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return {
            "success": False,
            "changed": False,
            "skipped": False,
            "details": "External LDAP proxy was not configured",
            "error": str(exc),
        }


def verify_external_ldap_backend(host) -> dict[str, Any]:
    """Verify external LDAP reachability from the omnia_auth container."""
    endpoint = "unavailable"
    try:
        settings = load_external_ldap_settings()
        if not settings["validation_enabled"]:
            return {
                "success": True,
                "skipped": True,
                "endpoint": "",
                "details": "validate_external_ldap is false",
                "error": "",
            }
        endpoint = (
            f"ldap://{_ldap_host(str(settings['server_ip']))}:{settings['server_port']}"
        )
        _verify_external_directory_reachability(host, settings)
        return {
            "success": True,
            "skipped": False,
            "endpoint": endpoint,
            "details": (
                "External LDAP protocol reachability and naming context "
                "verified from omnia_auth"
            ),
            "error": "",
        }
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return {
            "success": False,
            "skipped": False,
            "endpoint": endpoint,
            "details": "External LDAP protocol reachability failed",
            "error": str(exc),
        }


def verify_external_ldap_user_bind(host) -> dict[str, str]:
    """Verify the configured test user can bind through ``omnia_auth``."""
    settings = load_external_ldap_settings()
    if not settings["validation_enabled"]:
        raise ValueError("validate_external_ldap is false")
    credentials = load_external_ldap_credentials()
    config_path = resolve_proxy_config_path(host, settings)
    current = _checked(
        run_on_host(host, "cat -- %s", config_path),
        "Read deployed slapd.conf",
    ).stdout
    local_dn = extract_proxy_identity(current)["suffix"]
    user_dn = f"uid={credentials['username']},ou=People,{local_dn}"
    with _target_files(
        host, {"user_password": (credentials["password"], 0o600)}
    ) as staged:
        result = run_on_host(
            host,
            "%s %s %s %s %s %s %s %s",
            "ldapwhoami",
            "-x",
            "-H",
            "ldap://127.0.0.1:389",
            "-D",
            user_dn,
            "-y",
            staged["user_password"],
        )
    _checked(result, "Authenticate LDAP test user through proxy")
    return {"username": credentials["username"], "dn": user_dn}
