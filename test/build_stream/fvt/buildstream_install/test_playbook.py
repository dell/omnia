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
Build Stream Install — Playbook Deployment.

Deploys build_stream.yml with -e standalone_mode=true and verifies the
playbook completes successfully.  No --tags filter is applied so that
all plays (setup, credentials, prepare, build) execute — matching the
manual invocation::

    ansible-playbook build_stream.yml -e standalone_mode=true

The standalone_mode=true flag tells the playbook to use local input
directories instead of requiring container-based paths.
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_buildstream_install(host):
    """Deploy build_stream.yml -e standalone_mode=true (no tag filter).

    Runs the full playbook without --tags so all plays execute:
      1. build_stream_setup (input dirs, OIM metadata)
      2. credential_utility (create/validate credentials)
      3. prepare_build_stream (Postgres, GitLab, BSM containers)
      4. setup_gitlab (GitLab CI/CD configuration)
    """
    tc = TC["deploy_buildstream_install"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(
        timeout=3600,
        extra_vars={"standalone_mode": True},
    )

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=result["duration"],
        ))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See playbook output above"),
        )

    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="all",
        rc=result["rc"],
        duration=result["duration"],
    )
