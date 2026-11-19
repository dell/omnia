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

"""TC-UT-004: FileSystemLogAdapter tail reading and path validation (ER-BSM-003 FR-2.1)."""

import os

import pytest

from core.logs.exceptions import (
    LogContentError,
    LogNotAvailableError,
    LogPathViolationError,
    LogUnavailableReason,
)
from infra.logs.filesystem_adapter import FileSystemLogAdapter

pytestmark = pytest.mark.unit

JOB_ID = "019bf590-1234-7890-abcd-ef1234567890"
OTHER_JOB_ID = "019bf590-0000-7890-abcd-ef1234567890"
LOG_NAME = "build-image_image_build_manager.yml_20261113_101500_attempt1.log"
MAX_BYTES = 10 * 1024 * 1024


@pytest.fixture(name="log_root")
def log_root_fixture(tmp_path):
    """Container-side log root with one job directory."""
    root = tmp_path / "container" / "build_stream" / "log"
    (root / JOB_ID).mkdir(parents=True)
    return root


@pytest.fixture(name="adapter")
def adapter_fixture(log_root) -> FileSystemLogAdapter:
    """Adapter rooted at the temporary log root."""
    return FileSystemLogAdapter(log_root)


def _write_lines(path, count: int, trailing_newline: bool = True) -> None:
    """Write ``count`` numbered lines."""
    body = "\n".join(f"line {i}" for i in range(1, count + 1))
    path.write_text(body + ("\n" if trailing_newline else ""), encoding="utf-8")


def _host_path(name: str = LOG_NAME, job_id: str = JOB_ID) -> str:
    """Host-side path as stored by the result poller."""
    return f"/mnt/omnia_share/build_stream/log/{job_id}/{name}"


class TestResolve:
    """Host-to-container translation and root confinement."""

    def test_host_path_translated_to_container_path(self, adapter, log_root):
        """GIVEN a host path WHEN resolved THEN the file under the container root is returned."""
        target = log_root / JOB_ID / LOG_NAME
        _write_lines(target, 3)
        assert adapter.resolve(_host_path(), JOB_ID) == target.resolve()

    def test_container_style_path_also_resolves(self, adapter, log_root):
        """A path already using the container prefix resolves to the same file."""
        target = log_root / JOB_ID / LOG_NAME
        _write_lines(target, 1)
        stored = f"/opt/omnia/build_stream/log/{JOB_ID}/{LOG_NAME}"
        assert adapter.resolve(stored, JOB_ID) == target.resolve()

    @pytest.mark.parametrize(
        "stored",
        [
            "/etc/passwd",
            f"/mnt/omnia_share/build_stream/log/{JOB_ID}/../../../etc/passwd",
            f"/mnt/omnia_share/build_stream/log/{OTHER_JOB_ID}/{LOG_NAME}",
            f"/mnt/omnia_share/build_stream/log/{JOB_ID}/nested/{LOG_NAME}",
            f"/mnt/omnia_share/build_stream/log/{JOB_ID}/.hidden.log",
            f"relative/build_stream/log/{JOB_ID}/{LOG_NAME}",
            f"/mnt/omnia_share/build_stream/log/{JOB_ID}/a\x00.log",
        ],
    )
    def test_paths_outside_job_directory_rejected(self, adapter, stored):
        """GIVEN a stored path escaping the job log directory THEN a violation is raised."""
        with pytest.raises(LogPathViolationError):
            adapter.resolve(stored, JOB_ID)

    def test_symlink_escaping_root_rejected(self, adapter, log_root, tmp_path):
        """GIVEN a published name that is a symlink outside the root THEN a violation is raised."""
        secret = tmp_path / "secret.txt"
        secret.write_text("top secret\n", encoding="utf-8")
        os.symlink(secret, log_root / JOB_ID / LOG_NAME)
        with pytest.raises(LogPathViolationError):
            adapter.resolve(_host_path(), JOB_ID)

    def test_unpublished_fallback_path_not_available(self, adapter):
        """GIVEN the /var/log/omnia fallback THEN the log is reported as not published."""
        with pytest.raises(LogNotAvailableError) as exc:
            adapter.resolve(f"/var/log/omnia/image_build_manager/{LOG_NAME}", JOB_ID)
        assert exc.value.reason == LogUnavailableReason.NOT_PUBLISHED

    def test_missing_file_not_available(self, adapter):
        """GIVEN a valid path whose file was deleted THEN the log is reported missing."""
        with pytest.raises(LogNotAvailableError) as exc:
            adapter.resolve(_host_path(), JOB_ID)
        assert exc.value.reason == LogUnavailableReason.MISSING

    def test_empty_path_not_recorded(self, adapter):
        """GIVEN no stored path THEN the log is reported as not recorded."""
        with pytest.raises(LogNotAvailableError) as exc:
            adapter.resolve("", JOB_ID)
        assert exc.value.reason == LogUnavailableReason.NOT_RECORDED


