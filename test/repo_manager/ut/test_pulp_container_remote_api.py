# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Tests for authenticated Pulp container-remote reconciliation."""

import unittest
from unittest.mock import Mock, patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager import pulp_container_remote_api


class AuthenticatedContainerRemoteTests(unittest.TestCase):
    """Verify synchronous and asynchronous Pulp update responses."""

    def setUp(self):
        self.client = Mock()
        self.logger = Mock()

    def _update(self):
        return pulp_container_remote_api.reconcile_authenticated_container_remote(
            "update",
            name="remote_registry_example_library_ubuntu",
            url="https://registry.example",
            upstream_name="library/ubuntu",
            policy="immediate",
            include_tags=["22.04", "24.04"],
            username="user",
            password="secret",
            logger=self.logger,
            remote_href=(
                "/pulp/api/v3/remotes/container/container/"
                "12345678-1234-1234-1234-123456789abc/"
            ),
        )

    @patch.object(pulp_container_remote_api, "_pulp_rest_client")
    @patch.object(pulp_container_remote_api.time, "sleep")
    def test_async_update_waits_for_completed_task(self, sleep, client_factory):
        """HTTP 202 task responses are polled before reporting success."""
        task_href = (
            "/pulp/api/v3/tasks/12345678-1234-1234-1234-123456789abc/"
        )
        self.client.request_json.return_value = {"task": task_href}
        self.client.get.side_effect = [
            {"state": "waiting"},
            {"state": "running"},
            {"state": "completed"},
        ]
        client_factory.return_value = self.client

        self.assertTrue(self._update())
        self.assertEqual(self.client.get.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(
            self.client.request_json.call_args.kwargs["expected_statuses"],
            (200, 202),
        )

    @patch.object(pulp_container_remote_api, "_pulp_rest_client")
    def test_synchronous_update_response_remains_supported(self, client_factory):
        """An HTTP 200 response without a task remains a successful update."""
        self.client.request_json.return_value = {}
        client_factory.return_value = self.client

        self.assertTrue(self._update())
        self.client.get.assert_not_called()

    @patch.object(pulp_container_remote_api, "_pulp_rest_client")
    def test_failed_async_update_is_reported(self, client_factory):
        """A failed Pulp task cannot be reported as a successful mutation."""
        self.client.request_json.return_value = {
            "task": (
                "/pulp/api/v3/tasks/"
                "12345678-1234-1234-1234-123456789abc/"
            )
        }
        self.client.get.return_value = {"state": "failed"}
        client_factory.return_value = self.client

        self.assertFalse(self._update())
        self.logger.error.assert_called()

    @patch.object(pulp_container_remote_api, "_pulp_rest_client")
    def test_invalid_async_task_href_is_rejected(self, client_factory):
        """The task poller cannot be redirected outside the Pulp task API."""
        self.client.request_json.return_value = {
            "task": "https://attacker.example/task"
        }
        client_factory.return_value = self.client

        self.assertFalse(self._update())
        self.client.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
