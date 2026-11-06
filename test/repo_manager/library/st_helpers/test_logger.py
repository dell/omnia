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
Test Logger — Structured logging for system tests.
"""

import logging
from typing import Optional


class TestLogger:
    """Structured logger for system tests."""

    def __init__(self, test_name: str, test_id: str, level: int = logging.INFO):
        """Initialize test logger.
        
        Args:
            test_name: Human-readable test name
            test_id: Test case ID (e.g., TC-001)
            level: Logging level (default: INFO)
        """
        self.test_name = test_name
        self.test_id = test_id
        self.logger = logging.getLogger(f"st.{test_id}")
        self.logger.setLevel(level)
        
        # Add console handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f"[{test_id}] %(levelname)s: %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)

    def passed(self, message: str) -> None:
        """Log test passed."""
        self.logger.info(f"✓ PASSED: {message}")

    def failed(self, message: str, details: Optional[str] = None) -> None:
        """Log test failed."""
        msg = f"✗ FAILED: {message}"
        if details:
            msg += f"\n  Details: {details}"
        self.logger.error(msg)

    def skipped(self, reason: str) -> None:
        """Log test skipped."""
        self.logger.warning(f"⊘ SKIPPED: {reason}")
