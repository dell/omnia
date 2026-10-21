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
    TestLogger,
    check_minimal_os_additional_packages,
    check_minimal_os_additional_packages_fallback,
    check_minimal_os_base_packages,
    check_minimal_os_excluded_packages,
    check_minimal_os_excluded_services,
    check_minimal_os_functional_group_schema,
    check_minimal_os_kernel_version,
    check_minimal_os_ldms_packages,
    check_minimal_os_ldms_service_state,
    check_minimal_os_network_identity,
    check_minimal_os_network_isolation,
    check_minimal_os_no_embedded_credentials,
    check_minimal_os_package_manager,
    check_minimal_os_required_services,
    check_minimal_os_ssh_key_access,
)
from library.vars import TEST_CASES as TC


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40501)
def test_minimal_os_base_packages(host):
    """Verify base OS packages are installed on all OS-only nodes."""
    tc = TC["minimal_os_base_packages"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_base_packages)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40502)
def test_minimal_os_ldms_packages(host):
    """Verify LDMS monitoring packages and binary on OS-only nodes."""
    tc = TC["minimal_os_ldms_packages"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_ldms_packages)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40503)
def test_minimal_os_required_services(host):
    """Verify required services are active on all OS-only nodes."""
    tc = TC["minimal_os_required_services"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_required_services)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40504)
def test_minimal_os_excluded_packages(host):
    """Verify workload-specific packages are NOT installed on OS-only nodes."""
    tc = TC["minimal_os_excluded_packages"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_excluded_packages)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40505)
def test_minimal_os_excluded_services(host):
    """Verify workload-specific services are NOT active on OS-only nodes."""
    tc = TC["minimal_os_excluded_services"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_excluded_services)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40506)
def test_minimal_os_package_manager(host):
    """Verify package manager is functional on OS-only nodes."""
    tc = TC["minimal_os_package_manager"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_package_manager)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40507)
def test_minimal_os_kernel_version(host):
    """Verify kernel version is consistent across OS-only nodes per FG."""
    tc = TC["minimal_os_kernel_version"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_kernel_version)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40508)
def test_minimal_os_network_identity(host):
    """Verify admin IP is configured on all OS-only nodes."""
    tc = TC["minimal_os_network_identity"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_network_identity)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40509)
def test_minimal_os_functional_group_schema(host):
    """Verify functional-group definitions are valid on OS-only nodes."""
    tc = TC["minimal_os_functional_group_schema"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_functional_group_schema)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40510)
def test_minimal_os_additional_packages(host):
    """Verify configured extra packages are installed on OS-only nodes."""
    tc = TC["minimal_os_additional_packages"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_additional_packages)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40511)
def test_minimal_os_additional_packages_fallback(host):
    """Verify absent additional_packages config is handled on OS-only nodes."""
    tc = TC["minimal_os_additional_packages_fallback"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_additional_packages_fallback)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40512)
def test_minimal_os_ldms_service_state(host):
    """Verify LDMS service is installed but inactive at handoff."""
    tc = TC["minimal_os_ldms_service_state"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_ldms_service_state)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40513)
def test_minimal_os_ssh_key_access(host):
    """Verify SSH key authentication is proven on OS-only nodes."""
    tc = TC["minimal_os_ssh_key_access"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_ssh_key_access)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40514)
def test_minimal_os_network_isolation(host):
    """Verify default route is on management network on OS-only nodes."""
    tc = TC["minimal_os_network_isolation"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_network_isolation)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.minimal_os
@pytest.mark.order(40515)
def test_minimal_os_no_embedded_credentials(host):
    """Verify no plaintext secrets are present in the OS image."""
    tc = TC["minimal_os_no_embedded_credentials"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_minimal_os_no_embedded_credentials)
