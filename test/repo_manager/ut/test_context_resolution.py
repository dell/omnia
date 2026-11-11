# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Regression tests for Repo Manager catalog execution Cases 1-6."""

import unittest
from unittest.mock import Mock

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager.catalog_execution_context_resolver import (
    parse_functional_layer_context,
    resolve_catalog_execution_contexts,
    version_sort_key,
)


def _catalog(*layer_names):
    """Return a minimal catalog containing the requested functional layers."""
    return {
        "identifier": "repo-manager-context-test",
        "functionallayer": [
            {"name": name, "components": []} for name in layer_names
        ],
    }


class ContextResolutionTests(unittest.TestCase):
    """Protect supported RHEL version and architecture combinations."""

    def setUp(self):
        self.logger = Mock()

    def test_cases_one_to_six_resolve_exact_contexts(self):
        """Cases 1-6 resolve without inventing versions or architectures."""
        cases = {
            "case_1": (
                _catalog("baseos_rhel_10_0_x86_64"),
                [("10.0", ["x86_64"])],
            ),
            "case_2": (
                _catalog("baseos_rhel_10_2_x86_64"),
                [("10.2", ["x86_64"])],
            ),
            "case_3": (
                _catalog("baseos_rhel_10_0_aarch64"),
                [("10.0", ["aarch64"])],
            ),
            "case_4": (
                _catalog("baseos_rhel_10_2_aarch64"),
                [("10.2", ["aarch64"])],
            ),
            "case_5": (
                _catalog(
                    "baseos_rhel_10_0_x86_64",
                    "baseos_rhel_10_0_aarch64",
                ),
                [("10.0", ["x86_64", "aarch64"])],
            ),
            "case_6": (
                _catalog(
                    "baseos_rhel_10_2_aarch64",
                    "baseos_rhel_10_0_aarch64",
                    "baseos_rhel_10_2_x86_64",
                    "baseos_rhel_10_0_x86_64",
                ),
                [
                    ("10.0", ["x86_64", "aarch64"]),
                    ("10.2", ["x86_64", "aarch64"]),
                ],
            ),
        }

        for case_name, (catalog, expected) in cases.items():
            with self.subTest(case=case_name):
                resolved = resolve_catalog_execution_contexts(
                    catalog, self.logger
                )
                actual = [
                    (item["os_version"], item["architectures"])
                    for item in resolved["execution_contexts"]
                ]
                self.assertEqual(actual, expected)
                self.assertEqual(
                    resolved["os_versions"],
                    [version for version, _architectures in expected],
                )

    def test_single_version_preserves_legacy_os_version(self):
        """A single context retains the established top-level os_version."""
        resolved = resolve_catalog_execution_contexts(
            _catalog("baseos_rhel_10_2_x86_64"), self.logger
        )
        self.assertEqual(resolved["os_version"], "10.2")

    def test_multiple_versions_require_execution_contexts(self):
        """Multi-version output does not publish an ambiguous os_version."""
        resolved = resolve_catalog_execution_contexts(
            _catalog(
                "baseos_rhel_10_0_x86_64",
                "baseos_rhel_10_2_x86_64",
            ),
            self.logger,
        )
        self.assertNotIn("os_version", resolved)
        self.assertEqual(
            [item["context_id"] for item in resolved["execution_contexts"]],
            ["rhel_10.0", "rhel_10.2"],
        )

    def test_numeric_version_sort_does_not_use_lexical_order(self):
        """Version 10.10 sorts after 10.2 when ascending order is configured."""
        self.assertLess(version_sort_key("10.2"), version_sort_key("10.10"))

    def test_invalid_functional_layer_fails_closed(self):
        """A layer without an exact context suffix cannot enter execution."""
        with self.assertRaises(ValueError):
            parse_functional_layer_context("baseos_rhel_10_x86_64")


if __name__ == "__main__":
    unittest.main()
