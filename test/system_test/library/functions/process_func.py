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

import codecs
import os
import subprocess  # nosec B404  # argument lists only, no shell
import sys
import time
from typing import Dict, List, Mapping, Optional, TextIO

# Output kept in memory per command for its report row (the tail; the step log
# and the module log keep everything).
MAX_CAPTURE_CHARS = 1_000_000


class Tee:
    """Write to the stage log and, unless quiet, to the console."""

    def __init__(self, log: TextIO, console: Optional[TextIO]):
        self._log, self._console = log, console

    def write(self, text: str) -> int:
        """Write ``text`` to the log and the console."""
        self._log.write(text)
        if self._console:
            self._console.write(text)
        return len(text)

    def flush(self) -> None:
        """Flush the log and the console."""
        self._log.flush()
        if self._console:
            self._console.flush()

    def isatty(self) -> bool:
        """Report a non-terminal stream (pytest asks)."""
        return False

    @property
    def encoding(self) -> str:
        """Text encoding of the stream (pytest's terminal writer reads it)."""
        return "utf-8"


class Capture:
    """Keep the last MAX_CAPTURE_CHARS characters written by a command."""

    def __init__(self) -> None:
        self._parts: List[str] = []
        self._size = 0

    def add(self, text: str) -> None:
        """Append ``text``, dropping the oldest parts beyond the limit."""
        self._parts.append(text)
        self._size += len(text)
        while self._size > MAX_CAPTURE_CHARS and len(self._parts) > 1:
            self._size -= len(self._parts.pop(0))

    def text(self) -> str:
        """Return the captured output."""
        return "".join(self._parts)[-MAX_CAPTURE_CHARS:]


def _outcome(rc: int, started: float, command: List[str], capture: Capture) -> Dict[str, object]:
    return {"success": rc == 0, "rc": rc, "duration": time.monotonic() - started,
            "command": " ".join(command), "output": capture.text()}


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
        Dict with keys: success (rc 0), rc, duration (seconds), command (text),
        output (what was printed, the tail when very long).
    """
    started = time.monotonic()
    merged = {**os.environ, **(env or {})}
    capture = Capture()
    try:
        with subprocess.Popen(  # nosec B603  # fixed argument list, no shell
                command, cwd=cwd, env=merged, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace", bufsize=1) as process:
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                capture.add(line)
            rc = process.wait()
    except OSError as exc:
        message = f"cannot run {command[0]}: {exc}\n"
        sys.stdout.write(message)
        capture.add(message)
        rc = 127
    return _outcome(rc, started, command, capture)


def _without_venv(environ: Mapping[str, str]) -> Dict[str, str]:
    """Return ``environ`` as if no virtualenv were active (VIRTUAL_ENV and its bin/ removed)."""
    venv = environ.get("VIRTUAL_ENV", "")
    cleaned = {key: value for key, value in environ.items() if key != "VIRTUAL_ENV"}
    if venv:
        cleaned["PATH"] = os.pathsep.join(
            part for part in environ.get("PATH", "").split(os.pathsep)
            if os.path.realpath(part) != os.path.realpath(os.path.join(venv, "bin")))
    return cleaned


def _pump(descriptor: int, capture: Capture) -> None:
    """Echo a command's output in chunks (prompts show at once) and capture it, until EOF."""
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    while True:
        chunk = os.read(descriptor, 4096)
        text = decoder.decode(chunk, final=not chunk)
        sys.stdout.write(text)
        sys.stdout.flush()
        capture.add(text)
        if not chunk:
            break


def tee_command(command: List[str], cwd: str, env: Optional[Mapping[str, str]] = None,
                drop_venv: bool = False, no_input: bool = False,
                input_bytes: Optional[bytes] = None) -> Dict[str, object]:
    """Run ``command`` with the caller's stdin and echo its output through ``sys.stdout``.

    The output is read in chunks, not lines, so a prompt without a newline
    (``[y/N]:``) is shown at once and the user can answer it on the terminal.
    ``drop_venv`` runs the command outside any active virtualenv; ``no_input``
    gives it an empty stdin (unattended: a prompt gets no answer);
    ``input_bytes`` is written to its stdin instead (fixed answers).

    Returns:
        Dict with keys: success (rc 0), rc, duration (seconds), command (text),
        output (what was printed, the tail when very long).
    """
    started = time.monotonic()
    merged = {**os.environ, **(env or {})}
    capture = Capture()
    if drop_venv:
        merged = _without_venv(merged)
    try:
        with subprocess.Popen(  # nosec B603  # fixed argument list, no shell
                command, cwd=cwd, env=merged, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=(subprocess.PIPE if input_bytes is not None
                       else subprocess.DEVNULL if no_input else None)) as process:
            if input_bytes is not None:
                try:
                    process.stdin.write(input_bytes)
                    process.stdin.close()
                except BrokenPipeError:
                    pass
            _pump(process.stdout.fileno(), capture)
            rc = process.wait()
    except OSError as exc:
        message = f"cannot run {command[0]}: {exc}\n"
        sys.stdout.write(message)
        capture.add(message)
        rc = 127
    return _outcome(rc, started, command, capture)


def interactive_command(command: List[str], cwd: str, env: Optional[Mapping[str, str]] = None,
                        input_bytes: Optional[bytes] = None) -> Dict[str, object]:
    """Run ``command`` attached to the terminal (stdin, stdout, stderr); nothing is captured.

    Used for credential prompts: their output is never written to a log.
    ``input_bytes`` is given to the command as its stdin instead (a credential
    payload read once by the caller; never written anywhere).

    Returns:
        Dict with keys: success (rc 0), rc, duration (seconds), command (text).
    """
    started = time.monotonic()
    sys.stdout.flush()
    try:
        rc = subprocess.run(  # nosec B603  # fixed argument list, no shell
            command, cwd=cwd, env={**os.environ, **(env or {})}, check=False,
            input=input_bytes, stdout=sys.__stdout__, stderr=sys.__stderr__).returncode
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
