# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""External OpenLDAP test-environment provisioning and verification helpers.

The implementation follows the ``omnia-containers`` automation-v2.2.0.0
workflow: a Bitnami directory provides POSIX identities and ``omnia_auth``
proxies the local Omnia naming context to that directory through a generated
``slapd.conf``.  Secrets remain in the encrypted test credential store and are
passed to LDAP clients through mode-0600 files.
"""

from contextlib import contextmanager
import ipaddress
import os
import posixpath
import re
import secrets
import tempfile
import time
from typing import Any, Dict, Iterator, Mapping

from omnia_auto import (
    connection_params,
    load_test_config,
    load_test_credentials,
    read_remote_env,
    run_on_host,
    sync_files,
)


_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_SAFE_CONTAINER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
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
            raise ValueError("external_ldap.server_ip is invalid") from None
        return address
    return f"[{address}]" if parsed.version == 6 else address


def domain_to_dn(domain: str) -> str:
    """Convert a validated DNS domain into an LDAP base DN."""
    value = str(domain).strip().lower()
    if not _DOMAIN.fullmatch(value):
        raise ValueError(
            "external_ldap.domain must be a multi-label DNS name"
        )
    return ",".join(f"dc={label}" for label in value.split("."))


def _integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    """Return a bounded integer while rejecting booleans."""
    if isinstance(value, bool):
        raise ValueError(f"external_ldap.{field} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"external_ldap.{field} must be an integer"
        ) from exc
    if not minimum <= parsed <= maximum:
        raise ValueError(
            f"external_ldap.{field} must be between {minimum} and {maximum}"
        )
    return parsed


def load_external_ldap_settings(
    config: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Load and validate the non-sensitive external LDAP test settings."""
    source = dict(config if config is not None else load_test_config())
    raw = source.get("external_ldap", {})
    if not isinstance(raw, dict):
        raise ValueError("external_ldap must be a mapping")

    enabled = raw.get("enabled", False)
    managed = raw.get("manage_container", False)
    configure_proxy = raw.get("configure_proxy", True)
    for field, value in (
        ("enabled", enabled),
        ("manage_container", managed),
        ("configure_proxy", configure_proxy),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"external_ldap.{field} must be true or false")

    settings: Dict[str, Any] = {
        "enabled": enabled,
        "manage_container": managed,
        "configure_proxy": configure_proxy,
        "server_ip": str(raw.get("server_ip", "")).strip(),
        "server_port": _integer(
            raw.get("server_port", 1389), "server_port", 1, 65535
        ),
        "secure_port": _integer(
            raw.get("secure_port", 1636), "secure_port", 1, 65535
        ),
        "domain": str(raw.get("domain", "")).strip().lower(),
        "admin_username": str(
            raw.get("admin_username", "admin")
        ).strip(),
        "container_name": str(
            raw.get("container_name", "omnia_external_ldap")
        ).strip(),
        "volume_name": str(
            raw.get("volume_name", "omnia_external_ldap_data")
        ).strip(),
        "image": str(
            raw.get(
                "image", "docker.io/bitnamilegacy/openldap:latest"
            )
        ).strip(),
        "proxy_container_name": str(
            raw.get("proxy_container_name", "omnia_auth")
        ).strip(),
        "proxy_config_path": str(
            raw.get("proxy_config_path", "")
        ).strip(),
        "uid_number": _integer(
            raw.get("uid_number", 2000), "uid_number", 1, 2147483647
        ),
        "gid_number": _integer(
            raw.get("gid_number", 2000), "gid_number", 1, 2147483647
        ),
        "login_shell": str(
            raw.get("login_shell", "/bin/bash")
        ).strip(),
        "home_base": str(raw.get("home_base", "/home")).strip(),
    }

    if settings["enabled"]:
        for field in ("server_ip", "domain"):
            if not settings[field]:
                raise ValueError(
                    f"external_ldap.{field} is required when enabled"
                )
        domain_to_dn(settings["domain"])
        _ldap_host(settings["server_ip"])
    for field in (
        "admin_username",
        "container_name",
        "volume_name",
        "proxy_container_name",
    ):
        if not _SAFE_CONTAINER.fullmatch(settings[field]):
            raise ValueError(f"external_ldap.{field} is invalid")
    if not settings["image"] or any(
        character in settings["image"] for character in "\r\n\x00"
    ):
        raise ValueError("external_ldap.image is invalid")
    if not settings["login_shell"].startswith("/"):
        raise ValueError("external_ldap.login_shell must be absolute")
    if not settings["home_base"].startswith("/"):
        raise ValueError("external_ldap.home_base must be absolute")
    if settings["proxy_config_path"] and not settings[
        "proxy_config_path"
    ].startswith("/"):
        raise ValueError("external_ldap.proxy_config_path must be absolute")
    return settings


