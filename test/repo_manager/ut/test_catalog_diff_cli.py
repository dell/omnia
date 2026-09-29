# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""CLI-level regression tests for `catalog_manager.py diff`: the schema-
required-by-default behavior (with an explicit, disclosed degrade path) and
the output-path collision guard.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from source_loader import REPO_MANAGER_ROOT, REPOSITORY_ROOT

CATALOG_MANAGER = str(
    REPO_MANAGER_ROOT / "plugins" / "module_utils" / "catalog" / "catalog_manager.py"
)
SCHEMA = str(REPO_MANAGER_ROOT / "schemas" / "catalog_schema.json")
SAMPLE_CURRENT = str(
    REPOSITORY_ROOT / "src" / "main" / "samples" / "catalogs" / "10.0"
    / "service_k8s_x86_64.json"
)
SAMPLE_FUTURE = str(
    REPOSITORY_ROOT / "src" / "main" / "samples" / "catalogs" / "10.2"
    / "service_k8s_x86_64.json"
)


def _run(*args):
    return subprocess.run(
        [sys.executable, CATALOG_MANAGER, *args],
        check=False, capture_output=True, text=True,
    )


@unittest.skipUnless(
    os.path.isfile(SAMPLE_CURRENT) and os.path.isfile(SAMPLE_FUTURE),
    "sample catalogs not present in this checkout",
)
class DiffSchemaRequiredTests(unittest.TestCase):
    """`--schema` is required unless `--allow-schemaless` is passed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _outputs(self):
        return (
            os.path.join(self._tmp.name, "forward.json"),
            os.path.join(self._tmp.name, "reverse.json"),
        )

    def test_missing_schema_and_no_override_is_rejected(self):
        """Without --schema or --allow-schemaless, the command fails closed
        before touching either catalog."""
        forward, reverse = self._outputs()
        result = _run(
            "diff", "--current", SAMPLE_CURRENT, "--future", SAMPLE_FUTURE,
            "--output-forward", forward, "--output-reverse", reverse,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--schema is required", result.stdout + result.stderr)
        self.assertFalse(os.path.exists(forward))

    def test_schema_supplied_succeeds_without_degraded_warning(self):
        """A schema-validated diff succeeds and reports no schema-degraded
        warning in the changelog."""
        forward, reverse = self._outputs()
        changelog = os.path.join(self._tmp.name, "changelog.md")
        result = _run(
            "diff", "--current", SAMPLE_CURRENT, "--future", SAMPLE_FUTURE,
            "--schema", SCHEMA, "--output-forward", forward,
            "--output-reverse", reverse, "--output-changelog", changelog,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with open(changelog, encoding="utf-8") as fh:
            content = fh.read()
        self.assertNotIn("SCHEMA-DEGRADED", content)

    def test_allow_schemaless_succeeds_with_disclosed_degraded_warning(self):
        """Explicitly opting into a schema-less diff still succeeds, but the
        changelog artifact itself discloses the degradation."""
        forward, reverse = self._outputs()
        changelog = os.path.join(self._tmp.name, "changelog.md")
        result = _run(
            "diff", "--current", SAMPLE_CURRENT, "--future", SAMPLE_FUTURE,
            "--allow-schemaless", "--output-forward", forward,
            "--output-reverse", reverse, "--output-changelog", changelog,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with open(changelog, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("SCHEMA-DEGRADED", content)


@unittest.skipUnless(
    os.path.isfile(SAMPLE_CURRENT) and os.path.isfile(SAMPLE_FUTURE),
    "sample catalogs not present in this checkout",
)
class DiffOutputCollisionTests(unittest.TestCase):
    """No output path may resolve to the same file as an input or another
    output."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_forward_and_reverse_outputs_cannot_collide(self):
        """Reusing one path for both diff outputs is rejected."""
        same = os.path.join(self._tmp.name, "same.json")
        result = _run(
            "diff", "--current", SAMPLE_CURRENT, "--future", SAMPLE_FUTURE,
            "--schema", SCHEMA, "--output-forward", same, "--output-reverse", same,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolve to the same path", result.stdout + result.stderr)
        self.assertFalse(os.path.exists(same))

    def test_output_cannot_equal_an_input(self):
        """An output path that resolves to one of the input catalogs is
        rejected before any write happens."""
        forward = os.path.join(self._tmp.name, "forward.json")
        reverse = os.path.join(self._tmp.name, "reverse.json")
        result = _run(
            "diff", "--current", SAMPLE_CURRENT, "--future", SAMPLE_FUTURE,
            "--schema", SCHEMA, "--output-forward", SAMPLE_CURRENT,
            "--output-reverse", reverse,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolve to the same path", result.stdout + result.stderr)
        self.assertFalse(os.path.exists(forward))

    def test_symlinked_output_alias_of_an_input_is_rejected(self):
        """A symlink pointing at an input catalog cannot be used as an
        output path to smuggle a collision past a literal-string check."""
        forward = os.path.join(self._tmp.name, "forward.json")
        reverse = os.path.join(self._tmp.name, "reverse.json")
        alias = os.path.join(self._tmp.name, "alias.json")
        os.symlink(SAMPLE_CURRENT, alias)
        result = _run(
            "diff", "--current", SAMPLE_CURRENT, "--future", SAMPLE_FUTURE,
            "--schema", SCHEMA, "--output-forward", alias, "--output-reverse", reverse,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolve to the same path", result.stdout + result.stderr)

    def test_distinct_output_paths_succeed(self):
        """A normal, non-colliding set of output paths succeeds."""
        forward = os.path.join(self._tmp.name, "forward.json")
        reverse = os.path.join(self._tmp.name, "reverse.json")
        result = _run(
            "diff", "--current", SAMPLE_CURRENT, "--future", SAMPLE_FUTURE,
            "--schema", SCHEMA, "--output-forward", forward, "--output-reverse", reverse,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(os.path.isfile(forward))
        self.assertTrue(os.path.isfile(reverse))
        with open(forward, encoding="utf-8") as fh:
            self.assertIsInstance(json.load(fh), list)


if __name__ == "__main__":
    unittest.main()
