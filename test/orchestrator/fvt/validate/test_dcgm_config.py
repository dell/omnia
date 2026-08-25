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
Unit test for DCGM configuration in orchestrator_config.yml
Tests that dcgm_enabled is properly defined in schema and defaults to true
"""

import json
import os
import yaml


# Resolve paths relative to repo root (test/ -> repo/)
_TEST_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)))
_REPO_ROOT = os.path.dirname(_TEST_DIR)

_SCHEMA_PATH = os.path.join(
    _REPO_ROOT, "src", "orchestrator",
    "plugins", "module_utils", "orchestrator_validation",
    "schema", "orchestrator_config.json",
)
_INPUT_CONFIG_PATH = os.path.join(
    _REPO_ROOT, "src", "orchestrator", "input", "orchestrator_config.yml",
)


def test_dcgm_enabled_in_schema():
    """Test that dcgm_enabled is defined in orchestrator_config.json schema"""
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    assert "dcgm_enabled" in schema["properties"], (
        "dcgm_enabled should be in schema properties"
    )
    assert schema["properties"]["dcgm_enabled"]["type"] == "boolean", (
        "dcgm_enabled should be boolean type"
    )
    assert schema["properties"]["dcgm_enabled"]["default"] is True, (
        "dcgm_enabled should default to true"
    )


def test_dcgm_enabled_in_input_file():
    """Test that dcgm_enabled is defined in orchestrator_config.yml input file"""
    with open(_INPUT_CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "dcgm_enabled" in config, (
        "dcgm_enabled should be in orchestrator_config.yml"
    )
    assert config["dcgm_enabled"] is True, (
        "dcgm_enabled should default to true in input file"
    )


def test_dcgm_enabled_boolean_values():
    """Test that dcgm_enabled accepts boolean values"""
    with open(_INPUT_CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Test setting to false
    config["dcgm_enabled"] = False
    assert config["dcgm_enabled"] is False, "dcgm_enabled should accept false"

    # Test setting to true
    config["dcgm_enabled"] = True
    assert config["dcgm_enabled"] is True, "dcgm_enabled should accept true"
