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

"""Tests for BMC discovery report generation."""

import csv
import os
import tempfile
import unittest

import sys
from unittest.mock import MagicMock

# Mock ansible.module_utils.basic before importing the module under test
sys.modules['ansible'] = MagicMock()
sys.modules['ansible.module_utils'] = MagicMock()
sys.modules['ansible.module_utils.basic'] = MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from generate_discovery_report import generate_report, REPORT_HEADERS


class TestGenerateDiscoveryReport(unittest.TestCase):
    """Test the generate_report function."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.output_file = os.path.join(self.test_dir, "bmc_discovery_report.csv")

    def tearDown(self):
        if os.path.exists(self.output_file):
            os.remove(self.output_file)
        os.rmdir(self.test_dir)

    def _read_csv(self, filepath):
        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            return list(reader)

    def test_report_headers(self):
        """Report CSV should have the correct headers."""
        generate_report([], self.output_file)
        rows = self._read_csv(self.output_file)
        self.assertEqual(rows[0], REPORT_HEADERS)

    def test_empty_servers(self):
        """Empty server list should produce header-only CSV."""
        _, count = generate_report([], self.output_file)
        self.assertEqual(count, 0)
        rows = self._read_csv(self.output_file)
        self.assertEqual(len(rows), 1)

    def test_single_server_all_fields(self):
        """Single server with all fields populated."""
        servers = [{
            "service_tag": "ABC1234",
            "idrac_mac": "AA:BB:CC:DD:EE:FF",
            "idrac_ip": "10.0.0.1",
            "idrac_link_status": "Up",
            "first_nic_mac": "11:22:33:44:55:66",
            "first_nic_link_status": "Up",
            "ib_nic_name": "InfiniBand.Slot.7-1",
            "ib_nic_link_status": "Unknown"
        }]
        _, count = generate_report(servers, self.output_file)
        self.assertEqual(count, 1)
        rows = self._read_csv(self.output_file)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], "ABC1234")
        self.assertEqual(rows[1][1], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(rows[1][2], "10.0.0.1")
        self.assertEqual(rows[1][3], "Up")
        self.assertEqual(rows[1][4], "11:22:33:44:55:66")
        self.assertEqual(rows[1][5], "Up")
        self.assertEqual(rows[1][6], "InfiniBand.Slot.7-1")
        self.assertEqual(rows[1][7], "Unknown")

    def test_server_missing_ib_fields(self):
        """Server without IB NIC should have empty IB columns."""
        servers = [{
            "service_tag": "XYZ9999",
            "idrac_mac": "AA:BB:CC:00:00:01",
            "idrac_ip": "10.0.0.2",
            "idrac_link_status": "Up",
            "first_nic_mac": "11:22:33:00:00:01",
            "first_nic_link_status": "Up",
        }]
        _, count = generate_report(servers, self.output_file)
        self.assertEqual(count, 1)
        rows = self._read_csv(self.output_file)
        self.assertEqual(rows[1][6], "")
        self.assertEqual(rows[1][7], "")

    def test_multiple_servers(self):
        """Multiple servers should produce correct row count."""
        servers = [
            {
                "service_tag": "SRV001",
                "idrac_mac": "AA:00:00:00:00:01",
                "idrac_ip": "10.0.0.1",
                "idrac_link_status": "Up",
                "first_nic_mac": "BB:00:00:00:00:01",
                "first_nic_link_status": "Up",
                "ib_nic_name": "InfiniBand.Slot.7-1",
                "ib_nic_link_status": "Up"
            },
            {
                "service_tag": "SRV002",
                "idrac_mac": "AA:00:00:00:00:02",
                "idrac_ip": "10.0.0.2",
                "idrac_link_status": "Up",
                "first_nic_mac": "BB:00:00:00:00:02",
                "first_nic_link_status": "Down",
                "ib_nic_name": "",
                "ib_nic_link_status": ""
            },
            {
                "service_tag": "SRV003",
                "idrac_mac": "AA:00:00:00:00:03",
                "idrac_ip": "10.0.0.3",
                "idrac_link_status": "Up",
                "first_nic_mac": "BB:00:00:00:00:03",
                "first_nic_link_status": "Up",
                "ib_nic_name": "InfiniBand.Slot.7-1",
                "ib_nic_link_status": "Unknown"
            }
        ]
        _, count = generate_report(servers, self.output_file)
        self.assertEqual(count, 3)
        rows = self._read_csv(self.output_file)
        self.assertEqual(len(rows), 4)

    def test_creates_output_directory(self):
        """Report should create parent directories if they don't exist."""
        nested_path = os.path.join(self.test_dir, "sub", "dir", "report.csv")
        generate_report([], nested_path)
        self.assertTrue(os.path.exists(nested_path))
        # Cleanup nested dirs
        os.remove(nested_path)
        os.rmdir(os.path.join(self.test_dir, "sub", "dir"))
        os.rmdir(os.path.join(self.test_dir, "sub"))

    def test_return_values(self):
        """Should return correct file path and server count."""
        servers = [{"service_tag": "TEST01"}]
        report_file, count = generate_report(servers, self.output_file)
        self.assertEqual(report_file, self.output_file)
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
