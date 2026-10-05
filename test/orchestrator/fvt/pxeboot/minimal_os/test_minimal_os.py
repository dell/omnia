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

"""Minimal OS validation tests for OS-only provisioned nodes.

Verifies that nodes provisioned with an os_x86_64 or os_aarch64
functional group have the correct base packages, monitoring agent,
required services, and do NOT contain workload-specific software
(Slurm, Kubernetes, container runtimes, GPU drivers, MPI stacks).
"""

import pytest

from fvt.result import verify_pxeboot
from library.functions import (
    check_minimal_os_base_packages,
    check_minimal_os_excluded_packages,
    check_minimal_os_excluded_services,
    check_minimal_os_kernel_version,
    check_minimal_os_ldms_packages,
    check_minimal_os_network_identity,
    check_minimal_os_package_manager,
    check_minimal_os_required_services,
)

pytestmark = [pytest.mark.sanity, pytest.mark.minimal_os]


@pytest.mark.order(600)
def test_minimal_os_base_packages(host):
    """Verify base OS packages are installed on all OS-only nodes."""
    verify_pxeboot(
        host, "minimal_os_base_packages", check_minimal_os_base_packages
    )


@pytest.mark.order(601)
def test_minimal_os_ldms_packages(host):
    """Verify LDMS monitoring packages and binary on OS-only nodes."""
    verify_pxeboot(
        host, "minimal_os_ldms_packages", check_minimal_os_ldms_packages
    )


@pytest.mark.order(602)
def test_minimal_os_required_services(host):
    """Verify required services are active on all OS-only nodes."""
    verify_pxeboot(
        host, "minimal_os_required_services", check_minimal_os_required_services
    )


@pytest.mark.order(604)
def test_minimal_os_excluded_packages(host):
    """Verify workload-specific packages are NOT installed on OS-only nodes."""
    verify_pxeboot(
        host, "minimal_os_excluded_packages", check_minimal_os_excluded_packages
    )


@pytest.mark.order(605)
def test_minimal_os_excluded_services(host):
    """Verify workload-specific services are NOT active on OS-only nodes."""
    verify_pxeboot(
        host, "minimal_os_excluded_services", check_minimal_os_excluded_services
    )


@pytest.mark.order(606)
def test_minimal_os_package_manager(host):
    """Verify package manager is functional on OS-only nodes."""
    verify_pxeboot(
        host, "minimal_os_package_manager", check_minimal_os_package_manager
    )


@pytest.mark.order(607)
def test_minimal_os_kernel_version(host):
    """Verify kernel version is consistent across OS-only nodes per FG."""
    verify_pxeboot(
        host, "minimal_os_kernel_version", check_minimal_os_kernel_version
    )


@pytest.mark.order(608)
def test_minimal_os_network_identity(host):
    """Verify admin IP is configured on all OS-only nodes."""
    verify_pxeboot(
        host, "minimal_os_network_identity", check_minimal_os_network_identity
    )
