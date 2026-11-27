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

"""External OIM helpers for the external repo_manager contract (paramiko SSH and SFTP).

Run ``repo_manager`` on an external OIM (OIM1), fetch its ``repo_status.yml`` and Pulp
certificate to this OIM (OIM2), and check that the external OIM is ready. Connection
details come from the ``external_oim`` block of ``test_config.yml`` (or the
``SVT_EXTERNAL_*`` variables) and ``external_oim_password`` of ``test_creds.yml``.
"""

import os
import shlex
import time
from typing import Any, Dict, Optional

import paramiko
import yaml

_REPO_STATUS_FILENAME = "repo_status.yml"
_DEFAULT_TIMEOUT = 3600  # full repo_manager run
_STATUS_ONLY_TIMEOUT = 120  # --tags status only
_OMNIA_ENV_FILE = "/etc/omnia/omnia.env"
_SSH_ERRORS = (paramiko.SSHException, OSError)


def external_oim_secret() -> str:
    """Return the external OIM SSH secret from test_creds.yml or SVT_EXTERNAL_OIM_PASS."""
    from library.functions import load_test_credentials  # pylint: disable=import-outside-toplevel
    return (load_test_credentials().get("external_oim_password") or
            os.environ.get("SVT_EXTERNAL_OIM_PASS", ""))


def external_oim_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return the validated ``external_oim`` settings (config value, else SVT env, else default).

    Raises:
        ValueError: If ``external_oim`` is not a mapping or has no ``ip``.
    """
    block = config.get("external_oim", {})
    if not isinstance(block, dict):
        raise ValueError("external_oim must be a mapping in test_config.yml")

    def pick(key: str, env: str, default: Any = "") -> str:
        return str(block.get(key) or os.environ.get(env) or default).strip()

    ip = pick("ip", "SVT_EXTERNAL_OIM_IP")
    omnia_path = pick("omnia_path", "SVT_EXTERNAL_OMNIA_PATH")
    if not ip or not omnia_path:
        raise ValueError(
            "external_oim.ip and external_oim.omnia_path are required in test_config.yml "
            "(or SVT_EXTERNAL_OIM_IP / SVT_EXTERNAL_OMNIA_PATH) for remote repo_manager execution"
        )
    return {
        "ip": ip,
        "ssh_user": pick("ssh_user", "SVT_EXTERNAL_OIM_USER", "root"),
        "ssh_port": int(pick("ssh_port", "SVT_EXTERNAL_OIM_SSH_PORT", 22)),
        "omnia_path": omnia_path,
        "repo_manager_tags": str(
            block.get("repo_manager_tags", "prepare,precheck,download,status")),
        "project_name": pick("project_name", "SVT_EXTERNAL_PROJECT_NAME", "project_default"),
    }


def _connect(oim_cfg: Dict[str, Any], password: str) -> paramiko.SSHClient:
    """Open an SSH connection to the external OIM."""
    client = paramiko.SSHClient()
    # Lab OIM reached by IP for a test run; its host key is not known beforehand.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
    client.connect(oim_cfg["ip"], port=oim_cfg["ssh_port"], username=oim_cfg["ssh_user"],
                   password=password, timeout=30)
    return client


def _run(client: paramiko.SSHClient, command: str) -> str:
    """Run a fixed read-only command on the external OIM and return its stdout."""
    _, stdout, _ = client.exec_command(command)  # nosec B601  # fixed or shlex-quoted
    return stdout.read().decode().strip()


def _remote_env(client: paramiko.SSHClient) -> Dict[str, str]:
    """Return the KEY=value pairs of the external OIM's omnia.env."""
    env = {}
    for line in _run(client, f"cat {_OMNIA_ENV_FILE}").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            env[key.strip()] = value.strip().strip("\"'")
    return env


def _venv_activate(env: Dict[str, str]) -> str:
    """Return the activate script of the external OIM's Omnia venv."""
    venv = env.get("OMNIA_VENV_PATH") or os.path.join(env.get("OMNIA_DATA_PATH", ""), "venv")
    return os.path.join(venv, "bin", "activate")


