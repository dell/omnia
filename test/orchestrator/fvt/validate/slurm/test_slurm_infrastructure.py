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
Orchestrator Validate — Slurm Infrastructure Validation.

TC_SL_014: All nodes from PXE mapping are joined to Slurm cluster
TC_SL_015: All slurm compute nodes in idle state (sinfo)
TC_SL_016: All login and login compiler nodes in idle state (scontrol)
"""

import pytest

from library.functions import TestLogger
from library.functions.slurm_func import (
    check_slurm_enabled,
    check_all_pxe_nodes_in_slurm_cluster,
    check_slurm_nodes_idle,
    check_login_nodes_idle,
)
from library.messages import (
    SLURM_TEST_LOG_MSGS as LOG,
    SLURM_TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.slurm_vars import TEST_CASES as TC


def _skip_if_slurm_disabled(host):
    """Skip test if Slurm is not enabled in catalog."""
    result = check_slurm_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(1)
def test_all_pxe_nodes_in_slurm_cluster(host):
    """TC_SL_014: All nodes from PXE mapping are joined to Slurm cluster."""
    _skip_if_slurm_disabled(host)

    tc = TC["all_pxe_nodes_in_slurm_cluster"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking if PXE nodes are in SLURM cluster")
    result = check_all_pxe_nodes_in_slurm_cluster(host)

    if result["success"]:
        tl.passed(LOG["pxe_nodes_in_cluster_ok"], result["details"])
    else:
        tl.failed(LOG["pxe_nodes_in_cluster_failed"], result["error"])

    assert result["success"], ASSERT["pxe_nodes_in_cluster_failed"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(2)
def test_slurm_nodes_idle(host):
    """TC_SL_015: All slurm compute nodes in idle state (sinfo)."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurm_nodes_idle"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking SLURM compute nodes idle state")
    result = check_slurm_nodes_idle(host)

    if result["success"]:
        tl.passed(LOG["slurm_nodes_idle_ok"], result["details"])
    else:
        tl.failed(LOG["slurm_nodes_idle_failed"], result["error"])

    assert result["success"], ASSERT["slurm_nodes_idle_failed"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(3)
def test_login_nodes_idle(host):
    """TC_SL_016: All login and login compiler nodes in idle state (scontrol)."""
    _skip_if_slurm_disabled(host)

    tc = TC["login_nodes_idle"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking login nodes idle state")
    result = check_login_nodes_idle(host)

    if result["success"]:
        tl.passed(LOG["login_nodes_idle_ok"], result["details"])
    else:
        tl.failed(LOG["login_nodes_idle_failed"], result["error"])

    assert result["success"], ASSERT["login_nodes_idle_failed"]
