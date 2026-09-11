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
Orchestrator Validate — OpenCHAMI Input Validation Tests.

Tests that validate OpenCHAMI-related input configuration files.
"""

from typing import Dict, Any

import pytest
import yaml

from library.functions import TestLogger
from omnia_auto import load_test_config


@pytest.mark.functional
@pytest.mark.order(1)
def test_orchestrator_config_exists(host) -> None:
    """TC_VL_001: Verify orchestrator_config.yml exists on target.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify orchestrator_config.yml exists on target",
        "TC_VL_001"
    )

    config = load_test_config()
    project = config.get("project_name", "project_default")
    config_path = f"/opt/omnia/orchestrator/input/{project}/orchestrator_config.yml"

    config_exists = host.file(config_path).exists

    if config_exists:
        tl.passed(
            "orchestrator_config.yml present",
            f"orchestrator_config.yml found at {config_path}"
        )
    else:
        tl.failed(
            "orchestrator_config.yml missing",
            f"orchestrator_config.yml not found at {config_path}"
        )

    assert config_exists, f"orchestrator_config.yml not found at {config_path}"


@pytest.mark.functional
@pytest.mark.order(2)
def test_pxe_mapping_file_exists(host) -> None:
    """TC_VL_002: Verify pxe_mapping_file.csv exists on target.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify pxe_mapping_file.csv exists on target",
        "TC_VL_002"
    )

    config = load_test_config()
    project = config.get("project_name", "project_default")
    pxe_path = f"/opt/omnia/orchestrator/input/{project}/pxe_mapping_file.csv"

    pxe_exists = host.file(pxe_path).exists

    if pxe_exists:
        tl.passed(
            "pxe_mapping_file.csv present",
            f"pxe_mapping_file.csv found at {pxe_path}"
        )
    else:
        tl.failed(
            "pxe_mapping_file.csv missing",
            f"pxe_mapping_file.csv not found at {pxe_path}"
        )

    assert pxe_exists, f"pxe_mapping_file.csv not found at {pxe_path}"


@pytest.mark.functional
@pytest.mark.order(3)
def test_orchestrator_config_valid_yaml(host) -> None:
    """TC_VL_003: Verify orchestrator_config.yml is valid YAML.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify orchestrator_config.yml is valid YAML",
        "TC_VL_003"
    )

    config = load_test_config()
    project = config.get("project_name", "project_default")
    config_path = f"/opt/omnia/orchestrator/input/{project}/orchestrator_config.yml"

    try:
        content = host.file(config_path).content_string
        parsed: Dict[str, Any] = yaml.safe_load(content)

        if parsed and isinstance(parsed, dict):
            tl.passed(
                "orchestrator_config.yml is valid YAML",
                f"Successfully parsed orchestrator_config.yml with {len(parsed)} top-level keys"
            )
        else:
            tl.failed(
                "orchestrator_config.yml is not a valid YAML dict",
                f"Parsed content is not a dictionary: {type(parsed)}"
            )
            assert False, "orchestrator_config.yml is not a valid YAML dict"
    except yaml.YAMLError as e:
        tl.failed(
            "orchestrator_config.yml has invalid YAML syntax",
            f"YAML parsing error: {str(e)}"
        )
        assert False, f"YAML parsing error: {str(e)}"
    except Exception as e:
        tl.failed(
            "Failed to read orchestrator_config.yml",
            f"Error: {str(e)}"
        )
        assert False, f"Failed to read config: {str(e)}"
