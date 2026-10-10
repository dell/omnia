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
Telemetry — Non-Functional PowerScale Channel Transition Tests.

Validates playbook-level deployment and status reporting across
PowerScale ``metrics_enabled`` / ``logs_enabled`` flag variations.

Test Coverage:
  - Metrics enable/disable transitions
  - Status reporting verification (deployed/disabled/skipped)
  - Idempotency verification

This test focuses on playbook-level validation (can the playbook deploy with
different flag values and report the expected status) rather than
component-level verification, which is covered by FVT tests. Logs are managed
via the PowerScale API, not by Omnia, so the log channel assertions validate
status reporting only, not log forwarding.

Execution order:
  - Runs after the resilience tests (order 122) and before the cleanup
    tests (130+), which tear the stack down.

Test cases:
    TEL_NFT_025: PowerScale metrics/logs channel transitions (order 122)
"""

import pytest

from omnia_auto import TestLogger, run_playbook

from library.functions.powerscale_func import (
    get_powerscale_channel_status,
    set_powerscale_channel_state,
)
from library.messages.telemetry_msgs import (
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
)
from library.vars.common_vars import (
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
    POWERSCALE_CHANNEL_STEPS,
)
from library.vars.test_case_vars import TEST_CASES as TC


@pytest.mark.nft
@pytest.mark.source
@pytest.mark.order(122)
def test_powerscale_channels_comprehensive(host):
    """Verify PowerScale metrics/logs channel transitions.

    Walks the transitions listed in ``POWERSCALE_CHANNEL_STEPS``:
      1. true, true (baseline)
      2. true, false (metrics only)
      3. false, true (logs only)
      4. false, false (both disabled)
      5. true, true (re-enable both)
      6. true, true (idempotency, same state)

    For every step the source flags are updated, the execute playbook is
    run, and the PowerScale channel status reported in
    ``telemetry_status.yml`` is compared with the expected state.
    """
    tc = TC["nft_powerscale_channels"]
    tl = TestLogger(tc["title"], tc["id"])

    for step in POWERSCALE_CHANNEL_STEPS:
        name = step["name"]
        tl.check(
            LOG_MSGS["powerscale_channel_step"].format(
                step=name,
                metrics=step["metrics_enabled"],
                logs=step["logs_enabled"],
            )
        )

        update = set_powerscale_channel_state(
            host, step["metrics_enabled"], step["logs_enabled"],
        )
        if not update["success"]:
            tl.failed(
                LOG_MSGS["powerscale_channel_config_failed"].format(step=name),
                update["error"],
            )
            pytest.fail(
                ASSERT_MSGS["powerscale_channel_config_failed"].format(
                    step=name, error=update["error"],
                )
            )

        deploy = run_playbook(
            playbook=PLAYBOOK_ENTRY_POINT,
            playbook_workdir=PLAYBOOK_WORKDIR,
            tag="execute",
        )
        if deploy["rc"] != 0:
            tl.failed(
                LOG_MSGS["powerscale_channel_deploy_failed"].format(
                    step=name, rc=deploy["rc"],
                )
            )
            pytest.fail(
                ASSERT_MSGS["powerscale_channel_deploy_failed"].format(
                    step=name, rc=deploy["rc"],
                )
            )

        status = get_powerscale_channel_status(host)
        if not status["success"]:
            tl.failed(
                LOG_MSGS["powerscale_channel_status_unreadable"].format(step=name),
                status["error"],
            )
            pytest.fail(
                ASSERT_MSGS["powerscale_channel_status_unreadable"].format(
                    step=name, error=status["error"],
                )
            )

        if (
            status["metrics"] != step["expected_metrics"]
            or status["logs"] != step["expected_logs"]
        ):
            tl.failed(
                LOG_MSGS["powerscale_channel_status_mismatch"].format(step=name)
            )
            pytest.fail(
                ASSERT_MSGS["powerscale_channel_status_mismatch"].format(
                    step=name,
                    expected_metrics=step["expected_metrics"],
                    expected_logs=step["expected_logs"],
                    actual_metrics=status["metrics"],
                    actual_logs=status["logs"],
                )
            )

        tl.passed(
            LOG_MSGS["powerscale_channel_step_passed"].format(
                step=name, metrics=status["metrics"], logs=status["logs"],
            )
        )

    tl.passed(LOG_MSGS["powerscale_channel_all_passed"])
