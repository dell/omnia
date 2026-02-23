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

import os
import sys
import pytest

HERE = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))  # Go up 4 levels to reach build_stream root
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.catalog.parser import ParseCatalog, _DEFAULT_SCHEMA_PATH


class TestParseCatalogDefaults:
    def test_default_schema_path_points_to_resources(self):
        # The default schema path should point to the actual resources directory in core/catalog
        expected_schema = os.path.join(PROJECT_ROOT, "core", "catalog", "resources", "CatalogSchema.json")
        assert os.path.abspath(_DEFAULT_SCHEMA_PATH) == os.path.abspath(expected_schema)

    def test_parse_catalog_with_explicit_paths_uses_fixture(self):
        # Use the fixtures directory for test data
        fixtures_dir = os.path.join(PROJECT_ROOT, "tests", "fixtures", "catalogs")
        catalog_path = os.path.join(fixtures_dir, "catalog_rhel.json")
        schema_path = os.path.join(PROJECT_ROOT, "core", "catalog", "resources", "CatalogSchema.json")

        # Skip test if fixtures don't exist
        if not os.path.exists(catalog_path) or not os.path.exists(schema_path):
            pytest.skip("Test fixtures not found")

        catalog = ParseCatalog(catalog_path, schema_path)
        assert len(catalog.functional_packages) > 0
