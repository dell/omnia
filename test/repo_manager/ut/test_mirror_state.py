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
from plugins.modules import prepare_tasklist


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

    def test_corrupt_index_is_not_treated_as_confirmed_absence(self):
        """Corrupt state must fail rather than schedule everything as new."""
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
        self.assertEqual(
            saved["MirrorIndex"]["schema_version"],
            mirror_status.MIRROR_INDEX_SCHEMA_VERSION,
        )

    def test_repository_checkpoint_preserves_last_good_version_on_failure(self):
        """A failed refresh remains retryable without erasing version evidence."""
        mirror_data = mirror_status._empty_mirror_index()
        repository = "x86_64_rhel_10.0_baseos"
        version_href = "/pulp/api/v3/repositories/rpm/rpm/1/versions/4/"
        mirror_status.update_repository_sync_state(
            mirror_data, repository, "ready", version_href, "on_demand"
        )
        mirror_status.update_repository_sync_state(
            mirror_data, repository, "failed", policy="on_demand"
        )
        entry = mirror_data["MirrorIndex"]["repositories"][repository]
        self.assertEqual(entry["version_href"], version_href)
        self.assertTrue(entry["retry_required"])
        self.assertEqual(
            mirror_status.repositories_requiring_retry(mirror_data),
            {repository},
        )

    def test_resync_checkpoint_marks_only_selected_packages_pending(self):
        """A killed resync retries selected RPMs without invalidating others."""
        mirror_data = mirror_status._empty_mirror_index()
        mirror_data["MirrorIndex"]["packages"] = {
            "selected": _package("selected", "mirrored"),
            "other": _package("other", "mirrored"),
        }
        updated = mirror_status.mark_package_entries_pending(
            mirror_data, {"selected"}
        )
        self.assertEqual(updated, 1)
        self.assertEqual(
            mirror_data["MirrorIndex"]["packages"]["selected"]["status"],
            "pending",
        )
        self.assertEqual(
            mirror_data["MirrorIndex"]["packages"]["other"]["status"],
            "mirrored",
        )

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

    def test_failed_mirror_replacement_removes_temporary_file(self):
        """Interrupted mirror writes must not leave temporary files."""
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


class RpmTaskSelectionTests(unittest.TestCase):
    """Protect normal-rerun and explicit-resync RPM selection semantics."""

    @staticmethod
    def _rpm(package_hash, repository):
        return {
            "hash": package_hash,
            "package_name": package_hash,
            "type": "rpm",
            "repo_name": repository,
            "definition": {"repo_name": repository},
        }

    def setUp(self):
        self.changes = {
            "skip": [
                self._rpm("baseos-package", "baseos"),
                self._rpm("appstream-package", "appstream"),
            ]
        }

    def _select(self, **kwargs):
        resync_all, selected_repositories = (
            prepare_tasklist.normalize_resync_selection(
                kwargs.get("resync_repos"),
                retry_repositories=kwargs.get("retry_repositories"),
                policy_changed_repositories=kwargs.get(
                    "policy_changed_repositories"
                ),
            )
        )
        return prepare_tasklist.packages_requiring_reconciliation(
            self.changes,
            set(),
            ("x86_64", "rhel", "10.0"),
            resync_all=resync_all,
            selected_repositories=selected_repositories,
        )

    def test_normal_rerun_does_not_requeue_successful_rpms(self):
        """An unchanged rerun skips RPMs already marked mirrored."""
        self.assertEqual(self._select(), [])

    def test_targeted_resync_selects_only_packages_from_exact_repository(self):
        """Targeted resync selects packages from only the named repository."""
        selected = self._select(
            resync_repos=["x86_64_rhel_10.0_baseos"]
        )
        self.assertEqual(
            [package["hash"] for package in selected],
            ["baseos-package"],
        )

    def test_resync_all_selects_every_successful_rpm(self):
        """Resync-all selects every mirrored RPM in the active context."""
        selected = self._select(resync_repos="all")
        self.assertEqual(
            [package["hash"] for package in selected],
            ["baseos-package", "appstream-package"],
        )

    def test_failed_repository_checkpoint_selects_its_packages(self):
        """A failed repository checkpoint makes its RPMs retryable."""
        selected = self._select(
            retry_repositories={"x86_64_rhel_10.0_appstream"}
        )
        self.assertEqual(
            [package["hash"] for package in selected],
            ["appstream-package"],
        )

    def test_policy_transition_selects_affected_repository_only(self):
        """Policy transitions requeue only the affected repository RPMs."""
        selected = self._select(
            policy_changed_repositories={"x86_64_rhel_10.0_baseos"}
        )
        self.assertEqual(
            [package["hash"] for package in selected],
            ["baseos-package"],
        )


if __name__ == "__main__":
    unittest.main()
