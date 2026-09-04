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

"""Unit tests for Catalog parser."""

import json
import os
import tempfile
from jsonschema import ValidationError
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.catalog.parser import ParseCatalog, _DEFAULT_SCHEMA_PATH


class TestParseCatalog:
    """Tests for ParseCatalog function."""

    def test_parse_valid_catalog_with_default_schema(self) -> None:
        """Test parsing a valid catalog using the default schema."""
        # Create a minimal valid catalog
        catalog_data = {
            "Catalog": {
                "Name": "Test Catalog",
                "Version": "1.0.0",
                "FunctionalLayer": "test-functional",
                "BaseOS": "test-os",
                "Infrastructure": "test-infra",
                "FunctionalPackages": {
                    "pkg1": {
                        "Name": "Test Package",
                        "Type": "test",
                        "Architecture": "x86_64",
                        "SupportedOS": [{"Name": "Ubuntu", "Version": "20.04"}]
                    }
                },
                "OSPackages": {},
                "InfrastructurePackages": {},
                "DriverPackages": {}
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(catalog_data, f)
            catalog_path = f.name

        try:
            # Mock the schema loading to avoid dependency on actual schema file
            mock_schema = {"type": "object", "properties": {"Catalog": {"type": "object"}}}
            
            with patch('core.catalog.parser.load_json_file') as mock_load:
                # Configure mock to return schema for schema_path and catalog data for catalog_path
                def load_side_effect(path):
                    if path == _DEFAULT_SCHEMA_PATH:
                        return mock_schema
                    elif path == catalog_path:
                        return catalog_data
                    else:
                        raise FileNotFoundError(f"Unexpected path: {path}")
                
                mock_load.side_effect = load_side_effect
                
                result = ParseCatalog(catalog_path)
                
                # The function should return some object (we don't need to check the exact type)
                assert result is not None
                
        finally:
            os.unlink(catalog_path)

    def test_parse_catalog_with_custom_schema(self) -> None:
        """Test parsing a catalog with a custom schema path."""
        catalog_data = {
            "Catalog": {
                "Name": "Test Catalog",
                "Version": "1.0.0",
                "FunctionalLayer": "test-functional",
                "BaseOS": "test-os",
                "Infrastructure": "test-infra",
                "FunctionalPackages": {},
                "OSPackages": {},
                "InfrastructurePackages": {},
                "DriverPackages": {}
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(catalog_data, f)
            catalog_path = f.name

        custom_schema_path = "/path/to/custom/schema.json"
        mock_schema = {"type": "object", "properties": {"Catalog": {"type": "object"}}}

        try:
            with patch('core.catalog.parser.load_json_file') as mock_load:
                def load_side_effect(path):
                    if path == custom_schema_path:
                        return mock_schema
                    elif path == catalog_path:
                        return catalog_data
                    else:
                        raise FileNotFoundError(f"Unexpected path: {path}")
                
                mock_load.side_effect = load_side_effect
                
                result = ParseCatalog(catalog_path, custom_schema_path)
                
                # The function should return some object
                assert result is not None
                
        finally:
            os.unlink(catalog_path)

    def test_parse_catalog_validation_error_raises_exception(self) -> None:
        """Test that invalid catalog raises ValidationError."""
        # Create an invalid catalog (missing required fields)
        invalid_catalog_data = {"Catalog": {"Name": "Invalid Catalog"}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_catalog_data, f)
            catalog_path = f.name

        # Create a schema that requires more fields
        mock_schema = {
            "type": "object",
            "properties": {
                "Catalog": {
                    "type": "object",
                    "required": ["Name", "Version", "FunctionalLayer", "BaseOS", "Infrastructure"],
                    "properties": {
                        "Name": {"type": "string"},
                        "Version": {"type": "string"},
                        "FunctionalLayer": {"type": "string"},
                        "BaseOS": {"type": "string"},
                        "Infrastructure": {"type": "string"}
                    }
                }
            }
        }

        try:
            with patch('core.catalog.parser.load_json_file') as mock_load:
                def load_side_effect(path):
                    if path == _DEFAULT_SCHEMA_PATH:
                        return mock_schema
                    elif path == catalog_path:
                        return invalid_catalog_data
                    else:
                        raise FileNotFoundError(f"Unexpected path: {path}")
                
                mock_load.side_effect = load_side_effect
                
                with pytest.raises(ValidationError):
                    ParseCatalog(catalog_path)
                    
        finally:
            os.unlink(catalog_path)

    def test_parse_catalog_with_all_package_types(self) -> None:
        """Test parsing catalog with all types of packages."""
        catalog_data = {
            "Catalog": {
                "Name": "Full Catalog",
                "Version": "1.0.0",
                "FunctionalLayer": "test-functional",
                "BaseOS": "test-os",
                "Infrastructure": "test-infra",
                "Drivers": ["test-driver"],
                "FunctionalPackages": {
                    "func1": {
                        "Name": "Functional Package",
                        "Type": "functional",
                        "Architecture": "x86_64",
                        "SupportedOS": [{"Name": "Ubuntu", "Version": "20.04"}],
                        "Version": "1.0",
                        "Tag": "test-tag",
                        "Sources": ["source1"]
                    }
                },
                "OSPackages": {
                    "os1": {
                        "Name": "OS Package",
                        "Type": "os",
                        "Architecture": "x86_64",
                        "SupportedOS": [{"Name": "Ubuntu", "Version": "20.04"}],
                        "Version": "1.0",
                        "Tag": "os-tag",
                        "Sources": ["os-source"]
                    }
                },
                "InfrastructurePackages": {
                    "infra1": {
                        "Name": "Infrastructure Package",
                        "Type": "infrastructure",
                        "Version": "1.0",
                        "Uri": "http://example.com/infra",
                        "Architecture": ["x86_64", "arm64"],
                        "SupportedFunctions": {"function1": "value1"},
                        "Tag": "infra-tag",
                        "Sources": ["infra-source"]
                    }
                },
                "DriverPackages": {
                    "drv1": {
                        "Name": "Driver Package",
                        "Version": "1.0",
                        "Uri": "http://example.com/driver",
                        "Architecture": "x86_64",
                        "Config": {"param1": "value1"},
                        "Type": "driver"
                    }
                },
                "Miscellaneous": ["misc1", "misc2"]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(catalog_data, f)
            catalog_path = f.name

        mock_schema = {"type": "object", "properties": {"Catalog": {"type": "object"}}}

        try:
            with patch('core.catalog.parser.load_json_file') as mock_load:
                def load_side_effect(path):
                    if path == _DEFAULT_SCHEMA_PATH:
                        return mock_schema
                    elif path == catalog_path:
                        return catalog_data
                    else:
                        raise FileNotFoundError(f"Unexpected path: {path}")
                
                mock_load.side_effect = load_side_effect
                
                result = ParseCatalog(catalog_path)
                
                # The function should return some object
                assert result is not None
                
        finally:
            os.unlink(catalog_path)

    def test_parse_catalog_missing_optional_sections(self) -> None:
        """Test parsing catalog with missing optional sections."""
        catalog_data = {
            "Catalog": {
                "Name": "Minimal Catalog",
                "Version": "1.0.0",
                "FunctionalLayer": "test-functional",
                "BaseOS": "test-os",
                "Infrastructure": "test-infra",
                "FunctionalPackages": {},
                "OSPackages": {},
                "InfrastructurePackages": {}
                # No DriverPackages, Drivers, or Miscellaneous
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(catalog_data, f)
            catalog_path = f.name

        mock_schema = {"type": "object", "properties": {"Catalog": {"type": "object"}}}

        try:
            with patch('core.catalog.parser.load_json_file') as mock_load:
                def load_side_effect(path):
                    if path == _DEFAULT_SCHEMA_PATH:
                        return mock_schema
                    elif path == catalog_path:
                        return catalog_data
                    else:
                        raise FileNotFoundError(f"Unexpected path: {path}")
                
                mock_load.side_effect = load_side_effect
                
                result = ParseCatalog(catalog_path)
                
                # The function should return some object
                assert result is not None
                
        finally:
            os.unlink(catalog_path)
