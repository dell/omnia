# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Regression tests for `catalog_manager.py add` on multi-architecture and
multi-OS-version catalogs: updating a package must merge its sources instead
of replacing the whole entry, and a legacy Schema 1.0 catalog must point the
operator at `transform`.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import source_loader  # noqa: F401  # pylint: disable=unused-import
from source_loader import REPO_MANAGER_ROOT, REPOSITORY_ROOT

from ansible.module_utils.catalog.mutator import (
    delete_packages,
    merge_package_entry,
)

CATALOG_MANAGER = str(
    REPO_MANAGER_ROOT / "plugins" / "module_utils" / "catalog" / "catalog_manager.py"
)
SCHEMA = str(REPO_MANAGER_ROOT / "schemas" / "catalog_schema.json")
HYBRID_COMBINED = str(
    REPOSITORY_ROOT / "src" / "main" / "samples" / "catalogs" / "hybrid"
    / "slurm_service_k8s_hybrid_10_2_10_0_combined.json"
)

BOTH = ["10.2", "10.0"]


def _rpm(*sources):
    return {"name": "pkg", "packagetype": "rpm", "sources": list(sources)}


def _src(arch, versions, reponame="baseos"):
    return {"architecture": arch, "reponame": reponame, "name": "rhel",
            "version": list(versions)}


class MergePackageEntryTests(unittest.TestCase):
    """Unit behavior of merge_package_entry()."""

    def test_other_architecture_is_kept(self):
        """Updating x86_64 keeps the aarch64 source untouched."""
        existing = _rpm(_src("x86_64", BOTH), _src("aarch64", BOTH))
        merged = merge_package_entry(existing, _rpm(_src("x86_64", ["10.2"])))
        self.assertEqual(merged["sources"], [_src("x86_64", BOTH), _src("aarch64", BOTH)])

    def test_other_os_version_is_kept_when_source_changes(self):
        """A new repo for 10.2 only splits the source; 10.0 keeps its repo."""
        existing = _rpm(_src("x86_64", BOTH))
        merged = merge_package_entry(existing, _rpm(_src("x86_64", ["10.2"], "appstream")))
        self.assertEqual(merged["sources"], [_src("x86_64", ["10.0"]),
                                             _src("x86_64", ["10.2"], "appstream")])

    def test_new_os_version_is_added_to_matching_source(self):
        """Adding 10.2 to an identical 10.0 source extends its version list."""
        existing = _rpm(_src("x86_64", ["10.0"]))
        merged = merge_package_entry(existing, _rpm(_src("x86_64", ["10.2"])))
        self.assertEqual(merged["sources"], [_src("x86_64", ["10.0", "10.2"])])

    def test_image_update_keeps_other_architecture_and_os_fields(self):
        """An image line (no OS fields) replaces only its architecture."""
        existing = {"name": "img", "packagetype": "image", "tag": "v1", "sources": [
            {"architecture": "x86_64", "registry": "ghcr.io", "name": "rhel", "version": BOTH},
            {"architecture": "aarch64", "registry": "ghcr.io", "name": "rhel", "version": BOTH},
        ]}
        incoming = {"name": "img", "packagetype": "image", "tag": "v2",
                    "sources": [{"architecture": "x86_64", "registry": "quay.io"}]}
        merged = merge_package_entry(existing, incoming)
        self.assertEqual(merged["tag"], "v2")
        self.assertEqual(merged["sources"], [
            {"architecture": "aarch64", "registry": "ghcr.io", "name": "rhel", "version": BOTH},
            {"architecture": "x86_64", "registry": "quay.io", "name": "rhel", "version": BOTH},
        ])

    def test_package_type_change_replaces_entry(self):
        """Source shapes differ between types, so the entry is replaced."""
        existing = _rpm(_src("x86_64", BOTH), _src("aarch64", BOTH))
        incoming = {"name": "pkg", "packagetype": "tarball", "sources": [
            {"architecture": "x86_64", "name": "rhel", "version": ["10.2"], "url": "u"}]}
        self.assertEqual(merge_package_entry(existing, incoming), incoming)

    def test_inputs_are_not_modified(self):
        """The merge returns a new entry."""
        existing = _rpm(_src("x86_64", BOTH))
        incoming = _rpm(_src("x86_64", ["10.2"], "appstream"))
        before = json.dumps([existing, incoming], sort_keys=True)
        merge_package_entry(existing, incoming)
        self.assertEqual(json.dumps([existing, incoming], sort_keys=True), before)


