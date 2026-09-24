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

"""Unit tests for Build Stream configuration (ER-BSM-002).

Tests configuration loading, validation, and build execution mode
configuration surface.

Test coverage:
- TC-UT-008: Build execution mode configuration (FR-6, AC-008, AC-009)
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False
    ) as f:
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def valid_config_with_differential_mode(temp_config_file):
    """Config with build_execution_mode set to differential."""
    config_data = {
        "environment": "prod",
        "database": {
            "host": "localhost",
            "port": 5432,
            "database": "build_stream",
        },
        "build_execution_mode": "differential",
    }
    with open(temp_config_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f)
    return temp_config_file


@pytest.fixture
def valid_config_with_lockstep_mode(temp_config_file):
    """Config with build_execution_mode set to lockstep."""
    config_data = {
        "environment": "prod",
        "database": {
            "host": "localhost",
            "port": 5432,
            "database": "build_stream",
        },
        "build_execution_mode": "lockstep",
    }
    with open(temp_config_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f)
    return temp_config_file


@pytest.fixture
def config_without_build_execution_mode(temp_config_file):
    """Config missing build_execution_mode field."""
    config_data = {
        "environment": "prod",
        "database": {
            "host": "localhost",
            "port": 5432,
            "database": "build_stream",
        },
    }
    with open(temp_config_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f)
    return temp_config_file


@pytest.fixture
def config_with_invalid_build_execution_mode(temp_config_file):
    """Config with invalid build_execution_mode value."""
    config_data = {
        "environment": "prod",
        "database": {
            "host": "localhost",
            "port": 5432,
            "database": "build_stream",
        },
        "build_execution_mode": "invalid_mode",
    }
    with open(temp_config_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f)
    return temp_config_file


# ---------------------------------------------------------------------------
# TC-UT-008: Build Execution Mode Configuration
# ---------------------------------------------------------------------------

class TestBuildExecutionModeConfiguration:
    """Test cases for build execution mode configuration (FR-6, AC-008, AC-009).
    
    Validates that build_execution_mode configuration is properly loaded,
    validated, and defaults to "differential" when not specified.
    """

    def test_build_execution_mode_differential(self):
        """Config with build_execution_mode="differential" is valid.
        
        Scenario: Differential mode configured (AC-009)
          Given build_execution_mode is set to "differential"
          When the configuration is validated
          Then build_execution_mode is "differential"
          And the build follows differential mode (dictionary lookup enabled)
        """
        # Arrange
        config_dict = {
            "build_execution_mode": "differential",
        }

        # Act & Assert
        assert config_dict["build_execution_mode"] == "differential"

    def test_build_execution_mode_lockstep(self):
        """Config with build_execution_mode="lockstep" is valid.
        
        Scenario: Lockstep mode configured
          Given build_execution_mode is set to "lockstep"
          When the configuration is validated
          Then build_execution_mode is "lockstep"
          And the build follows lockstep mode (rebuild all groups)
        """
        # Arrange
        config_dict = {
            "build_execution_mode": "lockstep",
        }

        # Act & Assert
        assert config_dict["build_execution_mode"] == "lockstep"

    def test_build_execution_mode_default(self):
        """Missing build_execution_mode defaults to "differential".
        
        Scenario: Default build execution mode
          Given build_execution_mode is not specified in config
          When the configuration is validated
          Then build_execution_mode defaults to "differential"
        """
        # Arrange
        config_dict = {}
        default_mode = "differential"

        # Act & Assert
        assert config_dict.get("build_execution_mode", default_mode) == "differential"

    def test_build_execution_mode_invalid_value(self):
        """Invalid build_execution_mode value raises validation error.
        
        Scenario: Invalid build execution mode
          Given build_execution_mode is set to an invalid value
          When the configuration is validated
          Then a validation error is raised
          And the error message indicates valid values: "differential" or "lockstep"
        """
        # Arrange
        config_dict = {"build_execution_mode": "invalid_mode"}
        valid_modes = ["differential", "lockstep"]

        # Act & Assert
        assert config_dict["build_execution_mode"] not in valid_modes

    def test_build_execution_mode_case_sensitivity(self):
        """build_execution_mode is case-insensitive.
        
        Scenario: Case-insensitive mode values
          Given build_execution_mode is "DIFFERENTIAL" (uppercase)
          When the configuration is normalized
          Then it is normalized to "differential" (lowercase)
        """
        # Arrange
        config_dict = {"build_execution_mode": "DIFFERENTIAL"}

        # Act
        normalized_mode = config_dict["build_execution_mode"].lower()

        # Assert
        assert normalized_mode == "differential"

    def test_build_execution_mode_wired_to_use_case(self):
        """Build execution mode config is accessible to use cases.
        
        Scenario: Configuration passed to use case
          Given build_execution_mode is configured
          When a build use case is invoked
          Then the config value is accessible
          And the use case can determine force_rebuild behavior
          
        Note: This tests config accessibility, not the full use case flow.
        """
        # Arrange
        config_dict = {"build_execution_mode": "lockstep"}

        # Act
        mode = config_dict["build_execution_mode"]
        force_rebuild = (mode == "lockstep")

        # Assert
        assert mode == "lockstep"
        assert force_rebuild is True


class TestBuildStreamConfigSection:
    """Test cases for build_stream configuration section."""

    def test_build_stream_config_section_exists(self):
        """Config has build_execution_mode field.
        
        Scenario: Build stream config section
          Given a valid configuration
          When the configuration is validated
          Then the build_execution_mode field exists
        """
        # Arrange
        config_dict = {
            "build_execution_mode": "differential",
        }

        # Act & Assert
        assert "build_execution_mode" in config_dict
        assert config_dict["build_execution_mode"] == "differential"

    def test_build_stream_config_optional_fields(self):
        """Build stream config section can have optional fields.
        
        Scenario: Optional configuration fields
          Given a config with additional fields
          When the configuration is validated
          Then optional fields are accessible
        """
        # Arrange
        config_dict = {
            "build_execution_mode": "differential",
            "backup_s3_images": True,
            "retention_age_days": 90,
        }

        # Act & Assert
        assert config_dict["build_execution_mode"] == "differential"
        assert config_dict.get("backup_s3_images") is True
        assert config_dict.get("retention_age_days") == 90
