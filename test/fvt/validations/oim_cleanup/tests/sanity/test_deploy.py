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
OIM Cleanup — Playbook Deployment Test.

Runs the oim_cleanup.yml playbook inside omnia_core container using the
playbook_runner. Output is streamed live to the terminal.

This test runs the playbook deployment step. It should run BEFORE
the verification tests.

Usage:
    run_validation oim_cleanup deploy       # Run playbook only
    run_validation oim_cleanup test         # Run playbook + all verification tests
    run_validation oim_cleanup verify       # Run verification tests only (skip deploy)
"""

import pytest

from automation_library.core import TestLogger
from automation_library.playbook_runner import PlaybookRunner, RUNNER_ASSERT_MSGS
from automation_library.oim_cleanup.messages import (
    DEPLOY_TEST_NAMES,
    DEPLOY_LOG_MSGS,
    DEPLOY_SKIP_MSGS,
)


# =============================================================================
# PLAYBOOK CONFIGURATION
# =============================================================================

PLAYBOOK_PATH = "/omnia/src/playbooks/utils/oim_cleanup.yml"
PLAYBOOK_WORKDIR = "/omnia/src/playbooks/utils"


# =============================================================================
# 0. DEPLOY: PRE-FLIGHT CONTAINER CHECK + RUN OIM_CLEANUP PLAYBOOK
# =============================================================================

@pytest.mark.deploy
@pytest.mark.order(0)
def test_run_oim_cleanup_playbook(host):
    """
    Deploy: Verify omnia_core container then run oim_cleanup.yml.

    Single deploy test case that first verifies the omnia_core container is
    running. If it is NOT running there is nothing to clean up, so the test
    is skipped and reported as passed. If it IS running, the oim_cleanup
    playbook is executed inside the container with live streaming output.

    Equivalent to running the playbook directly:
        podman exec -w /omnia/src/playbooks/utils omnia_core ansible-playbook oim_cleanup.yml -v
    """
    log = TestLogger(DEPLOY_TEST_NAMES["run_oim_cleanup"])

    runner = PlaybookRunner()

    # Pre-flight: container must be running, otherwise nothing to clean up
    log.check(DEPLOY_LOG_MSGS["container_check"])
    if not runner.check_container():
        print(f"    │ {DEPLOY_SKIP_MSGS['container_not_running']}", flush=True)
        log.skipped(DEPLOY_SKIP_MSGS["container_not_running"])
        pytest.skip(DEPLOY_SKIP_MSGS["container_not_running"])

    log.check(DEPLOY_LOG_MSGS["container_running"])

    # Run the cleanup playbook (dataset sync handled inside runner.run())
    log.check(DEPLOY_LOG_MSGS["playbook_running"].format(playbook=PLAYBOOK_PATH))
    result = runner.run(PLAYBOOK_PATH, workdir=PLAYBOOK_WORKDIR)

    if result["success"]:
        log.passed(
            DEPLOY_LOG_MSGS["playbook_success"].format(
                rc=result["rc"], duration=result["duration"]
            )
        )
    else:
        log.failed(
            DEPLOY_LOG_MSGS["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"]
            ),
            result["error"],
        )

    assert result["success"], RUNNER_ASSERT_MSGS["playbook_failed"].format(
        playbook=PLAYBOOK_PATH,
        rc=result["rc"],
        duration=result["duration"],
    )
