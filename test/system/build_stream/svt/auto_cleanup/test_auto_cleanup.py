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
Automated Cleanup (retention) — Execute (exec entry point).

Runs the pass the AutoCleanupScheduler runs every evaluation interval:
  snapshot every image group (DB clock) and every s3://boot-images/ object
  compute the expected FAILED-phase and retention-phase candidates
  (cleanup_cron.py rules) and log the decision for each group
  run one cleanup_cron.main() pass in omnia_build_stream, logs followed
  wait until no submitted group is CLEANING
The facts are recorded for the verification suite (verify phase).
"""

import pytest

from library.functions import (
    TestLogger,
    installation_settings,
    load_test_config,
    retention_settings,
    run_auto_cleanup,
    save_run_state,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC
from library.vars.common_vars import SCENARIO_AUTO_CLEANUP


@pytest.mark.svt
@pytest.mark.br_86010
@pytest.mark.auto_cleanup
@pytest.mark.deploy
@pytest.mark.destructive
@pytest.mark.sanity
@pytest.mark.order(3002)
def test_run_auto_cleanup_pass(host):
    """Run one automated cleanup pass and wait until it is finalized."""
    tc = TC["run_auto_cleanup_pass"]
    tl = TestLogger(tc["title"], tc["id"])
    config = retention_settings(host)["config"]
    tl.info(LOG["auto_cleanup_settings"].format(**config))
    tl.info(LOG["auto_cleanup_pass"])

    poll = installation_settings(load_test_config())["poll_interval"]
    result = run_auto_cleanup(host, config, poll, tl.info)
    state = result["state"]
    if state:
        save_run_state(SCENARIO_AUTO_CLEANUP, state)
        expected = state["expected"]
        tl.check(LOG["auto_cleanup_expected"].format(
            failed=len(expected["failed"]), retention=len(expected["retention"]),
            total=len(state["before"]["groups"])))
        if not expected["failed"] and not expected["retention"]:
            tl.info(LOG["auto_cleanup_noop"])

    if result["success"]:
        tl.passed(LOG["auto_cleanup_pass_ok"].format(
            rc=state["cleanup_pass"]["rc"], count=len(state["final"])))
    else:
        tl.failed(LOG["auto_cleanup_pass_failed"].format(error=result["error"]))
    assert result["success"], ASSERT["auto_cleanup_pass_failed"].format(error=result["error"])
