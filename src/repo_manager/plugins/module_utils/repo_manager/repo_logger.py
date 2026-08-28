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
Thread-safe logger for RPM repository processing.
"""

import logging
import threading


class RepoLogger:
    """
    Thread-safe logger for RPM repository processing.

    Provides thread-safe logging with thread identifier and repo name.
    """

    def __init__(self, log_file_path):
        """
        Initialize the thread-safe logger.

        Args:
            log_file_path (str): Path to the log file
        """
        self.log_file_path = log_file_path
        self.log_lock = threading.Lock()

        # Setup logger
        self.logger = logging.getLogger('rpm_repo_processor')
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers
        self.logger.handlers = []

        # File handler
        file_handler = logging.FileHandler(log_file_path, mode='a')
        file_handler.setLevel(logging.INFO)

        # Formatter with thread identifier
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-5s [%(threadName)s] [%(filename)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def log_info(self, message):
        """
        Log an info message (thread-safe).

        Args:
            message (str): Message to log
        """
        with self.log_lock:
            self.logger.info(message)

    def log_error(self, message):
        """
        Log an error message (thread-safe).

        Args:
            message (str): Message to log
        """
        with self.log_lock:
            self.logger.error(message)

    def log_warning(self, message):
        """
        Log a warning message (thread-safe).

        Args:
            message (str): Message to log
        """
        with self.log_lock:
            self.logger.warning(message)

    def log_repo(self, repo_name, level, message):
        """
        Log a message with repo name (thread-safe).

        Args:
            repo_name (str): Repository name
            level (str): Log level (INFO, WARN, ERROR)
            message (str): Message to log
        """
        with self.log_lock:
            if level == "ERROR":
                self.logger.error(f"[{repo_name}] {message}")
            elif level == "WARN":
                self.logger.warning(f"[{repo_name}] {message}")
            else:
                self.logger.info(f"[{repo_name}] {message}")
