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

"""Secure LDAP SSH and pam_slurm_adopt behavioral verification."""

import base64
import os
import re
import secrets
import shlex
import socket
import subprocess
import time
from pathlib import Path

import paramiko
from omnia_auto import (
    connection_params,
    load_test_credentials,
)

from ..vars.pxeboot_vars import (
    PAM_ACCESS_SETTLE_SECONDS,
    PAM_SESSION_TERMINATION_TIMEOUT_SECONDS,
    PXEBOOT_COMMANDS,
    RECOVERY_POLL_SECONDS,
    SLURM_COMPILER_PREFIX,
    SLURM_CONTROL_PREFIX,
    SLURM_JOB_TIMEOUT_SECONDS,
    SLURM_LOGIN_PREFIX,
)
from ._pxeboot_helpers import (
    group_fields,
    marker_is_authorized,
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import ldap_test_username as _ldap_username
from ._workload_helpers import optional_skip as _skip
from ._workload_helpers import require_functional as _require_functional
from ._workload_helpers import slurm_compute_rows as _compute_rows
from ._workload_helpers import slurm_context as _context
from ._workload_helpers import slurm_shared_storage as _shared_storage
from ._workload_helpers import slurm_submission_rows as _allowed_rows

_IDENTITY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")
_HOST_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]*")
_RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
_PURPOSE_RE = re.compile(r"[a-z][a-z0-9-]{0,31}")
_SSH_KEY_TYPE_RE = re.compile(r"(?:ssh|ecdsa)-[A-Za-z0-9@._+-]+")
_SSH_KEY_DATA_RE = re.compile(r"[A-Za-z0-9+/]+={0,3}")


def _ldap_credentials() -> tuple[str, str]:
    credentials = load_test_credentials()
    username = str(credentials.get("ldap_username") or "")
    auth_secret = str(credentials.get("ldap_password") or "")
    if not _IDENTITY_RE.fullmatch(username):
        raise ValueError("ldap_username is missing or invalid in test_creds.yml")
    if not auth_secret:
        raise ValueError("ldap_password is missing in encrypted test_creds.yml")
    return username, auth_secret


class _MappedNodeHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """Accept a first-seen key only for one validated PXE-mapped node."""

    def __init__(self, mapped_target: str):
        self._mapped_target = mapped_target

    def missing_host_key(self, client, hostname, key):
        key_type = key.get_name()
        key_data = key.get_base64()
        if (
            hostname != self._mapped_target
            or not _HOST_RE.fullmatch(hostname)
            or not _SSH_KEY_TYPE_RE.fullmatch(key_type)
            or not _SSH_KEY_DATA_RE.fullmatch(key_data)
        ):
            raise paramiko.SSHException(
                "Refusing an untrusted SSH key outside the mapped node target"
            )
        client.get_host_keys().add(hostname, key_type, key)


def _new_client(mapped_target: str = "") -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    policy = (
        _MappedNodeHostKeyPolicy(mapped_target)
        if mapped_target
        else paramiko.RejectPolicy()
    )
    client.set_missing_host_key_policy(policy)
    return client


def _mapped_host_key_matches(exc: paramiko.BadHostKeyException, target: str) -> bool:
    """Return whether a host-key mismatch belongs to the mapped node."""
    reported = str(exc.hostname or "")
    return reported in {target, f"[{target}]:22"}


