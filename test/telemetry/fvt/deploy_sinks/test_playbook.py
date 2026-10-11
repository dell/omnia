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
Telemetry Deploy Sinks --- Playbook Execution.

Covers the ``deploy_sinks`` Ansible tag which deploys sink infrastructure
(Kafka, VictoriaMetrics, VictoriaLogs) independently of sources.

The runner sets ``OMNIA_DEPLOY_TAG=deploy_sinks`` before invoking this
test, so ``run_playbook(tag=tag)`` executes the correct Ansible tag.

When ``deploy_sinks_enabled`` is configured in ``test_config.yml``,
only the specified sinks are deployed.  An empty list deploys all sinks.

Test cases:
    TEL_FVT_DEPLOY_SINKS_E001: Deploy sinks (--tags deploy_sinks)
"""

import os

import pytest

from library.functions import TestLogger, run_playbook
from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.cleanup_func import (
    deploy_sinks_enabled,
    sinks_extra_vars,
)


@pytest.mark.deploy
@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_sinks(host):
    """TEL_FVT_DEPLOY_SINKS_E001: Run ``telemetry.yml --tags deploy_sinks``."""
    tag = os.environ.get("OMNIA_DEPLOY_TAG", "deploy_sinks")
    tc = TC["deploy_deploy_sinks"]
    tl = TestLogger(tc["title"], tc["id"])

    enabled = deploy_sinks_enabled()
    extra_vars = sinks_extra_vars(enabled)
    sink_label = ", ".join(enabled) if enabled else "all"
    tl.check(f"Running telemetry playbook --tags {tag} (sinks: {sink_label})")

    result = run_playbook(tag=tag, extra_vars=extra_vars or None)

    if result["success"]:
        tl.passed(
            LOG_MSGS["playbook_success"].format(
                duration=f"{result['duration']:.1f}s",
            ),
            f"rc={result['rc']}, sinks={sink_label}",
        )
    else:
        tl.failed(
            LOG_MSGS["playbook_failed"].format(
                rc=result["rc"],
                duration=f"{result['duration']:.1f}s",
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["playbook_failed"].format(
        playbook="telemetry.yml",
        tag=tag,
        rc=result["rc"],
    )
