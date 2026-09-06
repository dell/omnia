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

import os
import logging
import stat

from ansible.module_utils.repo_manager.security_utils import (
    redact_url_credentials,
)


LOG_DIRECTORY_MODE = 0o700
LOG_FILE_MODE = 0o600


class UrlCredentialRedactionFilter(logging.Filter):
    """Remove URL user information before a message reaches any handler."""

    def filter(self, record):
        record.msg = redact_url_credentials(record.getMessage())
        record.args = ()
        return True


def secure_log_directory(log_dir):
    """Create or restrict a Repo Manager log directory."""
    os.makedirs(log_dir, mode=LOG_DIRECTORY_MODE, exist_ok=True)
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    directory_descriptor = os.open(log_dir, flags)
    try:
        if not stat.S_ISDIR(os.fstat(directory_descriptor).st_mode):
            raise OSError("Repo Manager log path is not a directory")
        os.fchmod(directory_descriptor, LOG_DIRECTORY_MODE)
    finally:
        os.close(directory_descriptor)


def secure_log_file(log_filepath):
    """Create or restrict a regular Repo Manager log file."""
    log_dir = os.path.dirname(log_filepath) or "."
    secure_log_directory(log_dir)

    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    directory_descriptor = os.open(log_dir, directory_flags)

    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        file_descriptor = os.open(
            os.path.basename(log_filepath),
            flags,
            LOG_FILE_MODE,
            dir_fd=directory_descriptor,
        )
        try:
            if not stat.S_ISREG(os.fstat(file_descriptor).st_mode):
                raise OSError("Repo Manager log path is not a regular file")
            os.fchmod(file_descriptor, LOG_FILE_MODE)
        finally:
            os.close(file_descriptor)
    finally:
        os.close(directory_descriptor)


def setup_standard_logger(log_dir, log_filename="standard.log"):
    """
    Sets up a standard logger to log to a specified file.

    Parameters:
        log_dir (str): The directory where the log file will be saved.
        log_filename (str, optional): The name of the log file. Defaults to "standard.log".

    Returns:
        logging.Logger: The configured logger instance.
    """
    log_filepath = os.path.join(log_dir, log_filename)
    secure_log_file(log_filepath)

    # Create a logger
    logger = logging.getLogger("task_logger")
    logger.setLevel(logging.DEBUG)

    # Create file handler and set level to debug
    file_handler = logging.FileHandler(log_filepath)
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
