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
Orchestrator — Slurm Test Messages

Message templates for SLURM testing based on automation-v2.2.0.0 branch.
"""

from typing import Dict

# =============================================================================
# SLURM TEST LOG MESSAGES
# =============================================================================
TEST_LOG_MSGS: Dict[str, str] = {
    # Basic checks
    "slurm_enabled_ok": "Slurm is enabled in catalog",
    "slurm_enabled_failed": "Slurm is not enabled in catalog",

    # Service checks
    "slurmctld_check_ok": "slurmctld service is active on all control nodes",
    "slurmctld_check_failed": "slurmctld service failed on nodes: {nodes}",
    "slurmd_check_ok": "slurmd service is active on all compute nodes",
    "slurmd_check_failed": "slurmd service failed on nodes: {nodes}",
    "munge_check_ok": "munge service is active on all required nodes",
    "munge_check_failed": "munge service failed on nodes: {nodes}",

    # Job execution
    "srun_check_ok": "srun job execution successful",
    "srun_check_failed": "srun job execution failed: {error}",
    "sbatch_check_ok": "sbatch job {job_id} completed successfully",
    "sbatch_check_failed": "sbatch job execution failed: {error}",

    # Advanced scenarios
    "queue_test_ok": "Job queuing mechanism working correctly",
    "queue_test_failed": "Job queuing test failed: {error}",
    "drain_undrain_ok": "Drain/undrain functionality working correctly",
    "drain_undrain_failed": "Drain/undrain test failed: {error}",

    # LDAP scenarios
    "ldap_login_ok": "LDAP user login successful",
    "ldap_login_failed": "LDAP user login failed: {error}",
    "ldap_job_ok": "LDAP job submission successful",
    "ldap_job_failed": "LDAP job submission failed: {error}",

    # Infrastructure checks
    "slurm_service_ok": "{service} service is running",
    "slurm_service_failed": "{service} service is not running",
    "munge_service_ok": "Munge authentication service is running",
    "munge_service_failed": "Munge authentication service is not running",
    "slurm_services_ok": "All SLURM services are running",
    "slurm_services_failed": "One or more SLURM services are not running",
    "slurm_directories_ok": "All SLURM directories exist",
    "slurm_directories_failed": "One or more SLURM directories are missing",
    "slurm_config_files_ok": "All SLURM configuration files exist",
    "slurm_config_files_failed": "One or more SLURM configuration files are missing",
    "slurm_nodes_registered_ok": "SLURM nodes are registered in cluster",
    "slurm_nodes_registered_failed": "SLURM nodes are not registered in cluster",
    "slurm_partitions_ok": "SLURM partitions are configured",
    "slurm_partitions_failed": "SLURM partitions are not configured",
    "slurmctld_responding_ok": "SLURM controller is responding",
    "slurmctld_responding_failed": "SLURM controller is not responding",
    "slurm_job_submission_ok": "SLURM job submission works",
    "slurm_job_submission_failed": "SLURM job submission failed",
    "pxe_nodes_in_cluster_ok": "All PXE nodes are in SLURM cluster",
    "pxe_nodes_in_cluster_failed": "Not all PXE nodes are in SLURM cluster",
    "slurm_nodes_idle_ok": "SLURM compute nodes are in idle state",
    "slurm_nodes_idle_failed": "SLURM compute nodes are not in idle state",
    "login_nodes_idle_ok": "Login nodes are in idle state",
    "login_nodes_idle_failed": "Login nodes are not in idle state",
    "ssh_ok": "Passwordless SSH from {from_node} to {to_node} works",
    "ssh_failed": "Passwordless SSH from {from_node} to {to_node} failed",

    # GPU
    "gpu_available_ok": "GPU resources available in SLURM",
    "gpu_available_failed": "GPU availability check failed: {error}",
    "gpu_job_ok": "GPU job {job_id} executed successfully",
    "gpu_job_failed": "GPU job execution failed: {error}",

    # InfiniBand
    "ib_available_ok": "InfiniBand available on compute nodes",
    "ib_available_failed": "InfiniBand check failed: {error}",

    # MPI
    "mpi_available_ok": "MPI available on login compiler nodes",
    "mpi_available_failed": "MPI availability check failed: {error}",
    "mpi_job_ok": "MPI job execution successful",
    "mpi_job_failed": "MPI job execution failed: {error}",
}

# =============================================================================
# SLURM TEST ASSERTION MESSAGES
# =============================================================================
TEST_ASSERT_MSGS: Dict[str, str] = {
    "slurm_enabled_required": "Slurm must be enabled in catalog for SLURM tests",
    "slurmctld_required": "slurmctld service must be running on control nodes",
    "slurmd_required": "slurmd service must be running on compute nodes",
    "slurmdbd_required": "slurmdbd service must be running",
    "munge_required": "munge service must be running on required nodes",
    "slurm_directories_required": "SLURM directories must exist on NFS",
    "slurm_config_files_failed": "SLURM configuration files must exist",
    "slurm_directories_failed": "SLURM directories must exist",
    "node_config_required": "Node configuration must exist in slurm.conf",
    "slurm_conf_module_required": "slurm_conf module must be available",
    "slurm_conf_merge_required": "slurm_conf merge functionality must work",
    "slurm_conf_syntax_valid": "slurm.conf must have valid syntax",
}
