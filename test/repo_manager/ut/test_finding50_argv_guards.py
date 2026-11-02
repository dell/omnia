# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Regression tests for Finding-50 argument and option injection guards."""

# pylint: disable=protected-access

from subprocess import CompletedProcess
import tempfile
import unittest
from unittest.mock import Mock, patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager import dnf_package_manager
from ansible.module_utils.repo_manager import download_rpm
from ansible.module_utils.repo_manager import pulp_commands
from plugins.modules import pulp_cleanup


ARGS = ("/tmp/store", "rhel", "10.0", "x86_64", "/tmp/out")


def _download(packages, preferred=None):
    return dnf_package_manager.build_dnf_download_command(
        *ARGS, packages, preferred
    )


class DnfDownloadCommandTests(unittest.TestCase):
    """Option-like package names are rejected; valid names keep their argv."""

    def test_option_like_package_is_rejected(self):
        for name in ("--installroot=/tmp/e", "--setopt=evil=true", "-x"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                _download([name])

    def test_whitespace_package_is_rejected(self):
        with self.assertRaises(ValueError):
            _download(["kernel --setopt=evil=true"])

    def test_valid_packages_keep_order_and_values(self):
        names = ["kernel-core", "python3.12-devel", "libstdc++.x86_64",
                 "cffi-1.17.1-1.el10.x86_64", "a_b+c.d"]
        command = _download(names, "--setopt=x.priority=1")
        self.assertEqual(command[-len(names):], names)
        self.assertIn("--setopt=x.priority=1", command)
        self.assertIn("--destdir=/tmp/out", command)


class DnfInfoCommandTests(unittest.TestCase):
    """repo_name stays a literal value; package_name must not be an option."""

    def test_option_like_package_name_is_rejected(self):
        with self.assertRaises(ValueError):
            dnf_package_manager.build_dnf_info_command(
                *ARGS[:4], "repo_a", "--installroot=/tmp/e"
            )

    def test_valid_info_command_is_unchanged(self):
        command = dnf_package_manager.build_dnf_info_command(
            *ARGS[:4], "repo_a", "kernel-core"
        )
        self.assertEqual(command[-2:], ["--repo=repo_a", "kernel-core"])

    def test_option_like_repo_name_is_still_a_literal_value(self):
        command = dnf_package_manager.build_dnf_info_command(
            *ARGS[:4], "--installroot=/tmp/e", "kernel-core"
        )
        self.assertIn("--repo=--installroot=/tmp/e", command)


class RpmBatchRejectionTests(unittest.TestCase):
    """A rejected package fails alone; the rest of the batch still runs."""

    def test_rejected_name_is_detected_without_failing_batch(self):
        logger = Mock()
        self.assertTrue(download_rpm._is_rejected_package_name(
            "--installroot=/tmp/e", logger))
        self.assertFalse(download_rpm._is_rejected_package_name(
            "bash", logger))

    def test_download_batch_marks_only_rejected_package_failed(self):
        logger = Mock()
        with tempfile.TemporaryDirectory() as store:
            status = f"{store}/sw/status.csv"
            ok = CompletedProcess(["dnf"], 0, "", "")
            with patch.object(download_rpm, "_run_dnf_command",
                              return_value=ok) as run, \
                    patch.object(download_rpm, "_check_rpm_downloaded",
                                 return_value=True), \
                    patch.object(download_rpm, "_write_rpm_status") as write:
                downloaded, failed = download_rpm._download_rpm_packages(
                    ["--installroot=/tmp/e", "bash"], store, status,
                    "rhel", "10.0", "x86_64", logger,
                    {"bash": "", "--installroot=/tmp/e": ""}, {},
                )
        self.assertEqual(downloaded, ["bash"])
        self.assertEqual(failed, ["--installroot=/tmp/e"])
        statuses = {call.args[1]: call.args[2] for call in write.call_args_list}
        self.assertEqual(statuses["--installroot=/tmp/e"], "Failed")
        for call in run.call_args_list:
            self.assertNotIn("--installroot=/tmp/e", call.args[0])


class PulpCommandStringTests(unittest.TestCase):
    """String commands never reach subprocess; list commands are unchanged."""

    def test_ensure_pulp_command_rejects_string(self):
        with self.assertRaises(TypeError):
            pulp_commands.ensure_pulp_command("pulp rpm show")

    def test_ensure_pulp_command_keeps_list_behavior(self):
        self.assertEqual(
            pulp_commands.ensure_pulp_command(["rpm", "show"])[1:],
            ["rpm", "show"],
        )

    def test_run_cmd_returns_error_dict_for_string(self):
        logger = Mock()
        with patch.object(pulp_cleanup.subprocess, "run") as run:
            result = pulp_cleanup.run_cmd("pulp rpm show", logger)
        run.assert_not_called()
        self.assertEqual(result["rc"], 1)
        self.assertEqual(result["stderr"], "Unable to execute command")

    def test_run_cmd_list_still_executes(self):
        logger = Mock()
        ok = CompletedProcess(["pulp"], 0, "out", "")
        with patch.object(pulp_cleanup.subprocess, "run", return_value=ok) as run:
            result = pulp_cleanup.run_cmd(["pulp", "rpm", "show"], logger)
        self.assertEqual(result["rc"], 0)
        self.assertFalse(run.call_args.kwargs["shell"])


if __name__ == "__main__":
    unittest.main()
