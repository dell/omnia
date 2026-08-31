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
Prepare BuildStream — Playbook Execution (--test mode).

Runs repo_manager.yml --tags prepare and image_build_manager.yml --tags prepare
to deploy Pulp server, MinIO S3, and local container registry before running
build_stream.yml.

This file is marked ``@pytest.mark.deploy`` so it is excluded when
running with ``--verify`` (which uses ``-m 'not deploy'``).
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.vars import TEST_CASES as TC
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_prepare_buildstream(host):
    """Run repo_manager and image_build_manager with --tags prepare.

    Flow:
      1. Run repo_manager.yml --tags prepare (deploy Pulp server)
      2. Run image_build_manager.yml --tags prepare (deploy MinIO + Registry)
    """
    tc = TC["deploy_prepare_buildstream"]
    tl = TestLogger(tc["title"], tc["id"])

    # ------------------------------------------------------------------
    # Step 1: Run repo_manager.yml --tags prepare
    # ------------------------------------------------------------------
    tl.check("Running repo_manager.yml --tags prepare...")
    repo_result = run_playbook(
        playbook="../../src/repo_manager/playbooks/repo_manager.yml",
        tag="prepare",
        timeout=1800,
    )

    if repo_result["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=repo_result["duration"],
        ))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=repo_result["rc"], duration=repo_result["duration"],
            ),
            repo_result.get("error", "See playbook output above"),
        )

    assert repo_result["success"], ASSERT["playbook_failed"].format(
        playbook="repo_manager.yml",
        tag="prepare",
        rc=repo_result["rc"],
        duration=repo_result["duration"],
    )

    # ------------------------------------------------------------------
    # Step 2: Run image_build_manager.yml --tags prepare
    # ------------------------------------------------------------------
    tl.check("Running image_build_manager.yml --tags prepare...")
    image_result = run_playbook(
        playbook="../../src/image_build_manager/playbooks/image_build_manager.yml",
        tag="prepare",
        timeout=1800,
    )

    if image_result["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=image_result["duration"],
        ))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=image_result["rc"], duration=image_result["duration"],
            ),
            image_result.get("error", "See playbook output above"),
        )

    assert image_result["success"], ASSERT["playbook_failed"].format(
        playbook="image_build_manager.yml",
        tag="prepare",
        rc=image_result["rc"],
        duration=image_result["duration"],
    )

    tl.passed("Prepare buildstream completed successfully")
