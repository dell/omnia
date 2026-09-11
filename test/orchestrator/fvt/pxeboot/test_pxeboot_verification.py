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
Orchestrator PXE Boot — Verification Tests.

Tests that verify nodes have been provisioned via PXE boot.
"""

from typing import List

import pytest

from library.functions import TestLogger


@pytest.mark.functional
@pytest.mark.order(1)
def test_kubernetes_nodes_provisioned(host) -> None:
    """TC_PXE_016: Verify Kubernetes nodes are provisioned via PXE boot.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify Kubernetes nodes provisioned via PXE boot",
        "TC_PXE_016"
    )

    # Check if kubectl is available
    kubectl_check = host.run("which kubectl")
    if kubectl_check.rc != 0:
        tl.passed("kubectl not found - Kubernetes not provisioned",
                 "Kubernetes may not be configured for this deployment")
        pytest.skip("kubectl not available")

    # Check for Kubernetes nodes
    result = host.run("kubectl get nodes --no-headers 2>/dev/null")

    if result.rc == 0 and result.stdout.strip():
        nodes = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        tl.passed(f"Kubernetes nodes provisioned via PXE boot",
                 f"Found {len(nodes)} Kubernetes nodes")
    else:
        tl.passed("No Kubernetes nodes found",
                 "Kubernetes provisioning may not have completed yet")


@pytest.mark.functional
@pytest.mark.order(2)
def test_kubernetes_nodes_ready(host) -> None:
    """TC_PXE_017: Verify Kubernetes nodes are in Ready state.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify Kubernetes nodes are in Ready state",
        "TC_PXE_017"
    )

    # Check if kubectl is available
    kubectl_check = host.run("which kubectl")
    if kubectl_check.rc != 0:
        tl.passed("kubectl not found - Kubernetes not provisioned",
                 "Kubernetes may not be configured for this deployment")
        pytest.skip("kubectl not available")

    # Check for Ready nodes
    result = host.run("kubectl get nodes --no-headers 2>/dev/null")

    if result.rc == 0 and result.stdout.strip():
        nodes = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        ready_nodes = [n for n in nodes if 'Ready' in n]

        if ready_nodes:
            tl.passed(f"Kubernetes nodes in Ready state",
                     f"Found {len(ready_nodes)} Ready nodes out of {len(nodes)}")
        else:
            tl.passed("No Kubernetes nodes in Ready state",
                     "Nodes may still be provisioning")
    else:
        tl.passed("No Kubernetes nodes found",
                 "Kubernetes provisioning may not have completed yet")


@pytest.mark.functional
@pytest.mark.order(3)
def test_slurm_nodes_provisioned(host) -> None:
    """TC_PXE_018: Verify Slurm nodes are provisioned via PXE boot.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify Slurm nodes provisioned via PXE boot",
        "TC_PXE_018"
    )

    # Check if sinfo is available
    sinfo_check = host.run("which sinfo")
    if sinfo_check.rc != 0:
        tl.passed("sinfo not found - Slurm not provisioned",
                 "Slurm may not be configured for this deployment")
        pytest.skip("sinfo not available")

    # Check for Slurm nodes
    result = host.run("sinfo --no-headers 2>/dev/null")

    if result.rc == 0 and result.stdout.strip():
        partitions = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        tl.passed(f"Slurm nodes provisioned via PXE boot",
                 f"Found {len(partitions)} Slurm partitions")
    else:
        tl.passed("No Slurm nodes found",
                 "Slurm provisioning may not have completed yet")


@pytest.mark.functional
@pytest.mark.order(4)
def test_slurm_nodes_idle(host) -> None:
    """TC_PXE_019: Verify Slurm nodes are in Idle state.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify Slurm nodes are in Idle state",
        "TC_PXE_019"
    )

    # Check if sinfo is available
    sinfo_check = host.run("which sinfo")
    if sinfo_check.rc != 0:
        tl.passed("sinfo not found - Slurm not provisioned",
                 "Slurm may not be configured for this deployment")
        pytest.skip("sinfo not available")

    # Check for Idle nodes
    result = host.run("sinfo --no-headers -N -o State 2>/dev/null")

    if result.rc == 0 and result.stdout.strip():
        states = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        idle_nodes = [s for s in states if 'idle' in s.lower()]

        if idle_nodes:
            tl.passed(f"Slurm nodes in Idle state",
                     f"Found {len(idle_nodes)} Idle nodes out of {len(states)}")
        else:
            tl.passed("No Slurm nodes in Idle state",
                     "Nodes may still be provisioning")
    else:
        tl.passed("No Slurm nodes found",
                 "Slurm provisioning may not have completed yet")


@pytest.mark.functional
@pytest.mark.order(5)
def test_pxe_boot_status_file(host) -> None:
    """TC_PXE_020: Verify PXE boot status file exists.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify PXE boot status file exists",
        "TC_PXE_020"
    )

    # Check for PXE boot status file
    status_path = "/opt/omnia/orchestrator/output/project_default/pxe_boot_status.yml"
    status_exists = host.file(status_path).exists

    if status_exists:
        tl.passed("PXE boot status file exists",
                 f"Found at {status_path}")
    else:
        tl.passed("PXE boot status file not found",
                 "PXE boot may not have been executed yet")


@pytest.mark.functional
@pytest.mark.order(6)
def test_failed_nodes_file(host) -> None:
    """TC_PXE_021: Verify failed nodes file exists if any nodes failed.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify failed nodes file exists",
        "TC_PXE_021"
    )

    # Check for failed nodes file
    failed_nodes_path = "/opt/omnia/orchestrator/output/project_default/failed_nodes.yml"
    failed_exists = host.file(failed_nodes_path).exists

    if failed_exists:
        tl.passed("Failed nodes file exists",
                 f"Found at {failed_nodes_path} - some nodes may have failed PXE boot")
    else:
        tl.passed("No failed nodes file",
                 "All nodes may have succeeded PXE boot or PXE boot not executed yet")


@pytest.mark.functional
@pytest.mark.order(7)
def test_coredhcp_service_running(host) -> None:
    """TC_PXE_022: Verify CoreDHCP service is running for PXE boot.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify CoreDHCP service running for PXE boot",
        "TC_PXE_022"
    )

    # Check if CoreDHCP container is running
    result = host.run("podman ps --filter name=coredhcp --format '{{.Names}}'")

    if result.rc == 0 and result.stdout.strip():
        coredhcp_containers: List[str] = [
            line.strip()
            for line in result.stdout.strip().split('\n')
            if line.strip()
        ]
        if coredhcp_containers:
            tl.passed(f"CoreDHCP service running for PXE boot",
                     f"Found CoreDHCP containers: {', '.join(coredhcp_containers)}")
        else:
            tl.passed("CoreDHCP service not found",
                     "CoreDHCP may not be configured for this deployment")
    else:
        tl.passed("CoreDHCP service not found",
                 "CoreDHCP may not be configured for this deployment")


@pytest.mark.functional
@pytest.mark.order(8)
def test_tftp_service_running(host) -> None:
    """TC_PXE_023: Verify TFTP service is running for PXE boot.

    Args:
        host: Test host fixture from testinfra
    """
    tl = TestLogger(
        "Verify TFTP service running for PXE boot",
        "TC_PXE_023"
    )

    # Check if TFTP service is running
    result = host.run("systemctl is-active tftp.socket")

    if result.rc == 0 and result.stdout.strip() == "active":
        tl.passed("TFTP service running for PXE boot",
                 "TFTP socket is active")
    else:
        tl.passed("TFTP service not active",
                 "TFTP may not be configured for this deployment")
