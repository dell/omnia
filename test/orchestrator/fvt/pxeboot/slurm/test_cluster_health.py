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
    check_slurm_configless_mode,
    check_slurm_configuration_consistency,
    check_slurm_cross_node_ssh,
    check_slurm_membership,
    check_slurm_pam_policy,
    check_slurm_scheduler,
    check_slurm_services,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.slurm,
    pytest.mark.non_disruptive,
]


@pytest.mark.order(223)
def test_slurm_membership(host):
    """Verify mapped membership, healthy state, and basic hardware fields."""
    verify_pxeboot(host, "slurm_membership", check_slurm_membership)


@pytest.mark.order(224)
def test_slurm_scheduler(host):
    """Verify mapped compute nodes have healthy, available partitions."""
    verify_pxeboot(host, "slurm_scheduler", check_slurm_scheduler)


@pytest.mark.order(225)
def test_slurm_services(host):
    """Verify role and feature-specific Slurm services."""
    verify_pxeboot(host, "slurm_services", check_slurm_services)


@pytest.mark.openldap
@pytest.mark.order(226)
def test_slurm_pam_policy(host):
    """Verify SSHD, the PAM module, and pam_slurm_adopt account policy."""
    verify_pxeboot(host, "slurm_pam", check_slurm_pam_policy)


@pytest.mark.order(227)
def test_slurm_cross_node_ssh(host):
    """Verify every mapped Slurm role can reach every peer over root SSH."""
    verify_pxeboot(host, "slurm_cross_ssh", check_slurm_cross_node_ssh)


@pytest.mark.order(228)
def test_slurm_configless_mode(host):
    """Verify configless controller access and expected cluster identity."""
    verify_pxeboot(host, "slurm_configless", check_slurm_configless_mode)


@pytest.mark.order(229)
def test_slurm_configuration_consistency(host):
    """Compare authoritative Slurm files with every configless client cache."""
    verify_pxeboot(
        host, "slurm_config_consistency", check_slurm_configuration_consistency
    )
