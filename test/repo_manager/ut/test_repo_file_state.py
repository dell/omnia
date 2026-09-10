# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Tests for safe and idempotent DNF repository-file replacement."""

import errno
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager import repo_file_utils


class RepoFileUtilityTests(unittest.TestCase):
    """Verify destination validation and atomic replacement behavior."""

    def test_atomic_write_is_idempotent(self):
        """An identical complete file is reported unchanged."""
        with tempfile.TemporaryDirectory() as work_dir:
            repo_file = Path(work_dir) / "pulp.repo"
            repo_file.write_text("[repo]\n", encoding="utf-8")
            changed = repo_file_utils.atomic_write_repo_file(
                str(repo_file), "[repo]\n"
            )
            self.assertFalse(changed)
            self.assertEqual(repo_file.read_text(encoding="utf-8"), "[repo]\n")

    def test_read_only_destination_is_rejected_before_write(self):
        """A read-only filesystem is reported without creating a file."""
        with tempfile.TemporaryDirectory() as work_dir:
            repo_file = Path(work_dir) / "pulp.repo"
            read_only_flags = SimpleNamespace(f_flag=os.ST_RDONLY)
            with patch.object(
                repo_file_utils.os, "statvfs", return_value=read_only_flags
            ):
                with self.assertRaises(OSError) as raised:
                    repo_file_utils.atomic_write_repo_file(
                        str(repo_file), "[repo]\n"
                    )
            self.assertEqual(raised.exception.errno, errno.EROFS)
            self.assertFalse(repo_file.exists())

    def test_symbolic_link_target_is_rejected(self):
        """A symlink cannot redirect repository-file replacement."""
        with tempfile.TemporaryDirectory() as work_dir:
            target = Path(work_dir) / "target.repo"
            target.write_text("preserved\n", encoding="utf-8")
            repo_file = Path(work_dir) / "pulp.repo"
            repo_file.symlink_to(target)
            with self.assertRaises(OSError) as raised:
                repo_file_utils.atomic_write_repo_file(
                    str(repo_file), "replacement\n"
                )
            self.assertEqual(raised.exception.errno, errno.ELOOP)
            self.assertEqual(target.read_text(encoding="utf-8"), "preserved\n")


if __name__ == "__main__":
    unittest.main()
