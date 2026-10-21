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

"""Descriptor-based path helpers for privileged Repo Manager files."""

import errno
import os
import stat


def _directory_flags():
    """Return flags required for a pinned, no-follow directory open."""
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise OSError(
            errno.ENOTSUP, "Secure Repo Manager path opening is unavailable"
        )
    return (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )


def _validate_directory(
        directory_descriptor, *, require_trusted_owner=True):
    """Reject a directory component that another local user can replace."""
    directory_status = os.fstat(directory_descriptor)
    if not stat.S_ISDIR(directory_status.st_mode):
        raise OSError(errno.ENOTDIR, "Repo Manager path component is not a directory")

    effective_uid = os.geteuid()
    if (
            require_trusted_owner
            and directory_status.st_uid not in (0, effective_uid)
    ):
        raise PermissionError(
            errno.EPERM, "Repo Manager path component has untrusted ownership"
        )

    writable_by_others = directory_status.st_mode & (
        stat.S_IWGRP | stat.S_IWOTH
    )
    trusted_sticky_root = (
        directory_status.st_uid == 0
        and directory_status.st_mode & stat.S_ISVTX
    )
    if writable_by_others and not trusted_sticky_root:
        raise PermissionError(
            errno.EPERM,
            "Repo Manager path component is writable by other users",
        )


def open_secure_directory(
        directory_path, create=False, mode=0o700, *,
        require_trusted_owner=True):
    """Open a directory without following any component symlinks.

    By default every component must be owned by root or the effective user.
    Callers reading administrator-supplied public/TLS material may disable that
    ownership check, but group/world-writable components remain forbidden. A
    root-owned sticky directory such as /tmp is accepted because other users
    cannot replace entries they do not own.
    Missing components are created relative to an already validated parent.
    The caller owns the returned descriptor.
    """
    if not isinstance(directory_path, str) or not directory_path:
        raise ValueError("Repo Manager directory path must be a non-empty string")

    absolute_path = os.path.abspath(directory_path)
    flags = _directory_flags()
    current_descriptor = os.open(os.path.sep, flags)
    try:
        _validate_directory(
            current_descriptor,
            require_trusted_owner=require_trusted_owner,
        )
        for component in absolute_path.split(os.path.sep):
            if not component:
                continue
            try:
                next_descriptor = os.open(
                    component, flags, dir_fd=current_descriptor
                )
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(component, mode=mode, dir_fd=current_descriptor)
                except FileExistsError:
                    pass
                next_descriptor = os.open(
                    component, flags, dir_fd=current_descriptor
                )

            try:
                _validate_directory(
                    next_descriptor,
                    require_trusted_owner=require_trusted_owner,
                )
            except Exception:
                os.close(next_descriptor)
                raise
            os.close(current_descriptor)
            current_descriptor = next_descriptor

        result_descriptor = current_descriptor
        current_descriptor = None
        return result_descriptor
    finally:
        if current_descriptor is not None:
            os.close(current_descriptor)


def _relative_path_components(relative_path):
    """Validate an untrusted relative path and return its components."""
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError("Repo Manager relative path must be a non-empty string")
    if os.path.isabs(relative_path) or "\\" in relative_path:
        raise ValueError("Repo Manager relative path is unsafe")
    if any(ord(character) < 32 or ord(character) == 127
           for character in relative_path):
        raise ValueError("Repo Manager relative path contains control characters")

    components = tuple(relative_path.split("/"))
    if any(component in ("", ".", "..") for component in components):
        raise ValueError("Repo Manager relative path contains an unsafe segment")
    return components


def _open_child_directory(parent_descriptor, component, mode):
    """Open or create one trusted directory below an already pinned parent."""
    flags = _directory_flags()
    try:
        descriptor = os.open(component, flags, dir_fd=parent_descriptor)
    except FileNotFoundError:
        try:
            os.mkdir(component, mode=mode, dir_fd=parent_descriptor)
        except FileExistsError:
            pass
        descriptor = os.open(component, flags, dir_fd=parent_descriptor)
    try:
        _validate_directory(descriptor)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def open_secure_relative_file(
        directory_path, relative_path, *, directory_mode=0o700, file_mode=0o600):
    """Open one regular file below a trusted directory without following links.

    Parent components are opened relative to pinned descriptors. The leaf is
    opened with O_NOFOLLOW and is rejected when it is not a singly-linked
    regular file owned by root or the effective user. The caller owns the
    returned descriptor.
    """
    components = _relative_path_components(relative_path)
    directory_descriptor = open_secure_directory(
        directory_path, create=True, mode=directory_mode
    )
    try:
        for component in components[:-1]:
            next_descriptor = _open_child_directory(
                directory_descriptor, component, directory_mode
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor

        flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW
        flags |= getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NONBLOCK", 0)
        file_descriptor = os.open(
            components[-1],
            flags,
            file_mode,
            dir_fd=directory_descriptor,
        )
        try:
            file_status = os.fstat(file_descriptor)
            if (
                    not stat.S_ISREG(file_status.st_mode)
                    or file_status.st_nlink != 1
                    or file_status.st_uid not in (0, os.geteuid())
            ):
                raise PermissionError(
                    errno.EPERM, "Repo Manager destination file is not trusted"
                )
            os.fchmod(file_descriptor, file_mode)
        except Exception:
            os.close(file_descriptor)
            raise

        display_path = os.path.join(
            os.path.abspath(directory_path), *components
        )
        return file_descriptor, display_path
    finally:
        os.close(directory_descriptor)


def read_secure_text_file(
        file_path, *, max_bytes=1024 * 1024,
        require_trusted_owner=True):
    """Read a bounded, non-writable regular file without following symlinks."""
    if not isinstance(file_path, str) or not os.path.isabs(file_path):
        raise ValueError("Repo Manager secure file path must be absolute")
    directory_path, file_name = os.path.split(file_path)
    if file_name in ("", ".", ".."):
        raise ValueError("Repo Manager secure file path is unsafe")

    directory_descriptor = open_secure_directory(
        directory_path,
        require_trusted_owner=require_trusted_owner,
    )
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        file_descriptor = os.open(
            file_name, flags, dir_fd=directory_descriptor
        )
    finally:
        os.close(directory_descriptor)

    try:
        file_status = os.fstat(file_descriptor)
        if (
                not stat.S_ISREG(file_status.st_mode)
                or file_status.st_nlink != 1
                or (
                    require_trusted_owner
                    and file_status.st_uid not in (0, os.geteuid())
                )
                or file_status.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                or file_status.st_size > max_bytes
        ):
            raise PermissionError(
                errno.EPERM, "Repo Manager source file is not trusted"
            )
        with os.fdopen(file_descriptor, "r", encoding="utf-8") as source_file:
            file_descriptor = None
            content = source_file.read(max_bytes + 1)
            if len(content.encode("utf-8")) > max_bytes:
                raise ValueError("Repo Manager source file exceeds the allowed size")
            return content
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
