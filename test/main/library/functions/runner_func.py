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
Playbook/Shell Runner — live output streaming for the main module.

Runs shell commands (omnia.sh --build, --install, etc.) and Ansible
playbooks inside omnia_core with live output streaming.

Usage::

    runner = PlaybookRunner()
    result = runner.run_shell("bash /path/to/omnia.sh --build", label="omnia.sh --build")
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

from .host_func import (
    load_test_config,
    load_test_credentials,
    is_local_execution,
)
from .formatting_func import TestLogger, Colors, Symbols
from ..vars.runner_vars import (
    DEFAULT_CONTAINER,
    DEFAULT_VERBOSITY,
    DEFAULT_TIMEOUT,
    LINE_WIDTH,
    SSH_OPTIONS,
)
from ..messages.runner_msgs import (
    RUNNER_LOG_MSGS,
    RUNNER_ASSERT_MSGS,
)

# Regex to strip ANSI escape sequences
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\r")


class PlaybookRunner:
    """Runs shell commands and Ansible playbooks with live streaming output.

    Supports two execution modes:
      - **Local mode**: Runs commands directly (when running on the OIM itself).
      - **Remote mode**: Wraps commands inside SSH via ``sshpass``.

    Args:
        container: Container name (default: ``omnia_core``).
        verbosity: Ansible verbosity level 0-4 (default: 1).
        timeout: Maximum seconds to wait for command completion (default: 7200).
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

        self._config = load_test_config()
        self._credentials = load_test_credentials()
        self._local_mode = is_local_execution()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
        """Run an Ansible playbook inside omnia_core and stream output live.

        Args:
            playbook: Absolute path to playbook inside the container.
            workdir: Working directory inside the container.
            extra_vars: Extra ``--extra-vars`` key=value pairs.
            tags: Comma-separated Ansible tags.
            skip_tags: Comma-separated Ansible skip tags.
            verbosity: Override instance verbosity for this run.
            timeout: Override instance timeout for this run.

        Returns:
            Dict with ``success``, ``rc``, ``output``, ``duration``, ``error``, ``playbook``.
        """
        v = verbosity if verbosity is not None else self._verbosity
        t = timeout if timeout is not None else self._timeout

        if workdir is None:
            workdir = os.path.dirname(playbook)

        log = TestLogger("playbook_runner")

        if not self._local_mode and not shutil.which("sshpass"):
            return self._fail(playbook, 0.0, RUNNER_ASSERT_MSGS["sshpass_missing"])

        podman_cmd = self._build_podman_cmd(playbook, workdir, v, extra_vars, tags, skip_tags)
        cmd = self._wrap_for_execution(podman_cmd)

        if self._local_mode:
            log.check(RUNNER_LOG_MSGS["connecting_local"])
        else:
            host = self._config["oim_server_ip"]
            port = self._config.get("oim_ssh_port", 22)
            log.check(RUNNER_LOG_MSGS["connecting_remote"].format(host=host, port=port))

        log.check(RUNNER_LOG_MSGS["starting_playbook"].format(playbook=playbook))
        log.check(RUNNER_LOG_MSGS["streaming_output"])

        return self._stream_execute(cmd, playbook, t)

    def run_shell(
        self,
        command: str,
        label: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run an arbitrary shell command on the OIM host with live streaming.

        Uses the same live-streaming infrastructure as ``run()`` but runs
        a raw shell command instead of an Ansible playbook. Useful for
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
        """Check if the omnia_core container is running."""
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
        password = self._credentials.get("oim_password", "")

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
        """Execute command, stream stdout live inside | borders, return result."""
        pipe_prefix = f"    {Colors.GRAY}{Symbols.PIPE}{Colors.RESET} "
        output_lines: List[str] = []
        start = time.time()
        process = None

        def _read_output():
            """Reader thread — reads lines from stdout until EOF."""
            try:
                for raw_line in process.stdout:
                    clean = _ANSI_RE.sub("", raw_line).rstrip("\n\r")
                    output_lines.append(clean)
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
                f"{Colors.BRIGHT_YELLOW}Command cancelled by user (Ctrl+C){Colors.RESET}",
                flush=True,
            )
            return self._fail(
                playbook, duration, "Command cancelled by user (Ctrl+C)",
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
                playbook, duration, "Command execution encountered an OS error",
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
