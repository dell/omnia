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
from jsonschema import ValidationError

HERE = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))  # Go up 5 levels to reach build_stream root
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.catalog.generator import (
    FeatureList,
    serialize_json,
    get_functional_layer_roles_from_file,
)


class TestGetFunctionalLayerRolesFromFile(unittest.TestCase):
    def test_returns_all_role_names_from_fixture(self):
        fixture_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "fixtures", "catalogs", "functional_layer.json")
        )

        roles = get_functional_layer_roles_from_file(fixture_path)

        expected_roles = [
            "Compiler",
            "K8S Controller",
            "K8S Worker",
            "Login Node",
            "Slurm Controller",
            "Slurm Worker",
        ]

        self.assertCountEqual(roles, expected_roles)

    def test_empty_feature_list_returns_empty_roles(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_feature_list = FeatureList(features={})
            json_path = os.path.join(tmp_dir, "functional_layer.json")
            serialize_json(empty_feature_list, json_path)

            roles = get_functional_layer_roles_from_file(json_path)

            self.assertEqual(roles, [])

    def test_invalid_functional_layer_json_fails_schema_validation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Missing required 'architecture' field for a package item
            invalid_json = {
                "SomeRole": {
                    "packages": [
                        {
                            "package": "firewalld",
                            "type": "rpm",
                            "repo_name": "x86_64_baseos",
                        }
                    ]
                }
            }
            json_path = os.path.join(tmp_dir, "functional_layer_invalid.json")
            with open(json_path, "w") as f:
                import json

                json.dump(invalid_json, f)

            with self.assertRaises(ValidationError):
                get_functional_layer_roles_from_file(json_path)


if __name__ == "__main__":
    unittest.main()