def run_remote_repo_manager(
    oim_cfg: Dict[str, Any],
    password: str,
    timeout: Optional[int] = None,
    log_callback=None,
) -> Dict[str, Any]:
    """Run ``repo_manager.yml --tags <tags>`` in the Omnia venv of the external OIM.

    ``log_callback(line)`` receives the live output. Returns
    ``{success, rc, output, duration[, error]}``.
    """
    tags = oim_cfg["repo_manager_tags"]
    playbook_dir = os.path.join(oim_cfg["omnia_path"], "src", "repo_manager", "playbooks")
    if timeout is None:
        timeout = _STATUS_ONLY_TIMEOUT if tags.strip() == "status" else _DEFAULT_TIMEOUT

    start, lines = time.time(), []

    def outcome(rc: int, error: str = "") -> Dict[str, Any]:
        out = {"success": rc == 0, "rc": rc, "output": "\n".join(lines),
               "duration": time.time() - start}
        return {**out, "error": error} if error else out

    def emit(raw: bytes) -> None:
        for line in raw.decode("utf-8", errors="replace").splitlines():
            lines.append(line)
            if log_callback:
                log_callback(line)

    try:
        client = _connect(oim_cfg, password)
    except _SSH_ERRORS as exc:
        return outcome(-1, f"SSH connection failed: {exc}")
    try:
        env = _remote_env(client)
        if not env.get("OMNIA_DATA_PATH") and not env.get("OMNIA_VENV_PATH"):
            return outcome(-1, f"no OMNIA_DATA_PATH or OMNIA_VENV_PATH in {_OMNIA_ENV_FILE}")
        cmd = (f"source {shlex.quote(_venv_activate(env))} && cd {shlex.quote(playbook_dir)} && "
               f"ansible-playbook repo_manager.yml --tags {shlex.quote(tags)}")
        channel = client.get_transport().open_session()
        channel.settimeout(timeout)
        channel.exec_command(  # nosec B601  # inputs quoted with shlex
            f"bash -lc {shlex.quote(cmd)}")
        while not channel.exit_status_ready():
            if channel.recv_ready():
                emit(channel.recv(8192))
            if channel.recv_stderr_ready():
                emit(channel.recv_stderr(8192))
            time.sleep(0.1)
        while channel.recv_ready():
            emit(channel.recv(8192))
        while channel.recv_stderr_ready():
            emit(channel.recv_stderr(8192))
        return outcome(channel.recv_exit_status())
    except _SSH_ERRORS as exc:
        return outcome(-1, str(exc))
    finally:
        client.close()


def fetch_repo_status(
    oim_cfg: Dict[str, Any],
    password: str,
    local_dest: str,
) -> Dict[str, Any]:
    """Fetch repo_status.yml and its Pulp certificate from the external OIM by SFTP.

    The local repo_status.yml is rewritten to name the local copy of the certificate.
    Returns ``{success, path, remote_path[, error]}``.
    """
    remote_path = ""

    def outcome(error: str = "", path: str = "") -> Dict[str, Any]:
        out = {"success": not error, "path": path, "remote_path": remote_path}
        return {**out, "error": error} if error else out

    try:
        client = _connect(oim_cfg, password)
    except _SSH_ERRORS as exc:
        return outcome(f"SSH connection failed: {exc}")
    try:
        data_path = _remote_env(client).get("OMNIA_DATA_PATH", "")
        if not data_path:
            return outcome(f"no OMNIA_DATA_PATH in {_OMNIA_ENV_FILE} on the external OIM")
        remote_path = os.path.join(data_path, "repo_manager", "output",
                                   oim_cfg["project_name"], _REPO_STATUS_FILENAME)
        sftp = client.open_sftp()
        os.makedirs(local_dest, exist_ok=True)
        local_path = os.path.join(local_dest, _REPO_STATUS_FILENAME)
        try:
            sftp.get(remote_path, local_path)
        except FileNotFoundError:
            return outcome(f"repo_status.yml not found on external OIM at {remote_path}")
        with open(local_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict) or "repositories" not in data:
            return outcome("Fetched file is not a valid repo_status.yml "
                           "(missing 'repositories' key)", local_path)

        certs = data.get("repo_manager", {}).get("certificates", {})
        if certs.get("server_crt"):
            local_cert = os.path.join(local_dest, os.path.basename(certs["server_crt"]))
            try:
                sftp.get(certs["server_crt"], local_cert)
            except OSError:
                local_cert = ""  # not on OIM1: keep going, the playbook fails later if needed
            if local_cert:
                certs["server_crt"], certs["certs_dir"] = local_cert, local_dest
                with open(local_path, "w", encoding="utf-8") as fh:
                    yaml.dump(data, fh, default_flow_style=False)
        sftp.close()
        return outcome(path=local_path)
    except (*_SSH_ERRORS, yaml.YAMLError) as exc:
        return outcome(str(exc))
    finally:
        client.close()


def verify_remote_oim_ready(
    oim_cfg: Dict[str, Any], password: str
) -> Dict[str, Any]:
    """Check that the external OIM is reachable and has repo_manager and the Omnia venv.

    Returns ``{success, hostname, details, error}``.
    """
    try:
        client = _connect(oim_cfg, password)
    except _SSH_ERRORS as exc:
        return {"success": False, "hostname": "", "details": "",
                "error": f"Cannot reach external OIM at {oim_cfg['ip']}: {exc}"}
    try:
        hostname = _run(client, "hostname")
        env = _remote_env(client)
        playbook = os.path.join(oim_cfg["omnia_path"], "src", "repo_manager", "playbooks",
                                "repo_manager.yml")
        playbook_ok = _run(client, f"test -f {shlex.quote(playbook)} && echo ok") == "ok"
        venv_ok = _run(client, f"test -f {shlex.quote(_venv_activate(env))} && echo ok") == "ok"
    finally:
        client.close()
    details = (f"hostname={hostname}, admin_ip={env.get('SYSTEM_ADMIN_NIC_IPV4', '')}, "
               f"playbook={'found' if playbook_ok else 'MISSING'}, "
               f"venv={'found' if venv_ok else 'MISSING'}, "
               f"data_path={env.get('OMNIA_DATA_PATH') or 'MISSING'}")
    ok = playbook_ok and venv_ok and bool(env.get("OMNIA_DATA_PATH"))
    return {"success": ok, "hostname": hostname, "details": details,
            "error": "" if ok else f"External OIM not ready: {details}"}
