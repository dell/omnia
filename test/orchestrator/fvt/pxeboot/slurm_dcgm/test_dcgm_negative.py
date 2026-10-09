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

"""DCGM negative / error-handling verification after PXE boot.

Covers the 4 negative scenarios from the 2.2 DCGM baseline:
CUDA prerequisite enforcement, daemon crash recovery, socket
inaccessibility, and package install failure handling.

These tests require explicit functional marker authorization because they
create temporary side effects (SIGKILL, socket rename, RPM dry-run).
"""

import pytest

from library.functions import (
    TestLogger,
    check_dcgm_neg_cuda_prerequisite,
    check_dcgm_neg_daemon_recovery,
    check_dcgm_neg_package_install_failure,
    check_dcgm_neg_socket_inaccessible,
)
from library.vars import TEST_CASES as TC
from fvt.result import verify_pxeboot

@pytest.mark.buildstream
@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(41515)
def test_dcgm_neg_cuda_prerequisite(host):
    """Verify DCGM deployment requires CUDA driver as a prerequisite."""
    tc = TC["dcgm_neg_cuda_prerequisite"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_neg_cuda_prerequisite)


@pytest.mark.buildstream
@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(41516)
def test_dcgm_neg_daemon_recovery(host):
    """Simulate DCGM daemon crash via SIGKILL and verify systemd restarts it."""
    tc = TC["dcgm_neg_daemon_recovery"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_neg_daemon_recovery)


@pytest.mark.buildstream
@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(41517)
def test_dcgm_neg_socket_inaccessible(host):
    """Remove DCGM Unix socket and verify dcgmi returns a clear error."""
    tc = TC["dcgm_neg_socket_inaccessible"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_neg_socket_inaccessible)


@pytest.mark.buildstream
@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(41518)
def test_dcgm_neg_package_install_failure(host):
    """Verify error handling when datacenter-gpu-manager package is unavailable."""
    tc = TC["dcgm_neg_package_install_failure"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_neg_package_install_failure)
