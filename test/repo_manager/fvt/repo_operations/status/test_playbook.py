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
Repo Operations — Status playbook execution test.

  TC_ST_000: Run repo_manager.yml --tags status
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.messages import TEST_NAMES, LOG_MSGS, ASSERT_MSGS


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_run_status(host):
    """TC_ST_000: Run repo_manager.yml --tags status."""
    tag = "status"
    tl = TestLogger(
        TEST_NAMES["deploy_playbook"].format(tag=tag), "TC_ST_000",
    )

    result = run_playbook(tag=tag)

    if result["success"]:
        tl.passed(
            LOG_MSGS["playbook_success"].format(duration=result["duration"]),
        )
    else:
        tl.failed(
            LOG_MSGS["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"],
            ),
        )

    assert result["success"], ASSERT_MSGS["playbook_failed"].format(
        playbook="repo_manager.yml", tag=tag,
        rc=result["rc"], duration=result["duration"],
    )
