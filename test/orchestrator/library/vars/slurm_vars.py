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
Orchestrator — Slurm-Specific Variables

Slurm-specific constants for test automation.
"""

from typing import List

# =============================================================================
# Slurm Services
# =============================================================================
SLURM_SERVICES: List[str] = [
    "slurmctld",  # Slurm controller daemon
    "slurmd",     # Slurm compute daemon
    "slurmdbd",   # Slurm database daemon
    "munge",      # Munge authentication service
]

# =============================================================================
# Slurm Directories (on NFS)
# =============================================================================
SLURM_DIRECTORIES: List[str] = [
    "/opt/omnia/slurm",           # Main Slurm directory
    "/opt/omnia/slurm/spool",      # Slurm spool directory
    "/opt/omnia/slurm/log",        # Slurm log directory
    "/opt/omnia/slurm/state",     # Slurm state directory
    "/opt/omnia/slurm/config",    # Slurm config directory
]

# =============================================================================
# Slurm Configuration Files
# =============================================================================
SLURM_CONFIG_FILES: List[str] = [
    "/opt/omnia/slurm/config/slurm.conf",     # Main Slurm configuration
    "/opt/omnia/slurm/config/cgroup.conf",   # Cgroup configuration
    "/opt/omnia/slurm/config/slurmdbd.conf", # Database configuration
]

# =============================================================================
# Slurm Playbook Paths
# =============================================================================
SLURM_PROVISION_PLAYBOOK = "provision/provision_slurm.yml"
SLURM_PROVISION_WORKDIR = "src/orchestrator/playbooks"

# =============================================================================
# Slurm Test Case IDs
# =============================================================================
TEST_CASES: dict = {
    "slurm_enabled": {
        "id": "ORCH_FVT_SLURM_V001",
        "title": "Verify Slurm is enabled in catalog",
    },
    "slurm_provision": {
        "id": "ORCH_FVT_PROVISION_V006",
        "title": "Deploy Slurm cluster provision",
    },
    "slurmctld_running": {
        "id": "ORCH_FVT_SLURM_V002",
        "title": "Verify Slurm controller daemon is running",
    },
    "slurmd_running": {
        "id": "ORCH_FVT_SLURM_V003",
        "title": "Verify Slurm compute daemon is running",
    },
    "slurmdbd_running": {
        "id": "ORCH_FVT_SLURM_V004",
        "title": "Verify Slurm database daemon is running",
    },
    "munge_running": {
        "id": "ORCH_FVT_SLURM_V005",
        "title": "Verify Munge authentication service is running",
    },
    "slurm_services_running": {
        "id": "ORCH_FVT_SLURM_V006",
        "title": "Verify all Slurm services are running",
    },
    "slurm_directories_exist": {
        "id": "ORCH_FVT_SLURM_V007",
        "title": "Verify Slurm directories exist on NFS",
    },
    "slurm_config_files_exist": {
        "id": "ORCH_FVT_SLURM_V008",
        "title": "Verify Slurm configuration files exist",
    },
    "slurm_nodes_registered": {
        "id": "ORCH_FVT_SLURM_V009",
        "title": "Verify Slurm nodes are registered in cluster",
    },
    "slurm_partitions_exist": {
        "id": "ORCH_FVT_SLURM_V010",
        "title": "Verify Slurm partitions are configured",
    },
    "slurmctld_responding": {
        "id": "ORCH_FVT_SLURM_V011",
        "title": "Verify Slurm controller is responding",
    },
    "slurm_job_submission": {
        "id": "ORCH_FVT_SLURM_V012",
        "title": "Verify basic Slurm job submission works",
    },
    "all_pxe_nodes_in_slurm_cluster": {
        "id": "ORCH_FVT_SLURM_V013",
        "title": "All nodes from PXE mapping are joined to Slurm cluster",
    },
    "slurm_nodes_idle": {
        "id": "ORCH_FVT_SLURM_V014",
        "title": "All slurm compute nodes in idle state (sinfo)",
    },
    "login_nodes_idle": {
        "id": "ORCH_FVT_SLURM_V015",
        "title": "All login and login compiler nodes in idle state (scontrol)",
    },
    "ssh_control_to_compute": {
        "id": "ORCH_FVT_SLURM_V016",
        "title": "Passwordless SSH from control to compute nodes",
    },
    "ssh_control_to_login": {
        "id": "ORCH_FVT_SLURM_V017",
        "title": "Passwordless SSH from control to login nodes",
    },
    "ssh_control_to_login_compiler": {
        "id": "ORCH_FVT_SLURM_V018",
        "title": "Passwordless SSH from control to login compiler nodes",
    },
    "ssh_compute_to_control": {
        "id": "ORCH_FVT_SLURM_V019",
        "title": "Passwordless SSH from compute to control nodes",
    },
    "ssh_compute_to_login": {
        "id": "ORCH_FVT_SLURM_V020",
        "title": "Passwordless SSH from compute to login nodes",
    },
    "ssh_compute_to_login_compiler": {
        "id": "ORCH_FVT_SLURM_V021",
        "title": "Passwordless SSH from compute to login compiler nodes",
    },
    "ssh_login_to_control": {
        "id": "ORCH_FVT_SLURM_V022",
        "title": "Passwordless SSH from login to control nodes",
    },
    "ssh_login_to_compute": {
        "id": "ORCH_FVT_SLURM_V023",
        "title": "Passwordless SSH from login to compute nodes",
    },
    "ssh_login_to_login_compiler": {
        "id": "ORCH_FVT_SLURM_V024",
        "title": "Passwordless SSH from login to login compiler nodes",
    },
    "ssh_login_compiler_to_control": {
        "id": "ORCH_FVT_SLURM_V025",
        "title": "Passwordless SSH from login compiler to control nodes",
    },
    "ssh_login_compiler_to_compute": {
        "id": "ORCH_FVT_SLURM_V026",
        "title": "Passwordless SSH from login compiler to compute nodes",
    },
    "ssh_login_compiler_to_login": {
        "id": "ORCH_FVT_SLURM_V027",
        "title": "Passwordless SSH from login compiler to login nodes",
    },
    # Enhanced test cases from automation-v2.2.0.0
    "slurmctld_on_control_nodes": {
        "id": "ORCH_FVT_SLURM_V028",
        "title": "Verify slurmctld active on all control nodes",
    },
    "slurmd_on_compute_nodes": {
        "id": "ORCH_FVT_SLURM_V029",
        "title": "Verify slurmd active on all compute nodes",
    },
    "munge_on_required_nodes": {
        "id": "ORCH_FVT_SLURM_V030",
        "title": "Verify munge active on all required nodes",
    },
    "srun_execution": {
        "id": "ORCH_FVT_SLURM_V031",
        "title": "Verify srun job execution",
    },
    "sbatch_job_submission": {
        "id": "ORCH_FVT_SLURM_V032",
        "title": "Verify sbatch job submission and execution",
    },
    "job_queueing": {
        "id": "ORCH_FVT_SLURM_V033",
        "title": "Verify job queuing mechanism",
    },
    "drain_undrain_nodes": {
        "id": "ORCH_FVT_SLURM_V034",
        "title": "Verify drain and undrain functionality",
    },
    "ldap_user_login": {
        "id": "ORCH_FVT_SLURM_V035",
        "title": "Verify LDAP user login to login nodes",
    },
    "ldap_job_submission": {
        "id": "ORCH_FVT_SLURM_V036",
        "title": "Verify LDAP user job submission",
    },
    "gpu_available": {
        "id": "ORCH_FVT_SLURM_V037",
        "title": "Verify GPU resources available in SLURM",
    },
    "gpu_job_execution": {
        "id": "ORCH_FVT_SLURM_V038",
        "title": "Verify GPU job execution",
    },
    "infiniband_available": {
        "id": "ORCH_FVT_SLURM_V039",
        "title": "Verify InfiniBand available on compute nodes",
    },
    "mpi_available": {
        "id": "ORCH_FVT_SLURM_V040",
        "title": "Verify MPI available on login compiler nodes",
    },
    "mpi_job_execution": {
        "id": "ORCH_FVT_SLURM_V041",
        "title": "Verify MPI job execution",
    },
    # Custom SLURM configuration tests
    "custom_slurm_conf_structure": {
        "id": "ORCH_FVT_SLURM_V042",
        "title": "Validate custom slurm_conf module structure",
    },
    "custom_partition_config": {
        "id": "ORCH_FVT_SLURM_V043",
        "title": "Validate custom partition configuration in slurm.conf",
    },
    "custom_gres_config": {
        "id": "ORCH_FVT_SLURM_V044",
        "title": "Validate custom GRES (GPU) configuration in slurm.conf",
    },
    "custom_node_config": {
        "id": "ORCH_FVT_SLURM_V045",
        "title": "Validate custom node configuration in slurm.conf",
    },
    "extra_confs_handling": {
        "id": "ORCH_FVT_SLURM_V046",
        "title": "Validate extra_confs handling in slurm_config.yml",
    },
    "slurm_conf_merge": {
        "id": "ORCH_FVT_SLURM_V047",
        "title": "Validate slurm_conf merge functionality",
    },
    "custom_scheduling_params": {
        "id": "ORCH_FVT_SLURM_V048",
        "title": "Validate custom scheduling parameters in slurm.conf",
    },
    "slurm_conf_syntax_valid": {
        "id": "ORCH_FVT_SLURM_V049",
        "title": "Validate slurm.conf syntax is valid",
    },
    "custom_conf_files_exist": {
        "id": "ORCH_FVT_SLURM_V050",
        "title": "Validate custom conf files exist if configured",
    },
    "slurm_config_integrity": {
        "id": "ORCH_FVT_SLURM_V051",
        "title": "Validate deployed slurm.conf matches input configuration",
    },
}
