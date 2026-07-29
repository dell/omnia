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

"""Unit tests for generate_pxe_mapping_file."""

import csv
import pytest

from backend.services.config_file_generators import generate_pxe_mapping_file


class TestGeneratePxeMappingFile:
    """Tests for generate_pxe_mapping_file generator."""

    def test_writes_correct_header(self, tmp_path, sample_pxe_rows):
        wizard_data = {"pxe_mapping_data": sample_pxe_rows}
        generate_pxe_mapping_file(wizard_data, tmp_path, lambda p: None)

        csv_path = tmp_path / "pxe_mapping_file.csv"
        assert csv_path.exists()
        with open(csv_path) as f:
            reader = csv.reader(f)
            header = next(reader)
        expected = [
            "FUNCTIONAL_GROUP_NAME", "GROUP_NAME", "SERVICE_TAG",
            "PARENT_SERVICE_TAG", "HOSTNAME", "ADMIN_MAC", "ADMIN_IP",
            "BMC_MAC", "BMC_IP", "IB_NIC_NAME", "IB_IP",
        ]
        assert header == expected

    def test_writes_correct_row_data(self, tmp_path, sample_pxe_rows):
        wizard_data = {"pxe_mapping_data": sample_pxe_rows}
        generate_pxe_mapping_file(wizard_data, tmp_path, lambda p: None)

        csv_path = tmp_path / "pxe_mapping_file.csv"
        with open(csv_path) as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 3  # header + 2 data rows
        assert rows[1][2] == "SVC001"  # SERVICE_TAG

    def test_skips_when_no_data(self, tmp_path):
        generate_pxe_mapping_file({}, tmp_path, lambda p: None)
        assert not (tmp_path / "pxe_mapping_file.csv").exists()

    def test_skips_when_empty_list(self, tmp_path):
        generate_pxe_mapping_file({"pxe_mapping_data": []}, tmp_path, lambda p: None)
        assert not (tmp_path / "pxe_mapping_file.csv").exists()