class DeleteSideEffectTests(unittest.TestCase):
    """Deleting a group's last package removes the group from its layers."""

    def test_empty_group_removed_from_layers_with_warning(self):
        """The layer change is reported, not silent."""
        catalog = {"catalog": {
            "functionallayer": [{"name": "os_rhel_10_2_x86_64", "components": ["g"]}],
            "groups": {"g": {"name": "g", "type": "group", "components": ["p"]}},
            "packages": {"p": _rpm(_src("x86_64", ["10.2"]))},
        }}
        with self.assertLogs("ansible.module_utils.catalog.mutator", "WARNING") as logs:
            summary = delete_packages(catalog, {"g": ["p"]})
        self.assertEqual(summary["groups_removed"], 1)
        self.assertEqual(catalog["catalog"]["functionallayer"][0]["components"], [])
        self.assertIn("os_rhel_10_2_x86_64", logs.output[0])


class AddCliMergeTests(unittest.TestCase):
    """End-to-end `add` on the shipped hybrid combined catalog."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        self.catalog = os.path.join(self.root, "catalog.json")
        shutil.copyfile(HYBRID_COMBINED, self.catalog)

    def _add(self, text, *extra):
        input_file = os.path.join(self.root, "input.txt")
        with open(input_file, "w", encoding="utf-8") as fh:
            fh.write(text)
        result = subprocess.run(
            [sys.executable, CATALOG_MANAGER, "add", "--input", input_file,
             "--catalog", self.catalog, "--schema", SCHEMA,
             "--catalog-root", self.root, *extra],
            check=False, capture_output=True, text=True,
        )
        with open(self.catalog, encoding="utf-8") as fh:
            return result, json.load(fh)["catalog"]

    def test_update_keeps_aarch64_and_10_0_sources(self):
        """Re-adding openssh_clients for x86_64/10.2 keeps every other source."""
        result, cat = self._add(
            "[admin_debug_group]\nopenssh_clients, rpm, openssh-clients, baseos\n",
            "--default-os-version", "10.2")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        sources = cat["packages"]["openssh_clients"]["sources"]
        self.assertEqual(sorted((s["architecture"], tuple(sorted(s["version"])))
                                for s in sources),
                         [("aarch64", ("10.0", "10.2")), ("x86_64", ("10.0", "10.2"))])

    def test_new_package_for_both_arches_and_os_versions(self):
        """One key on several lines yields one entry with every source."""
        result, cat = self._add(
            "[admin_debug_group]\n"
            "new_tool, rpm, new-tool, baseos, arch=x86_64, os_version=10.2\n"
            "new_tool, rpm, new-tool, baseos, arch=x86_64, os_version=10.0\n"
            "new_tool, rpm, new-tool, baseos, arch=aarch64, os_version=10.2\n"
            "new_tool, rpm, new-tool, baseos, arch=aarch64, os_version=10.0\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        sources = cat["packages"]["new_tool"]["sources"]
        self.assertEqual(sorted((s["architecture"], tuple(sorted(s["version"])))
                                for s in sources),
                         [("aarch64", ("10.0", "10.2")), ("x86_64", ("10.0", "10.2"))])
        self.assertEqual(cat["groups"]["admin_debug_group"]["components"].count("new_tool"), 1)


class LegacyCatalogMessageTests(unittest.TestCase):
    """A Schema 1.0 catalog tells the operator to run transform."""

    def test_validate_points_to_transform(self):
        """The CLI names the transform command instead of a generic error."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"Catalog": {"Name": "old"}}, fh)
            result = subprocess.run(
                [sys.executable, CATALOG_MANAGER, "validate", "--catalog", path,
                 "--schema", SCHEMA],
                check=False, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("catalog_manager.py transform", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
