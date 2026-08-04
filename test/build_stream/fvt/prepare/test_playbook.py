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
Build Stream — Deploy (prepare tag only).

TC_PR_001: Deploy build_stream.yml --tags prepare
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_prepare(host):
    """TC_PR_001: Deploy build_stream.yml --tags prepare."""
    tl = TestLogger(
        TEST_NAMES["deploy_playbook"].format(tag="prepare"), "TC_PR_001",
    )
    result = run_playbook(tag="prepare")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=result["duration"]
        ))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See playbook output above"),
        )

    assert result["success"], ASSERT["playbook_failed"].format(
        playbook="build_stream.yml", tag="prepare",
        rc=result["rc"], duration=result["duration"],
        log_path="Check playbook output above",
    )
