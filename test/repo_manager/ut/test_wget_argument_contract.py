# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Regression tests for wget end-of-options hardening (CWE-88)."""

import ast
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from source_loader import REPO_MANAGER_ROOT

from ansible.module_utils.repo_manager import download_common
from ansible.module_utils.repo_manager import rpm_file_artifact_processor
from ansible.module_utils.repo_manager.security_utils import (
    ArtifactUrlValidationError,
    validate_artifact_url,
)


LOGGER = logging.getLogger("repo-manager-wget-argument-test")
PLUGINS_ROOT = REPO_MANAGER_ROOT / "plugins"
ARTIFACT_URL = "https://example.invalid/artifacts/tool.tar.gz"


def _content_path(root, architecture="x86_64", version="10.2"):
    return str(
        Path(root) / "offline_repo" / "cluster" / architecture / "rhel" /
        version
    )


def _wget_argv_literals():
    """Yield (location, argv) for every literal wget argv in Repo Manager."""
    for path in sorted(PLUGINS_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.List, ast.Tuple)) or not node.elts:
                continue
            first = node.elts[0]
            if isinstance(first, ast.Constant) and first.value == "wget":
                yield f"{path.relative_to(PLUGINS_ROOT)}:{node.lineno}", node


class WgetArgumentContractTests(unittest.TestCase):
    """Prove a catalog URL can never be parsed as a wget option."""

    def test_every_wget_argv_ends_options_before_url(self):
        """Every wget argv places a single '--' immediately before the URL."""
        found = list(_wget_argv_literals())
        self.assertGreaterEqual(len(found), 6)
        for location, node in found:
            with self.subTest(location=location):
                markers = [
                    index for index, element in enumerate(node.elts)
                    if isinstance(element, ast.Constant)
                    and element.value == "--"
                ]
                self.assertEqual(markers, [len(node.elts) - 2])
                self.assertNotIsInstance(node.elts[-1], ast.Constant)

    def test_artifact_url_rejects_option_like_values(self):
        """A value that wget would parse as an option fails URL validation."""
        for value in (
                "--output-document=/tmp/evil",
                "-O/tmp/evil",
                "-Ohttps://example.invalid/a",
                "--use-askpass=https://example.invalid/a",
                "-https://example.invalid/a",
                "--",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ArtifactUrlValidationError):
                    validate_artifact_url(value)

    def test_direct_rpm_wget_calls_end_options_before_url(self):
        """The direct RPM probe and transfer both terminate wget options."""
        url = "https://example.invalid/custom-agent.rpm"
        with tempfile.TemporaryDirectory() as root:
            rpm_path = str(Path(root) / "custom-agent.rpm")
            with patch.object(
                rpm_file_artifact_processor.subprocess, "run"
            ) as spider, patch.object(
                rpm_file_artifact_processor, "execute_command",
                return_value=True,
            ) as transfer:
                result = rpm_file_artifact_processor._ensure_local_rpm(  # pylint: disable=protected-access
                    url, rpm_path, LOGGER
                )

        self.assertTrue(result)
        spider.assert_called_once()
        transfer.assert_called_once()
        spider_argv = spider.call_args.args[0]
        transfer_argv = transfer.call_args.args[0]
        self.assertEqual(
            spider_argv, ["wget", "-q", "--spider", "--tries=1", "--", url]
        )
        self.assertEqual(transfer_argv[:2], ["wget", "-O"])
        self.assertEqual(transfer_argv[-2:], ["--", url])

    def test_tarball_spider_keeps_user_agent_before_end_of_options(self):
        """The tarball probe keeps its options parsed and the URL positional."""
        with tempfile.TemporaryDirectory() as root:
            with patch.object(
                download_common, "_shared_artifact_cache", return_value=None
            ), patch.object(
                download_common, "probe_http_validator", return_value=None
            ), patch.object(
                download_common.subprocess, "run"
            ) as spider, patch.object(
                download_common, "handle_post_request", return_value="Failed"
            ), patch.object(
                download_common, "write_status_to_file"
            ):
                result = download_common.process_tarball(
                    {"package": "tool", "type": "tarball", "url": ARTIFACT_URL},
                    str(Path(root) / "status.csv"),
                    {},
                    _content_path(root),
                    "x86_64_rhel_10.2_tarballtool",
                    LOGGER,
                )

        self.assertEqual(result, "Failed")
        spider.assert_called_once()
        argv = spider.call_args.args[0]
        self.assertEqual(argv[-2:], ["--", ARTIFACT_URL])
        self.assertLess(argv.index("--user-agent"), argv.index("--"))

    def test_iso_spider_ends_options_before_url(self):
        """The remote ISO probe terminates wget options before the URL."""
        url = "https://example.invalid/images/tools.iso"
        with tempfile.TemporaryDirectory() as root:
            with patch.object(
                download_common, "_shared_artifact_cache", return_value=None
            ), patch.object(
                download_common, "probe_http_validator", return_value=None
            ), patch.object(
                download_common.subprocess, "run"
            ) as spider, patch.object(
                download_common, "handle_post_request", return_value="Failed"
            ), patch.object(
                download_common, "write_status_to_file"
            ):
                result = download_common.process_iso(
                    {"package": "tools-iso", "type": "iso", "url": url},
                    str(Path(root) / "status.csv"),
                    {},
                    _content_path(root),
                    "x86_64_rhel_10.2_isotools-iso",
                    LOGGER,
                )

        self.assertEqual(result, "Failed")
        spider.assert_called_once()
        self.assertEqual(
            spider.call_args.args[0],
            ["wget", "-q", "--spider", "--tries=1", "--", url],
        )


if __name__ == "__main__":
    unittest.main()
