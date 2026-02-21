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

"""Utility functions for the catalog parser package."""

import json
import logging
import os
from typing import Any, Optional


def _configure_logging(log_file: Optional[str] = None, log_level: int = logging.INFO) -> None:
    """Configure root logging.

    If log_file is provided, logs are written to that file and the directory is
    created if needed; otherwise logs go to stderr.

    Note: This function clears existing handlers before configuring, allowing
    multiple calls with different log files to work correctly.
    """
    root_logger = logging.getLogger()

    # Remove existing handlers to allow reconfiguration
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename=log_file,
            encoding="utf-8",
            force=True,
        )
    else:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,
        )


def load_json_file(file_path: str) -> Any:
    """Load and parse a JSON file.

    Args:
        file_path: Path to the JSON file to load.

    Returns:
        The parsed JSON data (dict, list, or other JSON-compatible type).

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    with open(file_path, "r", encoding="utf-8") as json_file:
        return json.load(json_file)
