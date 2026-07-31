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

"""Unit tests for generate_admin_inventory_csv."""

# pylint: disable=missing-function-docstring,redefined-outer-name
import csv

from backend.services.config_file_generators import generate_admin_inventory_csv


class TestGenerateAdminInventoryCsv:
    """Tests for generate_admin_inventory_csv generator."""

    def test_writes_correct_header(self, tmp_path, sample_admin_inventory_rows):
        wizard_data = {"admin_inventory_data": sample_admin_inventory_rows}
        generate_admin_inventory_csv(wizard_data, tmp_path, lambda p: None)

        csv_path = tmp_path / "admin_inventory.csv"
        assert csv_path.exists()
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
        expected = [
            "SERVICE_TAG", "GROUP_NAME",
            "FUNCTIONAL_GROUP_NAME", "ROW",
            "RACK", "SLOT", "RANGE",
        ]
        assert header == expected

    def test_writes_correct_row_count(self, tmp_path, sample_admin_inventory_rows):
        wizard_data = {"admin_inventory_data": sample_admin_inventory_rows}
        generate_admin_inventory_csv(wizard_data, tmp_path, lambda p: None)

        csv_path = tmp_path / "admin_inventory.csv"
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 3  # header + 2 data rows

    def test_skips_when_no_data(self, tmp_path):
        wizard_data = {}
        generate_admin_inventory_csv(wizard_data, tmp_path, lambda p: None)
        assert not (tmp_path / "admin_inventory.csv").exists()

    def test_skips_when_empty_list(self, tmp_path):
        wizard_data = {"admin_inventory_data": []}
        generate_admin_inventory_csv(wizard_data, tmp_path, lambda p: None)
        assert not (tmp_path / "admin_inventory.csv").exists()

    def test_calls_ensure_directory_fn(self, tmp_path, sample_admin_inventory_rows):
        calls = []
        wizard_data = {"admin_inventory_data": sample_admin_inventory_rows}
        generate_admin_inventory_csv(wizard_data, tmp_path, lambda p: calls.append(p))
        assert len(calls) == 1

    def test_extra_keys_ignored(self, tmp_path):
        """Extra keys not in _ADMIN_INVENTORY_CSV_COLUMNS should be ignored."""
        wizard_data = {
            "admin_inventory_data": [
                {
                    "SERVICE_TAG": "SVC001",
                    "GROUP_NAME": "",
                    "FUNCTIONAL_GROUP_NAME": "",
                    "ROW": "",
                    "RACK": "",
                    "SLOT": "",
                    "RANGE": "",
                    "EXTRA_FIELD": "should_not_appear",
                }
            ]
        }
        generate_admin_inventory_csv(wizard_data, tmp_path, lambda p: None)

        csv_path = tmp_path / "admin_inventory.csv"
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert "EXTRA_FIELD" not in row

    def test_missing_optional_fields_default_to_empty(self, tmp_path):
        wizard_data = {
            "admin_inventory_data": [{"SERVICE_TAG": "SVC001"}]
        }
        generate_admin_inventory_csv(wizard_data, tmp_path, lambda p: None)

        csv_path = tmp_path / "admin_inventory.csv"
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["GROUP_NAME"] == ""
        assert row["FUNCTIONAL_GROUP_NAME"] == ""
