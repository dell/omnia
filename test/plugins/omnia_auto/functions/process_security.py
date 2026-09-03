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

"""Internal helpers for securely supplying credentials to child processes."""

from contextlib import contextmanager
import errno
import fcntl
import os
import secrets
import stat
import tempfile
from typing import Dict, Iterator, Optional, TextIO, Tuple


def validate_sensitive_fd(file_fd: int, file_path: str) -> None:
    """Require a sensitive descriptor to be a regular current-user file."""
    file_stat = os.fstat(file_fd)
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError(
            f"Sensitive path must be a regular file: {file_path}"
        )
    if file_stat.st_uid != os.geteuid():
        raise ValueError(
            f"Sensitive file must be owned by the current user: {file_path}"
        )


@contextmanager
def sensitive_file_descriptor(
    file_path: str, file_mode: int = 0o600,
) -> Iterator[int]:
    """Yield a validated descriptor without reopening the sensitive path."""
    if os.path.islink(file_path):
        raise ValueError(
            f"Sensitive file must not be a symbolic link: {file_path}"
        )
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        file_fd = os.open(file_path, flags)
    except OSError as exc:
        raise ValueError(
            f"Unable to secure sensitive file '{file_path}': {exc}"
        ) from exc

    try:
        validate_sensitive_fd(file_fd, file_path)
        os.fchmod(file_fd, file_mode)
    except ValueError:
        os.close(file_fd)
        raise
    except OSError as exc:
        os.close(file_fd)
        raise ValueError(
            f"Unable to secure sensitive file '{file_path}': {exc}"
        ) from exc

    try:
        yield file_fd
    finally:
        try:
            validate_sensitive_fd(file_fd, file_path)
            os.fchmod(file_fd, file_mode)
        finally:
            os.close(file_fd)


def protect_sensitive_file(file_path: str, file_mode: int = 0o600) -> None:
    """Validate an existing sensitive file and restrict its permissions."""
    with sensitive_file_descriptor(file_path, file_mode):
        pass


@contextmanager
def open_sensitive_text(
    file_path: str, file_mode: int = 0o600,
) -> Iterator[TextIO]:
    """Read a sensitive text file through its validated descriptor."""
    with sensitive_file_descriptor(file_path, file_mode) as file_fd:
        try:
            stream_fd = os.dup(file_fd)
        except OSError as exc:
            raise ValueError(
                f"Unable to read sensitive file '{file_path}': {exc}"
            ) from exc
        with os.fdopen(stream_fd, "r", encoding="utf-8") as file_stream:
            yield file_stream


