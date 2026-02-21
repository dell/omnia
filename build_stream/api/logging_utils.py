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

"""Generic secure logging utilities for Build Stream API."""

import logging
from typing import Optional


def log_secure_info(level: str, message: str, identifier: Optional[str] = None) -> None:
    """Log information securely with optional identifier truncation.
    
    This function provides consistent secure logging across all modules.
    When an identifier is provided, only the first 8 characters are logged
    to prevent exposure of sensitive data while maintaining debugging capability.
    
    Args:
        level: Log level ('info', 'warning', 'error', 'debug', 'critical')
        message: Log message template
        identifier: Optional identifier (client_id, token_id, etc.) - first 8 chars logged
    """
    logger = logging.getLogger(__name__)

    if identifier:
        # Always log first 8 characters for identification
        log_message = f"{message}: {identifier[:8]}..."
    else:
        # Generic message when no identifier context
        log_message = message

    log_func = getattr(logger, level)
    log_func(log_message)
