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
Discovery — Full End-to-End Deploy.

TC_DS_000: Deploy discovery.yml (full run)
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.test_case_vars import TEST_CASES as TC


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_discovery(host):
    """TC_DS_000: Deploy discovery.yml (full run)."""
    tc = TC["deploy_discovery"]
    tl = TestLogger(
        TEST_NAMES["deploy_playbook"].format(mechanism="ome"),
        tc["id"],
    )
    result = run_playbook(
        extra_vars={"discovery_mechanism": "ome"},
        timeout=3600,
    )

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
        playbook="discovery.yml",
        rc=result["rc"], duration=result["duration"],
    )
