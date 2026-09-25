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

"""
Telemetry Cleanup — Playbook Execution.

Runs the default cleanup playbook (--tags cleanup) which removes all
telemetry workloads, credentials, and logs.

Execution order:
    Order 5 — runs AFTER the preservation cleanup phase (orders 0-4).
    When delete_sinks_volume=true, the preservation phase is skipped
    and this is effectively the first test to run.

Variable interactions (from Ansible source):
    - delete_sinks_volume=true  → passes Delete_sinks_volume=true to
      the playbook, which deletes ALL PVCs including sink volumes.
    - Default (false)           → sink PVCs are preserved; source PVCs
      are always deleted.

Test cases:
    TEL_FVT_CLEANUP_E001: Deploy telemetry (--tags cleanup)
"""

import pytest

from library.functions import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions import run_playbook


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(3)
def test_deploy_cleanup(host, delete_sinks_volume):
    """TEL_FVT_CLEANUP_E001: Deploy telemetry (--tags cleanup).

    Runs the default cleanup playbook.  When delete_sinks_volume=true,
    passes -e Delete_sinks_volume=true to also delete sink PVCs.

    Ordered AFTER preservation verification (order 3).
    Deletion verification tests (V016, V018) run after this at orders 4-5.
    """
    tc = TC["deploy_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])

    extra_vars = {"Delete_sinks_volume": "true"} if delete_sinks_volume else None
    mode_label = "with volume deletion" if delete_sinks_volume else "default"
    tl.check(f"Running telemetry playbook --tags cleanup ({mode_label})")
    result = run_playbook(tag="cleanup", extra_vars=extra_vars)

    if result["success"]:
        tl.passed(
            LOG_MSGS["playbook_success"].format(
                duration=f"{result['duration']:.1f}s",
            ),
            f"rc={result['rc']}",
        )
    else:
        tl.failed(
            LOG_MSGS["playbook_failed"].format(
                rc=result["rc"],
                duration=f"{result['duration']:.1f}s",
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["playbook_failed"].format(
        playbook="telemetry.yml",
        tag="cleanup",
        rc=result["rc"],
    )
