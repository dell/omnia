# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared fixtures for the API unit tests."""

from typing import Iterator
from unittest.mock import patch

import pytest

_QUEUE_REPO = (
    "infra.repositories.nfs_playbook_queue_request_repository"
    ".NfsPlaybookQueueRequestRepository"
)


@pytest.fixture
def stub_playbook_queue(tmp_path) -> Iterator[None]:
    """Accept playbook queue submissions without touching the real NFS queue.

    The queue base is fixed at import time from OMNIA_DATA_PATH
    (/opt/omnia/build_stream/playbook_queue), which does not exist on a test
    host, so a stage request would fail with QueueUnavailableError (HTTP 500).
    Request this fixture only in tests that expect a submission to succeed;
    tests of queue failures must keep the real behaviour.
    """
    requests_dir = tmp_path / "playbook_queue" / "requests"
    requests_dir.mkdir(parents=True)
    with patch(f"{_QUEUE_REPO}.is_available", return_value=True), patch(
        f"{_QUEUE_REPO}.write_request", return_value=requests_dir / "request.json"
    ):
        yield
