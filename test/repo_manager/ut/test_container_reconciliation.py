# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Tests for container readiness, tag union and fail-closed query handling."""

# pylint: disable=protected-access

import unittest
from unittest.mock import Mock, patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager import container_repo_utils, download_image


class ContainerReconciliationTests(unittest.TestCase):
    """Model ready, incomplete and unknown Pulp container states."""

    def setUp(self):
        self.logger = Mock()

    def test_ready_tag_and_distribution_are_reused(self):
        """A tag with a serving distribution performs no repair."""
        with patch.object(
            download_image,
            "execute_command",
            side_effect=[
                {
                    "success": True,
                    "stdout": {"latest_version_href": "/repos/1/versions/2/"},
                },
                {"success": True, "stdout": {"results": [{"name": "1.0"}]}},
                {"success": True, "stdout": {"name": "repo"}},
            ],
        ) as execute:
            ready = download_image._image_already_synced("repo", "1.0", self.logger)
        self.assertTrue(ready)
        self.assertEqual(execute.call_count, 3)

    def test_missing_tag_is_incomplete(self):
        """An existing repository without the requested tag needs repair."""
        with patch.object(
            download_image,
            "execute_command",
            side_effect=[
                {
                    "success": True,
                    "stdout": {"latest_version_href": "/repos/1/versions/2/"},
                },
                {"success": True, "stdout": {"results": []}},
            ],
        ):
            ready = download_image._image_already_synced("repo", "1.0", self.logger)
        self.assertFalse(ready)

    def test_missing_distribution_is_incomplete(self):
        """Content without a pullable distribution is not ready."""
        with patch.object(
            download_image,
            "execute_command",
            side_effect=[
                {
                    "success": True,
                    "stdout": {"latest_version_href": "/repos/1/versions/2/"},
                },
                {"success": True, "stdout": {"results": [{"name": "1.0"}]}},
                {
                    "success": False,
                    "returncode": 1,
                    "stderr": "404 distribution does not exist",
                },
            ],
        ):
            ready = download_image._image_already_synced("repo", "1.0", self.logger)
        self.assertFalse(ready)

    def test_distribution_must_reference_current_repository_state(self):
        """Existence alone does not prove the distribution is current."""
        with patch.object(
            download_image,
            "execute_command",
            side_effect=[
                {
                    "success": True,
                    "stdout": {"latest_version_href": "/repos/1/versions/2/"},
                },
                {"success": True, "stdout": {"results": [{"name": "1.0"}]}},
                {
                    "success": True,
                    "stdout": {"name": "repo", "repository": "/repos/other/"},
                },
            ],
        ):
            ready = download_image._image_already_synced(
                "repo", "1.0", self.logger
            )
        self.assertFalse(ready)

    def test_direct_manifest_requires_target_architecture(self):
        """A direct image manifest must match the selected node CPU."""
        responses = [
            {
                "success": True,
                "stdout": {"latest_version_href": "/repos/1/versions/2/"},
            },
            {
                "success": True,
                "stdout": {
                    "results": [{"tagged_manifest": "/manifests/amd64/"}]
                },
            },
            {
                "success": True,
                "stdout": {"architecture": "amd64", "os": "linux"},
            },
            {
                "success": True,
                "stdout": {"repository": "/repos/1/"},
            },
        ]
        with patch.object(
                download_image, "execute_command", side_effect=responses):
            ready = download_image._image_already_synced(
                "repo", "1.0", self.logger, "x86_64"
            )
        self.assertTrue(ready)

    def test_wrong_container_architecture_is_incomplete(self):
        """An amd64-only image is not ready for an aarch64 context."""
        responses = [
            {
                "success": True,
                "stdout": {"latest_version_href": "/repos/1/versions/2/"},
            },
            {
                "success": True,
                "stdout": {
                    "results": [{"tagged_manifest": "/manifests/amd64/"}]
                },
            },
            {
                "success": True,
                "stdout": {"architecture": "amd64", "os": "linux"},
            },
        ]
        with patch.object(
                download_image, "execute_command", side_effect=responses):
            ready = download_image._image_already_synced(
                "repo", "1.0", self.logger, "aarch64"
            )
        self.assertFalse(ready)

    def test_multiarch_index_supports_arm64_context(self):
        """A manifest list is ready when one child is Linux arm64."""
        responses = [
            {
                "success": True,
                "stdout": {"latest_version_href": "/repos/1/versions/2/"},
            },
            {
                "success": True,
                "stdout": {
                    "results": [{"tagged_manifest": "/manifests/index/"}]
                },
            },
            {
                "success": True,
                "stdout": {
                    "listed_manifests": [
                        "/manifests/amd64/", "/manifests/arm64/"
                    ]
                },
            },
            {
                "success": True,
                "stdout": {"architecture": "amd64", "os": "linux"},
            },
            {
                "success": True,
                "stdout": {"architecture": "arm64", "os": "linux"},
            },
            {
                "success": True,
                "stdout": {"repository": "/repos/1/"},
            },
        ]
        with patch.object(
                download_image, "execute_command", side_effect=responses):
            ready = download_image._image_already_synced(
                "repo", "1.0", self.logger, "aarch64"
            )
        self.assertTrue(ready)

    def test_digest_image_is_synced_and_architecture_verified(self):
        """Digest-based public images execute sync with the target CPU."""
        digest = "sha256:" + ("a" * 64)
        package = {
            "type": "image",
            "package": "docker.io/library/example",
            "digest": digest,
        }
        with patch(
            "ansible.module_utils.repo_manager.repo_settings."
            "get_container_sync_policy",
            return_value="on_demand",
        ), patch.object(
            download_image, "create_container_repository", return_value=True
        ), patch.object(
            download_image, "_image_already_synced", return_value=False
        ), patch.object(
            download_image, "create_container_remote_digest", return_value=True
        ), patch.object(
            download_image, "sync_container_repository", return_value=True
        ) as sync, patch.object(
            download_image, "write_status_to_file"
        ):
            result = download_image.process_image(
                package,
                "/tmp/status.csv",
                {},
                {},
                "",
                "",
                "aarch64",
                self.logger,
            )
        self.assertEqual(result, "Success")
        self.assertEqual(sync.call_args.kwargs["tag"], digest)
        self.assertEqual(sync.call_args.kwargs["architecture"], "aarch64")

    def test_ready_public_image_skips_upstream_tag_validation(self):
        """A later context reuses ready public content without upstream I/O."""
        package = {
            "type": "image",
            "package": "docker.io/library/example",
            "tag": "1.0",
            "source_registry": "docker.io",
        }
        with patch(
            "ansible.module_utils.repo_manager.repo_settings."
            "get_container_sync_policy",
            return_value="on_demand",
        ), patch.object(
            download_image, "_image_already_synced", return_value=True
        ) as ready, patch.object(
            download_image, "validate_tag_via_pulp_sync"
        ) as validate_tag, patch.object(
            download_image, "create_container_repository"
        ) as create_repository, patch.object(
            download_image, "sync_container_repository"
        ) as sync, patch.object(
            download_image, "write_status_to_file"
        ):
            result = download_image.process_image(
                package,
                "/tmp/status.csv",
                {},
                {},
                "",
                "",
                "x86_64",
                self.logger,
            )
        self.assertEqual(result, "Success")
        ready.assert_called_once()
        validate_tag.assert_not_called()
        create_repository.assert_not_called()
        sync.assert_not_called()

    def test_ready_configured_image_reconciles_without_tag_validation(self):
        """Ready private content still reconciles its remote without a probe."""
        package = {
            "type": "image",
            "package": "registry.example/team/example",
            "tag": "1.0",
            "source_registry": "private",
        }
        registry_context = {
            "name": "private",
            "base_url": "https://registry.example",
            "auth_type": "none",
            "tls": {},
        }
        with patch.object(
            download_image, "_image_already_synced", return_value=True
        ) as ready, patch.object(
            download_image, "create_or_update_configured_remote", return_value=True
        ) as reconcile_remote, patch.object(
            download_image, "validate_tag_via_pulp_sync"
        ) as validate_tag, patch.object(
            download_image, "create_container_repository"
        ) as create_repository, patch.object(
            download_image, "sync_container_repository"
        ) as sync:
            result = download_image._process_configured_registry_image(
                package,
                {},
                registry_context,
                "on_demand",
                "aarch64",
                self.logger,
            )
        self.assertEqual(
            result,
            ("Success", "registry.example/team/example:1.0"),
        )
        ready.assert_called_once()
        reconcile_remote.assert_called_once()
        validate_tag.assert_not_called()
        create_repository.assert_not_called()
        sync.assert_not_called()

    def test_incomplete_public_image_validates_and_synchronizes(self):
        """A missing public tag keeps the original validation and sync flow."""
        package = {
            "type": "image",
            "package": "docker.io/library/example",
            "tag": "1.0",
            "source_registry": "docker.io",
        }
        with patch(
            "ansible.module_utils.repo_manager.repo_settings."
            "get_container_sync_policy",
            return_value="on_demand",
        ), patch.object(
            download_image, "_image_already_synced", side_effect=[False, False]
        ) as ready, patch.object(
            download_image, "validate_tag_via_pulp_sync", return_value=True
        ) as validate_tag, patch.object(
            download_image, "create_container_repository", return_value=True
        ) as create_repository, patch.object(
            download_image, "create_container_remote", return_value=True
        ) as create_remote, patch.object(
            download_image, "sync_container_repository", return_value=True
        ) as sync, patch.object(
            download_image, "write_status_to_file"
        ):
            result = download_image.process_image(
                package,
                "/tmp/status.csv",
                {},
                {},
                "",
                "",
                "x86_64",
                self.logger,
            )
        self.assertEqual(result, "Success")
        self.assertEqual(ready.call_count, 2)
        validate_tag.assert_called_once()
        create_repository.assert_called_once()
        create_remote.assert_called_once()
        sync.assert_called_once()

    def test_invalid_public_tag_is_rejected_before_persistent_mutation(self):
        """A missing upstream tag cannot create persistent Pulp objects."""
        package = {
            "type": "image",
            "package": "docker.io/library/example",
            "tag": "missing",
            "source_registry": "docker.io",
        }
        with patch(
            "ansible.module_utils.repo_manager.repo_settings."
            "get_container_sync_policy",
            return_value="on_demand",
        ), patch.object(
            download_image, "_image_already_synced", return_value=False
        ), patch.object(
            download_image, "validate_tag_via_pulp_sync", return_value=False
        ) as validate_tag, patch.object(
            download_image, "create_container_repository"
        ) as create_repository, patch.object(
            download_image, "create_container_remote"
        ) as create_remote, patch.object(
            download_image, "sync_container_repository"
        ) as sync, patch.object(
            download_image, "write_status_to_file"
        ):
            result = download_image.process_image(
                package,
                "/tmp/status.csv",
                {},
                {},
                "",
                "",
                "x86_64",
                self.logger,
            )
        self.assertEqual(result, "Skipped-InvalidTag")
        validate_tag.assert_called_once()
        create_repository.assert_not_called()
        create_remote.assert_not_called()
        sync.assert_not_called()

    def test_second_os_context_reuses_first_image_sync(self):
        """RHEL 10.2 reuses the image synchronized during the 10.0 pass."""
        package = {
            "type": "image",
            "package": "docker.io/library/example",
            "tag": "1.0",
            "source_registry": "docker.io",
        }
        with patch(
            "ansible.module_utils.repo_manager.repo_settings."
            "get_container_sync_policy",
            return_value="on_demand",
        ), patch.object(
            download_image,
            "_image_already_synced",
            side_effect=[False, False, True],
        ) as ready, patch.object(
            download_image, "validate_tag_via_pulp_sync", return_value=True
        ) as validate_tag, patch.object(
            download_image, "create_container_repository", return_value=True
        ) as create_repository, patch.object(
            download_image, "create_container_remote", return_value=True
        ) as create_remote, patch.object(
            download_image, "sync_container_repository", return_value=True
        ) as sync, patch.object(
            download_image, "write_status_to_file"
        ):
            first_result = download_image.process_image(
                package,
                "/tmp/status.csv",
                {"os_version": "10.0"},
                {},
                "",
                "",
                "x86_64",
                self.logger,
            )
            second_result = download_image.process_image(
                package,
                "/tmp/status.csv",
                {"os_version": "10.2"},
                {},
                "",
                "",
                "x86_64",
                self.logger,
            )
        self.assertEqual((first_result, second_result), ("Success", "Success"))
        self.assertEqual(ready.call_count, 3)
        validate_tag.assert_called_once()
        create_repository.assert_called_once()
        create_remote.assert_called_once()
        sync.assert_called_once()

    def test_process_image_preserves_positional_logger_compatibility(self):
        """The historic final positional logger argument remains supported."""
        package = {"type": "image", "package": ""}
        with patch.object(download_image, "write_status_to_file"):
            result = download_image.process_image(
                package,
                "/tmp/status.csv",
                {},
                {},
                "",
                "",
                self.logger,
            )
        self.assertEqual(result, "Failed")

    def test_repository_query_error_is_not_treated_as_absent(self):
        """Unknown repository state must not trigger create."""
        with patch.object(
            container_repo_utils,
            "execute_command",
            side_effect=[None, {"returncode": 0}],
        ) as execute:
            result = container_repo_utils.create_container_repository(
                "repo", self.logger
            )
        self.assertFalse(result)
        execute.assert_called_once()

    def test_distribution_query_error_does_not_trigger_mutation(self):
        """An unknown distribution state must fail without create/update."""
        with patch.object(
            container_repo_utils,
            "execute_command",
            side_effect=[None, {"returncode": 0}],
        ) as execute:
            result = container_repo_utils.create_container_distribution(
                "repo", "library/repo", self.logger
            )
        self.assertFalse(result)
        execute.assert_called_once()

    def test_remote_tag_query_error_does_not_become_empty_tag_set(self):
        """Unknown tags must not overwrite the existing tag union."""
        with patch.object(
            container_repo_utils, "execute_command", return_value=None
        ):
            with self.assertRaises(ValueError):
                container_repo_utils.extract_existing_tags("remote", self.logger)

    def test_new_tag_is_union_with_existing_tags(self):
        """Adding one tag preserves all tags already configured on the remote."""
        with patch.object(
            download_image,
            "execute_command",
            side_effect=[
                {
                    "returncode": 0,
                    "success": True,
                    "stdout": {"name": "remote"},
                },
                {"returncode": 0},
            ],
        ), patch.object(
            download_image, "extract_existing_tags", return_value=["1.0", "2.0"]
        ), patch.object(
            download_image,
            "build_container_remote_command",
            return_value=["pulp", "container", "remote", "update"],
        ) as build:
            result = download_image.create_container_remote(
                "remote",
                "https://registry.example",
                "library/image",
                "on_demand",
                "3.0",
                self.logger,
            )
        self.assertTrue(result)
        self.assertEqual(
            build.call_args.kwargs["include_tags"],
            ["1.0", "2.0", "3.0"],
        )

    def test_remote_query_error_does_not_trigger_create(self):
        """Unknown remote state cannot be treated as confirmed absence."""
        with patch.object(
            download_image, "execute_command", return_value=None
        ) as execute:
            result = download_image.create_container_remote(
                "remote",
                "https://registry.example",
                "library/image",
                "on_demand",
                "1.0",
                self.logger,
            )
        self.assertFalse(result)
        execute.assert_called_once()

    def test_confirmed_missing_remote_is_created(self):
        """Only an explicit not-found response authorizes remote creation."""
        not_found = {
            "returncode": 1,
            "success": False,
            "stdout": None,
            "stderr": "404 not found",
        }
        with patch.object(
            download_image,
            "execute_command",
            side_effect=[not_found, {"returncode": 0}],
        ), patch.object(
            download_image,
            "build_container_remote_command",
            return_value=["pulp", "container", "remote", "create"],
        ) as build:
            result = download_image.create_container_remote(
                "remote",
                "https://registry.example",
                "library/image",
                "on_demand",
                "1.0",
                self.logger,
            )
        self.assertTrue(result)
        self.assertEqual(build.call_args.args[0], "create")


if __name__ == "__main__":
    unittest.main()
