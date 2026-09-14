# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Unit tests for bounded, transient-only DNF retry behavior."""

# pylint: disable=protected-access

from subprocess import CompletedProcess
import unittest
from unittest.mock import Mock, patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager import download_rpm


def _result(returncode, stdout="", stderr=""):
    return CompletedProcess(["dnf"], returncode, stdout, stderr)


class DnfRetryTests(unittest.TestCase):
    """Keep retry behavior narrow, bounded and shell-free."""

    def setUp(self):
        self.logger = Mock()
        self.command = ["dnf", "download", "bash"]

    def test_success_runs_once_without_sleep(self):
        """A successful command returns immediately."""
        with patch.object(
            download_rpm.subprocess, "run", return_value=_result(0)
        ) as run, patch.object(download_rpm.time, "sleep") as sleep:
            actual = download_rpm._run_dnf_command(self.command, self.logger)
        self.assertEqual(actual.returncode, 0)
        run.assert_called_once_with(
            self.command,
            check=False,
            capture_output=True,
            shell=False,
            text=True,
        )
        sleep.assert_not_called()

    def test_transient_failure_retries_then_succeeds(self):
        """Temporary repository availability failures are retried."""
        with patch.object(
            download_rpm.subprocess,
            "run",
            side_effect=[
                _result(1, stderr="503 Service Unavailable"),
                _result(0),
            ],
        ) as run, patch.object(download_rpm.time, "sleep") as sleep:
            actual = download_rpm._run_dnf_command(self.command, self.logger)
        self.assertEqual(actual.returncode, 0)
        self.assertEqual(run.call_count, 2)
        sleep.assert_called_once_with(
            download_rpm.DNF_TRANSIENT_RETRY_DELAY_SECONDS
        )

    def test_transient_failure_stops_after_configured_attempts(self):
        """A persistent transient error cannot retry indefinitely."""
        failure = _result(1, stderr="cannot download repomd.xml")
        with patch.object(
            download_rpm.subprocess, "run", return_value=failure
        ) as run, patch.object(download_rpm.time, "sleep") as sleep:
            actual = download_rpm._run_dnf_command(self.command, self.logger)
        self.assertIs(actual, failure)
        self.assertEqual(run.call_count, download_rpm.DNF_TRANSIENT_RETRY_ATTEMPTS)
        self.assertEqual(
            sleep.call_count,
            download_rpm.DNF_TRANSIENT_RETRY_ATTEMPTS - 1,
        )

    def test_package_not_found_is_not_retried(self):
        """A catalog/package error fails immediately."""
        failure = _result(1, stderr="No match for argument: absent")
        with patch.object(
            download_rpm.subprocess, "run", return_value=failure
        ) as run, patch.object(download_rpm.time, "sleep") as sleep:
            download_rpm._run_dnf_command(self.command, self.logger)
        run.assert_called_once()
        sleep.assert_not_called()

    def test_checksum_failure_is_not_retried(self):
        """Integrity failures are never hidden by availability retries."""
        for message in ("checksum mismatch", "digest mismatch", "GPG check failed"):
            with self.subTest(message=message), patch.object(
                download_rpm.subprocess,
                "run",
                return_value=_result(1, stderr=message),
            ) as run, patch.object(download_rpm.time, "sleep") as sleep:
                download_rpm._run_dnf_command(self.command, self.logger)
                run.assert_called_once()
                sleep.assert_not_called()

    def test_non_retryable_marker_wins_over_transient_marker(self):
        """A mixed integrity/transport error remains non-retryable."""
        mixed = _result(
            1,
            stderr="503 Service Unavailable followed by checksum mismatch",
        )
        self.assertFalse(download_rpm._is_transient_dnf_failure(mixed))

    def test_warning_reports_next_attempt_numbers(self):
        """Retry logs expose bounded progress without raw command data."""
        with patch.object(
            download_rpm.subprocess,
            "run",
            side_effect=[
                _result(1, stderr="connection refused"),
                _result(1, stderr="gateway timeout"),
                _result(0),
            ],
        ), patch.object(download_rpm.time, "sleep"):
            download_rpm._run_dnf_command(self.command, self.logger)
        self.assertEqual(self.logger.warning.call_count, 2)
        self.assertEqual(
            [item.args[-2:] for item in self.logger.warning.call_args_list],
            [(2, 3), (3, 3)],
        )


if __name__ == "__main__":
    unittest.main()
