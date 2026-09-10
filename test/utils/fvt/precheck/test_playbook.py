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
Precheck Scenario - Playbook Deployment Test.

Deploys utils.yml with precheck tag to validate environment.
"""

import pytest

from library.functions import (
    TestLogger,
    load_test_config,
    run_playbook,
    get_utils_input_path,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_UTILS,
    PLAYBOOK_WORKDIR,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.precheck
@pytest.mark.order(0)
def test_deploy_precheck(host):
    """Deploy utils.yml with precheck tag."""
    tc = TC["deploy_precheck"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_UTILS, tag="precheck")

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
        tag="precheck",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" +
        PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )
