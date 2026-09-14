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


def _validate_directory(directory_descriptor):
    """Reject a directory component that another local user can replace."""
    directory_status = os.fstat(directory_descriptor)
    if not stat.S_ISDIR(directory_status.st_mode):
        raise OSError(errno.ENOTDIR, "Repo Manager path component is not a directory")

    effective_uid = os.geteuid()
    if directory_status.st_uid not in (0, effective_uid):
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


def open_secure_directory(directory_path, create=False, mode=0o700):
    """Open a directory without following any component symlinks.

    Every component must be owned by root or the effective user and must not
    be group/world writable. A root-owned sticky directory such as ``/tmp`` is
    accepted because other users cannot replace entries they do not own.
    Missing components are created relative to an already validated parent.
    The caller owns the returned descriptor.
    """
    if not isinstance(directory_path, str) or not directory_path:
        raise ValueError("Repo Manager directory path must be a non-empty string")

    absolute_path = os.path.abspath(directory_path)
    flags = _directory_flags()
    current_descriptor = os.open(os.path.sep, flags)
    try:
        _validate_directory(current_descriptor)
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
                _validate_directory(next_descriptor)
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