def load_external_ldap_credentials(
    credentials: Mapping[str, Any] | None = None,
) -> Dict[str, str]:
    """Load test-user and external-directory admin secrets."""
    source = dict(
        credentials if credentials is not None else load_test_credentials()
    )
    values = {
        "username": source.get("ldap_username", ""),
        "password": source.get("ldap_password", ""),
        "admin_password": source.get("external_ldap_admin_password", ""),
    }
    if not all(isinstance(value, str) for value in values.values()):
        raise ValueError("External LDAP credentials must be strings")
    if not _SAFE_NAME.fullmatch(values["username"]):
        raise ValueError(
            "ldap_username is missing or contains unsupported characters"
        )
    if not values["password"]:
        raise ValueError("ldap_password is required in test_creds.yml")
    if not values["admin_password"]:
        raise ValueError(
            "external_ldap_admin_password is required in test_creds.yml"
        )
    for field in ("password", "admin_password"):
        if any(character in values[field] for character in "\r\n\x00"):
            raise ValueError(f"{field} must be a single-line value")
    return values


def build_user_ldif(
    username: str,
    base_dn: str,
    uid_number: int,
    gid_number: int,
    login_shell: str,
    home_base: str,
) -> str:
    """Build one password-free POSIX user LDIF document."""
    if not _SAFE_NAME.fullmatch(username):
        raise ValueError("Invalid LDAP username")
    home = posixpath.join(home_base.rstrip("/"), username)
    return "\n".join((
        f"dn: uid={username},ou=People,{base_dn}",
        "objectClass: inetOrgPerson",
        "objectClass: posixAccount",
        "objectClass: shadowAccount",
        f"cn: {username}",
        f"sn: {username}",
        f"uid: {username}",
        f"uidNumber: {uid_number}",
        f"gidNumber: {gid_number}",
        f"loginShell: {login_shell}",
        f"homeDirectory: {home}",
        "shadowLastChange: 0",
        "shadowMax: 0",
        "shadowWarning: 0",
        "",
    ))


def build_group_ldif(
    username: str, base_dn: str, gid_number: int,
) -> str:
    """Build the matching POSIX group LDIF document."""
    if not _SAFE_NAME.fullmatch(username):
        raise ValueError("Invalid LDAP username")
    return "\n".join((
        f"dn: cn={username},ou=groups,{base_dn}",
        "objectClass: posixGroup",
        f"cn: {username}",
        f"gidNumber: {gid_number}",
        f"memberUid: {username}",
        "",
    ))


def extract_proxy_identity(current_config: str) -> Dict[str, str]:
    """Preserve the Omnia-local suffix/root identity from slapd.conf."""
    patterns = {
        "suffix": r'^\s*suffix\s+"?([^"\s]+)"?\s*$',
        "rootdn": r'^\s*rootdn\s+"?([^"\n]+?)"?\s*$',
        "rootpw": r"^\s*rootpw\s+(.+?)\s*$",
    }
    values = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, current_config, re.MULTILINE)
        if not match:
            raise ValueError(
                f"Existing slapd.conf does not define {field}"
            )
        values[field] = match.group(1).strip()
    return values


def resolve_proxy_config_path(
    host, settings: Mapping[str, Any] | None = None,
) -> str:
    """Resolve the mounted slapd.conf from config or target Omnia env."""
    values = dict(settings or load_external_ldap_settings())
    explicit = str(values.get("proxy_config_path", "")).strip()
    if explicit:
        return explicit
    data_path = read_remote_env(
        host, "OMNIA_DATA_PATH", required=False
    ) or "/opt/omnia"
    return posixpath.join(
        data_path.rstrip("/"), "auth/config/slapd.conf"
    )


