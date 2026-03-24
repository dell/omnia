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
import unittest

HERE = os.path.dirname(__file__)
CATALOG_PARSER_DIR = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(CATALOG_PARSER_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from catalog_parser.parser import ParseCatalog, _DEFAULT_SCHEMA_PATH


class TestParseCatalogDefaults(unittest.TestCase):
    def test_default_schema_path_points_to_resources(self):
        catalog_parser_dir = os.path.dirname(os.path.dirname(__file__))
        expected_schema = os.path.join(catalog_parser_dir, "resources", "CatalogSchema.json")
        self.assertEqual(os.path.abspath(_DEFAULT_SCHEMA_PATH), os.path.abspath(expected_schema))

    def test_parse_catalog_with_explicit_paths_uses_fixture(self):
        catalog_parser_dir = os.path.dirname(os.path.dirname(__file__))
        catalog_path = os.path.join(catalog_parser_dir, "test_fixtures", "catalog_rhel.json")
        schema_path = os.path.join(catalog_parser_dir, "resources", "CatalogSchema.json")

        catalog = ParseCatalog(catalog_path, schema_path)
        self.assertGreater(len(catalog.functional_packages), 0)


if __name__ == "__main__":
    unittest.main()
