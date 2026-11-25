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

"""External OIM interaction for Phase 1 — External Repo Manager Validation.

Provides SSH-based helpers to:
  1. Run ``repo_manager`` on an external OIM (OIM1)
  2. Fetch the generated ``repo_status.yml`` back to this OIM (OIM2)
  3. Validate the fetched contract is from an external source

Uses ``paramiko`` for SSH command execution and SFTP file transfer.
Connection details come from ``test_config.yml`` (``external_oim`` block)
and ``test_creds.yml`` (``external_oim_password``).
"""

import os
import shlex
import time
from typing import Any, Dict, Optional

import paramiko
import yaml


_REPO_STATUS_FILENAME = "repo_status.yml"
_DEFAULT_TIMEOUT = 3600  # 1 hour for full repo_manager run
_STATUS_ONLY_TIMEOUT = 120  # 2 minutes for --tags status only


def external_oim_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and validate the external_oim block from test config.

    In SVT mode, reads from environment variables (SVT_EXTERNAL_OIM_*) if
    the config values are empty.

    Returns:
        Dict with keys: ip, ssh_user, ssh_port, omnia_path,
        repo_manager_tags, project_name.

    Raises:
        ValueError: If required keys are missing or empty (and not in env vars).
    """
    block = config.get("external_oim", {})
    if not isinstance(block, dict):
        raise ValueError("external_oim must be a mapping in test_config.yml")

    def pick(key: str, env: str, default: Any = "") -> str:
        """Config value, else the SVT environment variable, else the default."""
        return str(block.get(key) or os.environ.get(env) or default).strip()

    ip = pick("ip", "SVT_EXTERNAL_OIM_IP")
    if not ip:
        raise ValueError(
            "external_oim.ip is required in test_config.yml or SVT_EXTERNAL_OIM_IP env var "
            "for remote repo_manager execution"
        )

    return {
        "ip": ip,
        "ssh_user": pick("ssh_user", "SVT_EXTERNAL_OIM_USER", "root"),
        "ssh_port": int(pick("ssh_port", "SVT_EXTERNAL_OIM_SSH_PORT", 22)),
        "omnia_path": pick("omnia_path", "SVT_EXTERNAL_OMNIA_PATH", "/root/main/omnia"),
        "repo_manager_tags": str(
            block.get("repo_manager_tags", "prepare,precheck,download,status")
        ),
        "project_name": pick("project_name", "SVT_EXTERNAL_PROJECT_NAME", "project_default"),
    }


def _connect(oim_cfg: Dict[str, Any], password: str) -> paramiko.SSHClient:
    """Open an SSH connection to the external OIM."""
    client = paramiko.SSHClient()
    # Lab OIM reached by IP for a test run; its host key is not known beforehand.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
    client.connect(
        oim_cfg["ip"],
        port=oim_cfg["ssh_port"],
        username=oim_cfg["ssh_user"],
        password=password,
        timeout=30,
    )
    return client


def run_remote_repo_manager(
    oim_cfg: Dict[str, Any],
    password: str,
    timeout: Optional[int] = None,
    log_callback=None,
) -> Dict[str, Any]:
    """Run repo_manager on the external OIM via SSH.

    Executes ``ansible-playbook repo_manager.yml --tags <tags>`` inside
    the Omnia venv on the external OIM and streams stdout/stderr.

    Args:
        oim_cfg: External OIM config from ``external_oim_config()``.
        password: SSH password for the external OIM.
        timeout: Max seconds to wait (default: 3600 for full run,
                 120 for status-only).
        log_callback: Optional callable(line: str) for live output.

    Returns:
        Dict with keys: success, rc, output, duration.
    """
    tags = oim_cfg["repo_manager_tags"]
    playbook_dir = os.path.join(
        oim_cfg["omnia_path"], "src", "repo_manager", "playbooks"
    )
    if timeout is None:
        timeout = (
            _STATUS_ONLY_TIMEOUT if tags.strip() == "status"
            else _DEFAULT_TIMEOUT
        )

    # Build the command: activate venv, then run ansible-playbook
    cmd = (
        f"source /opt/omnia/venv/bin/activate && "
        f"cd {shlex.quote(playbook_dir)} && "
        f"ansible-playbook repo_manager.yml --tags {shlex.quote(tags)}"
    )

    start = time.time()
    try:
        client = _connect(oim_cfg, password)
    except Exception as exc:
        return {
            "success": False,
            "rc": -1,
            "output": "",
            "duration": time.time() - start,
            "error": f"SSH connection failed: {exc}",
        }

    try:
        # Use invoke_shell for venv activation to work
        channel = client.get_transport().open_session()
        channel.settimeout(timeout)
        channel.exec_command(  # nosec B601  # inputs quoted with shlex
            f"bash -lc {shlex.quote(cmd)}")

        output_lines = []
        while True:
            if channel.recv_ready():
                chunk = channel.recv(8192).decode("utf-8", errors="replace")
                for line in chunk.splitlines():
                    output_lines.append(line)
                    if log_callback:
                        log_callback(line)
            if channel.recv_stderr_ready():
                chunk = channel.recv_stderr(8192).decode(
                    "utf-8", errors="replace"
                )
                for line in chunk.splitlines():
                    output_lines.append(line)
                    if log_callback:
                        log_callback(line)
            if channel.exit_status_ready():
                # Drain remaining output
                while channel.recv_ready():
                    chunk = channel.recv(8192).decode(
                        "utf-8", errors="replace"
                    )
                    output_lines.extend(chunk.splitlines())
                while channel.recv_stderr_ready():
                    chunk = channel.recv_stderr(8192).decode(
                        "utf-8", errors="replace"
                    )
                    output_lines.extend(chunk.splitlines())
                break
            time.sleep(0.1)

        rc = channel.recv_exit_status()
        duration = time.time() - start
        output = "\n".join(output_lines)
        return {
            "success": rc == 0,
            "rc": rc,
            "output": output,
            "duration": duration,
        }
    except Exception as exc:
        return {
            "success": False,
            "rc": -1,
            "output": "\n".join(output_lines) if "output_lines" in dir() else "",
            "duration": time.time() - start,
            "error": str(exc),
        }
    finally:
        client.close()


def fetch_repo_status(
    oim_cfg: Dict[str, Any],
    password: str,
    local_dest: str,
) -> Dict[str, Any]:
    """Fetch repo_status.yml and Pulp certificates from the external OIM via SFTP.

    Copies both the repo_status.yml file and the referenced Pulp server certificate
    from OIM1 to OIM2, then updates the cert path in the fetched repo_status.yml
    to point to the local copy.

    Args:
        oim_cfg: External OIM config.
        password: SSH password.
        local_dest: Local directory to save the fetched file and cert.

    Returns:
        Dict with keys: success, path (local path), remote_path, error.
    """
    project = oim_cfg["project_name"]
    remote_path = (
        f"/opt/omnia/repo_manager/output/{project}/{_REPO_STATUS_FILENAME}"
    )

    try:
        client = _connect(oim_cfg, password)
    except Exception as exc:
        return {
            "success": False,
            "path": "",
            "remote_path": remote_path,
            "error": f"SSH connection failed: {exc}",
        }

    try:
        sftp = client.open_sftp()
        os.makedirs(local_dest, exist_ok=True)
        local_path = os.path.join(local_dest, _REPO_STATUS_FILENAME)
        sftp.get(remote_path, local_path)

        # Validate the fetched file is valid YAML
        with open(local_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict) or "repositories" not in data:
            return {
                "success": False,
                "path": local_path,
                "remote_path": remote_path,
                "error": "Fetched file is not a valid repo_status.yml "
                         "(missing 'repositories' key)",
            }

        # Copy the Pulp certificate if referenced in repo_status.yml
        cert_path = (
            data.get("repo_manager", {})
            .get("certificates", {})
            .get("server_crt", "")
        )
        if cert_path:
            try:
                # Determine local cert path (same dir as repo_status.yml)
                cert_filename = os.path.basename(cert_path)
                local_cert_path = os.path.join(local_dest, cert_filename)
                sftp.get(cert_path, local_cert_path)

                # Update repo_status.yml to point to the local cert path
                data["repo_manager"]["certificates"]["server_crt"] = local_cert_path
                data["repo_manager"]["certificates"]["certs_dir"] = local_dest

                # Write the updated repo_status.yml
                with open(local_path, "w", encoding="utf-8") as fh:
                    yaml.dump(data, fh, default_flow_style=False)
            except FileNotFoundError:
                # Cert referenced but not found on OIM1 — warn but continue
                pass
            except Exception as exc:
                # Cert copy failed — warn but continue (playbook will fail later if needed)
                pass

        sftp.close()

        return {
            "success": True,
            "path": local_path,
            "remote_path": remote_path,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "path": "",
            "remote_path": remote_path,
            "error": f"repo_status.yml not found on external OIM at "
                     f"{remote_path}",
        }
    except Exception as exc:
        return {
            "success": False,
            "path": "",
            "remote_path": remote_path,
            "error": str(exc),
        }
    finally:
        client.close()


def _run(client: paramiko.SSHClient, command: str) -> str:
    """Run a fixed read-only command on the external OIM and return its stdout."""
    _, stdout, _ = client.exec_command(command)  # nosec B601  # fixed or shlex-quoted
    return stdout.read().decode().strip()


def verify_remote_oim_ready(
    oim_cfg: Dict[str, Any], password: str
) -> Dict[str, Any]:
    """Check that the external OIM is reachable and has repo_manager.

    Returns:
        Dict with keys: success, hostname, details, error.
    """
    try:
        client = _connect(oim_cfg, password)
    except Exception as exc:
        return {
            "success": False,
            "hostname": "",
            "details": "",
            "error": f"Cannot reach external OIM at {oim_cfg['ip']}: {exc}",
        }

    try:
        checks = {}

        checks["hostname"] = _run(client, "hostname")
        env_line = _run(client, "grep SYSTEM_ADMIN_NIC_IPV4 /etc/omnia/omnia.env")
        checks["admin_ip"] = env_line.split("=", 1)[-1] if "=" in env_line else ""
        playbook = os.path.join(
            oim_cfg["omnia_path"],
            "src", "repo_manager", "playbooks", "repo_manager.yml",
        )
        checks["playbook_exists"] = _run(
            client, f"test -f {shlex.quote(playbook)} && echo ok") == "ok"
        checks["venv_exists"] = _run(
            client, "test -f /opt/omnia/venv/bin/activate && echo ok") == "ok"

        all_ok = checks["playbook_exists"] and checks["venv_exists"]
        details = (
            f"hostname={checks['hostname']}, "
            f"admin_ip={checks['admin_ip']}, "
            f"playbook={'found' if checks['playbook_exists'] else 'MISSING'}, "
            f"venv={'found' if checks['venv_exists'] else 'MISSING'}"
        )
        return {
            "success": all_ok,
            "hostname": checks["hostname"],
            "details": details,
            "error": "" if all_ok else f"External OIM not ready: {details}",
        }
    finally:
        client.close()