def build_proxy_slapd_conf(
    local_identity: Mapping[str, str],
    settings: Mapping[str, Any],
    bind_password: str,
) -> str:
    """Render the automation-v2.2.0.0 meta-proxy slapd.conf contract."""
    external_dn = domain_to_dn(str(settings["domain"]))
    local_dn = str(local_identity["suffix"])
    bind_dn = f"cn={settings['admin_username']},{external_dn}"
    server_uri = (
        f"ldap://{_ldap_host(str(settings['server_ip']))}:"
        f"{settings['server_port']}/{local_dn}"
    )
    escaped_bind_password = bind_password.replace("\\", "\\\\").replace(
        '"', '\\"'
    )
    return f"""# Managed by the Orchestrator external LDAP test setup utility
# Compatible with dell/omnia-containers automation-v2.2.0.0

modulepath /usr/lib64/openldap
moduleload back_ldap.la
moduleload back_meta.la

include     /etc/openldap/schema/core.schema
include     /etc/openldap/schema/cosine.schema
include     /etc/openldap/schema/nis.schema
include     /etc/openldap/schema/inetorgperson.schema

pidfile     /run/openldap/slapd.pid
argsfile    /run/openldap/slapd.args

TLSCACertificateFile  /etc/openldap/certs/ldapserver.crt
TLSCertificateFile    /etc/openldap/certs/ldapserver.crt
TLSCertificateKeyFile /etc/openldap/certs/ldapserver.key

database    meta
suffix      "{local_dn}"
rootdn      "{local_identity['rootdn']}"
rootpw      {local_identity['rootpw']}

uri         "{server_uri}"
suffixmassage "{local_dn}" "{external_dn}"
idassert-bind
    bindmethod=simple
    binddn="{bind_dn}"
    credentials="{escaped_bind_password}"
    flags=override
    mode=none
idassert-authzFrom "dn.regex:.*"
"""


def _checked(result, action: str):
    """Raise an actionable error for a failed target command."""
    if result.rc != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        raise RuntimeError(f"{action} failed: {detail}")
    return result


@contextmanager
def _target_files(
    host, files: Mapping[str, tuple[str, int]],
) -> Iterator[Dict[str, str]]:
    """Copy protected temporary files to the execution OIM."""
    token = secrets.token_hex(8)
    remote_dir = posixpath.join(
        tempfile.gettempdir(), f"omnia_external_ldap_{token}"
    )
    local_dir = tempfile.mkdtemp(prefix="omnia_external_ldap_")
    remote_paths: Dict[str, str] = {}
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


def _ldap_command(
    host,
    settings: Mapping[str, Any],
    tool: str,
    arguments: list[str],
):
    """Run one LDAP client with all arguments shell-quoted by Testinfra."""
    parts = [
        tool,
        "-x",
        "-H",
        f"ldap://{_ldap_host(str(settings['server_ip']))}:"
        f"{settings['server_port']}",
        *arguments,
    ]
    return run_on_host(
        host, " ".join("%s" for _ in parts), *parts
    )


def _wait_for_external_ldap(
    host,
    settings: Mapping[str, Any],
    base_dn: str,
    admin_password_file: str,
    timeout: int = 90,
) -> None:
    """Wait for authenticated LDAP service readiness."""
    admin_dn = f"cn={settings['admin_username']},{base_dn}"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = _ldap_command(
            host,
            settings,
            "ldapsearch",
            [
                "-D", admin_dn,
                "-y", admin_password_file,
                "-b", base_dn,
                "-s", "base",
                "(objectClass=*)",
                "dn",
            ],
        )
        if result.rc == 0:
            return
        detail = (result.stderr or result.stdout or "").strip()
        if result.rc == 49 or "invalid credentials" in detail.lower():
            raise RuntimeError(
                "External LDAP rejected the configured administrator "
                "credential; update external_ldap_admin_password in the "
                "encrypted test credential store"
            )
        time.sleep(2)
    raise RuntimeError(
        "External LDAP did not accept the configured admin credential "
        f"within {timeout} seconds"
    )


