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
"""File utilities for utils domain validation."""

import json
import yaml
from ansible.module_utils.input_validation.core.config import VAULT_HEADER


def is_vault_encrypted(file_path):
    """Check if a file is Ansible vault encrypted."""
    try:
        with open(file_path, 'r') as f:
            first_line = f.readline().strip()
        return first_line.startswith(VAULT_HEADER)
    except (IOError, OSError):
        return False


def load_yaml(file_path):
    """Load YAML file and return parsed data."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


def load_json(file_path):
    """Load JSON file and return parsed data."""
    with open(file_path, 'r') as f:
        return json.load(f)
