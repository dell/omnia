# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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
#!/usr/bin/env python3
"""
Unit tests for validation_utils.py module
"""

import unittest
import sys
import os
import yaml
from unittest.mock import patch, MagicMock, mock_open

# # Add the parent directory to the path to point the module being tested
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import validation_utils  # pylint: disable=import-error,wrong-import-position


class TestValidationUtils(unittest.TestCase):
    """Tests for the config module."""

    def setUp(self):
        self.validation_utils = validation_utils

    def test_load_yaml_as_json(self):
        """Test that YAML file is loaded correctly."""
        # Mock setup
        mock_yaml_content = """
            key1: value1
            key2: value2
            nested:
            subkey: subvalue
        """
        expected_data = {
            "key1": "value1",
            "key2": "value2",
            "nested": {"subkey": "subvalue"}
        }

        # Create mock objects
        mock_logger = MagicMock()
        mock_module = MagicMock()

        # Mock the file operations
        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            with patch("yaml.safe_load", return_value=expected_data):
                with patch.object(validation_utils, "is_file_encrypted", return_value=False):
                    result = validation_utils.load_yaml_as_json(
                        "test.yml", "/omnia/base", "project_name", mock_logger, mock_module)

                    # Verify the result
                    self.assertEqual(result, expected_data)
                    # Verify that logger and module were not called for errors
                    mock_logger.error.assert_not_called()
                    mock_module.fail_json.assert_not_called()


    def test_load_yaml_as_json_with_yaml_error(self):
        """Test handling of YAML syntax errors."""
        # Mock setup
        mock_yaml_content = """
            key1: value1
            key2: value2
            indentation_error
        """

        # Create a YAMLError with problem_mark attributes
        yaml_error = yaml.YAMLError()
        yaml_error.problem_mark = MagicMock()
        yaml_error.problem_mark.line = 3
        yaml_error.problem_mark.column = 4
        yaml_error.problem = "mapping values are not allowed here"
        yaml_error.context = "while parsing a block mapping"

        # Create mock objects
        mock_logger = MagicMock()
        mock_module = MagicMock()

        # Mock the file operations
        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            with patch("yaml.safe_load", side_effect=yaml_error):
                with patch.object(validation_utils, "is_file_encrypted", return_value=False):
                    # Call the function
                    result = validation_utils.load_yaml_as_json(
                        "test.yml", "/omnia/base", "project_name", mock_logger, mock_module)

                    # Verify the result is None for YAML errors
                    self.assertIsNone(result)
                    # Verify that logger was called with error
                    mock_logger.error.assert_called_once()
                    # Verify error message contains line and column information
                    error_msg = mock_logger.error.call_args[0][0]
                    self.assertIn("line 4", error_msg)
                    self.assertIn("column 5", error_msg)

    def test_create_error_msg(self):
        """Test that error message is created correctly."""
        result = validation_utils.create_error_msg("test_key", "test_value", "test_message")
        expected = {
            "error_key": "test_key",
            "error_value": "test_value",
            "error_msg": "test_message"
        }
        self.assertEqual(result, expected)

    def test_create_error_msg_with_empty_values(self):
        """Test with empty values."""
        result = validation_utils.create_error_msg("", "", "")
        expected = {
            "error_key": "",
            "error_value": "",
            "error_msg": ""
        }
        self.assertEqual(result, expected)

    def test_create_file_path(self):
        """Test that file path is created correctly."""
        result = validation_utils.create_file_path("/path/to/file.txt", "newfile.txt")
        expected = "/path/to/newfile.txt"
        self.assertEqual(result, expected)

    def test_create_file_path_with_no_directory(self):
        """Test with filename only (no directory)."""
        result = validation_utils.create_file_path("file.txt", "newfile.txt")
        expected = "newfile.txt"
        self.assertEqual(result, expected)

    def test_create_file_path_with_empty_filename(self):
        """Test with empty new filename."""
        result = validation_utils.create_file_path("/path/to/file.txt", "")
        expected = "/path/to/"
        self.assertEqual(result, expected)

    def test_contains_software(self):
        """Test that software is found in the list."""
        # Setup test data
        softwares = [
            {"name": "Kubernetes"},
            {"name": "Docker"},
            {"name": "Ansible"}
        ]

        # Test with exact match (case-insensitive)
        result = validation_utils.contains_software(softwares, "kubernetes")
        self.assertTrue(result)

        # Test with partial match (case-insensitive)
        result = validation_utils.contains_software(softwares, "kube")
        self.assertTrue(result)

        # Test with non-existent software
        result = validation_utils.contains_software(softwares, "DOCKER")
        self.assertFalse(result)
        result = validation_utils.contains_software(softwares, "terraform")
        self.assertFalse(result)


    if __name__ == "__main__":
        unittest.main()
