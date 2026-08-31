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
_BORDER = "\u2550" * 74

TEST_ASSERT_MSGS: Dict[str, str] = {
    "slurm_enabled_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURM ENABLEMENT FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Slurm is not enabled in the catalog configuration.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check catalog configuration for slurm functional groups\n"
        "\u2551   2. Ensure slurm is enabled in orchestrator_config.yml\n"
        "\u2551   3. Verify slurm functional groups are defined\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "slurm_service_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURM SERVICE FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {service} service is not running.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check {service} service status\n"
        "\u2551   2. Restart service: systemctl restart {service}\n"
        "\u2551   3. Check service logs: journalctl -u {service}\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "munge_service_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 MUNGE SERVICE FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Munge authentication service is not running.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check munge service status\n"
        "\u2551   2. Restart service: systemctl restart munge\n"
        "\u2551   3. Verify munge key is consistent across nodes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "slurm_services_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURM SERVICES FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 One or more SLURM services are not running.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check status of all SLURM services\n"
        "\u2551   2. Restart failed services\n"
        "\u2551   3. Check service logs for errors\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "slurm_directories_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURM DIRECTORIES FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 One or more SLURM directories are missing.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Verify NFS mount is accessible\n"
        "\u2551   2. Create missing directories\n"
        "\u2551   3. Check directory permissions\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "slurm_config_files_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURM CONFIG FILES FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 One or more SLURM configuration files are missing.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Verify SLURM configuration directory exists\n"
        "\u2551   2. Check SLURM playbook execution\n"
        "\u2551   3. Verify configuration templates\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "slurm_nodes_registered_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURM NODE REGISTRATION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 SLURM nodes are not registered in cluster.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check node registration status\n"
        "\u2551   2. Verify network connectivity\n"
        "\u2551   3. Restart slurmd on compute nodes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "slurm_partitions_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURM PARTITIONS FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 SLURM partitions are not configured.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check slurm.conf partition configuration\n"
        "\u2551   2. Restart slurmctld after config changes\n"
        "\u2551   3. Verify partition definitions\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "slurmctld_responding_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURMCTLD NOT RESPONDING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 SLURM controller is not responding.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check slurmctld service status\n"
        "\u2551   2. Restart slurmctld\n"
        "\u2551   3. Check slurmctld logs\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "slurm_job_submission_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURM JOB SUBMISSION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 SLURM job submission test failed.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check SLURM cluster status\n"
        "\u2551   2. Verify user permissions\n"
        "\u2551   3. Check SLURM configuration\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "pxe_nodes_in_cluster_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 PXE NODES NOT IN CLUSTER\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Not all PXE nodes are in SLURM cluster.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check PXE mapping configuration\n"
        "\u2551   2. Verify node registration\n"
        "\u2551   3. Check network connectivity\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "slurm_nodes_idle_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURM NODES NOT IDLE\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 SLURM compute nodes are not in idle state.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check node state with sinfo\n"
        "\u2551   2. Drain running jobs if needed\n"
        "\u2551   3. Verify node configuration\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "login_nodes_idle_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 LOGIN NODES NOT IDLE\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Login nodes are not in idle state.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check login node state\n"
        "\u2551   2. Verify no running jobs\n"
        "\u2551   3. Check node configuration\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "ssh_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SSH CONNECTIVITY FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Passwordless SSH from {from_node} to {to_node} failed.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Verify SSH keys are configured\n"
        "\u2551   2. Check authorized_keys file\n"
        "\u2551   3. Test SSH connectivity manually\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "slurmctld_check_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURMCTLD SERVICE CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Failed nodes: {nodes}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check slurmctld service status on failed nodes\n"
        "\u2551   2. Restart service: systemctl restart slurmctld\n"
        "\u2551   3. Check slurm logs: journalctl -u slurmctld\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "slurmd_check_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SLURMD SERVICE CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Failed nodes: {nodes}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check slurmd service status on failed nodes\n"
        "\u2551   2. Restart service: systemctl restart slurmd\n"
        "\u2551   3. Check slurm logs: journalctl -u slurmd\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "munge_check_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 MUNGE SERVICE CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Failed nodes: {nodes}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check munge service status on failed nodes\n"
        "\u2551   2. Restart service: systemctl restart munge\n"
        "\u2551   3. Verify munge key is consistent across nodes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "srun_check_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SRUN EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check slurm cluster status: sinfo\n"
        "\u2551   2. Verify nodes are available and idle\n"
        "\u2551   3. Check slurm configuration: slurmctld responding\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "sbatch_check_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 SBATCH JOB EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check job submission logs: sacct\n"
        "\u2551   2. Verify job submission permissions\n"
        "\u2551   3. Check slurmctld and slurmd status\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "queue_test_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 JOB QUEUEING TEST FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check slurm scheduler configuration\n"
        "\u2551   2. Verify partition scheduling parameters\n"
        "\u2551   3. Check node availability and state\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "drain_undrain_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 DRAIN/UNDRAIN TEST FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check scontrol command permissions\n"
        "\u2551   2. Verify node state management\n"
        "\u2551   3. Check slurm controller logs\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "ldap_login_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 LDAP USER LOGIN FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Failed nodes: {nodes}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check LDAP service status\n"
        "\u2551   2. Verify LDAP credentials in test_config.yml\n"
        "\u2551   3. Check LDAP authentication on login nodes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "ldap_job_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 LDAP JOB SUBMISSION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Verify LDAP user has job submission permissions\n"
        "\u2551   2. Check LDAP user account status\n"
        "\u2551   3. Verify SLURM accounting integration\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "gpu_available_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 GPU AVAILABILITY CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check GPU driver installation\n"
        "\u2551   2. Verify GPU devices are detected\n"
        "\u2551   3. Check SLURM GRES configuration\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "gpu_job_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 GPU JOB EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check GPU job script\n"
        "\u2551   2. Verify CUDA availability\n"
        "\u2551   3. Check SLURM GPU scheduling\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "ib_available_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 INFINIBAND CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check InfiniBand driver installation\n"
        "\u2551   2. Verify IB devices are detected\n"
        "\u2551   3. Check IB network configuration\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "mpi_available_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 MPI AVAILABILITY CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check MPI installation\n"
        "\u2551   2. Verify MPI module availability\n"
        "\u2551   3. Check MPI environment variables\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "mpi_job_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 MPI JOB EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check MPI job script\n"
        "\u2551   2. Verify MPI runtime\n"
        "\u2551   3. Check SLURM MPI integration\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    # Custom SLURM configuration tests
    "slurm_conf_module_available": "slurm_conf module is available",
    "slurm_conf_module_not_available": "slurm_conf module is not available",
    "custom_partition_found": "Custom partition configuration found",
    "custom_partition_not_found": "No custom partition configuration",
    "gres_config_found": "GPU resources configured in slurm.conf",
    "gres_config_not_found": "No GPU resources configured",
    "node_config_found": "Node configuration found in slurm.conf",
    "node_config_not_found": "No node configuration found",
    "extra_confs_configured": "extra_confs found in slurm_config.yml",
    "extra_confs_not_configured": "No extra_confs configured",
    "scheduling_params_found": "Custom scheduling parameters found",
    "scheduling_params_not_found": "Using default scheduling parameters",
    "slurm_conf_syntax_valid": "No syntax errors in slurm.conf",
    "slurm_conf_syntax_invalid": "Syntax errors found in slurm.conf",
    "custom_conf_files_found": "Custom conf files configured",
    "custom_conf_files_not_found": "No custom conf files configured",
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
