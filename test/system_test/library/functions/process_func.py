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

"""Run commands without a shell and stream their output line by line.

Every command is an argument list built from constants and validated values;
nothing goes through a shell and no secret is passed as an argument.
"""

import os
import subprocess  # nosec B404  # argument lists only, no shell
import sys
import time
from typing import Dict, List, Mapping, Optional


def format_duration(seconds: float) -> str:
    """Return ``1h02m03s`` / ``2m03s`` / ``3s`` for a duration."""
    seconds = int(seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{secs:02d}s"
    return f"{minutes}m{secs:02d}s" if minutes else f"{secs}s"


def stream_command(command: List[str], cwd: str,
                   env: Optional[Mapping[str, str]] = None) -> Dict[str, object]:
    """Run ``command`` in ``cwd``, echo its output through ``sys.stdout``, wait.

    Returns:
        Dict with keys: success (rc 0), rc, duration (seconds), command (text).
    """
    started = time.monotonic()
    merged = {**os.environ, **(env or {})}
    try:
        with subprocess.Popen(  # nosec B603  # fixed argument list, no shell
                command, cwd=cwd, env=merged, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace", bufsize=1) as process:
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
            rc = process.wait()
    except OSError as exc:
        sys.stdout.write(f"cannot run {command[0]}: {exc}\n")
        rc = 127
    return {"success": rc == 0, "rc": rc, "duration": time.monotonic() - started,
            "command": " ".join(command)}


def capture_command(command: List[str], cwd: str) -> str:
    """Run a short read-only command and return its stripped stdout ("" on failure)."""
    try:
        result = subprocess.run(  # nosec B603  # fixed argument list, no shell
            command, cwd=cwd, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""
