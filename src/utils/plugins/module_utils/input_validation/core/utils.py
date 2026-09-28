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
"""Utility functions for utils domain validation."""

import logging
import os


class ValidationLogger:
    """Simple logger for validation operations."""

    def __init__(self, log_dir, log_name):
        self.log_dir = log_dir
        self.log_name = log_name
        self.log_file = ""
        self.logger = None

        if log_dir:
            try:
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, f"{log_name}.log")
                self.logger = logging.getLogger(log_name)
                self.logger.setLevel(logging.INFO)
                handler = logging.FileHandler(log_file)
                handler.setLevel(logging.INFO)
                formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.log_file = log_file
            except (IOError, OSError):
                # Fallback to no logging if directory creation fails
                pass

    def info(self, message):
        if self.logger:
            self.logger.info(message)

    def error(self, message):
        if self.logger:
            self.logger.error(message)

    def warning(self, message):
        if self.logger:
            self.logger.warning(message)


def create_logger(log_dir, log_name):
    """Create and return a ValidationLogger instance."""
    return ValidationLogger(log_dir, log_name)
