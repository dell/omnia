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

"""Internal locking and atomic-write helpers for generated artifacts."""

import fcntl
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from typing import Any, Iterator


@contextmanager
def advisory_lock(target_path: str) -> Iterator[None]:
    """Serialize same-user writers that cooperate on *target_path*.

    The lock itself is private, may not be a symbolic link, and must be a
    regular file owned by the current user.  These checks keep a lock used for
    credential updates from becoming a symlink-based overwrite primitive.
    """
    if not isinstance(target_path, (str, os.PathLike)):
        raise ValueError("Lock target must be a filesystem path")
    lock_path = f"{target_path}.lock"
    parent = os.path.dirname(os.path.abspath(lock_path))
    os.makedirs(parent, exist_ok=True)
    try:
        lock_fd = os.open(
            lock_path,
            os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except OSError as exc:
        raise ValueError(f"Unable to open lock file '{lock_path}': {exc}") from exc
    try:
        lock_stat = os.fstat(lock_fd)
        if not stat.S_ISREG(lock_stat.st_mode):
            raise ValueError(f"Lock path must be a regular file: {lock_path}")
        if lock_stat.st_uid != os.geteuid():
            raise ValueError(
                f"Lock file must be owned by the current user: {lock_path}"
            )
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def atomic_write_text(path: str, content: str) -> None:
    """Write UTF-8 text and atomically replace the destination."""
    if not isinstance(path, (str, os.PathLike)):
        raise ValueError("Output path must be a filesystem path")
    if not isinstance(content, str):
        raise ValueError("Output content must be text")
    absolute_path = os.path.abspath(path)
    parent = os.path.dirname(absolute_path)
    os.makedirs(parent, exist_ok=True)
    file_fd, temporary_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=parent,
    )
    try:
        with os.fdopen(file_fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, absolute_path)
        temporary_path = ""
    finally:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def atomic_write_json(path: str, data: Any) -> None:
    """Serialize JSON and atomically replace the destination."""
    atomic_write_text(
        path,
        json.dumps(data, indent=2, default=str) + "\n",
    )
