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

"""
File to setup standard logger
"""

from contextlib import contextmanager
import errno
import os
import logging
import stat

from ansible.module_utils.repo_manager.security_utils import (
    redact_url_credentials,
)
from ansible.module_utils.repo_manager.secure_path import open_secure_directory


LOG_DIRECTORY_MODE = 0o700
LOG_FILE_MODE = 0o600


class UrlCredentialRedactionFilter(logging.Filter):  # pylint: disable=too-few-public-methods
    """Remove URL user information before a message reaches any handler."""

    def filter(self, record):
        record.msg = redact_url_credentials(record.getMessage())
        record.args = ()
        return True


def _validate_owned_descriptor(file_status, expected_type, description):
    """Reject an opened object that is unsafe for privileged logging."""
    if not expected_type(file_status.st_mode):
        raise OSError(errno.EINVAL, f"Repo Manager {description} has invalid type")
    if file_status.st_uid != os.geteuid():
        raise PermissionError(
            errno.EPERM, f"Repo Manager {description} has untrusted ownership"
        )
    if file_status.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise PermissionError(
            errno.EPERM, f"Repo Manager {description} is writable by other users"
        )


def _open_secure_log_directory(log_dir):
    """Return a pinned, validated Repo Manager log-directory descriptor."""
    directory_descriptor = open_secure_directory(
        log_dir, create=True, mode=LOG_DIRECTORY_MODE
    )
    try:
        _validate_owned_descriptor(
            os.fstat(directory_descriptor), stat.S_ISDIR, "log directory"
        )
        os.fchmod(directory_descriptor, LOG_DIRECTORY_MODE)
        return directory_descriptor
    except Exception:
        os.close(directory_descriptor)
        raise


def open_secure_log_file(log_filepath, truncate=False):
    """Return a validated log descriptor; the caller must close it."""
    log_dir = os.path.dirname(log_filepath) or "."
    log_name = os.path.basename(log_filepath)
    if log_name in ("", ".", ".."):
        raise ValueError("Repo Manager log filename is invalid")

    directory_descriptor = _open_secure_log_directory(log_dir)
    flags = os.O_WRONLY | os.O_CREAT | os.O_NONBLOCK | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    if not truncate:
        flags |= os.O_APPEND
    file_descriptor = None
    try:
        file_descriptor = os.open(
            log_name,
            flags,
            LOG_FILE_MODE,
            dir_fd=directory_descriptor,
        )
        _validate_owned_descriptor(
            os.fstat(file_descriptor), stat.S_ISREG, "log file"
        )
        os.fchmod(file_descriptor, LOG_FILE_MODE)
        if truncate:
            os.ftruncate(file_descriptor, 0)
        return file_descriptor
    except Exception:
        if file_descriptor is not None:
            os.close(file_descriptor)
        raise
    finally:
        os.close(directory_descriptor)


def secure_log_file(log_filepath):
    """Create or restrict a regular Repo Manager log file."""
    file_descriptor = open_secure_log_file(log_filepath)
    os.close(file_descriptor)


@contextmanager
def secure_log_stream(log_filepath, mode="a"):
    """Yield a text stream backed by the securely opened log descriptor."""
    if mode not in ("a", "w"):
        raise ValueError("Secure Repo Manager log mode must be 'a' or 'w'")
    file_descriptor = open_secure_log_file(
        log_filepath, truncate=(mode == "w")
    )
    try:
        with os.fdopen(file_descriptor, mode, encoding="utf-8") as stream:
            file_descriptor = None
            yield stream
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)


class SecureFileHandler(logging.FileHandler):  # pylint: disable=too-few-public-methods
    """Logging handler that writes through one validated, pinned descriptor."""

    def __init__(self, log_filepath, mode="a"):
        if mode not in ("a", "w"):
            raise ValueError("Secure Repo Manager log mode must be 'a' or 'w'")
        super().__init__(
            log_filepath,
            mode=mode,
            encoding="utf-8",
            delay=True,
        )

        self.stream = self._open()

    def _open(self):
        """Open and return a stream backed by a validated descriptor."""
        file_descriptor = open_secure_log_file(
            self.baseFilename, truncate=(self.mode == "w")
        )
        try:
            return os.fdopen(
                file_descriptor,
                self.mode,
                encoding=self.encoding,
                errors=self.errors,
            )
        except Exception:
            os.close(file_descriptor)
            raise


def setup_standard_logger(log_dir, log_filename="standard.log"):
    """
    Sets up a standard logger to log to a specified file.

    Parameters:
        log_dir (str): The directory where the log file will be saved.
        log_filename (str, optional): The name of the log file. Defaults to "standard.log".

    Returns:
        logging.Logger: The configured logger instance.
    """
    if (
            not isinstance(log_filename, str)
            or not log_filename
            or os.path.isabs(log_filename)
            or os.path.basename(log_filename) != log_filename
    ):
        raise ValueError("Repo Manager log filename must be a basename")
    log_filepath = os.path.join(log_dir, log_filename)

    # Create a logger
    logger = logging.getLogger("task_logger")
    logger.setLevel(logging.DEBUG)

    # Create file handler and set level to debug
    file_handler = SecureFileHandler(log_filepath)
    file_handler.setLevel(logging.DEBUG)
    file_handler.addFilter(UrlCredentialRedactionFilter())

    # Create a console handler for error-level logging to stdout
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.addFilter(UrlCredentialRedactionFilter())

    # Create formatter and add it to handlers
    formatter = logging.Formatter("%(asctime)s - %(levelname)-7s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
