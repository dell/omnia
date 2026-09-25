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

"""Execute the Orchestrator provision lifecycle once."""

import pytest
from library.functions import TestLogger, run_playbook
from library.messages import PROVISION_TEST_ASSERT_MSGS as ASSERT
from library.messages import PROVISION_TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(100)
def test_deploy_provision(host):
    """Run ``orchestrator.yml --tags provision``."""
    tc = TC["deploy_provision"]
    test_log = TestLogger(tc["title"], tc["id"])
    result = run_playbook(tag="provision")

    fields = [
        ("Return code", result["rc"]),
        ("Duration seconds", f"{result['duration']:.1f}"),
    ]
    if result["success"]:
        test_log.passed_fields(LOG["playbook_success"], fields)
    else:
        test_log.failed_fields(
            LOG["playbook_failed"],
            [*fields, ("Error", result.get("error", "See playbook output"))],
        )

    assert result["success"], ASSERT["playbook_failed"].format(
        rc=result["rc"], duration=result["duration"]
    )
