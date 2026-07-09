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

"""
Playbook Runner — runs Ansible playbooks inside omnia_core with live output.

This runner executes Ansible playbooks with live output streaming. It:
  1. Connects to OIM server (SSH or local)
  2. Runs ``podman exec omnia_core ansible-playbook <playbook>``
  3. Streams every line of output to the terminal in real-time
  4. Returns a structured result dict for pytest assertions

Usage::

    runner = PlaybookRunner()
    result = runner.run("/omnia/src/playbooks/prepare_oim/prepare_oim.yml")
    assert result["success"], result["error"]
"""

import os
import re
import shutil
import signal
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

from automation_library.core import (
    load_omnia_test_config,
    load_omnia_test_credentials,
    is_local_execution,
    get_dataset_path,
    TestLogger,
    Colors,
    Symbols,
)
from automation_library.core.functions.host_func import (
    _is_vault_encrypted,
    _create_vault_key,
    _encrypt_vault_file,
)
from automation_library.playbook_runner.vars import (
    DEFAULT_CONTAINER,
    DEFAULT_VERBOSITY,
    DEFAULT_TIMEOUT,
    LINE_WIDTH,
    CONTAINER_SSH_PORT,
    CONTAINER_INPUT_PATH,
    CREDENTIALS_FILE,
    CREDENTIALS_KEY_FILE,
    SSH_OPTIONS,
)
from automation_library.playbook_runner.messages import (
    RUNNER_LOG_MSGS,
    RUNNER_ASSERT_MSGS,
)

# Regex to strip ANSI escape sequences
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\r")


