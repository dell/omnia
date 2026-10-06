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
    check_dcgm_neg_cuda_prerequisite,
    check_dcgm_neg_daemon_recovery,
    check_dcgm_neg_package_install_failure,
    check_dcgm_neg_socket_inaccessible,
)
from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.slurm,
    pytest.mark.functional,
]


@pytest.mark.order(320)
def test_dcgm_neg_cuda_prerequisite(host):
    """Verify DCGM deployment requires CUDA driver as a prerequisite."""
    verify_pxeboot(
        host, "dcgm_neg_cuda_prerequisite", check_dcgm_neg_cuda_prerequisite,
    )


@pytest.mark.order(321)
def test_dcgm_neg_daemon_recovery(host):
    """Simulate DCGM daemon crash via SIGKILL and verify systemd restarts it."""
    verify_pxeboot(
        host, "dcgm_neg_daemon_recovery", check_dcgm_neg_daemon_recovery,
    )


@pytest.mark.order(322)
def test_dcgm_neg_socket_inaccessible(host):
    """Remove DCGM Unix socket and verify dcgmi returns a clear error."""
    verify_pxeboot(
        host, "dcgm_neg_socket_inaccessible", check_dcgm_neg_socket_inaccessible,
    )


@pytest.mark.order(323)
def test_dcgm_neg_package_install_failure(host):
    """Verify error handling when datacenter-gpu-manager package is unavailable."""
    verify_pxeboot(
        host,
        "dcgm_neg_package_install_failure",
        check_dcgm_neg_package_install_failure,
    )
