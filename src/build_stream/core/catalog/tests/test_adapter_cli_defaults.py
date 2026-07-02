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
import tempfile
import unittest

HERE = os.path.dirname(__file__)
CATALOG_PARSER_DIR = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(CATALOG_PARSER_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from catalog_parser.adapter import generate_omnia_json_from_catalog, _DEFAULT_SCHEMA_PATH


class TestAdapterDefaults(unittest.TestCase):
    def test_default_schema_path_points_to_resources(self):
        catalog_parser_dir = os.path.dirname(os.path.dirname(__file__))
        expected_schema = os.path.join(catalog_parser_dir, "resources", "CatalogSchema.json")
        self.assertEqual(os.path.abspath(_DEFAULT_SCHEMA_PATH), os.path.abspath(expected_schema))

    def test_generate_omnia_json_with_defaults_writes_output(self):
        catalog_parser_dir = os.path.dirname(os.path.dirname(__file__))
        catalog_path = os.path.join(catalog_parser_dir, "test_fixtures", "catalog_rhel.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_omnia_json_from_catalog(
                catalog_path=catalog_path,
                output_root=tmpdir,
            )

            # We expect some JSON files under arch/os/version
            found_any_json = False
            for root, dirs, files in os.walk(tmpdir):
                if any(f.endswith('.json') for f in files):
                    found_any_json = True
                    break

            self.assertTrue(found_any_json, "No JSON configs generated under any arch/os/version")


if __name__ == "__main__":
    unittest.main()
