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
Generic validation helpers for image_build_manager input validation.
"""
import logging
import os


def create_logger(log_path, project_name):
    """
    Create a logger for image_build validation.

    Args:
        log_path (str): Base directory for log files.
        project_name (str): Project name used in the log filename.

    Returns:
        tuple: (logger, log_file_path)
    """
    log_file = os.path.join(
        log_path, f"image_build_validation_{project_name}.log"
    )
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        filename=log_file,
        format="%(asctime)s %(levelname)s %(message)s",
        filemode="w",
    )
    logger = logging.getLogger("image_build_validation")
    logger.setLevel(logging.DEBUG)
    return logger, log_file
