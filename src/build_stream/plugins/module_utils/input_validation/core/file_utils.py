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
File I/O utilities for build_stream input validation.

Provides YAML/JSON loading and Ansible Vault detection.
"""
import json
import os

import yaml

from ansible.module_utils.input_validation.core.config import VAULT_HEADER  # pylint: disable=E0401


def is_vault_encrypted(path):
    """Check if a file is Ansible Vault encrypted."""
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    return first_line.startswith(VAULT_HEADER)


def load_yaml(path):
    """Load a YAML file, returning None on failure."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path):
    """Load a JSON file, returning None on failure."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
