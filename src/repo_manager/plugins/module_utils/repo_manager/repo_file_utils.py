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

"""Safe, shared file operations for generated DNF repository configuration."""

import errno
import os
import stat
import tempfile


def validate_repo_file_target(repo_file_path):
    """Validate a repository-file target before reading or replacing it.

    The caller receives normal ``OSError`` subclasses so it can expose a safe,
    operation-specific result without returning raw exception text.
    """
    if not isinstance(repo_file_path, str) or not repo_file_path.strip():
        raise OSError(
            errno.EINVAL, "repository file path must be a non-empty string"
        )

    destination_directory = os.path.dirname(repo_file_path) or os.curdir
    if not os.path.exists(destination_directory):
        raise FileNotFoundError(
            errno.ENOENT, "repository file destination directory is absent"
        )
    if not os.path.isdir(destination_directory):
        raise NotADirectoryError(
            errno.ENOTDIR, "repository file destination is not a directory"
        )

    file_system = os.statvfs(destination_directory)
    if file_system.f_flag & getattr(os, "ST_RDONLY", 1):
        raise OSError(
            errno.EROFS, "repository file destination is read-only"
        )

    if os.path.lexists(repo_file_path):
        target_mode = os.lstat(repo_file_path).st_mode
        if stat.S_ISLNK(target_mode):
            raise OSError(
                errno.ELOOP, "repository file target must not be a symlink"
            )
        if not stat.S_ISREG(target_mode):
            raise OSError(
                errno.EINVAL, "repository file target must be a regular file"
            )

    return destination_directory


def atomic_write_repo_file(repo_file_path, desired_content, mode=0o644):
    """Atomically replace a DNF repository file and preserve it on failure.

    Returns ``True`` when the file changed and ``False`` when the existing
    regular file already contains the requested content.
    """
    destination_directory = validate_repo_file_target(repo_file_path)

    try:
        with open(repo_file_path, "r", encoding="utf-8") as current_file:
            if current_file.read() == desired_content:
                return False
    except FileNotFoundError:
        pass

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=destination_directory,
                prefix=f".{os.path.basename(repo_file_path)}.",
                delete=False) as repo_file:
            temporary_path = repo_file.name
            repo_file.write(desired_content)
            repo_file.flush()
            os.fsync(repo_file.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, repo_file_path)
        temporary_path = None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)

    return True


def repo_file_error_message(error):
    """Return a non-sensitive operator message for a repository-file error."""
    error_number = getattr(error, "errno", None)
    if error_number in (errno.EACCES, errno.EPERM):
        return "DNF repository destination is not writable"

    messages = {
        errno.EROFS: "DNF repository destination filesystem is read-only",
        errno.ENOENT: "DNF repository destination directory does not exist",
        errno.ENOSPC: (
            "DNF repository destination filesystem has no free space"
        ),
        errno.ELOOP: (
            "DNF repository file target must not be a symbolic link"
        ),
        errno.EINVAL: "DNF repository file destination is invalid",
        errno.ENOTDIR: "DNF repository file destination is invalid",
    }
    return messages.get(
        error_number, "Unable to write the configured DNF repository file"
    )