class PlaybookRunner:
    """Runs Ansible playbooks inside omnia_core container with live streaming.

    Supports two execution modes:
      - **Local mode**: Runs ``podman exec`` directly (when running on the OIM itself).
      - **Remote mode**: Wraps ``podman exec`` inside an SSH command via ``sshpass``.

    Args:
        container: Container name (default: ``omnia_core``).
        verbosity: Ansible verbosity level 0-4 (default: 1).
        timeout: Maximum seconds to wait for playbook completion (default: 7200).
    """

    def __init__(
        self,
        container: str = DEFAULT_CONTAINER,
        verbosity: int = DEFAULT_VERBOSITY,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self._container = container
        self._verbosity = verbosity
        self._timeout = timeout

        self._config = load_omnia_test_config()
        self._credentials = load_omnia_test_credentials()
        self._local_mode = is_local_execution()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync_dataset(self) -> Dict[str, Any]:
        """Sync dataset files into the omnia_core container.

        Reads ``sync_dataset_to_core`` from ``omnia_test_config.yml``.
        When enabled:
          1. Encrypts ``omnia_config_credentials.yml`` locally (if plain text)
          2. Rsyncs ``datasets/<dataset>/`` into the container at
             ``/opt/omnia/input/project_default/`` via SSH port 2222

        Since the credentials file is encrypted **before** the sync, no
        encryption step is needed inside the container afterwards.

        Returns:
            Dict with ``success`` (bool) and ``error`` (str | None).
        """
        log = TestLogger("playbook_runner")
        sync_enabled = self._config.get("sync_dataset_to_core", False)

        if not sync_enabled:
            log.info(RUNNER_LOG_MSGS["sync_skipped"])
            return {"success": True, "error": None}

        dataset_path = get_dataset_path()
        if not os.path.isdir(dataset_path):
            return {"success": False, "error": f"Dataset path not found: {dataset_path}"}

        container_password = self._credentials.get("omnia_core_password", "")
        if not container_password:
            return {"success": False, "error": "omnia_core_password not set in omnia_test_credentials.yml"}

        # Step 1: Encrypt omnia_config_credentials.yml locally before sync
        enc_result = self._encrypt_dataset_credentials(dataset_path)
        if not enc_result["success"]:
            return enc_result

        # Step 2: Rsync to container
        oim_host = "localhost" if self._local_mode else self._config["oim_server_ip"]
        log.check(RUNNER_LOG_MSGS["sync_starting"].format(dataset=os.path.basename(dataset_path)))

        ssh_opts = (
            f"sshpass -p '{container_password}' ssh -p {CONTAINER_SSH_PORT} "
            f"-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        )
        rsync_cmd = (
            f'rsync -avz -e "{ssh_opts}" '
            f'"{dataset_path}/" '
            f'"root@{oim_host}:{CONTAINER_INPUT_PATH}/"'
        )
        result = subprocess.run(
            ["bash", "-c", rsync_cmd],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            return {
                "success": False,
                "error": RUNNER_ASSERT_MSGS["sync_failed"].format(
                    rc=result.returncode, error=result.stderr.strip()
                ),
            }

        log.passed(RUNNER_LOG_MSGS["sync_completed"].format(dest=CONTAINER_INPUT_PATH))
        return {"success": True, "error": None}

    def _encrypt_dataset_credentials(self, dataset_path: str) -> Dict[str, Any]:
        """Encrypt omnia_config_credentials.yml in the dataset folder before sync.

        Uses the same vault helper functions from ``automation_library.core``
        that handle ``omnia_test_credentials.yml`` encryption.

        Logic:
          - If the file does not exist → nothing to do.
          - If the file is already vault-encrypted → nothing to do.
          - If the file is plain text → create a vault key (if missing)
            and encrypt the file in-place.

        Args:
            dataset_path: Absolute path to the dataset folder.

        Returns:
            Dict with ``success`` (bool) and ``error`` (str | None).
        """
        log = TestLogger("playbook_runner")

        cred_path = os.path.join(dataset_path, CREDENTIALS_FILE)
        key_path = os.path.join(dataset_path, CREDENTIALS_KEY_FILE)

        if not os.path.exists(cred_path):
            return {"success": True, "error": None}

        if _is_vault_encrypted(cred_path):
            return {"success": True, "error": None}

        log.check(RUNNER_LOG_MSGS["encrypt_starting"])

        try:
            if not os.path.exists(key_path):
                _create_vault_key(key_path)
            _encrypt_vault_file(cred_path, key_path)
        except Exception as exc:
            return {
                "success": False,
                "error": RUNNER_ASSERT_MSGS["encrypt_failed"].format(error=str(exc)),
            }

        log.passed(RUNNER_LOG_MSGS["encrypt_completed"])
        return {"success": True, "error": None}

    def run(
        self,
        playbook: str,
        workdir: Optional[str] = None,
        extra_vars: Optional[Dict[str, str]] = None,
        tags: Optional[str] = None,
        skip_tags: Optional[str] = None,
        verbosity: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run an Ansible playbook and stream output live.

        Args:
            playbook: Absolute path to playbook **inside** the container
                      (e.g. ``/omnia/src/playbooks/prepare_oim/prepare_oim.yml``).
            workdir: Working directory inside the container.
                     Defaults to the playbook's parent directory.
            extra_vars: Extra ``--extra-vars`` key=value pairs.
            tags: Comma-separated Ansible tags (``--tags``).
            skip_tags: Comma-separated Ansible skip tags (``--skip-tags``).
            verbosity: Override instance verbosity for this run.
            timeout: Override instance timeout for this run.

        Returns:
            Dict with keys:
              - ``success`` (bool): True if playbook exited with rc 0.
              - ``rc`` (int): Process return code.
              - ``output`` (str): Full captured output.
              - ``duration`` (float): Wall-clock seconds.
              - ``error`` (str | None): Error description on failure.
              - ``playbook`` (str): The playbook path that was run.
        """
        v = verbosity if verbosity is not None else self._verbosity
        t = timeout if timeout is not None else self._timeout

        if workdir is None:
            workdir = os.path.dirname(playbook)

        log = TestLogger("playbook_runner")

        # --- Pre-flight checks ---------------------------------------------------
        if not self._local_mode and not shutil.which("sshpass"):
            return self._fail(playbook, 0.0, RUNNER_ASSERT_MSGS["sshpass_missing"])

        # --- Build command --------------------------------------------------------
        podman_cmd = self._build_podman_cmd(playbook, workdir, v, extra_vars, tags, skip_tags)
        cmd = self._wrap_for_execution(podman_cmd)

        # --- Log start ------------------------------------------------------------
        if self._local_mode:
            log.check(RUNNER_LOG_MSGS["connecting_local"])
        else:
            host = self._config["oim_server_ip"]
            port = self._config.get("oim_ssh_port", 22)
            log.check(RUNNER_LOG_MSGS["connecting_remote"].format(host=host, port=port))

        log.check(RUNNER_LOG_MSGS["starting_playbook"].format(playbook=playbook))
        log.check(RUNNER_LOG_MSGS["streaming_output"])

        # --- Execute with live streaming ------------------------------------------
        return self._stream_execute(cmd, playbook, t)

    def run_shell(
        self,
        command: str,
        label: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run an arbitrary shell command on the OIM host with live streaming.

        Uses the same live-streaming infrastructure as ``run()`` but runs
        a raw shell command instead of an Ansible playbook.  Useful for
        ``omnia.sh --build``, ``omnia.sh --install``, etc.

        Args:
            command: Shell command to execute on the OIM host.
            label: Human-readable label for logging (defaults to *command*).
            timeout: Maximum seconds to wait (defaults to instance timeout).

        Returns:
            Dict with ``success``, ``rc``, ``output``, ``duration``, ``error``.
        """
        t = timeout if timeout is not None else self._timeout
        display = label or command
        log = TestLogger("shell_runner")

        if not self._local_mode and not shutil.which("sshpass"):
            return self._fail(display, 0.0, RUNNER_ASSERT_MSGS["sshpass_missing"])

        cmd = self._wrap_for_execution(command)

        if self._local_mode:
            log.check(RUNNER_LOG_MSGS["connecting_local"])
        else:
            host = self._config["oim_server_ip"]
            port = self._config.get("oim_ssh_port", 22)
            log.check(RUNNER_LOG_MSGS["connecting_remote"].format(host=host, port=port))

        log.check(RUNNER_LOG_MSGS["starting_shell"].format(command=display))
        log.check(RUNNER_LOG_MSGS["streaming_output"])

        return self._stream_execute(cmd, display, t)

    def check_container(self) -> bool:
        """Check if the omnia_core container is running.

        Returns:
            True if the container is running.
        """
        check_cmd = (
            f"podman ps --format '{{{{.Names}}}}' "
            f"--filter name={self._container} | grep -q {self._container}"
        )
        cmd = self._wrap_for_execution(check_cmd)

        try:
            process = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True, text=True, timeout=30
            )
            return process.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_podman_cmd(
        self,
        playbook: str,
        workdir: str,
        verbosity: int,
        extra_vars: Optional[Dict[str, str]],
        tags: Optional[str],
        skip_tags: Optional[str],
    ) -> str:
        """Build the ``podman exec ... ansible-playbook`` command string."""
        playbook_name = os.path.basename(playbook)
        v_flag = f" -{('v' * verbosity)}" if verbosity > 0 else ""

        parts = [
            "podman", "exec",
            f"-w {workdir}",
            self._container,
            f"ansible-playbook {playbook_name}{v_flag}",
        ]

        if extra_vars:
            for key, val in extra_vars.items():
                parts.append(f'--extra-vars "{key}={val}"')
        if tags:
            parts.append(f"--tags {tags}")
        if skip_tags:
            parts.append(f"--skip-tags {skip_tags}")

        return " ".join(parts)

    def _wrap_for_execution(self, cmd: str) -> str:
        """Wrap command for local or remote (SSH) execution."""
        if self._local_mode:
            return cmd

        host = self._config["oim_server_ip"]
        user = self._config.get("oim_ssh_user", "root")
        port = str(self._config.get("oim_ssh_port", 22))
        password = self._credentials.get("oim_ssh_password", "")

        ssh_parts = [
            "sshpass", f"-p '{password}'",
            "ssh", "-tt",
        ] + SSH_OPTIONS + [
            "-p", port,
            f"{user}@{host}",
            f"'{cmd}'",
        ]
        return " ".join(ssh_parts)

    def _stream_execute(
        self, cmd: str, playbook: str, timeout: int
    ) -> Dict[str, Any]:
        """Execute command, stream stdout live inside ``|`` borders, return result.

        Architecture:
          - A **daemon reader thread** reads stdout and prints each line
            with the ``|`` prefix, stripping ANSI codes and folding
            long lines across multiple ``|`` lines.
          - The **main thread** calls ``process.wait(timeout)`` which is
            interruptible by ``KeyboardInterrupt`` (Ctrl+C).
          - On Ctrl+C the entire process group is killed with SIGKILL
            for an immediate stop -- no dangling ansible processes.
        """
        pipe_prefix = f"    {Colors.GRAY}{Symbols.PIPE}{Colors.RESET} "
        output_lines: List[str] = []
        start = time.time()
        process = None

        def _read_output():
            """Reader thread -- reads lines from stdout until EOF."""
            try:
                for raw_line in process.stdout:
                    clean = _ANSI_RE.sub("", raw_line).rstrip("\n\r")
                    output_lines.append(clean)
                    # Fold long lines across multiple | lines
                    if not clean:
                        print(pipe_prefix, flush=True)
                        continue
                    while clean:
                        chunk = clean[:LINE_WIDTH]
                        clean = clean[LINE_WIDTH:]
                        print(f"{pipe_prefix}{chunk}", flush=True)
            except (ValueError, OSError):
                pass

        try:
            process = subprocess.Popen(
                ["bash", "-c", cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                text=True,
                preexec_fn=os.setsid,
            )

            reader = threading.Thread(target=_read_output, daemon=True)
            reader.start()

            process.wait(timeout=timeout)
            reader.join(timeout=5)

            duration = time.time() - start
            rc = process.returncode

            if rc == 0:
                return {
                    "success": True,
                    "rc": rc,
                    "output": "\n".join(output_lines),
                    "duration": duration,
                    "error": None,
                    "playbook": playbook,
                }

            return self._fail(
                playbook,
                duration,
                RUNNER_ASSERT_MSGS["playbook_failed"].format(
                    playbook=playbook, rc=rc, duration=duration
                ),
                rc=rc,
                output="\n".join(output_lines),
            )

        except KeyboardInterrupt:
            duration = time.time() - start
            self._kill_process_group(process)
            print(
                f"\n{pipe_prefix}"
                f"{Colors.BRIGHT_YELLOW}Playbook cancelled by user (Ctrl+C){Colors.RESET}",
                flush=True,
            )
            return self._fail(
                playbook, duration, "Playbook cancelled by user (Ctrl+C)",
                rc=-2, output="\n".join(output_lines),
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start
            self._kill_process_group(process)
            return self._fail(
                playbook,
                duration,
                RUNNER_ASSERT_MSGS["playbook_timeout"].format(
                    playbook=playbook, timeout=timeout
                ),
                rc=-1,
                output="\n".join(output_lines),
            )

        except OSError:
            duration = time.time() - start
            self._kill_process_group(process)
            return self._fail(
                playbook, duration, "Playbook execution encountered an OS error",
                rc=-1, output="\n".join(output_lines),
            )

        finally:
            self._cleanup_process(process)

    @staticmethod
    def _kill_process_group(process):
        """Kill the entire process group with SIGKILL for immediate stop."""
        if process is None:
            return
        try:
            pgid = os.getpgid(process.pid)
            os.killpg(pgid, signal.SIGKILL)
        except OSError:
            pass
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=3)
        except (subprocess.TimeoutExpired, OSError):
            pass

    @staticmethod
    def _cleanup_process(process):
        """Close all open streams on a process."""
        if process is None:
            return
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream and not stream.closed:
                try:
                    stream.close()
                except OSError:
                    pass

    @staticmethod
    def _fail(
        playbook: str,
        duration: float,
        error: str,
        rc: int = -1,
        output: str = "",
    ) -> Dict[str, Any]:
        """Build a failure result dict."""
        return {
            "success": False,
            "rc": rc,
            "output": output,
            "duration": duration,
            "error": error,
            "playbook": playbook,
        }


def run_playbook(
    playbook: str,
    workdir: Optional[str] = None,
    extra_vars: Optional[Dict[str, str]] = None,
    tags: Optional[str] = None,
    skip_tags: Optional[str] = None,
    verbosity: int = DEFAULT_VERBOSITY,
    timeout: int = DEFAULT_TIMEOUT,
    container: str = DEFAULT_CONTAINER,
) -> Dict[str, Any]:
    """Convenience function -- create a runner and execute a playbook.

    See :meth:`PlaybookRunner.run` for argument details.
    """
    runner = PlaybookRunner(container=container, verbosity=verbosity, timeout=timeout)
    return runner.run(
        playbook,
        workdir=workdir,
        extra_vars=extra_vars,
        tags=tags,
        skip_tags=skip_tags,
    )
