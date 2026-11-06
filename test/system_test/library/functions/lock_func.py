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

"""One SVT step at a time on this OIM: the lock, its heartbeat, interrupted steps.

Every ./setup_env.sh action and every ./run_validation.sh stage owns the OIM
while it runs. Ownership is a kernel lock (``flock``, LOCK_EX | LOCK_NB) on
reports/svt.flock, taken atomically, so two steps starting together cannot both
get it. reports/svt.lock only describes the owner: pid, host, step, run id,
start and a heartbeat refreshed every LOCK_HEARTBEAT_SECONDS.

- A second step while the owner lives is refused (exit 2).
- The kernel drops the lock when its process ends however it ends (kill -9, a
  dropped SSH session, a reboot). A description left behind by such a process
  means its step was interrupted: it is recorded as interrupted (the run is
  marked failed at it) by the step that takes the lock next.
- A clean exit removes the description before it releases the lock.
- A frozen owner (SIGSTOP) keeps the lock: stop it by its pid.
- Ctrl-C is recorded by the drivers themselves (_setup.py, _run.py).

Other test processes on the OIM (an FVT suite run by hand, an
ansible-playbook of another checkout) cannot take this lock; they are listed
as a warning when a step starts.
"""

import fcntl
import json
import os
import socket
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from . import run_func
from .svt_report_func import load_json, write_atomic
from ..messages.svt_msgs import LOCK_MSGS
from ..vars.common_vars import (
    LOCK_FILE,
    LOCK_GUARD_FILE,
    LOCK_HEARTBEAT_SECONDS,
    LOCK_STALE_SECONDS,
    REPORT_ROOT,
)

Emit = Callable[[str], None]


class LockError(RuntimeError):
    """Another SVT step holds the lock; the message names it."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_lock() -> Dict[str, Any]:
    """Return the lock record ({} when no step holds it)."""
    return load_json(LOCK_FILE)


def lock_state(lock: Dict[str, Any]) -> str:
    """Return "free", "held" or "stale" for a lock record."""
    if not lock.get("pid"):
        return "free"
    if lock.get("host") != socket.gethostname():
        return "held"
    beat = lock.get("heartbeat_epoch") or 0
    if not _alive(int(lock["pid"])) or time.time() - float(beat) > LOCK_STALE_SECONDS:
        return "stale"
    return "held"


def other_test_processes() -> List[str]:
    """Return FVT runners and ansible-playbook processes not started by this step."""
    mine = {os.getpid(), os.getppid()}
    found = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit() or int(entry) in mine:
            continue
        try:
            with open(f"/proc/{entry}/cmdline", "rb") as stream:
                args = stream.read().split(b"\0")
        except OSError:
            continue
        text = " ".join(part.decode(errors="replace") for part in args if part)
        if ("_run.py fvt_" in text or "/ansible-playbook " in text) and "_run.py svt_" not in text:
            found.append(f"pid {entry}: {text[:160]}")
    return found


class StepLock:
    """Context manager: own the OIM for one step (kernel lock), with a heartbeat."""

    def __init__(self, step: str, emit: Optional[Emit] = None):
        self.step, self.emit = step, emit or print
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._guard: Optional[int] = None
        self.record: Dict[str, Any] = {}

    def _write(self) -> None:
        self.record["heartbeat"] = _now()
        self.record["heartbeat_epoch"] = time.time()
        write_atomic(LOCK_FILE, json.dumps(self.record, indent=2))

    def _beat(self) -> None:
        while not self._stop.wait(LOCK_HEARTBEAT_SECONDS):
            try:
                self._write()
            except OSError:
                pass

    def _take_guard(self) -> None:
        """Take the kernel lock without waiting; raise LockError naming the owner."""
        self._guard = os.open(LOCK_GUARD_FILE, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(self._guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self._guard)
            self._guard = None
            held: Dict[str, Any] = {}
            for _ in range(10):  # the owner writes its description right after the lock
                held = read_lock()
                if held.get("pid"):
                    break
                time.sleep(0.1)
            raise LockError(LOCK_MSGS["held"].format(
                step=held.get("step") or "a step", pid=held.get("pid") or "?",
                run_id=held.get("run_id") or "?", heartbeat=held.get("heartbeat") or "?")) from exc

    def __enter__(self) -> "StepLock":
        os.makedirs(REPORT_ROOT, mode=0o750, exist_ok=True)
        self._take_guard()
        held = read_lock()
        if held.get("pid") and lock_state(held) == "held":
            # A live owner that holds no kernel lock: a step of an SVT version without it
            # (during an upgrade), or a recycled pid within the heartbeat window. Refuse.
            self._release_guard()
            raise LockError(LOCK_MSGS["held"].format(
                step=held.get("step"), pid=held.get("pid"), run_id=held.get("run_id"),
                heartbeat=held.get("heartbeat")))
        if held.get("pid"):  # its owner is gone (the kernel lock was free): it was interrupted
            record_interrupted(held, self.emit)
        run = run_func.load_run()
        self.record = {"pid": os.getpid(), "host": socket.gethostname(), "step": self.step,
                       "run_id": run.get("run_id", ""), "started_at": _now()}
        self._write()
        for line in other_test_processes():
            self.emit(LOCK_MSGS["other_process"].format(process=line))
        self._thread = threading.Thread(target=self._beat, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._stop.set()
        if read_lock().get("pid") == os.getpid():
            try:
                os.unlink(LOCK_FILE)
            except FileNotFoundError:
                pass
        self._release_guard()

    def _release_guard(self) -> None:
        if self._guard is not None:
            os.close(self._guard)
            self._guard = None


def record_interrupted(lock: Dict[str, Any], emit: Emit) -> None:
    """Record the step of a stale lock as interrupted (run marked failed at it)."""
    step = str(lock.get("step") or "unknown step")
    error = LOCK_MSGS["interrupted"].format(step=step, pid=lock.get("pid"),
                                            heartbeat=lock.get("heartbeat", ""))
    emit(error)
    run = run_func.load_run()
    if run.get("run_id") and run.get("run_id") == lock.get("run_id"):
        message = run_func.mark_failed(f"{step} (interrupted)", error)
        if message:
            emit(message)
    interrupted = os.path.join(REPORT_ROOT, "interrupted.json")
    history = load_json(interrupted).get("steps") or []
    history.append({**{k: lock.get(k) for k in ("step", "pid", "run_id", "started_at",
                                                  "heartbeat")}, "found_at": _now()})
    write_atomic(interrupted, json.dumps({"steps": history[-50:]}, indent=2))


def describe_lock() -> str:
    """Return one line about the lock for the status box."""
    lock = read_lock()
    state = lock_state(lock)
    if state == "free":
        return "lock   free"
    return (f"lock   {state}: {lock.get('step')} (pid {lock.get('pid')}, run "
            f"{lock.get('run_id')}, heartbeat {lock.get('heartbeat')})")
