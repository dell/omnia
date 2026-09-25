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

"""Execute the supported full Orchestrator cleanup lifecycle."""

import pytest
from library.functions import (
    TestLogger,
    cleanup_extra_vars,
    cleanup_selection_fields,
    run_playbook,
)
from library.messages import CLEANUP_TEST_ASSERT_MSGS as ASSERT
from library.messages import CLEANUP_TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

pytestmark = [pytest.mark.destructive]


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_cleanup(host):
    """Run ``orchestrator.yml --tags cleanup`` exactly once."""
    tc = TC["deploy_cleanup"]
    test_log = TestLogger(tc["title"], tc["id"])
    try:
        extra_vars = cleanup_extra_vars()
    except (TypeError, ValueError) as exc:
        test_log.failed_fields(
            LOG["playbook_failed"], [("Configuration error", str(exc))]
        )
        pytest.fail(str(exc))

    result = run_playbook(tag="cleanup", extra_vars=extra_vars or None)
    fields = [
        ("Command", "ansible-playbook playbooks/orchestrator.yml --tags cleanup"),
        *cleanup_selection_fields(),
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
