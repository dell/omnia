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
Full Cleanup — Precheck (exec, runs before any cleanup playbook).

Clears any earlier cleanup exec state, then checks that the configured
cleanup can run:
  at least one cleanup block is enabled in test_config.yml
  omnia.env sets the variables cleanup verification resolves paths from
  each enabled domain's playbook exists in the checkout
A failure skips the rest of the cleanup scenario.
"""

import pytest

from library.functions import (
    TestLogger,
    cleanup_plan,
    clear_run_state,
    failure_summary,
    load_test_config,
    precheck_cleanup,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC
from library.vars.common_vars import SCENARIO_CLEANUP


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.cleanup
@pytest.mark.deploy
@pytest.mark.precheck
@pytest.mark.sanity
@pytest.mark.order(4001)
def test_precheck_cleanup(host):
    """Check the enabled cleanup domains and their playbooks."""
    tc = TC["precheck_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    clear_run_state(SCENARIO_CLEANUP)
    result = precheck_cleanup(host, cleanup_plan(load_test_config()))

    if result["success"]:
        tl.passed_fields(LOG["precheck_ok"].format(scenario=SCENARIO_CLEANUP),
                         result["fields"])
    else:
        tl.failed_fields(LOG["precheck_failed"].format(
            scenario=SCENARIO_CLEANUP, count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["precheck_cleanup_failed"].format(
        failures=failure_summary(result))
