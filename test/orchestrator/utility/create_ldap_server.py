#!/usr/bin/env python3
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

"""Create and reconcile a standalone OpenLDAP test server.

The utility reads ``openldap_server_config.yml`` and supports a local Podman
host or a remote Podman host reached through the system SSH client. Reruns
preserve directory data unless an explicit data reset is requested.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_CONTAINER_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9./:@_-]*$")
_DOMAIN = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
    r"[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
    r"[A-Za-z0-9])?))+$"
)
_HOSTNAME = re.compile(
    r"^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$"
)
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9_./-]+$")
_INTERNAL_LDAP_URI = "ldap://127.0.0.1:1389"


class UtilityError(RuntimeError):
    """Expected configuration or runtime failure."""


def _info(message: str) -> None:
    print(f"[INFO] {message}", flush=True)


def _ok(message: str) -> None:
    print(f"[ OK ] {message}", flush=True)


def _warn(message: str) -> None:
    print(f"[WARN] {message}", flush=True)


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise UtilityError(f"{name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise UtilityError(f"{name} must be an integer") from exc
    if not minimum <= parsed <= maximum:
        raise UtilityError(f"{name} must be between {minimum} and {maximum}")
    return parsed


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise UtilityError(f"{name} must be true or false")
    return value


def _single_line(value: Any, name: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise UtilityError(f"{name} must be a string")
    result = value.strip() if not required else value
    if required and not result:
        raise UtilityError(f"{name} is required")
    if any(character in result for character in "\r\n\x00"):
        raise UtilityError(f"{name} must be a single-line value")
    return result


def _domain_to_dn(domain: str) -> str:
    normalized = domain.strip().lower()
    if not _DOMAIN.fullmatch(normalized):
        raise UtilityError(
            "openldap_domain must be a multi-label DNS name such as omnia.test"
        )
    return ",".join(f"dc={part}" for part in normalized.split("."))


def _validate_host(value: str) -> str:
    host = value.strip()
    if not host:
        return ""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not _HOSTNAME.fullmatch(host) or ".." in host:
            raise UtilityError("openldap_server_ip is not a valid IP or hostname")
    return host


def _load_encrypted_credentials(path: Path, key_path: Path) -> dict[str, Any]:
    """Decrypt and parse the ignored LDAP credential store."""
    if not path.is_file():
        raise UtilityError(
            f"Encrypted credential file does not exist: {path}. "
            "Run utility/setup_ldap_server.sh first."
        )
    if not key_path.is_file():
        raise UtilityError(f"Credential key file does not exist: {key_path}")
    if path.stat().st_mode & 0o077:
        raise UtilityError(f"Credential file must use mode 0600: {path}")
    if key_path.stat().st_mode & 0o077:
        raise UtilityError(f"Credential key file must use mode 0600: {key_path}")
    try:
        header = path.open(encoding="utf-8").readline().strip()
    except OSError as exc:
        raise UtilityError(f"Unable to read credential file: {path}") from exc
    if not header.startswith("$ANSIBLE_VAULT;"):
        raise UtilityError(f"Credential file is not Ansible Vault encrypted: {path}")
    vault = shutil.which("ansible-vault")
    if not vault:
        raise UtilityError("ansible-vault is required to read LDAP credentials")
    try:
        result = subprocess.run(
            [
                vault,
                "view",
                "--vault-password-file",
                str(key_path),
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UtilityError("Unable to decrypt LDAP credentials") from exc
    if result.returncode != 0:
        detail = (result.stderr or "ansible-vault returned an error").strip()
        raise UtilityError(f"Unable to decrypt LDAP credentials: {detail}")
    try:
        credentials = yaml.safe_load(result.stdout) or {}
    except yaml.YAMLError as exc:
        raise UtilityError("Decrypted LDAP credentials contain invalid YAML") from exc
    if not isinstance(credentials, dict):
        raise UtilityError("Decrypted LDAP credentials must be a YAML mapping")
    return credentials


def load_config(
    path: Path,
    credentials_path: Path,
    credentials_key_path: Path,
) -> dict[str, Any]:
    """Load and validate public configuration and encrypted credentials."""
    if not path.is_file():
        raise UtilityError(f"Configuration file does not exist: {path}")
    try:
        source = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise UtilityError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(source, dict):
        raise UtilityError("OpenLDAP configuration must be a YAML mapping")
    credentials = _load_encrypted_credentials(
        credentials_path,
        credentials_key_path,
    )
    server_ip = _validate_host(str(source.get("openldap_server_ip", "")))
    ssh_key = str(source.get("openldap_server_ssh_private_key", "")).strip()
    if ssh_key:
        ssh_key = str(Path(ssh_key).expanduser().resolve())
        if not Path(ssh_key).is_file():
            raise UtilityError(f"SSH private key does not exist: {ssh_key}")

    users_source = credentials.get("openldap_users", [])
    if not isinstance(users_source, list) or not users_source:
        raise UtilityError("openldap_users must contain at least one user")

    default_uid = _integer(
        source.get("openldap_default_uid_start", 2000),
        "openldap_default_uid_start",
        1,
        2_147_483_647,
    )
    default_shell = str(source.get("openldap_default_login_shell", "/bin/bash")).strip()
    if not _SAFE_PATH.fullmatch(default_shell):
        raise UtilityError("openldap_default_login_shell is not a safe path")

    users = []
    usernames: set[str] = set()
    uid_numbers: set[int] = set()
    gid_numbers: set[int] = set()
    for index, raw_user in enumerate(users_source):
        if not isinstance(raw_user, dict):
            raise UtilityError(f"openldap_users[{index}] must be a mapping")
        username = str(raw_user.get("username", "")).strip()
        if not _NAME.fullmatch(username):
            raise UtilityError(
                f"openldap_users[{index}].username is invalid or missing"
            )
        if username in usernames:
            raise UtilityError(f"Duplicate LDAP username: {username}")
        credential = _single_line(
            raw_user.get("credential", ""),
            f"openldap_users[{index}].credential",
        )
        uid_number = _integer(
            raw_user.get("uid_number", default_uid + index),
            f"openldap_users[{index}].uid_number",
            1,
            2_147_483_647,
        )
        gid_number = _integer(
            raw_user.get("gid_number", default_uid + index),
            f"openldap_users[{index}].gid_number",
            1,
            2_147_483_647,
        )
        if uid_number in uid_numbers:
            raise UtilityError(f"Duplicate LDAP uidNumber: {uid_number}")
        if gid_number in gid_numbers:
            raise UtilityError(f"Duplicate LDAP gidNumber: {gid_number}")
        login_shell = str(raw_user.get("login_shell", default_shell)).strip()
        home_directory = str(
            raw_user.get("home_directory", f"/home/{username}")
        ).strip()
        if not _SAFE_PATH.fullmatch(login_shell):
            raise UtilityError(f"Unsafe login shell for {username}")
        if not _SAFE_PATH.fullmatch(home_directory):
            raise UtilityError(f"Unsafe home directory for {username}")
        users.append(
            {
                "username": username,
                "credential": credential,
                "uid_number": uid_number,
                "gid_number": gid_number,
                "login_shell": login_shell,
                "home_directory": home_directory,
            }
        )
        usernames.add(username)
        uid_numbers.add(uid_number)
        gid_numbers.add(gid_number)

    container_name = str(source.get("openldap_container_name", "openldap")).strip()
    volume_name = str(source.get("openldap_data_volume", "openldap_data")).strip()
    image = str(
        source.get("openldap_image", "docker.io/bitnamilegacy/openldap:latest")
    ).strip()
    if not _CONTAINER_NAME.fullmatch(container_name):
        raise UtilityError("openldap_container_name is invalid")
    if not _CONTAINER_NAME.fullmatch(volume_name):
        raise UtilityError("openldap_data_volume is invalid")
    if not _IMAGE.fullmatch(image):
        raise UtilityError("openldap_image is invalid")

    admin_username = str(credentials.get("openldap_admin_username", "")).strip()
    if not _NAME.fullmatch(admin_username):
        raise UtilityError("openldap_admin_username is invalid")

    ssh_user = str(source.get("openldap_server_ssh_user", "root")).strip()
    if server_ip and not _NAME.fullmatch(ssh_user):
        raise UtilityError("openldap_server_ssh_user is invalid")

    return {
        "server_ip": server_ip,
        "ssh_user": ssh_user,
        "ssh_credential": _single_line(
            credentials.get("openldap_server_ssh_credential", ""),
            "openldap_server_ssh_credential",
            required=False,
        ),
        "ssh_private_key": ssh_key,
        "ssh_port": _integer(
            source.get("openldap_server_ssh_port", 22),
            "openldap_server_ssh_port",
            1,
            65535,
        ),
        "strict_host_key": _boolean(
            source.get("openldap_server_ssh_strict_host_key_checking", True),
            "openldap_server_ssh_strict_host_key_checking",
        ),
        "admin_username": admin_username,
        "admin_credential": _single_line(
            credentials.get("openldap_admin_credential", ""),
            "openldap_admin_credential",
        ),
        "domain": str(source.get("openldap_domain", "")).strip().lower(),
        "image": image,
        "container_name": container_name,
        "volume_name": volume_name,
        "ldap_port": _integer(
            source.get("openldap_port", 1389), "openldap_port", 1, 65535
        ),
        "ldaps_port": _integer(
            source.get("openldap_secure_port", 1636),
            "openldap_secure_port",
            1,
            65535,
        ),
        "pull_image": _boolean(
            source.get("openldap_pull_image", True), "openldap_pull_image"
        ),
        "reset_existing": _boolean(
            source.get("openldap_reset_existing", False),
            "openldap_reset_existing",
        ),
        "users": users,
    }


class CommandRunner:
    """Run argument-vector commands locally or through OpenSSH."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.is_local = config["server_ip"] in {
            "",
            "localhost",
            "127.0.0.1",
            "::1",
        }

    @property
    def target(self) -> str:
        return "localhost" if self.is_local else self.config["server_ip"]

    def _ssh_prefix(self) -> tuple[list[str], dict[str, str]]:
        environment = os.environ.copy()
        command = []
        credential = self.config["ssh_credential"]
        if credential:
            if not shutil.which("sshpass"):
                raise UtilityError(
                    "sshpass is required for password-based remote execution"
                )
            environment["SSHPASS"] = credential
            command.extend(["sshpass", "-e"])
        command.extend(
            [
                "ssh",
                "-p",
                str(self.config["ssh_port"]),
                "-o",
                "ConnectTimeout=15",
            ]
        )
        if not credential:
            command.extend(["-o", "BatchMode=yes"])
        if self.config["strict_host_key"]:
            command.extend(["-o", "StrictHostKeyChecking=yes"])
        else:
            command.extend(
                [
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                ]
            )
        if self.config["ssh_private_key"]:
            command.extend(["-i", self.config["ssh_private_key"]])
        command.append(f"{self.config['ssh_user']}@{self.config['server_ip']}")
        return command, environment

    def run(
        self,
        arguments: list[str],
        *,
        input_text: str | None = None,
        timeout: int = 120,
        check: bool = False,
        sensitive: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        command = list(arguments)
        environment = os.environ.copy()
        if not self.is_local:
            prefix, environment = self._ssh_prefix()
            command = [*prefix, shlex.join(arguments)]
        try:
            result = subprocess.run(
                command,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            label = "protected command" if sensitive else shlex.join(arguments)
            raise UtilityError(f"Unable to execute {label}: {exc}") from exc
        if check and result.returncode != 0:
            label = "protected command" if sensitive else shlex.join(arguments)
            detail = (result.stderr or result.stdout or "unknown error").strip()
            raise UtilityError(
                f"Command failed ({label}, rc={result.returncode}): {detail}"
            )
        return result


@contextmanager
def _target_file(
    runner: CommandRunner,
    content: str,
    suffix: str,
) -> Iterator[str]:
    # Randomized remote path, created under umask 077 and always removed.
    path = f"/tmp/omnia-openldap-{secrets.token_hex(8)}{suffix}"  # nosec B108
    try:
        runner.run(
            ["sh", "-c", f"umask 077; cat > {shlex.quote(path)}"],
            input_text=content,
            check=True,
            sensitive=True,
        )
        yield path
    finally:
        runner.run(["rm", "-f", "--", path], sensitive=True)


@contextmanager
def _container_file(
    runner: CommandRunner,
    container: str,
    content: str,
    suffix: str,
) -> Iterator[str]:
    # Randomized container path with mode 0600 and deterministic cleanup.
    container_path = f"/tmp/omnia-openldap-{secrets.token_hex(8)}{suffix}"  # nosec B108
    try:
        with _target_file(runner, content, suffix) as target_path:
            runner.run(
                ["podman", "cp", target_path, f"{container}:{container_path}"],
                check=True,
                sensitive=True,
            )
        runner.run(
            ["podman", "exec", container, "chmod", "0600", container_path],
            check=True,
            sensitive=True,
        )
        yield container_path
    finally:
        runner.run(
            ["podman", "exec", container, "rm", "-f", "--", container_path],
            sensitive=True,
        )


def _discover_domain(runner: CommandRunner) -> str:
    result = runner.run(["hostname", "-f"], check=True)
    hostname = result.stdout.strip().lower().rstrip(".")
    if "." not in hostname:
        raise UtilityError(
            "Target hostname has no DNS suffix; configure openldap_domain"
        )
    domain = hostname.split(".", 1)[1]
    _domain_to_dn(domain)
    return domain


def _container_exists(runner: CommandRunner, container: str) -> bool:
    return runner.run(["podman", "container", "exists", container]).returncode == 0


def _volume_exists(runner: CommandRunner, volume: str) -> bool:
    return runner.run(["podman", "volume", "exists", volume]).returncode == 0


def _container_state(runner: CommandRunner, container: str) -> str:
    result = runner.run(
        ["podman", "inspect", "--format", "{{.State.Status}}", container]
    )
    return result.stdout.strip() if result.returncode == 0 else "missing"


def _deploy_container(
    runner: CommandRunner,
    config: dict[str, Any],
    base_dn: str,
    allow_data_reset: bool,
) -> str:
    container = config["container_name"]
    volume = config["volume_name"]
    exists = _container_exists(runner, container)
    if config["reset_existing"]:
        if not allow_data_reset:
            raise UtilityError(
                "openldap_reset_existing is true; rerun with "
                "--allow-data-reset to authorize container and volume deletion"
            )
        if exists:
            runner.run(["podman", "rm", "-f", container], check=True)
            exists = False
        if _volume_exists(runner, volume):
            runner.run(["podman", "volume", "rm", volume], check=True)
        _warn(f"Reset existing OpenLDAP data volume: {volume}")

    if exists:
        state = _container_state(runner, container)
        if state != "running":
            runner.run(["podman", "start", container], check=True)
        _ok(f"Reusing existing container {container}; data preserved")
        return "reused"

    if config["pull_image"]:
        _info(f"Pulling image {config['image']}")
        runner.run(["podman", "pull", config["image"]], check=True, timeout=600)

    environment_file = "\n".join(
        [
            f"LDAP_ADMIN_USERNAME={config['admin_username']}",
            f"LDAP_ADMIN_PASSWORD={config['admin_credential']}",
            f"LDAP_ROOT={base_dn}",
            "",
        ]
    )
    digest = hashlib.sha256(
        (
            f"{config['image']}|{base_dn}|{config['admin_username']}|"
            f"{config['ldap_port']}|{config['ldaps_port']}"
        ).encode()
    ).hexdigest()
    with _target_file(runner, environment_file, ".env") as env_path:
        runner.run(
            [
                "podman",
                "run",
                "-d",
                "--name",
                container,
                "--label",
                f"com.dell.omnia.openldap.config={digest}",
                "--env-file",
                env_path,
                "-p",
                f"0.0.0.0:{config['ldap_port']}:1389",
                "-p",
                f"0.0.0.0:{config['ldaps_port']}:1636",
                "-v",
                f"{volume}:/bitnami/openldap",
                config["image"],
            ],
            check=True,
            sensitive=True,
        )
    _ok(f"Created OpenLDAP container {container}")
    return "created"


def _ldap_arguments(
    container: str,
    tool: str,
    admin_dn: str,
    admin_password_file: str,
    *arguments: str,
) -> list[str]:
    return [
        "podman",
        "exec",
        container,
        tool,
        "-x",
        "-H",
        _INTERNAL_LDAP_URI,
        "-D",
        admin_dn,
        "-y",
        admin_password_file,
        *arguments,
    ]


def _wait_for_ready(
    runner: CommandRunner,
    config: dict[str, Any],
    base_dn: str,
    password_file: str,
) -> None:
    admin_dn = f"cn={config['admin_username']},{base_dn}"
    for _ in range(30):
        result = runner.run(
            _ldap_arguments(
                config["container_name"],
                "ldapsearch",
                admin_dn,
                password_file,
                "-LLL",
                "-o",
                "nettimeout=3",
                "-b",
                base_dn,
                "-s",
                "base",
                "(objectClass=*)",
                "dn",
            ),
            sensitive=True,
        )
        if result.returncode == 0:
            _ok("OpenLDAP is ready")
            return
        time.sleep(2)
    raise UtilityError(
        f"OpenLDAP did not become ready; inspect podman logs {config['container_name']}"
    )


def _entry_exists(
    runner: CommandRunner,
    config: dict[str, Any],
    admin_dn: str,
    password_file: str,
    dn: str,
    object_class: str,
) -> bool:
    result = runner.run(
        _ldap_arguments(
            config["container_name"],
            "ldapsearch",
            admin_dn,
            password_file,
            "-LLL",
            "-b",
            dn,
            "-s",
            "base",
            f"(objectClass={object_class})",
            "dn",
        ),
        sensitive=True,
    )
    return result.returncode == 0 and any(
        line.lower().startswith("dn:") for line in result.stdout.splitlines()
    )


def _apply_ldif(
    runner: CommandRunner,
    config: dict[str, Any],
    admin_dn: str,
    password_file: str,
    ldif: str,
    *,
    modify: bool = False,
) -> None:
    tool = "ldapmodify" if modify else "ldapadd"
    with _container_file(runner, config["container_name"], ldif, ".ldif") as ldif_path:
        runner.run(
            _ldap_arguments(
                config["container_name"],
                tool,
                admin_dn,
                password_file,
                "-f",
                ldif_path,
            ),
            check=True,
            sensitive=True,
        )


def _ensure_ou(
    runner: CommandRunner,
    config: dict[str, Any],
    base_dn: str,
    admin_dn: str,
    password_file: str,
    name: str,
) -> None:
    dn = f"ou={name},{base_dn}"
    if _entry_exists(runner, config, admin_dn, password_file, dn, "organizationalUnit"):
        _info(f"OU already exists: {name}")
        return
    _apply_ldif(
        runner,
        config,
        admin_dn,
        password_file,
        f"dn: {dn}\nobjectClass: top\nobjectClass: organizationalUnit\nou: {name}\n",
    )
    _ok(f"Created OU {name}")


def _ensure_user(
    runner: CommandRunner,
    config: dict[str, Any],
    base_dn: str,
    admin_dn: str,
    admin_password_file: str,
    user: dict[str, Any],
) -> str:
    username = user["username"]
    user_dn = f"uid={username},ou=People,{base_dn}"
    exists = _entry_exists(
        runner,
        config,
        admin_dn,
        admin_password_file,
        user_dn,
        "posixAccount",
    )
    attributes = (
        f"cn: {username}\n"
        f"sn: {username}\n"
        f"loginShell: {user['login_shell']}\n"
        f"uidNumber: {user['uid_number']}\n"
        f"gidNumber: {user['gid_number']}\n"
        f"homeDirectory: {user['home_directory']}\n"
    )
    if exists:
        changes = "".join(
            f"replace: {line.split(':', 1)[0]}\n{line}\n-\n"
            for line in attributes.strip().splitlines()
        )
        _apply_ldif(
            runner,
            config,
            admin_dn,
            admin_password_file,
            f"dn: {user_dn}\nchangetype: modify\n{changes}",
            modify=True,
        )
        action = "updated"
    else:
        _apply_ldif(
            runner,
            config,
            admin_dn,
            admin_password_file,
            (
                f"dn: {user_dn}\n"
                "objectClass: inetOrgPerson\n"
                "objectClass: posixAccount\n"
                "objectClass: shadowAccount\n"
                f"uid: {username}\n"
                f"{attributes}"
                "shadowLastChange: 0\n"
                "shadowMax: 0\n"
                "shadowWarning: 0\n"
            ),
        )
        action = "created"

    group_dn = f"cn={username},ou=groups,{base_dn}"
    group_exists = _entry_exists(
        runner,
        config,
        admin_dn,
        admin_password_file,
        group_dn,
        "posixGroup",
    )
    if group_exists:
        _apply_ldif(
            runner,
            config,
            admin_dn,
            admin_password_file,
            (
                f"dn: {group_dn}\nchangetype: modify\n"
                f"replace: gidNumber\ngidNumber: {user['gid_number']}\n-\n"
                f"replace: memberUid\nmemberUid: {username}\n"
            ),
            modify=True,
        )
    else:
        _apply_ldif(
            runner,
            config,
            admin_dn,
            admin_password_file,
            (
                f"dn: {group_dn}\nobjectClass: top\n"
                f"objectClass: posixGroup\ncn: {username}\n"
                f"gidNumber: {user['gid_number']}\nmemberUid: {username}\n"
            ),
        )

    with _container_file(
        runner, config["container_name"], user["credential"], ".credential"
    ) as user_password_file:
        runner.run(
            _ldap_arguments(
                config["container_name"],
                "ldappasswd",
                admin_dn,
                admin_password_file,
                "-T",
                user_password_file,
                user_dn,
            ),
            check=True,
            sensitive=True,
        )
        bind = runner.run(
            [
                "podman",
                "exec",
                config["container_name"],
                "ldapwhoami",
                "-x",
                "-H",
                _INTERNAL_LDAP_URI,
                "-D",
                user_dn,
                "-y",
                user_password_file,
            ],
            sensitive=True,
        )
        if bind.returncode != 0:
            raise UtilityError(f"LDAP bind verification failed for {username}")
    _ok(f"User {username}: {action}; group and password reconciled")
    return action


def _print_plan(config: dict[str, Any], domain: str, base_dn: str) -> None:
    print("\nOpenLDAP server plan")
    print(f"  Target        : {config['server_ip'] or 'localhost'}")
    print(f"  Container     : {config['container_name']}")
    print(f"  Image         : {config['image']}")
    print(f"  Data volume   : {config['volume_name']}")
    print(f"  LDAP/LDAPS    : {config['ldap_port']}/{config['ldaps_port']}")
    print(f"  Domain        : {domain}")
    print(f"  Base DN       : {base_dn}")
    print(f"  Users         : {len(config['users'])}")
    print(f"  Reset data    : {config['reset_existing']}\n")


def reconcile(config: dict[str, Any], allow_data_reset: bool) -> None:
    """Deploy the server and reconcile all requested directory entries."""
    runner = CommandRunner(config)
    if not runner.is_local:
        result = runner.run(["hostname", "-f"], check=True)
        _ok(f"Connected to {result.stdout.strip()} via SSH")
    if runner.run(["podman", "--version"]).returncode != 0:
        raise UtilityError(f"Podman is unavailable on {runner.target}")

    domain = config["domain"] or _discover_domain(runner)
    base_dn = _domain_to_dn(domain)
    _print_plan(config, domain, base_dn)
    container_action = _deploy_container(runner, config, base_dn, allow_data_reset)
    admin_dn = f"cn={config['admin_username']},{base_dn}"

    with _container_file(
        runner,
        config["container_name"],
        config["admin_credential"],
        ".credential",
    ) as admin_password_file:
        _wait_for_ready(runner, config, base_dn, admin_password_file)
        _ensure_ou(
            runner,
            config,
            base_dn,
            admin_dn,
            admin_password_file,
            "People",
        )
        _ensure_ou(
            runner,
            config,
            base_dn,
            admin_dn,
            admin_password_file,
            "groups",
        )
        counts = {"created": 0, "updated": 0}
        for user in config["users"]:
            action = _ensure_user(
                runner,
                config,
                base_dn,
                admin_dn,
                admin_password_file,
                user,
            )
            counts[action] += 1

    print("\nOpenLDAP reconciliation complete")
    print(f"  Container     : {container_action}")
    print(f"  Users created : {counts['created']}")
    print(f"  Users updated : {counts['updated']}")
    print(
        f"  LDAP URL      : ldap://{config['server_ip'] or 'localhost'}:"
        f"{config['ldap_port']}"
    )
    print(f"  Base DN       : {base_dn}")
    print(f"  Admin DN      : {admin_dn}")


def _default_config_path() -> Path:
    return Path(__file__).resolve().with_name("openldap_server_config.yml")


def _default_credentials_path() -> Path:
    return Path(__file__).resolve().with_name("openldap_server_credentials.yml")


def _default_credentials_key_path() -> Path:
    return Path(__file__).resolve().with_name(".openldap_server_credentials.key")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or reconcile a standalone OpenLDAP test server"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=_default_config_path(),
        help="OpenLDAP YAML configuration path",
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=_default_credentials_path(),
        help="Ansible Vault encrypted LDAP credential file",
    )
    parser.add_argument(
        "--credentials-key",
        type=Path,
        default=_default_credentials_key_path(),
        help="Local Ansible Vault key file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate configuration without connecting or changing state",
    )
    parser.add_argument(
        "--allow-data-reset",
        action="store_true",
        help="Authorize deletion when openldap_reset_existing is true",
    )
    arguments = parser.parse_args()
    try:
        config = load_config(
            arguments.config.resolve(),
            arguments.credentials.resolve(),
            arguments.credentials_key.resolve(),
        )
        if arguments.check:
            domain = config["domain"] or "<discovered from target FQDN>"
            base_dn = (
                _domain_to_dn(domain)
                if not domain.startswith("<")
                else "<derived from target FQDN>"
            )
            _print_plan(config, domain, base_dn)
            _ok("Configuration is valid; no state was changed")
            return 0
        reconcile(config, arguments.allow_data_reset)
        return 0
    except UtilityError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
