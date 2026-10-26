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
Automated Cleanup (retention) — Verification.

Verifies the pass recorded by the auto_cleanup exec test:
  the pass used the configured retention settings and submitted exactly
  the expected candidates
  each candidate CLEANED, its job tombstoned, audit trail complete, S3
  objects and NFS artifacts removed
  every other image group and its S3 objects untouched
Skipped when no auto_cleanup exec state exists (exec skipped or not run).
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    load_run_state,
    verify_auto_cleanup,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC
from library.vars.common_vars import SCENARIO_AUTO_CLEANUP


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.auto_cleanup
@pytest.mark.sanity
@pytest.mark.order(3101)
def test_auto_cleanup_result(host):
    """Verify the recorded pass cleaned exactly the eligible image groups."""
    tc = TC["auto_cleanup_result"]
    tl = TestLogger(tc["title"], tc["id"])
    state = load_run_state(SCENARIO_AUTO_CLEANUP)
    if not state["success"]:
        message = LOG["state_missing"].format(error=state["error"],
                                              scenario=SCENARIO_AUTO_CLEANUP)
        tl.skipped(message)
        pytest.skip(message)
    tl.info(LOG["state_used"].format(scenario=SCENARIO_AUTO_CLEANUP,
                                     saved_at=state["saved_at"]))

    data = state["data"]
    result = verify_auto_cleanup(host, data["before"], data["expected"],
                                 data["cleanup_pass"], data["final"], data["config"])
    if result["success"]:
        tl.passed_fields(LOG["auto_cleanup_ok"], result["fields"])
    else:
        tl.failed_fields(LOG["auto_cleanup_failed"].format(count=len(result["failures"])),
                         result["fields"])
    assert result["success"], ASSERT["auto_cleanup_failed"].format(
        failures=failure_summary(result))
