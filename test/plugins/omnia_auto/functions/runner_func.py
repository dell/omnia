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
run_playbook — subprocess-based playbook execution with live streaming.

Runs ``ansible-playbook`` directly via subprocess on the target host
(bare-metal, no container exec) with live output streaming.  For remote
hosts the command is wrapped in SSH.

Output is read line-by-line in the calling thread — **no reader threads
are spawned**.  A lightweight ``threading.Timer`` enforces the timeout.

Usage::

    result = run_playbook(tag="prepare")
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
from ..vars.common_vars import get_setting
from ..messages.runner_msgs import (
    RUNNER_LOG_MSGS,
    RUNNER_ASSERT_MSGS,
)

_ANSI_RE = re.compile(
    r"\x1b\[[0-9;]*[a-zA-Z]"
    r"|\x1b\][^\x07]*\x07"
    r"|\x1b\([A-Z]"
    r"|[\x00-\x08\x0e-\x1f]"
    r"|\r"
)


# =====================================================================
# PUBLIC API
# =====================================================================

def run_playbook(
    playbook: Optional[str] = None,
    tag = None,
    extra_vars: Optional[Dict[str, str]] = None,
    verbosity: Optional[int] = None,
    timeout: Optional[int] = None,
    limit: Optional[str] = None,
    playbook_workdir: Optional[str] = None,
) -> Dict[str, Any]:
    """Run an ansible-playbook with live output streaming.

    Builds the ``ansible-playbook`` command, wraps it in SSH for remote
    targets, and streams output line-by-line in the calling thread.

    Args:
        playbook: Playbook filename (e.g. ``image_build_manager.yml``).
        tag: Ansible tag(s). Accepts a single string
             (``"prepare"``), a list (``["prepare", "build"]``),
             or ``None`` to run without ``--tags``.
        extra_vars: Extra ``-e key=value`` pairs.
        verbosity: Ansible verbosity 0-4.
        timeout: Max seconds to wait.
        limit: Ansible ``--limit`` pattern.
        playbook_workdir: Subdirectory under ``clone_path`` where
                          the playbook lives.

    Returns:
        Dict with keys: success, rc, output, duration, error, playbook.
    """
    config = load_test_config()
    credentials = load_test_credentials()
    local_mode = is_local_execution()

    v = verbosity if verbosity is not None else get_setting("default_verbosity", 1)
    t = timeout if timeout is not None else get_setting("default_timeout", 7200)

    clone_path = config.get("clone_path", "")
    if not clone_path:
        return _fail(
            playbook or "unknown", 0.0,
            "'clone_path' must be set in test_config.yml",
        )
    if playbook is None:
        return _fail(
            "unknown", 0.0,
            "'playbook' argument is required",
        )
    if not playbook_workdir:
        return _fail(
            playbook, 0.0,
            "'playbook_workdir' argument is required",
        )
    workdir = os.path.join(clone_path, playbook_workdir)

    logger_name = get_setting("runner_logger_name", "playbook_runner")  # safe default
    log = TestLogger(logger_name)

    password = credentials.get("oim_password", "")
    if not local_mode and password and not shutil.which("sshpass"):
        return _fail(
            playbook, 0.0,
            RUNNER_ASSERT_MSGS["sshpass_missing"],
        )

    venv_path = config.get("venv_path", "")
    # venv_path is optional - if provided, venv is activated before ansible-playbook

    ansible_cmd = _build_ansible_cmd(
        playbook, workdir, v, extra_vars, tag, limit, venv_path,
    )

    if local_mode:
        cmd = ansible_cmd
        log.check(RUNNER_LOG_MSGS["connecting_local"])
    else:
        cmd = _wrap_ssh(ansible_cmd, config, credentials)
        host = config["oim_server_ip"]
        port = config.get("oim_ssh_port", 22)
        log.check(RUNNER_LOG_MSGS["connecting_remote"].format(
            host=host, port=port,
        ))

    tag_str = ",".join(tag) if isinstance(tag, list) else (tag or "all")
    log.check(RUNNER_LOG_MSGS["starting_playbook"].format(
        playbook=playbook, tag=tag_str,
    ))
    log.check(RUNNER_LOG_MSGS["streaming_output"])

    return _stream_cmd(cmd, playbook, t, tag, config, playbook_workdir)


# =====================================================================
# COMMAND BUILDERS
# =====================================================================

def _build_ansible_cmd(
    playbook: str,
    workdir: str,
    verbosity: int,
    extra_vars: Optional[Dict[str, str]],
    tag,
    limit: Optional[str],
    venv_path: str = "",
) -> str:
    """Build the ``ansible-playbook`` command string."""
    v_flag = f" -{'v' * verbosity}" if verbosity > 0 else ""

    parts = []
    # Activate venv if specified
    if venv_path:
        parts.append(f"source {venv_path}/bin/activate &&")
    parts.extend([
        f"cd {workdir} &&",
        f"COLUMNS={get_setting('line_width', 160)} ansible-playbook {playbook}{v_flag}",  # 160 safe default
    ])

    if extra_vars:
        for key, val in extra_vars.items():
            parts.append(f'--extra-vars "{key}={val}"')
    if tag:
        tag_str = ",".join(tag) if isinstance(tag, list) else tag
        parts.append(f"--tags {tag_str}")
    if limit:
        parts.append(f"--limit {limit}")

    return " ".join(parts)


