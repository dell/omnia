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
Unit tests for data_verification.py module
"""

import unittest
import sys
import logging
import os
from unittest.mock import MagicMock

# Add the parent directory to the path to point the module being tested
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import data_verification  # pylint: disable=import-error,wrong-import-position


class TestDataVerification(unittest.TestCase):
    """Tests for the data_verification module."""

    def setUp(self):
        self.data_verification = data_verification

    def tearDown(self):
        pass

    def test_data_verification_file_exists(self):
        """
        Test case for successful data verification.

        This test case validates the data_verification function with a valid input.
        """
        test_file_path = (
        "/opt/omnia/common/library/module_utils/input_validation/schema/provision_config.json")
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)
        self.assertTrue(self.data_verification.file_exists(test_file_path, None, logger))

    def test_data_verification_file_exists_failure(self):
        """
        Test case for failture data verification.

        This test case validates the data_verification function with a valid input.
        """
        test_file_path = "test_file.json"
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)
        module = MagicMock()
        # This module do nothing rather it is a placeholder to return False
        module.fail_json.side_effect = lambda *args, **kwargs: None
        self.assertFalse(self.data_verification.file_exists(test_file_path, module, logger))

    def test_data_verification_directory_exists(self):
        """
        Test case for successful data verification.

        This test case validates the data_verification function with a valid input.
        """
        test_directory_path = "/opt/omnia/input/project_default"
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)
        self.assertTrue(self.data_verification.directory_exists(test_directory_path, None, logger))

    def test_data_verification_directory_exists_failure(self):
        """
        Test case for failture data verification.

        This test case validates the data_verification function with a valid input.
        """
        test_directory_path = "test_file.json"
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)
        module = MagicMock()
        # This module do nothing rather it is a placeholder to return False
        module.fail_json.side_effect = lambda *args, **kwargs: None
        dir_exists = self.data_verification.directory_exists(test_directory_path, module, logger)
        self.assertFalse(dir_exists)


if __name__ == "__main__":
    unittest.main()
