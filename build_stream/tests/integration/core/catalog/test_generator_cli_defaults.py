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
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))  # Go up 5 levels to reach build_stream root
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.catalog.generator import generate_root_json_from_catalog, _DEFAULT_SCHEMA_PATH


class TestGeneratorDefaults(unittest.TestCase):
    def test_default_schema_path_points_to_resources(self):
        # The default schema path should point to the actual resources directory
        expected_schema = os.path.join(PROJECT_ROOT, "core", "catalog", "resources", "CatalogSchema.json")
        self.assertEqual(os.path.abspath(_DEFAULT_SCHEMA_PATH), os.path.abspath(expected_schema))

    def test_generate_root_json_with_defaults_writes_output(self):
        catalog_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "fixtures", "catalogs", "catalog_rhel.json")
        )
        
        # Skip test if fixture doesn't exist
        if not os.path.exists(catalog_path):
            self.skipTest("Catalog fixture not found")
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_root_json_from_catalog(
                catalog_path=catalog_path,
                output_root=tmpdir,
            )

            # We expect at least one arch/os/version directory with functional_layer.json
            found = False
            for root, dirs, files in os.walk(tmpdir):
                if "functional_layer.json" in files:
                    found = True
                    break

            self.assertTrue(found, "functional_layer.json not generated under any arch/os/version")


if __name__ == "__main__":
    unittest.main()