@contextmanager
def sensitive_parent_descriptor(
    file_path: str,
) -> Iterator[Tuple[int, str, str]]:
    """Open a trusted parent directory for an atomic sensitive update."""
    absolute_path = os.path.abspath(file_path)
    parent_path = os.path.dirname(absolute_path)
    file_name = os.path.basename(absolute_path)
    if not file_name:
        raise ValueError(f"Sensitive path must name a file: {file_path}")

    try:
        os.makedirs(parent_path, mode=0o700, exist_ok=True)
        parent_fd = os.open(
            parent_path,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as exc:
        raise ValueError(
            f"Unable to secure parent directory '{parent_path}': {exc}"
        ) from exc

    try:
        parent_stat = os.fstat(parent_fd)
        if not stat.S_ISDIR(parent_stat.st_mode):
            raise ValueError(
                f"Sensitive parent must be a directory: {parent_path}"
            )
        if parent_stat.st_uid != os.geteuid():
            raise ValueError(
                "Sensitive parent directory must be owned by the current "
                f"user: {parent_path}"
            )
        if stat.S_IMODE(parent_stat.st_mode) & 0o022:
            raise ValueError(
                "Sensitive parent directory must not be group/world "
                f"writable: {parent_path}"
            )
        yield parent_fd, file_name, absolute_path
    finally:
        os.close(parent_fd)


def _open_existing_sensitive_output(
    parent_fd: int, file_name: str, file_path: str, file_mode: int,
) -> None:
    """Validate and secure an existing output relative to its open parent."""
    try:
        target_fd = os.open(
            file_name,
            os.O_RDONLY
            | getattr(os, "O_NONBLOCK", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except FileNotFoundError:
        return
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError(
                f"Sensitive file must not be a symbolic link: {file_path}"
            ) from exc
        raise ValueError(
            f"Unable to secure sensitive file '{file_path}': {exc}"
        ) from exc

    try:
        validate_sensitive_fd(target_fd, file_path)
        os.fchmod(target_fd, file_mode)
    except OSError as exc:
        raise ValueError(
            f"Unable to secure sensitive file '{file_path}': {exc}"
        ) from exc
    finally:
        os.close(target_fd)


@contextmanager
def atomic_sensitive_output(
    file_path: str, file_mode: int = 0o600,
) -> Iterator[int]:
    """Yield a private output descriptor and atomically replace *file_path*."""
    with sensitive_parent_descriptor(file_path) as parent_details:
        parent_fd, file_name, absolute_path = parent_details
        _open_existing_sensitive_output(
            parent_fd, file_name, absolute_path, file_mode,
        )
        temporary_name = ""
        output_fd = -1
        try:
            try:
                for _attempt in range(128):
                    candidate_name = (
                        f".{file_name}.{secrets.token_hex(12)}.tmp"
                    )
                    try:
                        output_fd = os.open(
                            candidate_name,
                            os.O_RDWR
                            | os.O_CREAT
                            | os.O_EXCL
                            | getattr(os, "O_NOFOLLOW", 0),
                            file_mode,
                            dir_fd=parent_fd,
                        )
                        temporary_name = candidate_name
                        break
                    except FileExistsError:
                        continue
                else:
                    raise ValueError(
                        f"Unable to allocate sensitive file '{file_path}'"
                    )

                validate_sensitive_fd(output_fd, absolute_path)
                os.fchmod(output_fd, file_mode)
            except OSError as exc:
                raise ValueError(
                    f"Unable to create sensitive file '{file_path}': {exc}"
                ) from exc

            yield output_fd
            try:
                validate_sensitive_fd(output_fd, absolute_path)
                os.fchmod(output_fd, file_mode)
                os.fsync(output_fd)
                os.replace(
                    temporary_name,
                    file_name,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
                temporary_name = ""
            except OSError as exc:
                raise ValueError(
                    f"Unable to replace sensitive file '{file_path}': {exc}"
                ) from exc
        finally:
            if output_fd >= 0:
                os.close(output_fd)
            if temporary_name:
                try:
                    os.unlink(temporary_name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass


def descriptor_path(file_fd: int) -> str:
    """Return the Linux procfs path for an inherited open descriptor."""
    if file_fd < 0:
        raise ValueError("File descriptor must not be negative")
    return f"/proc/self/fd/{file_fd}"


@contextmanager
def temporary_sensitive_descriptor(
    directory: Optional[str] = None, file_mode: int = 0o600,
) -> Iterator[int]:
    """Yield an unlinked private regular file for transient secret data."""
    try:
        temporary_file = tempfile.TemporaryFile(dir=directory)
    except OSError as exc:
        raise ValueError(
            f"Unable to create temporary sensitive file: {exc}"
        ) from exc

    try:
        file_fd = temporary_file.fileno()
        validate_sensitive_fd(file_fd, "<temporary sensitive file>")
        os.fchmod(file_fd, file_mode)
    except (OSError, ValueError) as exc:
        temporary_file.close()
        raise ValueError(
            f"Unable to create temporary sensitive file: {exc}"
        ) from exc

    try:
        yield file_fd
    finally:
        temporary_file.close()


@contextmanager
def sshpass_pipe(auth_secret: Optional[str]) -> Iterator[Optional[int]]:
    """Yield a private descriptor containing one password line for sshpass."""
    if not auth_secret:
        yield None
        return
    if not isinstance(auth_secret, str):
        raise ValueError("SSH authentication value must be a string")
    if any(character in auth_secret for character in ("\x00", "\r", "\n")):
        raise ValueError("SSH authentication value must be a single line")

    payload = auth_secret.encode("utf-8") + b"\n"
    read_fd, write_fd = os.pipe()
    try:
        if read_fd < 3:
            duplicated_fd = fcntl.fcntl(
                read_fd, fcntl.F_DUPFD_CLOEXEC, 3,
            )
            os.close(read_fd)
            read_fd = duplicated_fd
        pipe_buffer = os.fpathconf(write_fd, "PC_PIPE_BUF")
        if len(payload) > pipe_buffer:
            raise ValueError("SSH authentication value is too long")
        written = os.write(write_fd, payload)
        if written != len(payload):
            raise OSError("Unable to write the complete SSH authentication value")
    except (OSError, ValueError):
        os.close(read_fd)
        raise
    finally:
        os.close(write_fd)

    try:
        yield read_fd
    finally:
        os.close(read_fd)


def descriptor_tuple(auth_fd: Optional[int]) -> Tuple[int, ...]:
    """Return a subprocess ``pass_fds`` tuple for an optional descriptor."""
    return (auth_fd,) if auth_fd is not None else ()


def scrubbed_subprocess_environment() -> Dict[str, str]:
    """Copy the environment without a possibly inherited sshpass value."""
    child_environment = os.environ.copy()
    child_environment.pop("SSHPASS", None)
    return child_environment
