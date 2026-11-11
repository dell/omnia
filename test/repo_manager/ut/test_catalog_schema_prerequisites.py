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

"""Requested schema validation must run before a catalog is accepted or edited."""

import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from source_loader import REPO_MANAGER_ROOT, REPOSITORY_ROOT
from ansible.module_utils.catalog import catalog_manager


SCHEMA = str(REPO_MANAGER_ROOT / "schemas" / "catalog_schema.json")
SAMPLE = (
    REPOSITORY_ROOT
    / "src/main/samples/catalogs/rhel/10.2/slurm_x86_64.json"
)


class SchemaPrerequisiteTests(unittest.TestCase):
    """Missing validation prerequisites cannot be mistaken for schema success."""

    def setUp(self):
        self.catalog = json.loads(SAMPLE.read_text(encoding="utf-8"))

    def test_valid_catalog_passes_with_schema_library_available(self):
        """The ordinary schema-validated path remains successful."""
        issues = catalog_manager.validate_catalog(self.catalog, SCHEMA)
        self.assertFalse([issue for issue in issues if issue["severity"] == "error"])

    def test_missing_library_rejects_valid_and_invalid_catalogs(self):
        """No schema conclusion is possible without the requested validator."""
        for version in (2, "invalid"):
            with self.subTest(schema_version=version):
                self.catalog["catalog"]["schema_version"] = version
                with patch.dict(sys.modules, {"jsonschema": None}):
                    issues = catalog_manager.validate_catalog(self.catalog, SCHEMA)
                self.assertTrue(any(issue["severity"] == "error"
                                    and "jsonschema" in issue["message"] for issue in issues))

    def test_invalid_catalog_is_rejected_when_schema_runs(self):
        """A schema-only type violation is still caught with the library present."""
        self.catalog["catalog"]["schema_version"] = "invalid"
        issues = catalog_manager.validate_catalog(self.catalog, SCHEMA)
        self.assertTrue(any(issue["severity"] == "error"
                            and "Schema validation failed" in issue["message"] for issue in issues))

    def test_missing_schema_is_an_error(self):
        """A supplied schema path must exist, even for a valid catalog."""
        with tempfile.TemporaryDirectory() as directory:
            issues = catalog_manager.validate_catalog(
                self.catalog, str(Path(directory) / "missing.json"))
        self.assertTrue(any(issue["severity"] == "error"
                            and "Schema file not found" in issue["message"] for issue in issues))

    def test_unreadable_schema_is_an_error(self):
        """Permission/read failures are reported as validation errors."""
        with patch("builtins.open", side_effect=PermissionError):
            issues = catalog_manager.validate_catalog(self.catalog, SCHEMA)
        self.assertTrue(any(issue["severity"] == "error"
                            and "could not be read" in issue["message"] for issue in issues))

    def test_no_schema_keeps_explicit_business_rule_only_behavior(self):
        """Callers that never requested a schema do not require jsonschema."""
        with patch.dict(sys.modules, {"jsonschema": None}):
            issues = catalog_manager.validate_catalog(self.catalog)
        self.assertFalse([issue for issue in issues if issue["severity"] == "error"])

    def test_commands_fail_without_touching_catalogs_or_outputs(self):
        """Validate, add, delete, and diff fail closed for either missing prerequisite."""
        commands = (
            (catalog_manager.cmd_validate, ""),
            (catalog_manager.cmd_add, "[baseos_group]\ncurl, rpm, curl, baseos\n"),
            (catalog_manager.cmd_delete, "[baseos_group]\niproute\n"),
            (catalog_manager.cmd_diff, ""),
        )
        for missing in ("library", "schema"):
            for command, input_text in commands:
                with self.subTest(prerequisite=missing, command=command.__name__):
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory)
                        current = root / "current.json"
                        future = root / "future.json"
                        original = SAMPLE.read_bytes()
                        current.write_bytes(original)
                        future.write_bytes(original)
                        input_file = root / "input.txt"
                        input_file.write_text(input_text, encoding="utf-8")
                        outputs = [root / filename for filename in (
                            "forward.json", "reverse.json", "changelog.md", "changelog.html")]
                        # Existing artifacts must survive rejection byte-for-byte too.
                        for output in outputs:
                            output.write_text("existing artifact", encoding="utf-8")
                        args = argparse.Namespace(
                            catalog=str(current), input=str(input_file), output=None,
                            schema=SCHEMA if missing == "library" else str(root / "missing.json"),
                            validate=True, catalog_root=str(root), default_arch="x86_64",
                            default_os="rhel", default_os_version="10.2",
                            current=str(current), future=str(future),
                            output_forward=str(outputs[0]), output_reverse=str(outputs[1]),
                            output_changelog=str(outputs[2]), output_html=str(outputs[3]),
                        )
                        with patch.dict(
                            sys.modules, {"jsonschema": None} if missing == "library" else {}
                        ), redirect_stdout(io.StringIO()):
                            result = command(args)
                        self.assertEqual(result, 1)
                        self.assertEqual(current.read_bytes(), original)
                        self.assertEqual(future.read_bytes(), original)
                        for output in outputs:
                            self.assertEqual(
                                output.read_text(encoding="utf-8"), "existing artifact")


if __name__ == "__main__":
    unittest.main()
