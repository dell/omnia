# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Regression tests for the catalog write-path boundary and output-path
collision checks introduced for the AI-skills catalog-authoring tooling
(NFR-2, Req-SEC-I-1/I-4).
"""

import json
import os
import tempfile
import unittest

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.catalog.catalog_io import (
    CatalogPathError,
    find_path_collisions,
    resolve_and_validate_catalog_path,
    write_catalog,
)


class ResolveAndValidateCatalogPathTests(unittest.TestCase):
    """A resolved write target must stay inside its allowed root."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = os.path.join(self._tmp.name, "catalogs")
        os.makedirs(self.root)

    def test_path_inside_root_is_accepted(self):
        """A normal path under the root resolves without error."""
        target = os.path.join(self.root, "service_k8s_x86_64.json")
        resolved = resolve_and_validate_catalog_path(target, self.root)
        self.assertEqual(resolved, os.path.realpath(target))

    def test_dotdot_escape_is_rejected(self):
        """A relative path containing '..' that escapes the root is rejected."""
        target = os.path.join(self.root, "..", "escaped.json")
        with self.assertRaises(CatalogPathError):
            resolve_and_validate_catalog_path(target, self.root)

    def test_absolute_path_elsewhere_is_rejected(self):
        """An absolute path outside the root entirely is rejected."""
        target = os.path.join(self._tmp.name, "elsewhere.json")
        with self.assertRaises(CatalogPathError):
            resolve_and_validate_catalog_path(target, self.root)

    def test_symlinked_parent_directory_escape_is_rejected(self):
        """A symlinked directory inside the root that points outside it
        cannot be used to smuggle a write past the boundary."""
        outside = os.path.join(self._tmp.name, "outside")
        os.makedirs(outside)
        link = os.path.join(self.root, "link_dir")
        os.symlink(outside, link)
        target = os.path.join(link, "catalog.json")
        with self.assertRaises(CatalogPathError):
            resolve_and_validate_catalog_path(target, self.root)

    def test_symlinked_leaf_escape_is_rejected(self):
        """A symlink at the leaf position redirecting outside the root is
        rejected, not silently followed and written through."""
        outside = os.path.join(self._tmp.name, "outside")
        os.makedirs(outside)
        outside_file = os.path.join(outside, "real.json")
        link = os.path.join(self.root, "catalog.json")
        os.symlink(outside_file, link)
        with self.assertRaises(CatalogPathError):
            resolve_and_validate_catalog_path(link, self.root)

    def test_root_itself_is_accepted(self):
        """A file directly at the root (not in a subdirectory) is inside it."""
        target = os.path.join(self.root, "catalog.json")
        resolved = resolve_and_validate_catalog_path(target, self.root)
        self.assertTrue(resolved.startswith(os.path.realpath(self.root)))


class WriteCatalogBoundaryTests(unittest.TestCase):
    """`write_catalog()` enforces the boundary and writes atomically when
    `allowed_root` is supplied."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = os.path.join(self._tmp.name, "catalogs")
        os.makedirs(self.root)
        self.catalog = {"catalog": {"name": "t", "packages": {}, "groups": {}}}

    def test_write_inside_root_succeeds(self):
        """A write inside the allowed root is performed."""
        target = os.path.join(self.root, "c.json")
        write_catalog(self.catalog, target, allowed_root=self.root)
        with open(target, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), self.catalog)

    def test_write_outside_root_raises_and_writes_nothing(self):
        """A rejected write leaves no file behind anywhere."""
        target = os.path.join(self._tmp.name, "escaped.json")
        with self.assertRaises(CatalogPathError):
            write_catalog(self.catalog, target, allowed_root=self.root)
        self.assertFalse(os.path.exists(target))

    def test_no_temp_file_left_behind_on_success(self):
        """The atomic replace leaves no stray '.catalog-*.tmp' sibling file."""
        target = os.path.join(self.root, "c.json")
        write_catalog(self.catalog, target, allowed_root=self.root)
        leftovers = [f for f in os.listdir(self.root) if f != "c.json"]
        self.assertEqual(leftovers, [])

    def test_without_allowed_root_behavior_is_unchanged(self):
        """Omitting `allowed_root` preserves the pre-existing, unrestricted
        write behavior for callers that manage their own path boundary."""
        target = os.path.join(self._tmp.name, "anywhere.json")
        write_catalog(self.catalog, target)
        with open(target, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), self.catalog)


class FindPathCollisionsTests(unittest.TestCase):
    """Output paths must never resolve to the same file as an input or
    another output (NFR-3-adjacent data-integrity requirement)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_no_collision_among_distinct_paths(self):
        """Distinct real paths never report a collision."""
        collisions = find_path_collisions({
            "a": os.path.join(self._tmp.name, "a.json"),
            "b": os.path.join(self._tmp.name, "b.json"),
        })
        self.assertEqual(collisions, [])

    def test_identical_path_strings_collide(self):
        """The same literal path used under two labels is a collision."""
        path = os.path.join(self._tmp.name, "a.json")
        collisions = find_path_collisions({"current": path, "forward-diff": path})
        self.assertEqual(len(collisions), 1)
        self.assertEqual(collisions[0][2], os.path.realpath(path))

    def test_differently_spelled_same_path_collides(self):
        """Two differently-spelled paths to the same file still collide."""
        real = os.path.join(self._tmp.name, "sub", "a.json")
        os.makedirs(os.path.dirname(real))
        spelled_with_dotdot = os.path.join(self._tmp.name, "sub", "..", "sub", "a.json")
        collisions = find_path_collisions({
            "current": real,
            "output": spelled_with_dotdot,
        })
        self.assertEqual(len(collisions), 1)

    def test_symlink_alias_collides_with_its_target(self):
        """An output path that is a symlink to an input catalog is a
        collision, not a distinct file."""
        target = os.path.join(self._tmp.name, "current.json")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("{}")
        link = os.path.join(self._tmp.name, "output.json")
        os.symlink(target, link)
        collisions = find_path_collisions({"current catalog": target, "output": link})
        self.assertEqual(len(collisions), 1)

    def test_falsy_paths_are_ignored(self):
        """An unset optional output (None/empty string) is never a collision
        candidate."""
        collisions = find_path_collisions({
            "current": os.path.join(self._tmp.name, "a.json"),
            "html output": None,
            "changelog output": "",
        })
        self.assertEqual(collisions, [])


if __name__ == "__main__":
    unittest.main()
