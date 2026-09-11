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
                {"stdout": {"latest_version_href": "/repos/1/versions/2/"}},
                {"stdout": {"results": [{"name": "1.0"}]}},
                {"stdout": {"name": "repo"}},
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
                {"stdout": {"latest_version_href": "/repos/1/versions/2/"}},
                {"stdout": {"results": []}},
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
                {"stdout": {"latest_version_href": "/repos/1/versions/2/"}},
                {"stdout": {"results": [{"name": "1.0"}]}},
                None,
            ],
        ):
            ready = download_image._image_already_synced("repo", "1.0", self.logger)
        self.assertFalse(ready)

    @unittest.expectedFailure
    def test_distribution_must_reference_current_repository_state(self):
        """Known gap: existence alone does not prove the distribution is current."""
        with patch.object(
            download_image,
            "execute_command",
            side_effect=[
                {"stdout": {"latest_version_href": "/repos/1/versions/2/"}},
                {"stdout": {"results": [{"name": "1.0"}]}},
                {"stdout": {"name": "repo", "repository": "/repos/other/"}},
            ],
        ):
            ready = download_image._image_already_synced(
                "repo", "1.0", self.logger
            )
        self.assertFalse(ready)

    @unittest.expectedFailure
    def test_repository_query_error_is_not_treated_as_absent(self):
        """Known gap: unknown repository state must not trigger create."""
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

    @unittest.expectedFailure
    def test_distribution_query_error_does_not_trigger_mutation(self):
        """Known gap: an unknown distribution state must fail without create/update."""
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

    @unittest.expectedFailure
    def test_remote_tag_query_error_does_not_become_empty_tag_set(self):
        """Known gap: unknown tags must not overwrite the existing tag union."""
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
            side_effect=[{"returncode": 0}, {"returncode": 0}],
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


if __name__ == "__main__":
    unittest.main()