class TestReadTail:
    """Seek-based tail reading."""

    def test_returns_last_n_lines(self, adapter, log_root):
        """GIVEN 1000 lines WHEN read_tail(50) THEN exactly the last 50 lines are returned."""
        target = log_root / JOB_ID / LOG_NAME
        _write_lines(target, 1000)
        result = adapter.read_tail(target, 50, MAX_BYTES)
        assert result.lines == [f"line {i}" for i in range(951, 1001)]
        assert result.total_lines == 1000
        assert result.truncated is True

    def test_short_file_returns_everything(self, adapter, log_root):
        """GIVEN 30 lines WHEN read_tail(50) THEN all 30 lines are returned untruncated."""
        target = log_root / JOB_ID / LOG_NAME
        _write_lines(target, 30)
        result = adapter.read_tail(target, 50, MAX_BYTES)
        assert len(result.lines) == 30
        assert result.total_lines == 30
        assert result.truncated is False

    def test_large_file_spanning_many_chunks(self, adapter, log_root):
        """Lines spanning several 64 KiB chunks are reassembled correctly."""
        target = log_root / JOB_ID / LOG_NAME
        _write_lines(target, 50_000)
        result = adapter.read_tail(target, 10_000, MAX_BYTES)
        assert result.lines[0] == "line 40001"
        assert result.lines[-1] == "line 50000"
        assert len(result.lines) == 10_000

    def test_unterminated_last_line_counted(self, adapter, log_root):
        """A final line without newline is returned and counted."""
        target = log_root / JOB_ID / LOG_NAME
        _write_lines(target, 5, trailing_newline=False)
        result = adapter.read_tail(target, 2, MAX_BYTES)
        assert result.lines == ["line 4", "line 5"]
        assert result.total_lines == 5

    def test_byte_bound_truncates_and_drops_partial_line(self, adapter, log_root):
        """GIVEN max_bytes smaller than the window THEN only whole lines are returned."""
        target = log_root / JOB_ID / LOG_NAME
        _write_lines(target, 100)
        result = adapter.read_tail(target, 100, 40)
        assert result.truncated is True
        assert result.lines[-1] == "line 100"
        assert all(line.startswith("line ") for line in result.lines)
        assert len("\n".join(result.lines)) <= 40

    def test_empty_file(self, adapter, log_root):
        """An empty log returns no lines."""
        target = log_root / JOB_ID / LOG_NAME
        target.write_bytes(b"")
        result = adapter.read_tail(target, 50, MAX_BYTES)
        assert result.lines == []
        assert result.total_lines == 0

    def test_binary_content_rejected(self, adapter, log_root):
        """GIVEN NUL bytes in the window THEN the content is refused."""
        target = log_root / JOB_ID / LOG_NAME
        target.write_bytes(b"ok\n\x00\x01\x02binary\n")
        with pytest.raises(LogContentError):
            adapter.read_tail(target, 50, MAX_BYTES)

    def test_invalid_utf8_replaced_not_rejected(self, adapter, log_root):
        """Non-UTF-8 text bytes are decoded with replacement characters."""
        target = log_root / JOB_ID / LOG_NAME
        target.write_bytes(b"caf\xe9 ok\n")
        assert adapter.read_tail(target, 5, MAX_BYTES).lines == ["caf\ufffd ok"]

    def test_growing_file_snapshot(self, adapter, log_root, monkeypatch):
        """GIVEN a file grows during the read THEN only bytes present at open time are used."""
        target = log_root / JOB_ID / LOG_NAME
        _write_lines(target, 10)
        real_fstat = os.fstat

        def fstat_then_grow(fd):
            stat = real_fstat(fd)
            with open(target, "a", encoding="utf-8") as handle:
                handle.write("appended later\n")
            return stat

        monkeypatch.setattr("infra.logs.filesystem_adapter.os.fstat", fstat_then_grow)
        result = adapter.read_tail(target, 50, MAX_BYTES)
        assert "appended later" not in result.lines
        assert result.lines[-1] == "line 10"


class TestReadFull:
    """Bounded full-log retrieval."""

    def test_within_bound_returns_whole_log(self, adapter, log_root):
        """GIVEN a log under max_bytes WHEN read_full THEN every line is returned."""
        target = log_root / JOB_ID / LOG_NAME
        _write_lines(target, 1830)
        result = adapter.read_full(target, MAX_BYTES)
        assert len(result.lines) == 1830
        assert result.truncated is False

    def test_over_bound_truncated_from_head(self, adapter, log_root):
        """GIVEN a log over max_bytes THEN the head is dropped and truncated=True."""
        target = log_root / JOB_ID / LOG_NAME
        _write_lines(target, 1000)
        result = adapter.read_full(target, 1024)
        assert result.truncated is True
        assert result.lines[-1] == "line 1000"
        assert result.total_lines == 1000
        assert len("\n".join(result.lines).encode()) <= 1024


class TestCountLines:  # pylint: disable=too-few-public-methods
    """Line counting used by GET /jobs/{id}."""

    def test_count_and_cache_invalidation(self, adapter, log_root):
        """Counts are cached per (size, mtime) and refreshed when the file changes."""
        target = log_root / JOB_ID / LOG_NAME
        _write_lines(target, 245)
        assert adapter.count_lines(target) == 245
        assert adapter.count_lines(target) == 245
        _write_lines(target, 512)
        assert adapter.count_lines(target) == 512