def _deploy_external_container(
    host,
    settings: Mapping[str, Any],
    env_file: str,
    recreate: bool,
) -> None:
    """Create or start the explicitly configured Bitnami container."""
    container = settings["container_name"]
    volume = settings["volume_name"]
    exists = run_on_host(
        host, "podman container exists %s", container
    ).rc == 0
    if recreate and exists:
        _checked(
            run_on_host(host, "podman rm -f -- %s", container),
            "Remove configured external LDAP container",
        )
        exists = False
    if recreate:
        volume_exists = run_on_host(
            host, "podman volume exists %s", volume
        ).rc == 0
        if volume_exists:
            _checked(
                run_on_host(host, "podman volume rm -- %s", volume),
                "Remove configured external LDAP volume",
            )
    if exists:
        running = run_on_host(
            host,
            "podman inspect --format '{{.State.Running}}' %s",
            container,
        )
        _checked(running, "Inspect external LDAP container")
        if running.stdout.strip().lower() != "true":
            _checked(
                run_on_host(host, "podman start -- %s", container),
                "Start external LDAP container",
            )
        return

    _checked(
        run_on_host(host, "podman pull -- %s", settings["image"]),
        "Pull external LDAP image",
    )
    run_on_host(host, "podman volume create -- %s", volume)
    command = [
        "podman", "run", "-d", "--name", container,
        "-p", f"0.0.0.0:{settings['server_port']}:1389",
        "-p", f"0.0.0.0:{settings['secure_port']}:1636",
        "--env-file", env_file,
        "-v", f"{volume}:/bitnami/openldap",
        settings["image"],
    ]
    _checked(
        run_on_host(host, " ".join("%s" for _ in command), *command),
        "Deploy external LDAP container",
    )


def _ensure_posix_number_available(
    host,
    settings: Mapping[str, Any],
    admin_dn: str,
    admin_password_file: str,
    base_dn: str,
    attribute: str,
    value: int,
    expected_dn: str,
) -> None:
    """Fail when a requested POSIX ID belongs to a different LDAP entry."""
    lookup = _ldap_command(
        host,
        settings,
        "ldapsearch",
        [
            "-D", admin_dn,
            "-y", admin_password_file,
            "-b", base_dn,
            "-s", "sub",
            f"({attribute}={value})",
            "dn",
        ],
    )
    _checked(lookup, f"Check external_ldap.{attribute}")
    expected = expected_dn.casefold()
    conflicts = []
    for line in lookup.stdout.splitlines():
        if line.casefold().startswith("dn: "):
            found_dn = line[4:].strip()
            if found_dn.casefold() != expected:
                conflicts.append(found_dn)
    if conflicts:
        raise RuntimeError(
            f"external_ldap.{attribute} value {value} already belongs to "
            f"{', '.join(conflicts)}; choose an unused value for the new user"
        )


def _ensure_ldap_entry(
    host,
    settings: Mapping[str, Any],
    admin_dn: str,
    admin_password_file: str,
    entry_dn: str,
    object_filter: str,
    ldif_file: str,
) -> bool:
    """Create an LDAP entry if its exact DN is absent."""
    lookup = _ldap_command(
        host,
        settings,
        "ldapsearch",
        [
            "-D", admin_dn,
            "-y", admin_password_file,
            "-b", entry_dn,
            "-s", "base",
            object_filter,
            "dn",
        ],
    )
    if lookup.rc == 0:
        return False
    created = _ldap_command(
        host,
        settings,
        "ldapadd",
        ["-D", admin_dn, "-y", admin_password_file, "-f", ldif_file],
    )
    _checked(created, f"Create LDAP entry {entry_dn}")
    return True


