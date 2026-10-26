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
Automated Cleanup — Precheck (exec, runs before the cleanup pass).

Clears any earlier auto_cleanup exec state, then checks that one pass can
run and be finalized:
  retention group of build_stream_config.yml valid (as the scheduler
  validates it)
  omnia_build_stream container running (runs cleanup_cron.main())
  playbook-watcher active (runs the playbook that finalizes CLEANING groups)
Skipped when retention.auto_cleanup_enabled is false (the scheduler is
idle); a skip or failure skips the rest of the auto_cleanup scenario.
"""

import pytest

from library.functions import (
    TestLogger,
    clear_run_state,
    failure_summary,
    precheck_auto_cleanup,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC
from library.vars.common_vars import SCENARIO_AUTO_CLEANUP


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.auto_cleanup
@pytest.mark.deploy
@pytest.mark.precheck
@pytest.mark.sanity
@pytest.mark.order(3001)
def test_precheck_auto_cleanup(host):
    """Check retention settings, the BuildStream container and playbook-watcher."""
    tc = TC["precheck_auto_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    clear_run_state(SCENARIO_AUTO_CLEANUP)
    result = precheck_auto_cleanup(host)

    if result["success"] and not result["enabled"]:
        tl.skipped(LOG["auto_cleanup_disabled"].format(path=result["path"]))
        pytest.skip(LOG["auto_cleanup_disabled"].format(path=result["path"]))
    if result["success"]:
        tl.passed_fields(LOG["precheck_ok"].format(scenario=SCENARIO_AUTO_CLEANUP),
                         result["fields"])
    else:
        tl.failed_fields(LOG["precheck_failed"].format(
            scenario=SCENARIO_AUTO_CLEANUP, count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["precheck_auto_cleanup_failed"].format(
        failures=failure_summary(result))
