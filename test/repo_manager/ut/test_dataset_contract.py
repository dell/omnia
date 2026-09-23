# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Dataset consumer, generator, and publication contracts."""

import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from library.functions import host_func, validation_func
from source_loader import REPOSITORY_ROOT


TEST_ROOT = REPOSITORY_ROOT / "test" / "repo_manager"
DATASETS_ROOT = TEST_ROOT / "datasets"
GENERATOR_PATH = DATASETS_ROOT / "generator" / "generate_dataset.py"
SPEC = importlib.util.spec_from_file_location(
    "repo_manager_dataset_contract_generator", GENERATOR_PATH
)
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


def _config(dataset=""):
    """Return one valid baseline Repo Manager test configuration."""
    return {
        "oim_server_ip": "",
        "clone_path": "/root/omnia",
        "project_name": "project_default",
        "report_path": "/opt/omnia/reports",
        "report_name": "repo_manager_test_report",
        "dataset": dataset,
        "sync_repo_manager_input": False,
    }


def _write_public_input(input_dir, config_content="---\nrepo_config: partial\n"):
    """Write the complete public input contract below *input_dir*."""
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "repo_manager_config.yml").write_text(
        config_content, encoding="utf-8"
    )
    (input_dir / "repo_manager_endpoint_config.yml").write_text(
        "---\npulp_server_port: 2225\n", encoding="utf-8"
    )


def _files(directory):
    """Return deterministic file bytes indexed by relative path."""
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


