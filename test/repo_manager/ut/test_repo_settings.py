# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Tests for typed Repo Manager configuration and environment overrides."""

import unittest
from unittest.mock import patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager import repo_settings


class RepoSettingsTests(unittest.TestCase):
    """Require deterministic precedence and strict operator input types."""

    def test_yaml_value_is_used_when_environment_is_absent(self):
        """Declarative configuration takes precedence over the fallback."""
        with patch.object(
            repo_settings, "_config", {"parallel_config": {"default_nthreads": 7}}
        ), patch.dict(repo_settings.os.environ, {}, clear=True):
            self.assertEqual(
                repo_settings.get_config_value(
                    "parallel_config.default_nthreads", 3, "RM_TEST_THREADS"
                ),
                7,
            )

    def test_default_is_used_for_missing_key(self):
        """A missing environment and YAML key uses the defensive default."""
        with patch.object(repo_settings, "_config", {}), patch.dict(
            repo_settings.os.environ, {}, clear=True
        ):
            self.assertEqual(
                repo_settings.get_config_value("missing.value", 5, "RM_TEST_MISSING"),
                5,
            )

    def test_valid_integer_environment_override(self):
        """A valid numeric override is returned as an integer."""
        with patch.dict(
            repo_settings.os.environ, {"RM_TEST_THREADS": "4"}, clear=True
        ):
            value = repo_settings.get_config_value(
                "parallel_config.default_nthreads", 3, "RM_TEST_THREADS"
            )
        self.assertEqual(value, 4)
        self.assertIsInstance(value, int)

    @unittest.expectedFailure
    def test_invalid_integer_environment_override_is_rejected(self):
        """Known gap: malformed numeric inputs must not become strings."""
        with patch.dict(
            repo_settings.os.environ, {"RM_TEST_THREADS": "four"}, clear=True
        ):
            with self.assertRaises(ValueError):
                repo_settings.get_config_value(
                    "parallel_config.default_nthreads", 3, "RM_TEST_THREADS"
                )

    @unittest.expectedFailure
    def test_false_boolean_environment_override_is_typed(self):
        """Known gap: the bool/int subclass ordering currently returns a string."""
        with patch.dict(
            repo_settings.os.environ, {"RM_TEST_BOOL": "false"}, clear=True
        ):
            value = repo_settings.get_config_value(
                "rpm_repo_config.continue_on_failure", True, "RM_TEST_BOOL"
            )
        self.assertIs(value, False)

    @unittest.expectedFailure
    def test_true_boolean_environment_override_is_typed(self):
        """Known gap: valid true values must return bool rather than text."""
        with patch.dict(
            repo_settings.os.environ, {"RM_TEST_BOOL": "true"}, clear=True
        ):
            value = repo_settings.get_config_value(
                "rpm_repo_config.continue_on_failure", False, "RM_TEST_BOOL"
            )
        self.assertIs(value, True)

    @unittest.expectedFailure
    def test_invalid_boolean_environment_override_is_rejected(self):
        """Known gap: arbitrary boolean spellings must fail closed."""
        with patch.dict(
            repo_settings.os.environ, {"RM_TEST_BOOL": "sometimes"}, clear=True
        ):
            with self.assertRaises(ValueError):
                repo_settings.get_config_value(
                    "rpm_repo_config.continue_on_failure", True, "RM_TEST_BOOL"
                )


if __name__ == "__main__":
    unittest.main()
