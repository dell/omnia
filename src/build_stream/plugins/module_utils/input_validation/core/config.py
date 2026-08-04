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
Core configuration for build_stream input validation.

This module contains domain-specific constants, paths, and file mappings
used across the input validation framework.
"""
import os

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

VALIDATION_LOG_PATH = "/var/log/omnia/build_stream/"

# =============================================================================
# FILE CONFIGURATION
# =============================================================================

VALIDATION_FILES = [
    {
        "config_file": "build_stream_config.yml",
        "schema_file": "build_stream_config.json",
        "required": True,
    },
    {
        "config_file": "build_stream_credentials.yml",
        "schema_file": "build_stream_credentials.json",
        "required": False,
    },
]

# =============================================================================
# VAULT CONFIGURATION
# =============================================================================

VAULT_HEADER = "$ANSIBLE_VAULT"

# =============================================================================
# VALIDATOR ROUTING
# =============================================================================

VALIDATOR_MAP = {
    "build_stream_config.yml": "build_stream_config_validator",
    "build_stream_credentials.yml": "build_stream_credentials_validator",
}

# =============================================================================
# SCHEMA DIRECTORY
# =============================================================================

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema")