class DatasetContractTests(unittest.TestCase):
    """Keep Repo Manager datasets aligned with the shared framework contract."""

    def test_checked_in_dataset_is_current(self):
        """The committed default dataset remains reproducible from its profile."""
        result = generator.main(["data_set_01", "defaults", "--check"])
        self.assertEqual(result, 0)

    def test_dry_run_generates_without_publishing(self):
        """Dry-run validates all artifacts and leaves no dataset behind."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            with patch.object(generator, "DATASETS_DIR", root):
                result = generator.main(
                    ["dry_run_case", "defaults", "--dry-run"]
                )
            self.assertEqual(result, 0)
            self.assertFalse((root / "dry_run_case").exists())
            self.assertEqual(list(root.iterdir()), [])

    def test_check_mode_detects_dataset_drift(self):
        """Check mode succeeds for current output and fails after modification."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            with patch.object(generator, "DATASETS_DIR", root):
                self.assertEqual(generator.main(["check_case", "defaults"]), 0)
                self.assertEqual(
                    generator.main(["check_case", "defaults", "--check"]),
                    0,
                )
                endpoint = (
                    root
                    / "check_case"
                    / "input"
                    / "repo_manager_endpoint_config.yml"
                )
                endpoint.write_text("pulp_server_port: 9999\n", encoding="utf-8")
                self.assertEqual(
                    generator.main(["check_case", "defaults", "--check"]),
                    1,
                )

    def test_manifest_records_provenance_and_artifact_hashes(self):
        """Published datasets contain deterministic source and artifact hashes."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            with patch.object(generator, "DATASETS_DIR", root):
                self.assertEqual(generator.main(["manifest_case", "defaults"]), 0)
            output = root / "manifest_case"
            manifest_path = output / "dataset_manifest.yml"
            manifest_text = manifest_path.read_text(encoding="utf-8")
            manifest = yaml.safe_load(manifest_text)
            self.assertIn("external_inputs:\n  - ", manifest_text)
            self.assertNotIn("external_inputs:\n- ", manifest_text)
            self.assertEqual(manifest["generator_version"], 2)
            self.assertTrue(manifest["source_documents"])
            self.assertEqual(
                set(manifest["artifacts"]),
                {
                    "input/repo_manager_config.yml",
                    "input/repo_manager_endpoint_config.yml",
                },
            )
            for relative, expected_hash in manifest["artifacts"].items():
                actual_hash = hashlib.sha256(
                    (output / relative).read_bytes()
                ).hexdigest()
                self.assertEqual(actual_hash, expected_hash)

    def test_repeated_generation_is_reproducible(self):
        """Force regeneration produces byte-identical checked artifacts."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            with patch.object(generator, "DATASETS_DIR", root):
                self.assertEqual(generator.main(["repeat_case", "defaults"]), 0)
                first = _files(root / "repeat_case")
                self.assertEqual(
                    generator.main(
                        ["repeat_case", "defaults", "--force"]
                    ),
                    0,
                )
                second = _files(root / "repeat_case")
            self.assertEqual(first, second)

    def test_atomic_publication_restores_previous_dataset(self):
        """A failed staged rename restores the previous published dataset."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            output = root / "atomic_case"
            staging = root / ".atomic_case.staging"
            output.mkdir()
            staging.mkdir()
            (output / "state").write_text("old\n", encoding="utf-8")
            (staging / "state").write_text("new\n", encoding="utf-8")
            real_rename = Path.rename

            def fail_staging_rename(path, target):
                if path == staging:
                    raise OSError("simulated publication failure")
                return real_rename(path, target)

            with patch.object(generator, "DATASETS_DIR", root), patch.object(
                Path, "rename", fail_staging_rename
            ):
                with self.assertRaises(generator.GeneratorError):
                    generator._publish(staging, output, True)

            self.assertEqual(
                (output / "state").read_text(encoding="utf-8"), "old\n"
            )
            self.assertTrue(staging.is_dir())

    def test_missing_named_dataset_fails_closed(self):
        """A selected dataset must exist before test startup can continue."""
        with tempfile.TemporaryDirectory() as work_dir, patch.object(
            validation_func, "DATASETS_DIR", work_dir
        ), patch.dict(
            os.environ,
            {"OMNIA_DATASET_OVERRIDE": "", "OMNIA_SYNC_INPUT_OVERRIDE": ""},
        ):
            result = validation_func.validate_test_config(_config("missing"))
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("Dataset directory not found" in error for error in result["errors"])
        )

    def test_incomplete_named_dataset_fails_closed(self):
        """Both public Repo Manager input files are mandatory."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            input_dir = root / "incomplete" / "input"
            input_dir.mkdir(parents=True)
            (input_dir / "repo_manager_config.yml").write_text(
                "repo_config: partial\n", encoding="utf-8"
            )
            with patch.object(validation_func, "DATASETS_DIR", str(root)), patch.dict(
                os.environ,
                {"OMNIA_DATASET_OVERRIDE": "", "OMNIA_SYNC_INPUT_OVERRIDE": ""},
            ):
                result = validation_func.validate_test_config(
                    _config("incomplete")
                )
        self.assertFalse(result["valid"])
        self.assertTrue(
            any(
                "repo_manager_endpoint_config.yml" in error
                for error in result["errors"]
            )
        )

    def test_invalid_dataset_yaml_fails_closed(self):
        """Malformed YAML cannot reach target synchronization."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            _write_public_input(
                root / "invalid" / "input", "repo_config: [unterminated\n"
            )
            with patch.object(validation_func, "DATASETS_DIR", str(root)), patch.dict(
                os.environ,
                {"OMNIA_DATASET_OVERRIDE": "", "OMNIA_SYNC_INPUT_OVERRIDE": ""},
            ):
                result = validation_func.validate_test_config(_config("invalid"))
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("Unable to parse dataset YAML" in error for error in result["errors"])
        )

    def test_credential_like_dataset_file_fails_closed(self):
        """Datasets cannot become a plaintext credential transport."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            input_dir = root / "sensitive" / "input"
            _write_public_input(input_dir)
            (input_dir / "repo_manager_config_credentials.yml").write_text(
                "password: plaintext\n", encoding="utf-8"  # gitleaks:allow - credentials loaded from secure test config file
            )
            with patch.object(validation_func, "DATASETS_DIR", str(root)), patch.dict(
                os.environ,
                {"OMNIA_DATASET_OVERRIDE": "", "OMNIA_SYNC_INPUT_OVERRIDE": ""},
            ):
                result = validation_func.validate_test_config(
                    _config("sensitive")
                )
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("Credential-like files" in error for error in result["errors"])
        )

    def test_dataset_symlink_fails_closed(self):
        """A named dataset cannot redirect consumers outside the dataset root."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            outside = root / "outside"
            _write_public_input(outside / "input")
            datasets = root / "datasets"
            datasets.mkdir()
            (datasets / "linked").symlink_to(outside, target_is_directory=True)
            with patch.object(
                validation_func, "DATASETS_DIR", str(datasets)
            ), patch.dict(
                os.environ,
                {"OMNIA_DATASET_OVERRIDE": "", "OMNIA_SYNC_INPUT_OVERRIDE": ""},
            ):
                result = validation_func.validate_test_config(_config("linked"))
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("symlinks are not allowed" in error for error in result["errors"])
        )

    def test_invalid_sync_override_fails_closed(self):
        """Boolean environment overrides are parsed strictly."""
        with patch.dict(
            os.environ,
            {"OMNIA_DATASET_OVERRIDE": "", "OMNIA_SYNC_INPUT_OVERRIDE": "sometimes"},
        ):
            result = validation_func.validate_test_config(_config())
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("OMNIA_SYNC_INPUT_OVERRIDE" in error for error in result["errors"])
        )

    def test_batch_scenarios_expose_dataset_controls(self):
        """Every FVT batch scenario can select and synchronize a dataset."""
        config = yaml.safe_load(
            (TEST_ROOT / "test_run_config.yml").read_text(encoding="utf-8")
        )
        for scenario in config["fvt_repo_manager"].values():
            self.assertIsInstance(scenario["dataset"], str)
            self.assertIsInstance(scenario["sync_input"], bool)

    def test_host_resolution_rejects_unsafe_or_missing_datasets(self):
        """Runtime consumers enforce the same contained dataset selection."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            _write_public_input(root / "valid" / "input")
            with patch.object(host_func, "DATASETS_DIR", str(root)):
                resolved = host_func._resolve_dataset_subdir(
                    {"dataset": "valid"}, "input", host_func.SRC_INPUT_DIR
                )
                self.assertEqual(resolved, str((root / "valid" / "input").resolve()))
                with self.assertRaisesRegex(ValueError, "Unsafe dataset name"):
                    host_func._resolve_dataset_subdir(
                        {"dataset": "../outside"},
                        "input",
                        host_func.SRC_INPUT_DIR,
                    )
                with self.assertRaisesRegex(ValueError, "directory not found"):
                    host_func._resolve_dataset_subdir(
                        {"dataset": "missing"},
                        "input",
                        host_func.SRC_INPUT_DIR,
                    )

    def test_sync_staging_copies_only_public_input_allowlist(self):
        """Defense in depth prevents extra files from entering sync staging."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            source = root / "source"
            staging = root / "staging"
            _write_public_input(source)
            (source / "repo_manager_config_credentials.yml").write_text(
                "password: plaintext\n", encoding="utf-8"  # gitleaks:allow - credentials loaded from secure test config file
            )
            staging.mkdir()
            staged = Path(host_func._stage_public_input(str(source), str(staging)))
            self.assertEqual(
                sorted(path.name for path in staged.iterdir()),
                sorted(host_func.REQUIRED_DATASET_INPUT_FILES),
            )

    def test_named_dataset_reaches_remote_sync_staging(self):
        """The selected dataset supplies the exact files sent to the target."""
        with tempfile.TemporaryDirectory() as work_dir:
            root = Path(work_dir)
            input_dir = root / "selected" / "input"
            _write_public_input(
                input_dir, "---\nrepo_config: selected_dataset\n"
            )
            captured = {}

            def capture_sync(**kwargs):
                staged = Path(kwargs["src"])
                captured["files"] = sorted(
                    path.name for path in staged.iterdir()
                )
                captured["config"] = (
                    staged / "repo_manager_config.yml"
                ).read_text(encoding="utf-8")
                return {"success": True, "details": "synced", "error": ""}

            connection = {
                "mode": "ssh",
                "ip": "192.0.2.10",
                "user": "root",
                "auth_secret": "",
                "ssh_opts": [],
            }
            with patch.object(host_func, "DATASETS_DIR", str(root)), patch.object(
                host_func, "connection_params", return_value=connection
            ), patch.object(
                host_func, "is_local_execution", return_value=False
            ), patch.object(
                host_func,
                "resolve_domain_input_path",
                return_value="/opt/omnia/repo_manager/input/project_default",
            ), patch.object(
                host_func, "ensure_remote_dir"
            ), patch.object(
                host_func, "sync_files", side_effect=capture_sync
            ):
                result = host_func.sync_repo_manager_input(
                    object(), {"dataset": "selected"}
                )

            self.assertTrue(result["success"], result["error"])
            self.assertEqual(
                captured["files"],
                sorted(host_func.REQUIRED_DATASET_INPUT_FILES),
            )
            self.assertIn("selected_dataset", captured["config"])

    def test_empty_dataset_validates_canonical_source_fallback(self):
        """Empty dataset mode validates the same public source contract."""
        with tempfile.TemporaryDirectory() as work_dir:
            source = Path(work_dir) / "input"
            _write_public_input(source)
            with patch.object(
                validation_func, "SRC_INPUT_DIR", str(source)
            ), patch.dict(
                os.environ,
                {"OMNIA_DATASET_OVERRIDE": "", "OMNIA_SYNC_INPUT_OVERRIDE": ""},
            ):
                result = validation_func.validate_test_config(_config())
        self.assertTrue(result["valid"], result["errors"])


if __name__ == "__main__":
    unittest.main()
