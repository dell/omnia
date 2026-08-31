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
Orchestrator Validate — Slurm Service Status.

TC_SL_001: Verify Slurm is enabled in catalog
TC_SL_003: Verify Slurm controller daemon (slurmctld) is running
TC_SL_004: Verify Slurm compute daemon (slurmd) is running
TC_SL_005: Verify Slurm database daemon (slurmdbd) is running
TC_SL_006: Verify Munge authentication service is running
TC_SL_007: Verify all Slurm services are running
TC_SL_008: Verify Slurm directories exist on NFS
TC_SL_009: Verify Slurm configuration files exist
TC_SL_012: Verify Slurm controller is responding
"""

import pytest

from library.functions import TestLogger
from library.functions.slurm_func import (
    check_slurm_enabled,
    check_slurm_service_running,
    check_slurm_services_running,
    check_slurm_directories_exist,
    check_slurm_config_files_exist,
    check_munge_service_running,
    check_slurmctld_responding,
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
@pytest.mark.sanity
@pytest.mark.order(1)
def test_slurm_enabled(host):
    """TC_SL_001: Verify Slurm is enabled in catalog."""
    tc = TC["slurm_enabled"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking catalog for Slurm functional groups")
    result = check_slurm_enabled(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["slurm_enabled_ok"], result["details"])
    else:
        tl.failed(LOG["slurm_disabled"], result["details"])

    assert result["success"], ASSERT["slurm_enabled_failed"]


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(2)
def test_slurmctld_running(host):
    """TC_SL_003: Verify Slurm controller daemon (slurmctld) is running."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurmctld_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking slurmctld service status")
    result = check_slurm_service_running(host)

    if result["success"]:
        tl.passed(LOG["slurm_service_ok"].format(service="slurmctld"), result["details"])
    else:
        tl.failed(LOG["slurm_service_failed"].format(service="slurmctld"), result["error"])

    assert result["success"], ASSERT["slurm_service_failed"].format(service="slurmctld")


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(3)
def test_slurmd_running(host):
    """TC_SL_004: Verify Slurm compute daemon (slurmd) is running."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurmd_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking slurmd service status")
    result = check_slurm_service_running(host)

    if result["success"]:
        tl.passed(LOG["slurm_service_ok"].format(service="slurmd"), result["details"])
    else:
        tl.failed(LOG["slurm_service_failed"].format(service="slurmd"), result["error"])

    assert result["success"], ASSERT["slurm_service_failed"].format(service="slurmd")


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(4)
def test_slurmdbd_running(host):
    """TC_SL_005: Verify Slurm database daemon (slurmdbd) is running."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurmdbd_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking slurmdbd service status")
    result = check_slurm_service_running(host)

    if result["success"]:
        tl.passed(LOG["slurm_service_ok"].format(service="slurmdbd"), result["details"])
    else:
        tl.failed(LOG["slurm_service_failed"].format(service="slurmdbd"), result["error"])

    assert result["success"], ASSERT["slurm_service_failed"].format(service="slurmdbd")


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(5)
def test_munge_running(host):
    """TC_SL_006: Verify Munge authentication service is running."""
    _skip_if_slurm_disabled(host)

    tc = TC["munge_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking munge service status")
    result = check_munge_service_running(host)

    if result["success"]:
        tl.passed(LOG["munge_service_ok"], result["details"])
    else:
        tl.failed(LOG["munge_service_failed"], result["error"])

    assert result["success"], ASSERT["munge_service_failed"]


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(6)
def test_slurm_services_running(host):
    """TC_SL_007: Verify all Slurm services are running."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurm_services_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking all SLURM services status")
    result = check_slurm_services_running(host)

    if result["success"]:
        tl.passed(LOG["slurm_services_ok"], result["details"])
    else:
        tl.failed(LOG["slurm_services_failed"], result["error"])

    assert result["success"], ASSERT["slurm_services_failed"]


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(7)
def test_slurm_directories_exist(host):
    """TC_SL_008: Verify Slurm directories exist on NFS."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurm_directories_exist"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking SLURM directories")
    result = check_slurm_directories_exist(host)

    if result["success"]:
        tl.passed(LOG["slurm_directories_ok"], result["details"])
    else:
        tl.failed(LOG["slurm_directories_failed"], result["error"])

    assert result["success"], ASSERT["slurm_directories_failed"]


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(8)
def test_slurm_config_files_exist(host):
    """TC_SL_009: Verify Slurm configuration files exist."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurm_config_files_exist"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking SLURM configuration files")
    result = check_slurm_config_files_exist(host)

    if result["success"]:
        tl.passed(LOG["slurm_config_files_ok"], result["details"])
    else:
        tl.failed(LOG["slurm_config_files_failed"], result["error"])

    assert result["success"], ASSERT["slurm_config_files_failed"]


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(9)
def test_slurmctld_responding(host):
    """TC_SL_012: Verify Slurm controller is responding."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurmctld_responding"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking slurmctld responsiveness")
    result = check_slurmctld_responding(host)

    if result["success"]:
        tl.passed(LOG["slurmctld_responding_ok"], result["details"])
    else:
        tl.failed(LOG["slurmctld_responding_failed"], result["error"])

    assert result["success"], ASSERT["slurmctld_responding_failed"]
