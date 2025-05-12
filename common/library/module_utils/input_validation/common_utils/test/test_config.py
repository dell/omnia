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
Unit tests for config.py module
"""

import unittest
import sys
import os
from unittest.mock import patch

# Add the parent directory to the path to point the module being tested
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import config  # pylint: disable=import-error,wrong-import-position

class TestConfig(unittest.TestCase):
    """Tests for the config module."""

    def setUp(self):
        self.config = config

    def test_files(self):
        """Test that file_names is set."""
        self.assertIsNotNone(self.config.files)

    def test_input_file_inventory(self):
        """Test that input_file_inventory is set."""
        self.assertIsNotNone(self.config.input_file_inventory)

    def test_input_file_inventory_not_empty(self):
        """Test that input_file_inventory is not empty."""
        self.assertEqual(self.config.input_file_inventory, {
            'scheduler': ['omnia_config.yml', 'software_config.json'],
            'provision': ['provision_config.yml', 'network_spec.yml',
                         'software_config.json', 'roles_config.yml',
                         'high_availability_config.yml'],
            'server_spec': ['server_spec.yml'],
            'security': ['security_config.yml', 'login_node_security_config.yml',
                         'passwordless_ssh_config.yml', 'software_config.json'],
            'monitoring': ['telemetry_config.yml'],
            'local_repo': ['local_repo_config.yml', 'software_config.json'],
            'k8s': ['k8s_access_config.yml'],
            'roce': ['roce_plugin_config.yml'],
            'storage': ['storage_config.yml'],
            'proxy': ['site_config.yml'],
            'prepare_oim': ['high_availability_config.yml',
                            'roles_config.yml', 'network_spec.yml'],
            'high_availability': ['high_availability_config.yml'],
            'all': ['passwordless_ssh_config.yml', 'local_repo_config.yml',
                    'network_spec.yml', 'server_spec.yml', 'omnia_config.yml',
                    'security_config.yml', 'login_node_security_config.yml',
                    'telemetry_config.yml', 'provision_config.yml',
                    'roce_plugin_config.yml', 'k8s_access_config.yml',
                    'software_config.json', 'storage_config.yml', 'roles_config.yml',
                    'high_availability_config.yml']})

    def test_passwords_set(self):
        """Test that passwords_set is set."""
        self.assertIsNotNone(self.config.passwords_set)

    def test_extensions(self):
        """Test that extensions is set."""
        self.assertIsNotNone(self.config.extensions)

    def test_os_version_ranges(self):
        """Test that os_version_ranges is set."""
        self.assertIsNotNone(self.config.os_version_ranges)

    @patch('config.os.path.exists')
    @patch('config.get_vault_password')
    def test_get_vault_password_with_cache(self, mock_get_vault_password, mock_exists): # pylint: disable=unused-argument
        """Test get_vault_password with pre-populated cache"""
        mock_get_vault_password.return_value = 'test_password'
        result = config.get_vault_password('vault_password_file')
        self.assertEqual(result, 'test_password')

if __name__ == "__main__":
    unittest.main()