def _install_proxy_config(
    host,
    settings: Mapping[str, Any],
    bind_password: str,
) -> Dict[str, str]:
    """Validate and atomically install slapd.conf, rolling back on failure."""
    config_path = resolve_proxy_config_path(host, settings)
    current = _checked(
        run_on_host(host, "cat -- %s", config_path),
        "Read deployed slapd.conf",
    ).stdout
    identity = extract_proxy_identity(current)
    content = build_proxy_slapd_conf(identity, settings, bind_password)

    with _target_files(host, {"slapd.conf": (content, 0o600)}) as generated:
        candidate = f"{config_path}.omnia-test-candidate"
        _checked(
            run_on_host(
                host, "install -o root -g root -m 0600 -- %s %s",
                generated["slapd.conf"], candidate,
            ),
            "Stage generated slapd.conf",
        )
        container_candidate = (
            f"/run/omnia-test-slapd-{secrets.token_hex(8)}.conf"
        )
        container = settings["proxy_container_name"]
        try:
            _checked(
                run_on_host(
                    host, "podman cp %s %s", candidate,
                    f"{container}:{container_candidate}",
                ),
                "Copy candidate slapd.conf into proxy container",
            )
            _checked(
                run_on_host(
                    host, "podman exec %s slaptest -u -f %s",
                    container, container_candidate,
                ),
                "Validate candidate slapd.conf",
            )
        finally:
            run_on_host(
                host, "podman exec %s rm -f -- %s",
                container, container_candidate,
            )

        backup = f"{config_path}.pre-external-ldap"
        if run_on_host(host, "test -f %s", backup).rc != 0:
            _checked(
                run_on_host(host, "cp -a -- %s %s", config_path, backup),
                "Back up deployed slapd.conf",
            )
        _checked(
            run_on_host(host, "mv -f -- %s %s", candidate, config_path),
            "Install generated slapd.conf",
        )
        run_on_host(host, "restorecon -F -- %s 2>/dev/null || true", config_path)

    service = settings["proxy_container_name"]
    restarted = run_on_host(host, "systemctl restart %s", service)
    if restarted.rc != 0:
        run_on_host(host, "cp -a -- %s %s", backup, config_path)
        run_on_host(host, "systemctl restart %s", service)
        _checked(restarted, "Restart LDAP proxy service")
    healthy = False
    for _ in range(30):
        state = run_on_host(
            host,
            "podman inspect --format '{{.State.Status}}' %s",
            settings["proxy_container_name"],
        )
        probe = run_on_host(
            host,
            "%s %s %s %s %s %s %s %s %s %s",
            "ldapsearch", "-x", "-H", "ldap://127.0.0.1:389",
            "-b", identity["suffix"], "-s", "base",
            "(objectClass=*)", "dn",
        )
        if (
            state.rc == 0
            and state.stdout.strip() == "running"
            and probe.rc == 0
        ):
            healthy = True
            break
        time.sleep(2)
    if not healthy:
        run_on_host(host, "cp -a -- %s %s", backup, config_path)
        run_on_host(host, "systemctl restart %s", service)
        raise RuntimeError("LDAP proxy failed to become running; backup restored")
    return {"path": config_path, "local_dn": identity["suffix"]}


