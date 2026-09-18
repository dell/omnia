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
Orchestrator Provision — Slurm Provisioning.

ORCH_FVT_PROVISION_E002: Deploy orchestrator.yml --tags provision
"""

from pathlib import Path

import pytest

from library.functions import TestLogger, run_playbook
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.common_vars import SRC_ORCHESTRATOR_DIR


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(0)
def test_slurm_provision(host):
    """ORCH_FVT_PROVISION_E002: Deploy the public provision lifecycle for Slurm."""
    tl = TestLogger(
        TEST_NAMES["deploy_playbook"].format(tag="provision"),
        "ORCH_FVT_PROVISION_E002",
    )
    result = run_playbook(tag="provision")

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
        playbook="orchestrator.yml", tag="provision",
        rc=result["rc"], duration=result["duration"],
    )


@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(1)
def test_slurm_provision_contract():
    """ORCH_FVT_PROVISION_V006: Slurm is part of the public provision lifecycle."""
    tl = TestLogger(
        "Validate Slurm provision lifecycle contract",
        "ORCH_FVT_PROVISION_V006",
    )
    source = (
        Path(SRC_ORCHESTRATOR_DIR) / "playbooks" / "orchestrator.yml"
    ).read_text(encoding="utf-8")
    expected = "ansible.builtin.import_playbook: provision/provision_slurm.yml"
    assert expected in source
    tl.passed("Slurm provision playbook is included by orchestrator.yml")
