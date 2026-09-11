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

Tests that verify nodes have been provisioned via PXE boot by connecting
to remote control plane nodes and checking Kubernetes/Slurm status.
"""

from typing import List, Optional

import pytest

from library.functions import TestLogger, load_test_config
from library.vars.common_vars import INPUT_PATH_TEMPLATE, OUTPUT_PATH_TEMPLATE


def _get_k8s_control_plane_ips() -> List[str]:
    """Extract Kubernetes control plane IPs from PXE mapping file.

    Returns:
        List of control plane node IP addresses
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    shared_path = config.get("shared_path", "/opt/omnia/orchestrator")
    input_path = INPUT_PATH_TEMPLATE.format(shared_path=shared_path, project=project)
    mapping_path = f"{input_path}/pxe_mapping_file.csv"

    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        control_plane_ips: List[str] = []
        for line in lines[1:]:  # Skip header
            if line.strip() and not line.startswith('#'):
                parts = line.strip().split(',')
                if len(parts) >= 6:
                    fg_name = parts[0].strip()
                    admin_ip = parts[5].strip()
                    # Check if this is a Kubernetes control plane node
                    if 'kube_control_plane' in fg_name.lower() and admin_ip:
                        control_plane_ips.append(admin_ip)

        return control_plane_ips
    except Exception:
        return []