def _wrap_ssh(
    cmd: str,
    config: Dict,
    credentials: Dict,
) -> str:
    """Wrap a command in SSH for remote execution."""
    host = config["oim_server_ip"]
    user = config.get("oim_ssh_user", "root")
    port = str(config.get("oim_ssh_port", 22))
    password = credentials.get("oim_password", "")

    if password:
        parts = ["sshpass", f"-p '{password}'", "ssh", "-T"]
    else:
        parts = ["ssh", "-T"]

    parts.extend(get_setting("ssh_options_list", [
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
    ]))
    parts.extend(["-p", port, f"{user}@{host}", f"'{cmd}'"])
    return " ".join(parts)


# =====================================================================
# EXECUTION — single path for local and remote
# =====================================================================

def _stream_cmd(
    cmd: str,
    playbook: str,
    timeout: int,
    tag: Optional[str],
    config: Dict,
    pb_workdir: str = "src",
) -> Dict[str, Any]:
    """Execute *cmd* via subprocess, streaming output line-by-line.

    Output is read in the calling thread (no spawned reader threads).
    A lightweight ``threading.Timer`` enforces the timeout by killing
    the process group if the deadline is exceeded.
    """
    pipe_prefix = (
        f"    {Colors.GRAY}{Symbols.PIPE}{Colors.RESET} "
    )
    output_lines: List[str] = []
    start = time.time()
    timed_out = False
    process = None

    try:
        process = subprocess.Popen(
            ["bash", "-c", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
            preexec_fn=os.setsid,
        )

        # Lightweight timeout watchdog (no reader threads)
        def _on_timeout():
            nonlocal timed_out
            timed_out = True
            _kill_process_group(process)

        watchdog = threading.Timer(timeout, _on_timeout)
        watchdog.start()

        # Read output line-by-line in the calling thread
        try:
            for raw_line in process.stdout:
                clean = _ANSI_RE.sub(
                    "", raw_line,
                ).rstrip("\n\r ")
                output_lines.append(clean)
                if not clean:
                    print(pipe_prefix, flush=True)
                else:
                    _print_wrapped(clean, pipe_prefix)
        except (ValueError, OSError):
            pass

        rc = process.wait()
        watchdog.cancel()

        duration = time.time() - start

        if timed_out:
            return _fail(
                playbook, duration,
                RUNNER_ASSERT_MSGS["playbook_timeout"].format(
                    playbook=playbook, timeout=timeout,
                ),
                rc=-1, output="\n".join(output_lines),
            )

        if rc == 0:
            return _ok(playbook, rc, output_lines, duration)

        clone_path = config.get("clone_path", "")
        return _fail(
            playbook, duration,
            RUNNER_ASSERT_MSGS["playbook_failed"].format(
                playbook=playbook,
                tag=(",".join(tag) if isinstance(tag, list) else tag) or "all",
                rc=rc, duration=duration,
                log_path=config.get("shared_path", "") + "/log/",
                workdir=os.path.join(clone_path, pb_workdir),
            ),
            rc=rc, output="\n".join(output_lines),
        )

    except KeyboardInterrupt:
        duration = time.time() - start
        _kill_process_group(process)
        print(
            f"\n{pipe_prefix}"
            f"{Colors.BRIGHT_YELLOW}Cancelled by user"
            f"{Colors.RESET}",
            flush=True,
        )
        return _fail(
            playbook, duration,
            RUNNER_ASSERT_MSGS["cancelled"],
            rc=-2, output="\n".join(output_lines),
        )

    except subprocess.TimeoutExpired:
        duration = time.time() - start
        _kill_process_group(process)
        return _fail(
            playbook, duration,
            RUNNER_ASSERT_MSGS["playbook_timeout"].format(
                playbook=playbook, timeout=timeout,
            ),
            rc=-1, output="\n".join(output_lines),
        )

    except OSError as exc:
        duration = time.time() - start
        _kill_process_group(process)
        return _fail(
            playbook, duration,
            RUNNER_ASSERT_MSGS["os_error"] + f": {exc}",
            rc=-1, output="\n".join(output_lines),
        )

    finally:
        _cleanup_process(process)


# =====================================================================
# SHARED HELPERS
# =====================================================================

def _print_wrapped(line: str, prefix: str) -> None:
    """Print a line, wrapping at configured line_width."""
    width = get_setting("line_width", 160)  # 160 safe default
    while line:
        chunk = line[:width]
        line = line[width:]
        print(f"{prefix}{chunk}", flush=True)


def _ok(
    playbook: str,
    rc: int,
    output_lines: List[str],
    duration: float,
) -> Dict[str, Any]:
    """Build a success result dict."""
    return {
        "success": True,
        "rc": rc,
        "output": "\n".join(output_lines),
        "duration": duration,
        "error": None,
        "playbook": playbook,
    }


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


def _kill_process_group(process: Any) -> None:
    """Kill the entire process group."""
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


def _cleanup_process(process: Any) -> None:
    """Close all open streams on a process."""
    if process is None:
        return
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream and not stream.closed:
            try:
                stream.close()
            except OSError:
                pass