def _remove_stale_mapped_host_key(
    target: str,
    replacement_key: paramiko.PKey,
) -> tuple[bool, str]:
    """Replace one mapped node key after Paramiko proves an exact mismatch."""
    known_hosts = os.path.expanduser(
        os.environ.get("OMNIA_SSH_KNOWN_HOSTS", "~/.ssh/known_hosts")
    )
    if not os.path.isfile(known_hosts):
        return False, f"known-hosts file does not exist: {known_hosts}"
    try:
        result = subprocess.run(
            ["ssh-keygen", "-R", target, "-f", known_hosts],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"unable to remove the stale SSH host key: {exc}"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return False, detail or "ssh-keygen could not remove the stale host key"
    key_type = replacement_key.get_name()
    key_data = replacement_key.get_base64()
    if not _SSH_KEY_TYPE_RE.fullmatch(key_type) or not _SSH_KEY_DATA_RE.fullmatch(
        key_data
    ):
        return False, "the replacement SSH host key has an invalid format"
    try:
        flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(known_hosts, flags)
        with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
            stream.write(f"{target} {key_type} {key_data}\n")
        os.chmod(known_hosts, 0o600)
    except OSError as exc:
        return False, f"unable to store the replacement SSH host key: {exc}"
    return True, f"replaced stale SSH host key for {target} in {known_hosts}"


def _ldap_ssh_identity(
    target: str, username: str, auth_secret: str
) -> tuple[bool, str]:
    if not _HOST_RE.fullmatch(target) or not _IDENTITY_RE.fullmatch(username):
        raise ValueError("LDAP SSH target or identity is invalid")
    connection = connection_params()
    host_key_reconciled = False
    for attempt in range(2):
        jump_client = None
        node_client = None
        channel = None
        try:
            if connection["mode"] == "local":
                channel = socket.create_connection((target, 22), timeout=10)
            else:
                oim_host = str(connection["ip"])
                oim_user = str(connection["user"])
                oim_port = int(connection["port"])
                jump_password = connection["auth_secret"]
                jump_client = _new_client()
                jump_client.connect(
                    oim_host,
                    port=oim_port,
                    username=oim_user,
                    password=jump_password,
                    allow_agent=jump_password is None,
                    look_for_keys=jump_password is None,
                    timeout=10,
                    auth_timeout=10,
                    banner_timeout=10,
                )
                transport = jump_client.get_transport()
                if transport is None or not transport.is_active():
                    raise RuntimeError("The OIM SSH transport is not active")
                channel = transport.open_channel(
                    "direct-tcpip",
                    (target, 22),
                    ("127.0.0.1", 0),
                    timeout=10,
                )

            node_client = _new_client(target)
            node_client.connect(
                target,
                port=22,
                username=username,
                password=auth_secret,
                sock=channel,
                allow_agent=False,
                look_for_keys=False,
                timeout=10,
                auth_timeout=10,
                banner_timeout=10,
            )
            _stdin, stdout, _stderr = node_client.exec_command(  # nosec B601
                "id -un", timeout=10
            )
            output = stdout.read(128).decode("utf-8", errors="replace").strip()
            rc = stdout.channel.recv_exit_status()
            if rc != 0:
                return False, "SSH session command failed"
            if output != username:
                return False, "SSH session identity did not match the LDAP user"
            detail = "session opened"
            if host_key_reconciled:
                detail += "; stale mapped-node host key removed"
            return True, detail
        except paramiko.BadHostKeyException as exc:
            if attempt == 0 and _mapped_host_key_matches(exc, target):
                removed, detail = _remove_stale_mapped_host_key(target, exc.key)
                if removed:
                    host_key_reconciled = True
                    continue
                return False, f"SSH host key mismatch; {detail}"
            return False, f"SSH host key mismatch for {exc.hostname}"
        except paramiko.AuthenticationException:
            return False, "password authentication denied"
        except (TimeoutError, OSError, paramiko.SSHException) as exc:
            return False, f"SSH transport failed: {type(exc).__name__}"
        finally:
            if node_client is not None:
                node_client.close()
            if channel is not None:
                channel.close()
            if jump_client is not None:
                jump_client.close()
    return False, "SSH host-key reconciliation did not establish a session"


def _open_ldap_persistent_session(target: str, username: str, auth_secret: str):
    """Open an LDAP SSH command that must be killed when its job ends."""
    if not _HOST_RE.fullmatch(target) or not _IDENTITY_RE.fullmatch(username):
        raise ValueError("LDAP SSH target or identity is invalid")
    connection = connection_params()
    host_key_reconciled = False
    for attempt in range(2):
        jump_client = None
        node_client = None
        proxy_channel = None
        session = None
        try:
            if connection["mode"] == "local":
                proxy_channel = socket.create_connection((target, 22), timeout=10)
            else:
                jump_client = _new_client()
                jump_password = connection["auth_secret"]
                jump_client.connect(
                    str(connection["ip"]),
                    port=int(connection["port"]),
                    username=str(connection["user"]),
                    password=jump_password,
                    allow_agent=jump_password is None,
                    look_for_keys=jump_password is None,
                    timeout=10,
                    auth_timeout=10,
                    banner_timeout=10,
                )
                transport = jump_client.get_transport()
                if transport is None or not transport.is_active():
                    raise RuntimeError("The OIM SSH transport is not active")
                proxy_channel = transport.open_channel(
                    "direct-tcpip",
                    (target, 22),
                    ("127.0.0.1", 0),
                    timeout=10,
                )

            node_client = _new_client(target)
            node_client.connect(
                target,
                port=22,
                username=username,
                password=auth_secret,
                sock=proxy_channel,
                allow_agent=False,
                look_for_keys=False,
                timeout=10,
                auth_timeout=10,
                banner_timeout=10,
            )
            _stdin, stdout, stderr = node_client.exec_command(  # nosec B601
                "printf 'OMNIA_LOGIN_READY=%s\\n' \"$(id -un)\"; exec sleep 300",
                timeout=10,
            )
            ready = stdout.readline().strip()
            if ready != f"OMNIA_LOGIN_READY={username}":
                return None, "SSH session identity did not match the LDAP user"
            stdout.channel.settimeout(None)
            session = {
                "jump_client": jump_client,
                "node_client": node_client,
                "proxy_channel": proxy_channel,
                "command_channel": stdout.channel,
                "stdout": stdout,
                "stderr": stderr,
            }
            detail = "persistent session opened as the LDAP identity"
            if host_key_reconciled:
                detail += "; stale mapped-node host key removed"
            return session, detail
        except paramiko.BadHostKeyException as exc:
            if attempt == 0 and _mapped_host_key_matches(exc, target):
                removed, detail = _remove_stale_mapped_host_key(target, exc.key)
                if removed:
                    host_key_reconciled = True
                    continue
                return None, f"SSH host key mismatch; {detail}"
            return None, f"SSH host key mismatch for {exc.hostname}"
        except paramiko.AuthenticationException:
            return None, "password authentication denied"
        except (TimeoutError, OSError, paramiko.SSHException) as exc:
            return None, f"SSH transport failed: {type(exc).__name__}"
        finally:
            if session is None:
                if node_client is not None:
                    node_client.close()
                if proxy_channel is not None:
                    proxy_channel.close()
                if jump_client is not None:
                    jump_client.close()
    return None, "SSH host-key reconciliation did not establish a session"


def _close_ldap_persistent_session(session):
    """Close every transport retained for a persistent LDAP SSH session."""
    if not session:
        return
    session["node_client"].close()
    proxy_channel = session.get("proxy_channel")
    if proxy_channel is not None:
        proxy_channel.close()
    jump_client = session.get("jump_client")
    if jump_client is not None:
        jump_client.close()


def _wait_for_pam_session_termination(session):
    """Wait until Slurm terminates the adopted SSH process after job exit."""
    deadline = time.monotonic() + PAM_SESSION_TERMINATION_TIMEOUT_SECONDS
    command_channel = session["command_channel"]
    while time.monotonic() < deadline:
        transport = session["node_client"].get_transport()
        if (
            command_channel.closed
            or command_channel.exit_status_ready()
            or transport is None
            or not transport.is_active()
        ):
            return True
        time.sleep(1)
    return False


def _role_rows(rows, role_prefix):
    """Return mapped nodes for one exact Slurm submission-role prefix."""
    return [
        row for row in rows if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(role_prefix)
    ]


def _unique_rows(rows):
    """Return one entry per mapped host while preserving input order."""
    unique = {}
    for row in rows:
        unique.setdefault(row["HOSTNAME"], row)
    return list(unique.values())


def _workspace_path(context, slurm_config, username: str, purpose: str):
    """Return a validated, project-configured shared job workspace."""
    storage = _shared_storage(context, slurm_config)
    run_id = str(os.environ.get("RUN_ID") or "").strip()
    if not run_id:
        run_id = "manual-" + secrets.token_hex(6)
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("RUN_ID is invalid for a shared Slurm workspace")
    if not _IDENTITY_RE.fullmatch(username) or not _PURPOSE_RE.fullmatch(purpose):
        raise ValueError("LDAP workspace identity or purpose is invalid")
    workspace = f"{storage['mount_point']}/.omnia_fvt/{run_id}/{purpose}/{username}"
    expected_prefix = f"{storage['mount_point']}/.omnia_fvt/{run_id}/"
    if not workspace.startswith(expected_prefix):
        raise ValueError("Resolved Slurm workspace escaped the configured mount")
    return storage, workspace


def _cleanup_ldap_workspace(host, control, workspace: str, username: str):
    """Remove only one validated, test-owned LDAP workspace."""
    if "/.omnia_fvt/" not in workspace or not _IDENTITY_RE.fullmatch(username):
        raise ValueError("Refusing unsafe LDAP workspace cleanup")
    quoted_workspace = shlex.quote(workspace)
    command = (
        f"if test -d {quoted_workspace}; then "
        f"find {quoted_workspace} -mindepth 1 -delete && "
        f"rmdir {quoted_workspace}; "
        "fi; "
        f"rmdir {shlex.quote(os.path.dirname(workspace))} "
        f"{shlex.quote(os.path.dirname(os.path.dirname(workspace)))} "
        "2>/dev/null || true"
    )
    remote_command(host, control, command)


def _prepare_ldap_workspace(
    host,
    context,
    slurm_config,
    control,
    rows,
    username: str,
    purpose: str,
):
    """Create and attest one LDAP-owned directory on common Slurm storage."""
    storage, workspace = _workspace_path(
        context,
        slurm_config,
        username,
        purpose,
    )
    marker = secrets.token_hex(16)
    mount_point = storage["mount_point"]
    run_root = os.path.dirname(os.path.dirname(workspace))
    purpose_root = os.path.dirname(workspace)
    marker_path = f"{workspace}/.omnia-workspace"
    command = (
        f"uid=$(id -u {shlex.quote(username)}) && "
        f"gid=$(id -g {shlex.quote(username)}) && "
        f"install -d -m 0711 {shlex.quote(f'{mount_point}/.omnia_fvt')} "
        f"{shlex.quote(run_root)} {shlex.quote(purpose_root)} && "
        f'install -d -m 0700 -o "$uid" -g "$gid" '
        f"{shlex.quote(workspace)} && "
        f"printf %s {shlex.quote(marker)} > {shlex.quote(marker_path)} && "
        f'chown "$uid:$gid" {shlex.quote(marker_path)} && '
        f"chmod 0600 {shlex.quote(marker_path)}"
    )
    created = remote_command(host, control, command)
    if created.rc != 0:
        raise RuntimeError("Could not create the shared LDAP job workspace")

    failures = []
    node_checks = []
    for row in _unique_rows([control, *rows]):
        probe_command = (
            f"source=$(findmnt -rn -T {shlex.quote(workspace)} -o SOURCE "
            "2>/dev/null || true); "
            f"marker_value=$(cat {shlex.quote(marker_path)} 2>/dev/null || true); "
            "marker_match=no; writable=no; "
            f'if test "$marker_value" = {shlex.quote(marker)}; then '
            "marker_match=yes; fi; "
            f"if runuser -u {shlex.quote(username)} -- "
            f"test -w {shlex.quote(workspace)}; then writable=yes; fi; "
            'printf \'%s|%s|%s\' "$source" "$marker_match" "$writable"; '
            f'test "$source" = {shlex.quote(storage["source"])} && '
            'test "$marker_match" = yes && test "$writable" = yes'
        )
        probe = remote_command(host, row, probe_command)
        observed_source, separator, remainder = probe.stdout.strip().partition("|")
        marker_state, second_separator, writable_state = remainder.partition("|")
        source_ok = observed_source == storage["source"]
        marker_ok = bool(separator) and marker_state == "yes"
        writable = bool(second_separator) and writable_state == "yes"
        success = probe.rc == 0 and source_ok and marker_ok and writable
        node_checks.append(
            {
                "row": row,
                "success": success,
                "source": observed_source or "not mounted",
                "source_ok": source_ok,
                "marker_ok": marker_ok,
                "writable": writable,
            }
        )
        if not success:
            failures.append(row["HOSTNAME"])
    if failures:
        _cleanup_ldap_workspace(host, control, workspace, username)
        raise RuntimeError(
            "Configured Slurm storage is not common and writable on: "
            + ", ".join(failures)
        )
    return {
        "name": storage["name"],
        "source": storage["source"],
        "mount_point": mount_point,
        "path": workspace,
        "node_checks": node_checks,
    }


def _workspace_fields(workspace_info):
    """Render concise evidence after strict per-node storage validation."""
    checks = workspace_info["node_checks"]
    passed = sum(1 for check in checks if check["success"])
    return [
        (
            "Shared job storage",
            f"✓ {workspace_info['name']} | {workspace_info['mount_point']}",
        ),
        (
            "Common mount and LDAP write access",
            f"✓ {passed}/{len(checks)} participating nodes",
        ),
    ]


def _ldap_sbatch_command(
    username: str,
    workspace: str,
    workload: str = "",
    *,
    target_node: str = "",
    wait: bool = False,
    script_path: str = "",
) -> str:
    """Build a shell-safe LDAP-owned sbatch command using shared storage."""
    if bool(workload) == bool(script_path):
        raise ValueError("Exactly one Slurm workload or script path is required")
    if script_path and (
        not script_path.startswith(f"{workspace}/") or not script_path.endswith(".sh")
    ):
        raise ValueError("Slurm job script is outside the validated workspace")
    arguments = [
        "runuser",
        "-u",
        username,
        "--",
        "sbatch",
        "--parsable",
        f"--chdir={workspace}",
        f"--output={workspace}/slurm-%j.out",
        f"--error={workspace}/slurm-%j.err",
    ]
    if wait:
        arguments.append("--wait")
    if target_node:
        if not _HOST_RE.fullmatch(target_node):
            raise ValueError("Mapped compute hostname is invalid")
        arguments.append(f"--nodelist={target_node}")
    if script_path:
        arguments.append(script_path)
    else:
        arguments.append(f"--wrap={workload}")
    return shlex.join(arguments)


def _install_pam_job_script(host, control, workspace: str, username: str):
    """Install the version-controlled PAM wait job in shared runtime storage."""
    source_path = Path(__file__).resolve().parents[1] / "vars" / "slurm_pam_job.sh"
    if not source_path.is_file():
        raise FileNotFoundError(f"PAM job script is missing: {source_path}")
    script_content = source_path.read_bytes()
    encoded = base64.b64encode(script_content).decode("ascii")
    runtime_path = f"{workspace}/slurm_pam_job.sh"
    command = (
        f"uid=$(id -u {shlex.quote(username)}) && "
        f"gid=$(id -g {shlex.quote(username)}) && "
        f"printf %s {shlex.quote(encoded)} | base64 -d > "
        f"{shlex.quote(runtime_path)} && "
        f'chown "$uid:$gid" {shlex.quote(runtime_path)} && '
        f"chmod 0700 {shlex.quote(runtime_path)}"
    )
    result = remote_command(host, control, command)
    if result.rc != 0:
        raise RuntimeError("Could not install the PAM wait-job script")
    return runtime_path


def _job_artifacts(host, control, workspace: str, job_id: str) -> tuple[str, str]:
    """Read bounded stdout and stderr produced by one shared-storage job."""
    if not job_id.isdigit() or "/.omnia_fvt/" not in workspace:
        return "", ""
    output_path = shlex.quote(f"{workspace}/slurm-{job_id}.out")
    error_path = shlex.quote(f"{workspace}/slurm-{job_id}.err")
    result = remote_command(
        host,
        control,
        f"head -c 300 {output_path} 2>/dev/null; "
        f"printf '\\n---STDERR---\\n'; head -c 300 {error_path} 2>/dev/null",
    )
    stdout, separator, stderr = result.stdout.partition("\n---STDERR---\n")
    return stdout.strip(), stderr.strip() if separator else ""


def _check_slurm_role_ldap_authentication(
    host,
    role_prefix,
    summary,
    missing_role,
    *,
    invalid_password=False,
):
    """Verify one explicit LDAP SSH credential outcome for one role."""
    try:
        context, rows, _control, _config = _context(host)
        if not rows or not context["features"].get("openldap", False):
            return _skip(summary, "OpenLDAP is not enabled")
        role_rows = _role_rows(rows, role_prefix)
        if not role_rows:
            return _skip(summary, f"No {missing_role} nodes are mapped")
        username, auth_secret = _ldap_credentials()
        credential = (
            "invalid-" + secrets.token_urlsafe(24) if invalid_password else auth_secret
        )
        outcomes = {}
        for row in role_rows:
            accepted, detail = _ldap_ssh_identity(row["ADMIN_IP"], username, credential)
            success = not accepted if invalid_password else accepted
            outcomes[row["HOSTNAME"]] = {
                "success": success,
                "accepted": accepted,
                "detail": detail,
            }
        failures = [
            name for name, outcome in outcomes.items() if not outcome["success"]
        ]
        fields = [
            ("LDAP test identity", username),
            (
                "Credential under test",
                "generated invalid password"
                if invalid_password
                else "configured LDAP password",
            ),
        ]
        grouped = {}
        for row in role_rows:
            grouped.setdefault(row["EXPECTED_FUNCTIONAL_GROUP"], []).append(row)
        for group_name, group_rows in grouped.items():
            passed = sum(
                1 for row in group_rows if outcomes[row["HOSTNAME"]]["success"]
            )
            fields.append(
                ("Functional group", f"[{group_name}] ({passed}/{len(group_rows)})")
            )
            for row in group_rows:
                outcome = outcomes[row["HOSTNAME"]]
                fields.extend(
                    [
                        (
                            f"  {row['HOSTNAME']}",
                            f"{'✓' if outcome['success'] else '✗'} {row['ADMIN_IP']}",
                        ),
                        (
                            "    Authentication request",
                            (
                                "✓ rejected as expected"
                                if invalid_password and not outcome["accepted"]
                                else "✗ unexpectedly accepted"
                                if invalid_password
                                else "✓ accepted"
                                if outcome["accepted"]
                                else "✗ rejected"
                            ),
                        ),
                        (
                            "    Verification",
                            outcome["detail"],
                        ),
                    ]
                )
        return runtime_result(
            bool(outcomes) and not failures,
            summary,
            fields,
            "LDAP authentication failed on: " + ", ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_control_ldap_authentication(host):
    """Verify a valid LDAP password on the Slurm control node."""
    return _check_slurm_role_ldap_authentication(
        host,
        SLURM_CONTROL_PREFIX,
        "Slurm control-node valid LDAP authentication",
        "Slurm control",
    )


def check_slurm_control_ldap_invalid_password(host):
    """Verify an invalid LDAP password is rejected on the control node."""
    return _check_slurm_role_ldap_authentication(
        host,
        SLURM_CONTROL_PREFIX,
        "Slurm control-node invalid LDAP password rejection",
        "Slurm control",
        invalid_password=True,
    )


def check_slurm_login_ldap_authentication(host):
    """Verify a valid LDAP password on every login node."""
    return _check_slurm_role_ldap_authentication(
        host,
        SLURM_LOGIN_PREFIX,
        "Slurm login-node valid LDAP authentication",
        "login",
    )


def check_slurm_login_ldap_invalid_password(host):
    """Verify an invalid LDAP password is rejected on every login node."""
    return _check_slurm_role_ldap_authentication(
        host,
        SLURM_LOGIN_PREFIX,
        "Slurm login-node invalid LDAP password rejection",
        "login",
        invalid_password=True,
    )


def check_slurm_compiler_ldap_authentication(host):
    """Verify a valid LDAP password on every login-compiler node."""
    return _check_slurm_role_ldap_authentication(
        host,
        SLURM_COMPILER_PREFIX,
        "Slurm login-compiler valid LDAP authentication",
        "login-compiler",
    )


def check_slurm_compiler_ldap_invalid_password(host):
    """Verify invalid LDAP passwords are rejected on login-compiler nodes."""
    return _check_slurm_role_ldap_authentication(
        host,
        SLURM_COMPILER_PREFIX,
        "Slurm login-compiler invalid LDAP password rejection",
        "login-compiler",
        invalid_password=True,
    )


def check_slurm_pam_no_job_access(host):
    """Verify LDAP compute login is denied when the user has no running job."""
    summary = "Slurm PAM no-job access policy"
    try:
        context, rows, control, _config = _context(host)
        if not rows or not context["features"].get("openldap", False):
            return _skip(summary, "OpenLDAP is not enabled")
        username, auth_secret = _ldap_credentials()
        computes = _compute_rows(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")

        active = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_user_running_jobs"] % username,
        )
        if active.rc != 0:
            raise RuntimeError("Slurm could not query existing LDAP-user jobs")
        active_jobs = [
            line.strip() for line in active.stdout.splitlines() if line.strip()
        ]
        if active_jobs:
            return runtime_result(
                False,
                summary,
                [
                    ("LDAP test identity", username),
                    ("Existing running jobs", ", ".join(active_jobs)),
                ],
                "No-job PAM behavior cannot be verified while the LDAP test user "
                "has an active job",
            )

        outcomes = {}
        for row in computes:
            allowed, _detail = _ldap_ssh_identity(
                row["ADMIN_IP"], username, auth_secret
            )
            outcomes[row["HOSTNAME"]] = (
                not allowed,
                "login denied without an active job"
                if not allowed
                else "login unexpectedly allowed",
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            [("LDAP test identity", username), *group_fields(computes, outcomes)],
            "Compute login unexpectedly allowed on: " + ", ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _wait_job_state(host, control, job_id: str, expected: str) -> tuple[bool, str]:
    deadline = time.monotonic() + SLURM_JOB_TIMEOUT_SECONDS
    last = ""
    while time.monotonic() < deadline:
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_job_state"] % (job_id, job_id),
        )
        last = result.stdout.strip()
        state = last.partition("|")[0].split("+", 1)[0].upper()
        if result.rc == 0 and state == expected.upper():
            return True, last
        if state in {"CANCELLED", "COMPLETED", "FAILED", "TIMEOUT"}:
            return False, last
        time.sleep(RECOVERY_POLL_SECONDS)
    return False, last


def _check_slurm_role_pam_job_access(
    host,
    role_prefix,
    summary,
    missing_role,
    workspace_purpose,
):
    """Verify PAM allow-during-job and deny-after-job for one role."""
    jobs: list[str] = []
    control = None
    username = ""
    workspace_info = None
    persistent_sessions = []
    try:
        if not marker_is_authorized("functional"):
            return _skip(summary, "Select the functional marker to authorize test jobs")
        context, rows, control, slurm_config = _context(host)
        if not rows or not context["features"].get("openldap", False):
            return _skip(summary, "OpenLDAP is not enabled")
        computes = _compute_rows(rows)
        submit_rows = _role_rows(rows, role_prefix)
        if not submit_rows:
            return _skip(summary, f"No {missing_role} nodes are mapped")
        if not computes:
            return _skip(summary, "At least one Slurm compute node is required")
        username, auth_secret = _ldap_credentials()
        workspace_info = _prepare_ldap_workspace(
            host,
            context,
            slurm_config,
            control,
            [*submit_rows, *computes],
            username,
            workspace_purpose,
        )
        workspace = workspace_info["path"]
        job_script = _install_pam_job_script(
            host,
            control,
            workspace,
            username,
        )

        lifecycle_results = []
        for index, submit in enumerate(submit_rows):
            compute = computes[index % len(computes)]
            if not _HOST_RE.fullmatch(compute["HOSTNAME"]):
                raise ValueError("Mapped compute hostname is invalid")
            command = _ldap_sbatch_command(
                username,
                workspace,
                target_node=compute["HOSTNAME"],
                script_path=job_script,
            )
            display_command = (
                f"runuser -u {username} -- sbatch "
                f"--nodelist={compute['HOSTNAME']} slurm_pam_job.sh"
            )
            result = remote_command(
                host,
                submit,
                command,
            )
            job_id = result.stdout.strip().split(";", 1)[0]
            submitted = result.rc == 0 and job_id.isdigit()
            session = None
            running = False
            running_state = "not submitted"
            login_detail = "job was not submitted"
            completed = False
            final_state = "not submitted"
            automatically_logged_out = False
            if submitted:
                jobs.append(job_id)
                running, running_state = _wait_job_state(
                    host,
                    control,
                    job_id,
                    "RUNNING",
                )
                if running:
                    session, login_detail = _open_ldap_persistent_session(
                        compute["ADMIN_IP"],
                        username,
                        auth_secret,
                    )
                    if session is not None:
                        persistent_sessions.append(session)
                else:
                    login_detail = "job did not reach RUNNING"
                completed, final_state = _wait_job_state(
                    host,
                    control,
                    job_id,
                    "COMPLETED",
                )
                if session is not None and completed:
                    automatically_logged_out = _wait_for_pam_session_termination(
                        session
                    )
                if session is not None:
                    _close_ldap_persistent_session(session)
                    persistent_sessions.remove(session)
            time.sleep(PAM_ACCESS_SETTLE_SECONDS)
            access_after, post_login_detail = _ldap_ssh_identity(
                compute["ADMIN_IP"], username, auth_secret
            )
            stdout, stderr = _job_artifacts(host, control, workspace, job_id)
            output_lines = [
                line.strip() for line in stdout.splitlines() if line.strip()
            ]
            output_ok = (
                "Hello, world!" in output_lines
                and "Job completed" in output_lines
                and f"Job {job_id} started on {compute['HOSTNAME']}" in output_lines
                and "Waiting 45 seconds for PAM session validation" in output_lines
            )
            success = (
                submitted
                and running
                and session is not None
                and completed
                and automatically_logged_out
                and not access_after
                and output_ok
                and not stderr
            )
            lifecycle_results.append(
                {
                    "submit": submit,
                    "compute": compute,
                    "command": display_command,
                    "job_script": os.path.basename(job_script),
                    "job_id": job_id or "missing",
                    "submitted": submitted,
                    "running": running,
                    "running_state": running_state or "unknown",
                    "login_allowed": session is not None,
                    "login_detail": login_detail,
                    "completed": completed,
                    "final_state": final_state or "unknown",
                    "automatically_logged_out": automatically_logged_out,
                    "post_login_denied": not access_after,
                    "post_login_detail": post_login_detail,
                    "stdout": stdout or "none",
                    "output_lines": output_lines,
                    "output_ok": output_ok,
                    "stderr": stderr or "none",
                    "stderr_ok": not stderr,
                    "success": success,
                }
            )
        failures = [
            result["submit"]["HOSTNAME"]
            for result in lifecycle_results
            if not result["success"]
        ]
        fields = [("LDAP test identity", username)]
        fields.extend(_workspace_fields(workspace_info))
        grouped = {}
        for lifecycle in lifecycle_results:
            grouped.setdefault(
                lifecycle["submit"]["EXPECTED_FUNCTIONAL_GROUP"],
                [],
            ).append(lifecycle)
        for group_name, group_results in grouped.items():
            passed = sum(1 for result in group_results if result["success"])
            fields.append(
                (
                    "Submission functional group",
                    f"[{group_name}] ({passed}/{len(group_results)})",
                )
            )
            for lifecycle in group_results:
                submit = lifecycle["submit"]
                compute = lifecycle["compute"]
                fields.extend(
                    [
                        (
                            f"  Submission node {submit['HOSTNAME']}",
                            f"{'✓' if lifecycle['success'] else '✗'} {submit['ADMIN_IP']}",
                        ),
                        (
                            "    Compute node",
                            f"{compute['HOSTNAME']} | {compute['ADMIN_IP']}",
                        ),
                        ("    Job script", lifecycle["job_script"]),
                        ("    Job command", lifecycle["command"]),
                        (
                            "    Job submitted",
                            (
                                f"{'✓' if lifecycle['submitted'] else '✗'} "
                                f"job ID {lifecycle['job_id']}"
                            ),
                        ),
                        (
                            "    Job reached RUNNING",
                            (
                                f"{'✓' if lifecycle['running'] else '✗'} "
                                f"{lifecycle['running_state']}"
                            ),
                        ),
                        (
                            "    LDAP login while job was running",
                            (
                                f"{'✓ allowed' if lifecycle['login_allowed'] else '✗ denied'} "
                                f"({lifecycle['login_detail']})"
                            ),
                        ),
                        (
                            "    Persistent SSH session",
                            "✓ opened and monitored"
                            if lifecycle["login_allowed"]
                            else "✗ not established",
                        ),
                        (
                            "    Job completed",
                            (
                                f"{'✓' if lifecycle['completed'] else '✗'} "
                                f"{lifecycle['final_state']}"
                            ),
                        ),
                        (
                            "    Automatic logout after job completion",
                            (
                                f"✓ session terminated within "
                                f"{PAM_SESSION_TERMINATION_TIMEOUT_SECONDS}s"
                                if lifecycle["automatically_logged_out"]
                                else (
                                    f"✗ session remained active after "
                                    f"{PAM_SESSION_TERMINATION_TIMEOUT_SECONDS}s"
                                )
                            ),
                        ),
                        (
                            "    New login after job completion",
                            (
                                "✓ denied as expected"
                                if lifecycle["post_login_denied"]
                                else "✗ unexpectedly allowed"
                            )
                            + f" ({lifecycle['post_login_detail']})",
                        ),
                    ]
                )
                fields.append(
                    (
                        "    Job output validation",
                        "✓ expected messages captured"
                        if lifecycle["output_ok"]
                        else "✗ expected messages missing",
                    )
                )
                fields.extend(
                    ("      Output", line)
                    for line in (lifecycle["output_lines"] or ["none"])
                )
                fields.append(
                    (
                        "    Error output",
                        (
                            f"{'✓' if lifecycle['stderr_ok'] else '✗'} "
                            f"{lifecycle['stderr']}"
                        ),
                    )
                )
        return runtime_result(
            bool(lifecycle_results) and not failures,
            summary,
            fields,
            "PAM active-job lifecycle failed from: " + ", ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
    finally:
        for session in persistent_sessions:
            _close_ldap_persistent_session(session)
        if control is not None:
            for job_id in jobs:
                try:
                    remote_command(
                        host,
                        control,
                        PXEBOOT_COMMANDS["slurm_cancel_job"] % job_id,
                    )
                except (OSError, RuntimeError, TypeError, ValueError):
                    pass
        if control is not None and workspace_info is not None and username:
            try:
                _cleanup_ldap_workspace(
                    host,
                    control,
                    workspace_info["path"],
                    username,
                )
            except (OSError, RuntimeError, TypeError, ValueError):
                pass


def check_slurm_control_pam_job_access(host):
    """Verify the PAM active-job lifecycle for control-node submission."""
    return _check_slurm_role_pam_job_access(
        host,
        SLURM_CONTROL_PREFIX,
        "Slurm control-node PAM active-job lifecycle",
        "Slurm control",
        "pam-control",
    )


def check_slurm_login_pam_job_access(host):
    """Verify the PAM active-job lifecycle for every login node."""
    return _check_slurm_role_pam_job_access(
        host,
        SLURM_LOGIN_PREFIX,
        "Slurm login-node PAM active-job lifecycle",
        "login",
        "pam-login",
    )


def check_slurm_compiler_pam_job_access(host):
    """Verify the PAM active-job lifecycle for every login-compiler node."""
    return _check_slurm_role_pam_job_access(
        host,
        SLURM_COMPILER_PREFIX,
        "Slurm login-compiler PAM active-job lifecycle",
        "login-compiler",
        "pam-compiler",
    )


def check_slurm_invalid_ldap_identity(host):
    """Verify a generated non-existent identity is rejected on login roles."""
    summary = "Slurm invalid LDAP identity rejection"
    try:
        context, rows, _control, _config = _context(host)
        if not rows or not context["features"].get("openldap", False):
            return _skip(summary, "OpenLDAP is not enabled")
        invalid_user = "omnia_missing_" + secrets.token_hex(6)
        allowed = _allowed_rows(rows)
        outcomes = {}
        for row in allowed:
            result = remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["ldap_missing_identity"] % invalid_user,
            )
            outcomes[row["HOSTNAME"]] = (
                result.rc != 0,
                "identity rejected" if result.rc != 0 else "unexpectedly resolved",
            )
        failed = [name for name, value in outcomes.items() if not value[0]]
        return runtime_result(
            bool(allowed) and not failed,
            summary,
            group_fields(allowed, outcomes),
            "Invalid identity resolved on: " + ", ".join(failed)
            if failed
            else ("No LDAP login roles are mapped" if not allowed else ""),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _check_slurm_role_ldap_jobs(
    host,
    role_prefix,
    summary,
    missing_role,
    workspace_purpose,
):
    """Submit one LDAP-owned job per mapped compute from every role node."""
    control = None
    username = ""
    workspace_info = None
    submitted_jobs = []
    try:
        gated = _require_functional(summary)
        if gated:
            return gated
        context, rows, control, slurm_config = _context(host)
        if not rows or not context["features"].get("openldap", False):
            return _skip(summary, "OpenLDAP is not enabled")
        submit_rows = _role_rows(rows, role_prefix)
        if not submit_rows:
            return _skip(summary, f"No {missing_role} nodes are mapped")
        computes = _compute_rows(rows)
        if not computes:
            return _skip(summary, "At least one Slurm compute node is required")
        username = _ldap_username()
        workspace_info = _prepare_ldap_workspace(
            host,
            context,
            slurm_config,
            control,
            [*submit_rows, *computes],
            username,
            workspace_purpose,
        )
        workspace = workspace_info["path"]
        submission_results = []
        failures = []
        for submit_row in submit_rows:
            target_results = []
            for compute_row in computes:
                command = _ldap_sbatch_command(
                    username,
                    workspace,
                    "hostname -s",
                    target_node=compute_row["HOSTNAME"],
                    wait=True,
                )
                result = remote_command(host, submit_row, command)
                output_lines = [
                    line.strip() for line in result.stdout.splitlines() if line.strip()
                ]
                job_id = (
                    output_lines[0].split(";", 1)[0].strip() if output_lines else ""
                )
                submitted = result.rc == 0 and job_id.isdigit()
                if job_id.isdigit():
                    submitted_jobs.append(job_id)
                completed, state_record = (
                    _wait_job_state(host, control, job_id, "COMPLETED")
                    if submitted
                    else (False, "")
                )
                state, separator, allocated_node = state_record.partition("|")
                state = state or "unavailable"
                allocated_node = allocated_node.strip() if separator else "missing"
                allocated_hostname = allocated_node.split(".", 1)[0]
                allocated_ok = allocated_hostname == compute_row["HOSTNAME"]
                stdout, stderr = _job_artifacts(
                    host,
                    control,
                    workspace,
                    job_id,
                )
                output_hostname = (
                    stdout.splitlines()[-1].split(".", 1)[0] if stdout else ""
                )
                output_ok = output_hostname == compute_row["HOSTNAME"]
                stderr_text = stderr or "none"
                success = (
                    submitted
                    and completed
                    and allocated_ok
                    and output_ok
                    and not stderr
                )
                if not success:
                    failures.append(
                        f"{submit_row['HOSTNAME']}->{compute_row['HOSTNAME']}"
                    )
                target_results.append(
                    {
                        "row": compute_row,
                        "job_id": job_id or "missing",
                        "submitted": submitted,
                        "state": state,
                        "completed": completed,
                        "allocated_node": allocated_node,
                        "allocated_ok": allocated_ok,
                        "stdout": stdout or "none",
                        "output_ok": output_ok,
                        "stderr": stderr_text,
                        "stderr_ok": not stderr,
                        "success": success,
                    }
                )
            submission_results.append(
                {
                    "row": submit_row,
                    "targets": target_results,
                    "success": bool(target_results)
                    and all(target["success"] for target in target_results),
                }
            )

        fields = [("LDAP test identity", username)]
        fields.extend(_workspace_fields(workspace_info))
        grouped = {}
        for submission in submission_results:
            grouped.setdefault(
                submission["row"]["EXPECTED_FUNCTIONAL_GROUP"],
                [],
            ).append(submission)
        for group_name, submissions in grouped.items():
            passed = sum(1 for submission in submissions if submission["success"])
            fields.append(
                (
                    "Submission functional group",
                    f"[{group_name}] ({passed}/{len(submissions)})",
                )
            )
            for submission in submissions:
                submit_row = submission["row"]
                fields.extend(
                    [
                        (
                            f"  Submission node {submit_row['HOSTNAME']}",
                            (
                                f"{'✓' if submission['success'] else '✗'} "
                                f"{submit_row['ADMIN_IP']}"
                            ),
                        ),
                        (
                            "    Targeted compute jobs",
                            (
                                f"{sum(1 for target in submission['targets'] if target['success'])}/"
                                f"{len(submission['targets'])}"
                            ),
                        ),
                        (
                            "    Job command",
                            f"runuser -u {username} -- sbatch "
                            + "--nodelist=<mapped-compute> --wrap='hostname -s'",
                        ),
                    ]
                )
                for target in submission["targets"]:
                    compute_row = target["row"]
                    fields.extend(
                        [
                            (
                                f"    Target {compute_row['HOSTNAME']}",
                                (
                                    f"{'✓' if target['success'] else '✗'} "
                                    f"{compute_row['ADMIN_IP']}"
                                ),
                            ),
                            (
                                "      Job ID",
                                f"{'✓' if target['submitted'] else '✗'} {target['job_id']}",
                            ),
                            (
                                "      Final state",
                                f"{'✓' if target['completed'] else '✗'} {target['state']}",
                            ),
                            (
                                "      Allocated node",
                                (
                                    f"{'✓' if target['allocated_ok'] else '✗'} "
                                    f"{target['allocated_node']}"
                                ),
                            ),
                            (
                                "      Standard output",
                                f"{'✓' if target['output_ok'] else '✗'} {target['stdout']}",
                            ),
                            (
                                "      Error output",
                                f"{'✓' if target['stderr_ok'] else '✗'} {target['stderr']}",
                            ),
                        ]
                    )
        return runtime_result(
            bool(submission_results) and not failures,
            summary,
            fields,
            "LDAP-user jobs failed on: " + ", ".join(failures)
            if failures
            else ("No LDAP submission roles are mapped" if not submit_rows else ""),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
    finally:
        if control is not None:
            for job_id in submitted_jobs:
                try:
                    remote_command(
                        host,
                        control,
                        PXEBOOT_COMMANDS["slurm_cancel_job"] % job_id,
                    )
                except (OSError, RuntimeError, TypeError, ValueError):
                    pass
        if control is not None and workspace_info is not None and username:
            try:
                _cleanup_ldap_workspace(
                    host,
                    control,
                    workspace_info["path"],
                    username,
                )
            except (OSError, RuntimeError, TypeError, ValueError):
                pass


def check_slurm_control_ldap_jobs(host):
    """Submit an LDAP-owned job from the Slurm control node."""
    return _check_slurm_role_ldap_jobs(
        host,
        SLURM_CONTROL_PREFIX,
        "Slurm control-node LDAP job submission",
        "Slurm control",
        "ldap-control",
    )


def check_slurm_login_ldap_jobs(host):
    """Submit an LDAP-owned job from every login node."""
    return _check_slurm_role_ldap_jobs(
        host,
        SLURM_LOGIN_PREFIX,
        "Slurm login-node LDAP job submission",
        "login",
        "ldap-login",
    )


def check_slurm_compiler_ldap_jobs(host):
    """Submit an LDAP-owned job from every login-compiler node."""
    return _check_slurm_role_ldap_jobs(
        host,
        SLURM_COMPILER_PREFIX,
        "Slurm login-compiler LDAP job submission",
        "login-compiler",
        "ldap-compiler",
    )
