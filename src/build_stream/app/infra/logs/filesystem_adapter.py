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

# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-INPUT-001.5, CG-OUTPUT-001.2
# ****

"""Filesystem adapter serving published stage logs (ER-BSM-003 HLD 5.3).

The playbook watcher publishes each stage log to
``<host OMNIA_DATA_PATH>/build_stream/log/<job_id>/<file>`` and the result
poller stores that *host* path in ``job_stages.log_file_path``. Inside the BSM
container the same directory is mounted under a different prefix, so stored
paths are never opened directly: only the ``<job_id>/<file>`` suffix after the
``build_stream/log`` segment is kept and re-rooted under the configured log
root. The result is canonicalised (symlinks resolved) and must stay inside the
root.
"""

import os
import re
import threading
from collections import OrderedDict
from pathlib import Path, PurePosixPath
from typing import BinaryIO, List, Optional, Tuple

from core.logs.exceptions import (
    LogContentError,
    LogNotAvailableError,
    LogPathViolationError,
    LogUnavailableReason,
)
from core.logs.services import LogReadResult

PUBLISHED_LOG_SEGMENTS = ("build_stream", "log")
UNPUBLISHED_LOG_PREFIX = PurePosixPath("/var/log/omnia")
SAFE_LOG_FILE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")
READ_CHUNK_BYTES = 64 * 1024


class FileSystemLogAdapter:
    """Reads stage logs below a single configured log root."""

    def __init__(self, log_root: Path, line_cache_size: int = 256) -> None:
        """Create the adapter.

        Args:
            log_root: Container path of the published job log directory.
            line_cache_size: Number of (path, size, mtime) line counts to cache.
        """
        self._root = Path(log_root).resolve()
        self._line_cache: "OrderedDict[Tuple[str, int, int], int]" = OrderedDict()
        self._line_cache_size = line_cache_size
        self._lock = threading.Lock()

    @property
    def log_root(self) -> Path:
        """Return the canonical log root."""
        return self._root

    def resolve(self, stored_path: str, job_id: str) -> Path:
        """Translate a stored host log path to a canonical path under the log root."""
        if not stored_path:
            raise LogNotAvailableError(LogUnavailableReason.NOT_RECORDED)
        if "\x00" in stored_path:
            raise LogPathViolationError()
        pure = PurePosixPath(stored_path)
        if not pure.is_absolute() or ".." in pure.parts:
            raise LogPathViolationError()

        marker = _last_marker_index(pure.parts)
        if marker is None:
            if pure.is_relative_to(UNPUBLISHED_LOG_PREFIX):
                raise LogNotAvailableError(LogUnavailableReason.NOT_PUBLISHED)
            raise LogPathViolationError()

        suffix = pure.parts[marker + len(PUBLISHED_LOG_SEGMENTS):]
        if (
            len(suffix) != 2
            or suffix[0] != job_id
            or not SAFE_LOG_FILE_NAME.match(suffix[1])
        ):
            raise LogPathViolationError()

        candidate = self._root / suffix[0] / suffix[1]
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise LogNotAvailableError(LogUnavailableReason.MISSING) from exc
        if not resolved.is_relative_to(self._root) or not resolved.is_file():
            raise LogPathViolationError()
        return resolved

    def read_tail(self, path: Path, lines: int, max_bytes: int) -> LogReadResult:
        """Return the last ``lines`` lines of the file, bounded by ``max_bytes``."""
        with open(path, "rb") as handle:
            size = os.fstat(handle.fileno()).st_size
            data, start = _read_tail_bytes(handle, size, lines, max_bytes)
            total = self._total_lines(handle, path, size)
        _reject_binary(data)
        text_lines = _split_lines(data, drop_partial_head=start > 0)
        selected = text_lines[-lines:] if lines < len(text_lines) else text_lines
        return LogReadResult(
            lines=selected,
            total_lines=total,
            truncated=len(selected) < total,
        )

    def read_full(self, path: Path, max_bytes: int) -> LogReadResult:
        """Return the whole file, keeping only the last ``max_bytes`` bytes."""
        with open(path, "rb") as handle:
            size = os.fstat(handle.fileno()).st_size
            start = max(0, size - max_bytes)
            handle.seek(start)
            data = handle.read(size - start)
            total = self._total_lines(handle, path, size)
        _reject_binary(data)
        text_lines = _split_lines(data, drop_partial_head=start > 0)
        return LogReadResult(
            lines=text_lines,
            total_lines=total,
            truncated=start > 0,
        )

    def count_lines(self, path: Path) -> int:
        """Return the number of lines in the file (cached by size and mtime)."""
        with open(path, "rb") as handle:
            size = os.fstat(handle.fileno()).st_size
            return self._total_lines(handle, path, size)

    def _total_lines(self, handle: BinaryIO, path: Path, size: int) -> int:
        """Count lines in the first ``size`` bytes, reusing a cached value when unchanged."""
        key = (str(path), size, os.fstat(handle.fileno()).st_mtime_ns)
        with self._lock:
            cached = self._line_cache.get(key)
            if cached is not None:
                self._line_cache.move_to_end(key)
                return cached
        count = _count_lines(handle, size)
        with self._lock:
            self._line_cache[key] = count
            while len(self._line_cache) > self._line_cache_size:
                self._line_cache.popitem(last=False)
        return count


def _last_marker_index(parts: Tuple[str, ...]) -> Optional[int]:
    """Return the index of the last ``build_stream/log`` segment pair, if any."""
    width = len(PUBLISHED_LOG_SEGMENTS)
    for index in range(len(parts) - width, -1, -1):
        if parts[index:index + width] == PUBLISHED_LOG_SEGMENTS:
            return index
    return None


def _read_tail_bytes(
    handle: BinaryIO, size: int, lines: int, max_bytes: int
) -> Tuple[bytes, int]:
    """Read backwards from ``size`` until ``lines`` complete lines or ``max_bytes``."""
    position = size
    data = b""
    while position > 0 and data.count(b"\n") <= lines and len(data) < max_bytes:
        chunk = min(READ_CHUNK_BYTES, position, max_bytes - len(data))
        position -= chunk
        handle.seek(position)
        data = handle.read(chunk) + data
    return data, position


def _count_lines(handle: BinaryIO, size: int) -> int:
    """Count newline-terminated lines plus a final unterminated line."""
    handle.seek(0)
    remaining = size
    count = 0
    last = b""
    while remaining > 0:
        chunk = handle.read(min(READ_CHUNK_BYTES, remaining))
        if not chunk:
            break
        count += chunk.count(b"\n")
        last = chunk[-1:]
        remaining -= len(chunk)
    if size > 0 and last != b"\n":
        count += 1
    return count


def _reject_binary(data: bytes) -> None:
    """Refuse to serve content that contains NUL bytes."""
    if b"\x00" in data:
        raise LogContentError()


def _split_lines(data: bytes, drop_partial_head: bool) -> List[str]:
    """Decode bytes and split into lines, dropping a partial first line when cut."""
    text = data.decode("utf-8", errors="replace")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if drop_partial_head and lines:
        lines.pop(0)
    return lines
