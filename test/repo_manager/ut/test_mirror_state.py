# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Tests for persisted mirror state, rerun classification and atomic writes."""

# pylint: disable=protected-access

import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager import mirror_status


LOGGER = logging.getLogger("repo-manager-mirror-state-test")


def _package(composite_hash, status):
    return {
        "package_name": "bash",
        "type": "rpm",
        "version": "1.0",
        "arch": "x86_64",
        "hash": composite_hash,
        "group_name": "baseos_group",
        "catalog_name": "catalog",
        "catalogs": ["catalog"],
        "status": status,
    }


class MirrorStateTests(unittest.TestCase):
    """Exercise every persisted rerun state without a live Pulp service."""

    def test_missing_index_starts_with_current_empty_schema(self):
        """Confirmed absence of local state creates a valid empty index."""
        with tempfile.TemporaryDirectory() as work_dir:
            result = mirror_status.load_mirror_index(
                str(Path(work_dir) / "missing.json"), LOGGER
            )
        self.assertEqual(
            result["MirrorIndex"]["schema_version"],
            mirror_status.MIRROR_INDEX_SCHEMA_VERSION,
        )
        self.assertEqual(result["MirrorIndex"]["packages"], {})

    @unittest.expectedFailure
    def test_corrupt_index_is_not_treated_as_confirmed_absence(self):
        """Known gap: corrupt state must fail rather than schedule everything as new."""
        with tempfile.TemporaryDirectory() as work_dir:
            index_path = Path(work_dir) / "pulp_mirror_index.json"
            index_path.write_text('{"MirrorIndex":', encoding="utf-8")
            with patch.object(LOGGER, "error"), self.assertRaises(ValueError):
                mirror_status.load_mirror_index(str(index_path), LOGGER)

    def test_rerun_classifies_absent_failed_pending_and_mirrored(self):
        """The persisted-state matrix selects new, retry and skip work exactly."""
        global_index = {
            "x86_64": {
                "new": _package("new", "pending"),
                "failed": _package("failed", "pending"),
                "pending": _package("pending", "pending"),
                "ready": _package("ready", "pending"),
            }
        }
        mirror_data = mirror_status._empty_mirror_index()
        mirror_data["MirrorIndex"]["packages"] = {
            "failed": _package("failed", "failed"),
            "pending": _package("pending", "pending"),
            "ready": _package("ready", "mirrored"),
        }
        result = mirror_status.detect_package_changes(
            global_index, mirror_data, "x86_64", LOGGER
        )
        self.assertEqual([item["hash"] for item in result["mirror"]], ["new"])
        self.assertEqual(
            [item["hash"] for item in result["retry"]],
            ["failed", "pending"],
        )
        self.assertEqual([item["hash"] for item in result["skip"]], ["ready"])

    def test_filter_processes_only_actionable_states(self):
        """Skipped artifacts are excluded from the worker task list."""
        changes = {
            "mirror": [{"hash": "new"}],
            "re_mirror": [{"hash": "changed"}],
            "retry": [{"hash": "failed"}],
            "skip": [{"hash": "ready"}],
        }
        result = mirror_status.filter_tasks_for_processing(changes, LOGGER)
        self.assertEqual(
            [item["hash"] for item in result],
            ["new", "changed", "failed"],
        )

    def test_ambiguous_name_match_does_not_select_an_identity(self):
        """A name-only collision cannot update the wrong mirror entry."""
        mirror_data = mirror_status._empty_mirror_index()
        mirror_data["MirrorIndex"]["packages"] = {
            "one": _package("one", "pending"),
            "two": _package("two", "pending"),
        }
        key, entry = mirror_status.find_mirror_entry(
            mirror_data, "bash", "rpm", "x86_64"
        )
        self.assertIsNone(key)
        self.assertIsNone(entry)

    def test_save_updates_summary_and_schema(self):
        """A complete write publishes deterministic status counts."""
        with tempfile.TemporaryDirectory() as work_dir:
            index_path = Path(work_dir) / "pulp_mirror_index.json"
            mirror_data = mirror_status._empty_mirror_index()
            mirror_data["MirrorIndex"]["packages"] = {
                "ready": _package("ready", "mirrored"),
                "failed": _package("failed", "failed"),
                "pending": _package("pending", "pending"),
            }
            mirror_status.save_mirror_index(str(index_path), mirror_data, LOGGER)
            saved = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual(
            saved["MirrorIndex"]["summary"],
            {"total_unique": 3, "mirrored": 1, "failed": 1, "pending": 1},
        )
        self.assertEqual(saved["MirrorIndex"]["schema_version"], 2)

    def test_mirror_replacement_failure_preserves_previous_file(self):
        """An interrupted replacement leaves the last complete index intact."""
        with tempfile.TemporaryDirectory() as work_dir:
            index_path = Path(work_dir) / "pulp_mirror_index.json"
            index_path.write_text('{"previous": true}\n', encoding="utf-8")
            data = mirror_status._empty_mirror_index()
            with patch.object(
                mirror_status.os,
                "replace",
                side_effect=OSError("simulated interruption"),
            ):
                with self.assertRaises(OSError):
                    mirror_status.save_mirror_index(str(index_path), data, LOGGER)
            self.assertEqual(
                index_path.read_text(encoding="utf-8"),
                '{"previous": true}\n',
            )

    @unittest.expectedFailure
    def test_failed_mirror_replacement_removes_temporary_file(self):
        """Known gap: interrupted mirror writes must not leave PID temp files."""
        with tempfile.TemporaryDirectory() as work_dir:
            index_path = Path(work_dir) / "pulp_mirror_index.json"
            index_path.write_text('{"previous": true}\n', encoding="utf-8")
            with patch.object(
                mirror_status.os,
                "replace",
                side_effect=OSError("simulated interruption"),
            ):
                with self.assertRaises(OSError):
                    mirror_status.save_mirror_index(
                        str(index_path), mirror_status._empty_mirror_index(), LOGGER
                    )
            self.assertEqual(list(Path(work_dir).glob("*.tmp.*")), [])

    def test_global_index_replacement_failure_cleans_temporary_file(self):
        """The hardened global-index writer preserves and cleans on failure."""
        with tempfile.TemporaryDirectory() as work_dir:
            index_path = Path(work_dir) / "global_package_index.json"
            index_path.write_text('{"previous": true}\n', encoding="utf-8")
            global_index = {
                "x86_64": {
                    "hash": {
                        **_package("hash", "pending"),
                        "repo_name": "baseos",
                        "source_catalog_file": "/catalog.json",
                    }
                }
            }
            with patch.object(
                mirror_status.os,
                "replace",
                side_effect=OSError("simulated interruption"),
            ):
                with self.assertRaises(OSError):
                    mirror_status.save_global_package_index(
                        str(index_path), global_index, LOGGER
                    )
            self.assertEqual(
                index_path.read_text(encoding="utf-8"),
                '{"previous": true}\n',
            )
            self.assertEqual(
                list(Path(work_dir).glob(".global_package_index.json.*.tmp")),
                [],
            )


if __name__ == "__main__":
    unittest.main()
