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
Cleanup Backup OIM Logs Scenario - Test Automation.

Tests for utils.yml --tags cleanup_backup_oim_logs functionality.
Validates that the tag removes every omnia_oim_logs_* run directory from
the backup workspace. There is no retention policy - cleanup is a full wipe.
"""

import pytest

from library.functions import (
    TestLogger,
    load_test_config,
    run_playbook,
    get_backup_oim_logs_output_path,
    check_backup_workspace_removed,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_UTILS,
    PLAYBOOK_WORKDIR,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.cleanup_backup_oim_logs
@pytest.mark.order(0)
def test_deploy_cleanup_backup_oim_logs(host):
    """Deploy utils.yml with cleanup_backup_oim_logs tag."""
    tc = TC["deploy_cleanup_backup_oim_logs"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_UTILS, tag="cleanup_backup_oim_logs")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_UTILS,
        tag="cleanup_backup_oim_logs",
        rc=result["rc"],
        duration=result["duration"],
        input_path="N/A",
        workdir=config.get("clone_path", "/root/omnia") + "/" +
        PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


@pytest.mark.sanity
@pytest.mark.cleanup_backup_oim_logs
@pytest.mark.order(1)
def test_cleanup_backup_oim_logs_workspace_removed(host):
    """Verify no omnia_oim_logs_* run directories remain after cleanup."""
    tc = TC["cleanup_backup_oim_logs_workspace_removed"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_backup_oim_logs_output_path(host)
    result = check_backup_workspace_removed(host, output_path)

    if result["success"]:
        tl.passed(f"Backup workspace clean: {output_path}")
    else:
        tl.failed(f"Run directories still present: {result['remaining']}")

    assert result["success"], (
        f"Backup run directories not removed: {result['remaining']}"
    )
