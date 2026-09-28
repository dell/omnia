# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Tests for Repo Manager dataset-generation safety boundaries."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


GENERATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "generator"
    / "generate_dataset.py"
)
SPEC = importlib.util.spec_from_file_location(
    "repo_manager_dataset_generator", GENERATOR_PATH
)
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


class DatasetGeneratorTests(unittest.TestCase):
    """Require contained output, explicit inputs, and secret-free overrides."""

    def test_dataset_name_rejects_path_traversal(self):
        """Dataset names cannot escape the datasets directory."""
        for value in ("../outside", "/tmp/outside", "nested/name", ".."):
            with self.subTest(value=value), self.assertRaises(ValueError):
                generator._dataset_path(value)

    def test_dataset_name_accepts_portable_identifier(self):
        """Normal dataset identifiers resolve directly below datasets/."""
        result = generator._dataset_path("rhel10-x86_64.case-1")
        self.assertEqual(result.parent, generator.DATASETS_DIR.resolve())

    def test_secret_like_override_is_rejected(self):
        """Credentials cannot be written into a generated dataset via --var."""
        with self.assertRaises(ValueError):
            generator._validate_override_key(
                "registry_password", {"registry_password": ""}
            )

    def test_unknown_override_is_rejected(self):
        """Typos cannot silently create unused profile variables."""
        with self.assertRaises(ValueError):
            generator._validate_override_key(
                "pulp_sever_port", {"pulp_server_port": 2225}
            )

    def test_declared_non_secret_override_is_allowed(self):
        """Known operational variables remain configurable."""
        self.assertEqual(
            generator._validate_override_key(
                "pulp_server_port", {"pulp_server_port": 2225}
            ),
            "pulp_server_port",
        )

    def test_from_src_copies_only_public_input_allowlist(self):
        """Source-copy mode never sweeps credentials or unrelated YAML files."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            for filename in generator.SOURCE_INPUT_FILES:
                (source / filename).write_text("---\n{}\n", encoding="utf-8")
            (source / "omnia_config_credentials.yml").write_text(
                "password: secret\n", encoding="utf-8"
            )
            (source / "unrelated.yml").write_text("value: true\n", encoding="utf-8")

            with patch.object(generator, "SRC_INPUT_DIR", source):
                generator._copy_from_src(target)

            copied = sorted(path.name for path in (target / "input").iterdir())
            self.assertEqual(copied, sorted(generator.SOURCE_INPUT_FILES))


if __name__ == "__main__":
    unittest.main()