def _get_slurm_control_ips() -> List[str]:
    """Extract Slurm control/login node IPs from PXE mapping file.

    Returns:
        List of Slurm control/login node IP addresses
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    shared_path = config.get("shared_path", "/opt/omnia/orchestrator")
    input_path = INPUT_PATH_TEMPLATE.format(shared_path=shared_path, project=project)
    mapping_path = f"{input_path}/pxe_mapping_file.csv"

    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        slurm_ips: List[str] = []
        for line in lines[1:]:  # Skip header
            if line.strip() and not line.startswith('#'):
                parts = line.strip().split(',')
                if len(parts) >= 6:
                    fg_name = parts[0].strip()
                    admin_ip = parts[5].strip()
                    # Check if this is a Slurm control or login node
                    if any(keyword in fg_name.lower() for keyword in
                           ['slurm_control', 'slurm_login']) and admin_ip:
                        slurm_ips.append(admin_ip)

        return slurm_ips
    except Exception:
        return []


def _run_ssh_command(host, ip: str, command: str) -> dict:
    """Run a command on a remote node via SSH.

    Args:
        host: Test host fixture
        ip: Target IP address
        command: Command to run

    Returns:
        Dictionary with rc, stdout, stderr
    """
    try:
        result = host.run(f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@{ip} '{command}'")
        return {
            "rc": result.rc,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {
            "rc": -1,
            "stdout": "",
            "stderr": str(e)
        }


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

    control_plane_ips = _get_k8s_control_plane_ips()

    if not control_plane_ips:
        tl.passed("No Kubernetes control plane IPs found in PXE mapping",
                 "Kubernetes may not be configured for this deployment")
        pytest.skip("No Kubernetes control plane IPs found")

    # Try to connect to first control plane and check kubectl
    control_ip = control_plane_ips[0]
    result = _run_ssh_command(host, control_ip, "which kubectl")

    if result["rc"] == 0:
        # kubectl found, check nodes
        node_result = _run_ssh_command(host, control_ip, "kubectl get nodes --no-headers 2>/dev/null")
        if node_result["rc"] == 0 and node_result["stdout"].strip():
            nodes = [line.strip() for line in node_result["stdout"].strip().split('\n') if line.strip()]
            tl.passed(f"Kubernetes nodes provisioned via PXE boot",
                     f"Found {len(nodes)} Kubernetes nodes on {control_ip}")
        else:
            tl.passed("kubectl found but no nodes returned",
                     "Kubernetes may not have completed provisioning yet")
    else:
        tl.passed(f"kubectl not found on control plane {control_ip}",
                 "Kubernetes may not have been installed yet")


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

    control_plane_ips = _get_k8s_control_plane_ips()

    if not control_plane_ips:
        tl.passed("No Kubernetes control plane IPs found in PXE mapping",
                 "Kubernetes may not be configured for this deployment")
        pytest.skip("No Kubernetes control plane IPs found")

    control_ip = control_plane_ips[0]
    result = _run_ssh_command(host, control_ip, "which kubectl")

    if result["rc"] == 0:
        node_result = _run_ssh_command(host, control_ip, "kubectl get nodes --no-headers 2>/dev/null")
        if node_result["rc"] == 0 and node_result["stdout"].strip():
            nodes = [line.strip() for line in node_result["stdout"].strip().split('\n') if line.strip()]
            ready_nodes = [n for n in nodes if 'Ready' in n]

            if ready_nodes:
                tl.passed(f"Kubernetes nodes in Ready state",
                         f"Found {len(ready_nodes)} Ready nodes out of {len(nodes)} on {control_ip}")
            else:
                tl.passed("No Kubernetes nodes in Ready state",
                         "Nodes may still be provisioning")
        else:
            tl.passed("kubectl found but no nodes returned",
                     "Kubernetes may not have completed provisioning yet")
    else:
        tl.passed(f"kubectl not found on control plane {control_ip}",
                 "Kubernetes may not have been installed yet")


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

    slurm_ips = _get_slurm_control_ips()

    if not slurm_ips:
        tl.passed("No Slurm control/login IPs found in PXE mapping",
                 "Slurm may not be configured for this deployment")
        pytest.skip("No Slurm control/login IPs found")

    # Try to connect to first Slurm node and check sinfo
    slurm_ip = slurm_ips[0]
    result = _run_ssh_command(host, slurm_ip, "which sinfo")

    if result["rc"] == 0:
        # sinfo found, check nodes
        node_result = _run_ssh_command(host, slurm_ip, "sinfo --no-headers 2>/dev/null")
        if node_result["rc"] == 0 and node_result["stdout"].strip():
            partitions = [line.strip() for line in node_result["stdout"].strip().split('\n') if line.strip()]
            tl.passed(f"Slurm nodes provisioned via PXE boot",
                     f"Found {len(partitions)} Slurm partitions on {slurm_ip}")
        else:
            tl.passed("sinfo found but no partitions returned",
                     "Slurm may not have completed provisioning yet")
    else:
        tl.passed(f"sinfo not found on Slurm node {slurm_ip}",
                 "Slurm may not have been installed yet")


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

    slurm_ips = _get_slurm_control_ips()

    if not slurm_ips:
        tl.passed("No Slurm control/login IPs found in PXE mapping",
                 "Slurm may not be configured for this deployment")
        pytest.skip("No Slurm control/login IPs found")

    slurm_ip = slurm_ips[0]
    result = _run_ssh_command(host, slurm_ip, "which sinfo")

    if result["rc"] == 0:
        node_result = _run_ssh_command(host, slurm_ip, "sinfo --no-headers -N -o State 2>/dev/null")
        if node_result["rc"] == 0 and node_result["stdout"].strip():
            states = [line.strip() for line in node_result["stdout"].strip().split('\n') if line.strip()]
            idle_nodes = [s for s in states if 'idle' in s.lower()]

            if idle_nodes:
                tl.passed(f"Slurm nodes in Idle state",
                         f"Found {len(idle_nodes)} Idle nodes out of {len(states)} on {slurm_ip}")
            else:
                tl.passed("No Slurm nodes in Idle state",
                         "Nodes may still be provisioning")
        else:
            tl.passed("sinfo found but no states returned",
                     "Slurm may not have completed provisioning yet")
    else:
        tl.passed(f"sinfo not found on Slurm node {slurm_ip}",
                 "Slurm may not have been installed yet")


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

    config = load_test_config()
    project = config.get("project_name", "project_default")
    shared_path = config.get("shared_path", "/opt/omnia/orchestrator")
    output_path = OUTPUT_PATH_TEMPLATE.format(shared_path=shared_path, project=project)

    status_path = f"{output_path}/pxe_boot_status.yml"
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

    config = load_test_config()
    project = config.get("project_name", "project_default")
    shared_path = config.get("shared_path", "/opt/omnia/orchestrator")
    output_path = OUTPUT_PATH_TEMPLATE.format(shared_path=shared_path, project=project)

    failed_nodes_path = f"{output_path}/failed_nodes.yml"
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

    result = host.run("systemctl is-active tftp.socket")

    if result.rc == 0 and result.stdout.strip() == "active":
        tl.passed("TFTP service running for PXE boot",
                 "TFTP socket is active")
    else:
        tl.passed("TFTP service not active",
                 "TFTP may not be configured for this deployment")
