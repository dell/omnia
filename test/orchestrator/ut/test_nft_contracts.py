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

"""Unit tests for orchestrator non-functional test contracts."""

# These contract tests intentionally exercise internal NFT helpers.
# pylint: disable=protected-access

import pytest

from nft import test_idempotency as idempotency
from nft import test_performance as performance
from nft import test_permissions as permissions


pytestmark = pytest.mark.unit


def test_validate_performance_budget_covers_complete_lifecycle():
    """ORCH_UT_107: Validate uses the complete-lifecycle performance budget."""
    assert performance.VALIDATE_THRESHOLD == 60


def test_idempotency_ignores_only_ephemeral_inventory_changes():
    """ORCH_UT_108: Temporary add_host changes do not mask persistent drift."""
    ephemeral_change = {
        "output": """
TASK [orchestrator_setup : Create OIM host group oim] ****************
changed: [localhost]
PLAY RECAP **********************************************************
localhost : ok=1 changed=1 unreachable=0 failed=0 skipped=0
""",
    }
    persistent_change = {
        "output": """
TASK [orchestrator_setup : Create OIM host group oim] ****************
changed: [localhost]
TASK [orchestrator_setup : Persist configuration] *******************
changed: [localhost]
PLAY RECAP **********************************************************
localhost : ok=2 changed=2 unreachable=0 failed=0 skipped=0
""",
    }

    assert idempotency._persistent_changed_count(ephemeral_change) == 0
    assert idempotency._persistent_changed_count(persistent_change) == 1


def test_log_exposure_requires_directory_traversal_and_file_read():
    """ORCH_UT_109: Log exposure includes parent-directory traversal."""
    assert not permissions._is_world_exposed("700", "644")
    assert permissions._is_world_exposed("755", "644")
    assert not permissions._is_world_exposed("755", "640")
    assert not permissions._is_world_exposed("", "644")