def reconcile_external_ldap(host, recreate: bool = False) -> Dict[str, Any]:
    """Deploy/reconcile an external POSIX user and the Omnia LDAP proxy."""
    settings = load_external_ldap_settings()
    if not settings["enabled"]:
        raise ValueError(
            "external_ldap.enabled must be true in test_config.yml"
        )
    credentials = load_external_ldap_credentials()
    base_dn = domain_to_dn(settings["domain"])
    username = credentials["username"]
    admin_dn = f"cn={settings['admin_username']},{base_dn}"
    user_dn = f"uid={username},ou=People,{base_dn}"
    group_dn = f"cn={username},ou=groups,{base_dn}"

    env_content = "\n".join((
        f"LDAP_ADMIN_USERNAME={settings['admin_username']}",
        f"LDAP_ADMIN_PASSWORD={credentials['admin_password']}",
        f"LDAP_ROOT={base_dn}",
        "LDAP_ALLOW_ANON_BINDING=yes",
        "",
    ))
    people_ldif = "\n".join((
        f"dn: ou=People,{base_dn}",
        "objectClass: top",
        "objectClass: organizationalUnit",
        "ou: People",
        "",
    ))
    groups_ldif = "\n".join((
        f"dn: ou=groups,{base_dn}",
        "objectClass: top",
        "objectClass: organizationalUnit",
        "ou: groups",
        "",
    ))
    files = {
        "admin_password": (credentials["admin_password"], 0o600),
        "user_password": (credentials["password"], 0o600),
        "container.env": (env_content, 0o600),
        "people.ldif": (people_ldif, 0o600),
        "groups.ldif": (groups_ldif, 0o600),
        "user.ldif": (
            build_user_ldif(
                username,
                base_dn,
                settings["uid_number"],
                settings["gid_number"],
                settings["login_shell"],
                settings["home_base"],
            ),
            0o600,
        ),
        "group.ldif": (
            build_group_ldif(username, base_dn, settings["gid_number"]),
            0o600,
        ),
    }
    created = []
    with _target_files(host, files) as staged:
        if settings["manage_container"]:
            _deploy_external_container(
                host,
                settings,
                staged["container.env"],
                recreate,
            )
        elif recreate:
            raise ValueError(
                "--recreate requires external_ldap.manage_container=true"
            )
        _wait_for_external_ldap(
            host, settings, base_dn, staged["admin_password"]
        )
        _ensure_posix_number_available(
            host,
            settings,
            admin_dn,
            staged["admin_password"],
            base_dn,
            "uidNumber",
            settings["uid_number"],
            user_dn,
        )
        _ensure_posix_number_available(
            host,
            settings,
            admin_dn,
            staged["admin_password"],
            base_dn,
            "gidNumber",
            settings["gid_number"],
            group_dn,
        )

        entries = (
            (
                f"ou=People,{base_dn}",
                "(objectClass=organizationalUnit)",
                staged["people.ldif"],
            ),
            (
                f"ou=groups,{base_dn}",
                "(objectClass=organizationalUnit)",
                staged["groups.ldif"],
            ),
            (user_dn, "(objectClass=posixAccount)", staged["user.ldif"]),
            (group_dn, "(objectClass=posixGroup)", staged["group.ldif"]),
        )
        for entry_dn, object_filter, ldif_path in entries:
            if _ensure_ldap_entry(
                host,
                settings,
                admin_dn,
                staged["admin_password"],
                entry_dn,
                object_filter,
                ldif_path,
            ):
                created.append(entry_dn)

        password_update = _ldap_command(
            host,
            settings,
            "ldappasswd",
            [
                "-D", admin_dn,
                "-y", staged["admin_password"],
                "-T", staged["user_password"],
                user_dn,
            ],
        )
        _checked(password_update, "Set LDAP test-user password")

        direct_bind = _ldap_command(
            host,
            settings,
            "ldapwhoami",
            ["-D", user_dn, "-y", staged["user_password"]],
        )
        _checked(direct_bind, "Authenticate LDAP test user directly")

        proxy_path = ""
        if settings["configure_proxy"]:
            proxy = _install_proxy_config(
                host,
                settings,
                credentials["admin_password"],
            )
            proxy_path = proxy["path"]
            proxy_user_dn = (
                f"uid={username},ou=People,{proxy['local_dn']}"
            )
            proxy_bind = run_on_host(
                host,
                "%s %s %s %s %s %s %s %s",
                "ldapwhoami", "-x", "-H", "ldap://127.0.0.1:389",
                "-D", proxy_user_dn, "-y", staged["user_password"],
            )
            _checked(proxy_bind, "Authenticate LDAP test user through proxy")

    return {
        "username": username,
        "user_dn": user_dn,
        "created_entries": created,
        "proxy_config_path": proxy_path,
    }


def verify_external_ldap_user_bind(host) -> Dict[str, str]:
    """Verify the configured test user can bind through ``omnia_auth``."""
    settings = load_external_ldap_settings()
    if not settings["enabled"]:
        raise ValueError("external_ldap is not enabled")
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
            "ldapwhoami", "-x", "-H", "ldap://127.0.0.1:389",
            "-D", user_dn, "-y", staged["user_password"],
        )
    _checked(result, "Authenticate LDAP test user through proxy")
    return {"username": credentials["username"], "dn": user_dn}
