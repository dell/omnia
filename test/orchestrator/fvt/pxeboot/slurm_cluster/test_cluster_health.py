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

"""Read-only Slurm membership, services, scheduler, and SSH checks."""

import pytest
from library.functions import (
    TestLogger,
    check_slurm_configless_mode,
    check_slurm_configuration_consistency,
    check_slurm_cross_node_ssh,
    check_slurm_membership,
    check_slurm_scheduler,
    check_slurm_services,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41101)
def test_slurm_membership(host):
    """Verify mapped membership, healthy state, and basic hardware fields."""
    tc = TC["slurm_membership"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_membership)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41102)
def test_slurm_scheduler(host):
    """Verify mapped compute nodes have healthy, available partitions."""
    tc = TC["slurm_scheduler"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_scheduler)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41103)
def test_slurm_services(host):
    """Verify role and feature-specific Slurm services."""
    tc = TC["slurm_services"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_services)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41104)
def test_slurm_cross_node_ssh(host):
    """Verify every mapped Slurm role can reach every peer over root SSH."""
    tc = TC["slurm_cross_ssh"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_cross_node_ssh)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41105)
def test_slurm_configless_mode(host):
    """Verify configless controller access and expected cluster identity."""
    tc = TC["slurm_configless"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_configless_mode)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41106)
def test_slurm_configuration_consistency(host):
    """Compare authoritative Slurm files with every configless client cache."""
    tc = TC["slurm_config_consistency"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_configuration_consistency)
