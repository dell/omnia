# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Tests for environment-derived Repo Manager validation paths."""

import unittest
from unittest.mock import patch

from library.vars.common_vars import _get_catalog_path


class CommonVarsTests(unittest.TestCase):
    """Keep test paths aligned with the deployed environment contract."""

    def test_catalog_path_uses_explicit_catalog_file(self):
        """The selected versioned catalog takes precedence over defaults."""
        with patch.dict(
            "os.environ",
            {"CATALOG_FILE_PATH": "/srv/catalog/selected.json"},
            clear=True,
        ):
            self.assertEqual(
                _get_catalog_path(), "/srv/catalog/selected.json"
            )

    def test_catalog_path_falls_back_below_omnia_data_path(self):
        """Legacy environments retain their data-root-derived default."""
        with patch.dict(
            "os.environ", {"OMNIA_DATA_PATH": "/srv/omnia/"}, clear=True
        ):
            self.assertEqual(
                _get_catalog_path(), "/srv/omnia/catalog/catalog_rhel.json"
            )

    def test_blank_catalog_path_uses_default(self):
        """A blank override is never treated as a usable file path."""
        with patch.dict(
            "os.environ",
            {"CATALOG_FILE_PATH": "   ", "OMNIA_DATA_PATH": "/opt/omnia"},
            clear=True,
        ):
            self.assertEqual(
                _get_catalog_path(),
                "/opt/omnia/catalog/catalog_rhel.json",
            )


if __name__ == "__main__":
    unittest.main()
