# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Regression tests for safe cross-context artifact reuse."""

import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager import download_common
from ansible.module_utils.repo_manager import rpm_file_artifact_processor
from ansible.module_utils.repo_manager.pulp_commands import pulp_rpm_commands


LOGGER = logging.getLogger("repo-manager-artifact-reuse-test")


def _content_path(root, architecture="x86_64", version="10.2"):
    return str(
        Path(root) / "offline_repo" / "cluster" / architecture / "rhel" /
        version
    )


class ArtifactCompatibilityTests(unittest.TestCase):
    """Prove each artifact class uses its documented compatibility scope."""

    def test_content_architecture_is_read_from_managed_path(self):
        """Architecture scoping is independent of the surrounding data root."""
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(
                download_common._content_architecture(  # pylint: disable=protected-access
                    _content_path(root, "aarch64", "10.0")
                ),
                "aarch64",
            )
            self.assertIsNone(
                download_common._content_architecture(  # pylint: disable=protected-access
                    str(Path(root) / "unmanaged")
                )
            )

    def test_shell_reuses_verified_bytes_without_network_download(self):
        """The same validated script is reconciled into a second endpoint."""
        with tempfile.TemporaryDirectory() as root:
            restored = Path(root) / "verified.sh"
            restored.write_text("#!/bin/sh\n", encoding="utf-8")
            cache = Mock()
            cache.restore.return_value = [str(restored)]
            with patch.object(
                download_common, "_shared_artifact_cache", return_value=cache
            ), patch.object(
                download_common,
                "probe_http_validator",
                return_value={"etag": '"stable"'},
            ), patch.object(
                download_common,
                "process_file_without_download",
                return_value="Success",
            ) as reconcile, patch.object(
                download_common, "process_file"
            ) as transfer, patch.object(
                download_common, "write_status_to_file"
            ) as write_status:
                result = download_common.process_shell(
                    {
                        "package": "install-helper",
                        "type": "shell",
                        "url": "https://example.invalid/install-helper.sh",
                    },
                    str(Path(root) / "status.csv"),
                    _content_path(root),
                    "x86_64_rhel_10.2_shellinstall-helper",
                    LOGGER,
                )

            self.assertEqual(result, "Success")
            transfer.assert_not_called()
            reconcile.assert_called_once()
            write_status.assert_called_once()

    def test_galaxy_reuses_exact_collection_version(self):
        """A pinned collection archive is reused without invoking Galaxy."""
        with tempfile.TemporaryDirectory() as root:
            content = Path(_content_path(root))
            archive_dir = (
                content / "ansible_galaxy_collection" / "community.general"
            )
            archive_dir.mkdir(parents=True)
            archive = archive_dir / "community-general-10.0.0.tar.gz"
            archive.write_bytes(b"collection")
            cache = Mock()
            cache.restore.return_value = [str(archive)]
            with patch.object(
                download_common, "_shared_artifact_cache", return_value=cache
            ), patch.object(
                download_common,
                "process_file_without_download",
                return_value="Success",
            ), patch.object(
                download_common.subprocess, "run"
            ) as galaxy_download, patch.object(
                download_common, "write_status_to_file"
            ) as write_status:
                result = download_common.process_ansible_galaxy_collection(
                    {
                        "package": "community.general",
                        "version": "10.0.0",
                        "type": "ansible_galaxy_collection",
                    },
                    str(Path(root) / "status.csv"),
                    str(content),
                    "x86_64_rhel_10.2_ansible_galaxy_collectioncommunity.general",
                    LOGGER,
                )

            self.assertEqual(result, "Success")
            galaxy_download.assert_not_called()
            write_status.assert_called_once()

    def test_iso_cache_identity_is_architecture_scoped(self):
        """The same ISO source is not assumed compatible across architectures."""
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "tools.iso"
            source.write_bytes(b"iso-content")
            cache = Mock()
            cache.restore.return_value = []
            with patch.object(
                download_common, "_shared_artifact_cache", return_value=cache
            ), patch.object(
                download_common,
                "build_source_key",
                return_value="iso-key",
            ) as build_key, patch.object(
                download_common,
                "process_file_without_download",
                return_value="Success",
            ), patch.object(
                download_common, "write_status_to_file"
            ):
                result = download_common.process_iso(
                    {
                        "package": "tools-iso",
                        "type": "iso",
                        "path": str(source),
                    },
                    str(Path(root) / "status.csv"),
                    {},
                    _content_path(root, "aarch64"),
                    "aarch64_rhel_10.2_isotools-iso",
                    LOGGER,
                )

            self.assertEqual(result, "Success")
            self.assertEqual(
                build_key.call_args.kwargs["compatibility"], "aarch64"
            )


class DirectRpmProcessorTests(unittest.TestCase):
    """Prove direct RPM serving is bound to the requested repository."""

    def test_distribution_reconciliation_uses_exact_repository(self):
        """No global publication lookup can select another context's RPM."""
        with tempfile.TemporaryDirectory() as root:
            content = Path(_content_path(root, "x86_64", "10.2"))
            rpm_dir = content / "rpm_file" / "custom-agent"
            rpm_dir.mkdir(parents=True)
            (rpm_dir / "custom-agent.rpm").write_bytes(b"rpm")
            repo_name = "x86_64_rhel_10.2_rpm_filecustom-agent"
            with patch.object(
                rpm_file_artifact_processor,
                "_ensure_pulp_object",
                return_value=(True, {"pulp_href": "/repositories/expected/"}),
            ), patch.object(
                rpm_file_artifact_processor,
                "_reconcile_pulp_distribution",
                return_value=True,
            ) as reconcile, patch.object(
                rpm_file_artifact_processor, "execute_command", return_value=True
            ), patch.object(
                rpm_file_artifact_processor, "write_status_to_file"
            ) as write_status:
                result = rpm_file_artifact_processor.process_rpm_file(
                    {
                        "package": "custom-agent",
                        "type": "rpm_file",
                        "url": "https://example.invalid/custom-agent.rpm",
                    },
                    str(Path(root) / "status.csv"),
                    str(content),
                    repo_name,
                    LOGGER,
                )

            self.assertEqual(result, "Success")
            self.assertEqual(
                reconcile.call_args.args[-1],
                pulp_rpm_commands["show_repository"] % repo_name,
            )
            self.assertNotIn("list_all_publications", pulp_rpm_commands)
            write_status.assert_called_once()

    def test_failed_download_leaves_no_partial_rpm(self):
        """A failed transfer cannot become trusted input on the next run."""
        with tempfile.TemporaryDirectory() as root:
            content = Path(_content_path(root, "x86_64", "10.2"))
            rpm_dir = content / "rpm_file" / "custom-agent"
            expected_rpm = rpm_dir / "custom-agent.rpm"
            with patch.object(
                rpm_file_artifact_processor.subprocess,
                "run",
            ), patch.object(
                rpm_file_artifact_processor, "execute_command", return_value=False
            ), patch.object(
                rpm_file_artifact_processor, "write_status_to_file"
            ) as write_status:
                result = rpm_file_artifact_processor.process_rpm_file(
                    {
                        "package": "custom-agent",
                        "type": "rpm_file",
                        "url": "https://example.invalid/custom-agent.rpm",
                    },
                    str(Path(root) / "status.csv"),
                    str(content),
                    "x86_64_rhel_10.2_rpm_filecustom-agent",
                    LOGGER,
                )

            self.assertEqual(result, "Failed")
            self.assertFalse(expected_rpm.exists())
            self.assertEqual(list(rpm_dir.iterdir()), [])
            write_status.assert_called_once()


if __name__ == "__main__":
    unittest.main()
