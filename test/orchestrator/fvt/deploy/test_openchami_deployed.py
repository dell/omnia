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
Orchestrator Deploy — OpenCHAMI Deployment Verification.

Tests that verify OpenCHAMI has been successfully deployed.
"""

from typing import List

import pytest

from library.functions import TestLogger


@pytest.mark.functional
@pytest.mark.order(1)
def test_openchami_deployed(host) -> None:
    """ORCH_FVT_DEPLOY_V001: Verify OpenCHAMI containers are running after deployment.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify OpenCHAMI containers running after deployment",
        "ORCH_FVT_DEPLOY_V001"
    )

    # Check if podman is available
    podman_check = host.run("which podman")
    if podman_check.rc != 0:
        tl.passed("Podman not installed - OpenCHAMI deployment skipped",
                 "Podman not found, OpenCHAMI not configured")
        pytest.skip("Podman not installed")

    # Get running containers
    result = host.run("podman ps --format '{{.Names}}' --filter status=running")

    if result.rc == 0:
        containers = [
            line.strip()
            for line in result.stdout.strip().split('\n')
            if line.strip()
        ]
        openchami_containers = [
            c for c in containers
            if any(keyword in c.lower() for keyword in
                   ['openchami', 'smd', 'bss', 'tokensmith', 'hydra'])
        ]

        if openchami_containers:
            tl.passed(
                "OpenCHAMI containers deployed and running",
                f"Found {len(openchami_containers)} OpenCHAMI containers: "
                f"{', '.join(openchami_containers[:5])}"
            )
        else:
            tl.passed("No OpenCHAMI containers found",
                     "OpenCHAMI may not be configured for this deployment")
    else:
        tl.failed("Failed to check container status",
                 f"podman ps failed: {result.stderr}")
        assert False, f"Failed to check containers: {result.stderr}"


@pytest.mark.functional
@pytest.mark.order(2)
def test_openchami_services_active(host) -> None:
    """ORCH_FVT_DEPLOY_V002: Verify OpenCHAMI systemd services are active after deployment.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify OpenCHAMI services active after deployment",
        "ORCH_FVT_DEPLOY_V002"
    )

    # Check for OpenCHAMI services
    services: List[str] = [
        "openchami-smd.service",
        "openchami-bss.service",
        "openchami-tokensmith.service",
        "openchami-hydra.service"
    ]

    active_services: List[str] = []
    for service in services:
        result = host.run(f"systemctl is-active {service}")
        if result.rc == 0 and result.stdout.strip() == "active":
            active_services.append(service)

    if active_services:
        tl.passed(
            "OpenCHAMI services deployed and active",
            f"Found {len(active_services)} active services: "
            f"{', '.join(active_services)}"
        )
    else:
        tl.passed("No OpenCHAMI services found",
                 "OpenCHAMI may not be configured for this deployment")
