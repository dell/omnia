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

"""Public helper surface used by Orchestrator verification modules."""

from omnia_auto import TestLogger
from omnia_auto import run_playbook as _run_playbook

from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR
from .apptainer_accelerator_pxeboot_func import (
    check_apptainer_cuda_workload,
    check_apptainer_gpu_access,
    check_apptainer_gpu_count,
    check_apptainer_gpu_memory,
    check_apptainer_infiniband,
)
from .apptainer_jobs_pxeboot_func import (
    check_apptainer_concurrent_jobs,
    check_apptainer_failure_cleanup,
    check_apptainer_invalid_sif,
    check_apptainer_job_array,
    check_apptainer_ldap_job,
    check_apptainer_multi_node_job,
    check_apptainer_nfs_visibility,
    check_apptainer_restricted_sif,
    check_apptainer_single_node_job,
    check_apptainer_slurm_environment,
)
from .apptainer_recovery_pxeboot_func import (
    check_apptainer_reboot_artifacts,
    check_apptainer_reboot_job,
    check_apptainer_reboot_storage,
)
from .apptainer_runtime_pxeboot_func import (
    check_apptainer_download,
    check_apptainer_download_idempotency,
    check_apptainer_download_memory,
    check_apptainer_image_inventory,
    check_apptainer_ldap_readability,
    check_apptainer_missing_image_contract,
    check_apptainer_non_root_execution,
    check_apptainer_pulp_policy,
    check_apptainer_runtime,
    check_apptainer_shared_artifacts,
    check_apptainer_shared_storage,
    check_apptainer_sif_format,
    check_apptainer_sif_integrity,
    check_apptainer_sif_permissions,
)
from .boot_service_provision_func import check_boot_configurations, check_boot_nodes
from .cleanup_func import (
    check_cleanup_artifacts,
    check_cleanup_credentials,
    check_cleanup_kubernetes,
    check_cleanup_openchami,
    check_cleanup_openldap,
    check_cleanup_slurm,
    cleanup_extra_vars,
    cleanup_selection_fields,
)
from .kubernetes_etcd_pxeboot_func import (
    check_kubernetes_etcd_health,
    check_kubernetes_etcd_topology,
)
from .kubernetes_pxeboot_func import (
    check_kubernetes_control_plane,
    check_kubernetes_local_etcd,
    check_kubernetes_node_services,
    check_kubernetes_nodes,
    check_kubernetes_storage,
    check_kubernetes_system_pods,
    check_kubernetes_virtual_ip,
)
from .kubernetes_recovery_pxeboot_func import (
    check_kubernetes_control_plane_recovery,
    check_kubernetes_local_etcd_recovery,
)
from .kubernetes_runtime_pxeboot_func import (
    check_kubernetes_local_etcd_integrity,
    check_kubernetes_version_compatibility,
)
from .kubernetes_storage_pxeboot_func import (
    check_kubernetes_csi_dynamic_provisioning,
    check_kubernetes_default_storage_class,
    check_kubernetes_nfs_dynamic_provisioning,
    check_kubernetes_snapshot_controller,
    check_kubernetes_workload_scheduling,
)
from .metadata_service_provision_func import (
    check_metadata_groups,
    check_metadata_instances,
)
from .network_inventory_func import check_network_inventory
from .nft_func import (
    check_clean_baseline,
    check_cleanup_idempotency,
    check_credential_file_permissions,
    check_lifecycle_fresh_install,
    check_lifecycle_performance,
    check_log_file_permissions,
    check_precheck_idempotency,
    check_prepare_idempotency,
    check_ssh_private_key_permissions,
    check_vault_encryption,
    persistent_changed_count,
    resolve_nft_thresholds,
)
from .postgres_prepare_func import check_prepare_postgresql_readiness
from .precheck_func import (
    check_precheck_admin_ipv4,
    check_precheck_dependencies,
    check_precheck_hostname_domain,
    check_precheck_inputs,
    check_precheck_nfs_servers,
    check_precheck_repositories,
    check_precheck_s3_artifacts,
)
from .provision_status_func import check_provision_reports
from .pxeboot_func import (
    check_node_cloud_init,
    check_node_hostname_ssh,
    check_node_ping,
    check_node_ssh,
)
from .slurm_auth_pxeboot_func import (
    check_slurm_compiler_ldap_authentication,
    check_slurm_compiler_ldap_invalid_password,
    check_slurm_compiler_ldap_jobs,
    check_slurm_compiler_pam_job_access,
    check_slurm_control_ldap_authentication,
    check_slurm_control_ldap_invalid_password,
    check_slurm_control_ldap_jobs,
    check_slurm_control_pam_job_access,
    check_slurm_invalid_ldap_identity,
    check_slurm_login_ldap_authentication,
    check_slurm_login_ldap_invalid_password,
    check_slurm_login_ldap_jobs,
    check_slurm_login_pam_job_access,
    check_slurm_pam_no_job_access,
)
from .slurm_configuration_pxeboot_func import (
    check_slurm_configless_mode,
    check_slurm_configuration_consistency,
    check_slurm_custom_configuration,
    check_slurm_reconfigure,
)
from .slurm_discovery_pxeboot_func import check_slurm_hardware_discovery
from .slurm_fabric_pxeboot_func import (
    check_slurm_gpu_inventory,
    check_slurm_infiniband_configuration,
    check_slurm_infiniband_connectivity,
    check_slurm_ucx_transport,
)
from .slurm_jobs_pxeboot_func import (
    check_slurm_compiler_node_jobs,
    check_slurm_concurrent_jobs,
    check_slurm_control_node_jobs,
    check_slurm_drain_queue_recovery,
    check_slurm_gpu_job,
    check_slurm_gpu_memory_stress,
    check_slurm_insufficient_resources,
    check_slurm_job_queueing,
    check_slurm_login_node_jobs,
    check_slurm_openmpi_job,
)
from .slurm_pxeboot_func import (
    check_slurm_cross_node_ssh,
    check_slurm_membership,
    check_slurm_openmpi_installation,
    check_slurm_pam_policy,
    check_slurm_scheduler,
    check_slurm_services,
)
from .slurm_recovery_pxeboot_func import check_slurm_cluster_recovery
from .smd_provision_func import check_smd_groups, check_smd_identity


def run_playbook(tag: str | None = None, **kwargs):
    """Run the canonical Orchestrator playbook for the requested lifecycle tag."""
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag,
        **kwargs,
    )


__all__ = [
    "TestLogger",
    "check_apptainer_concurrent_jobs",
    "check_apptainer_cuda_workload",
    "check_apptainer_download",
    "check_apptainer_download_idempotency",
    "check_apptainer_download_memory",
    "check_apptainer_failure_cleanup",
    "check_apptainer_gpu_access",
    "check_apptainer_gpu_count",
    "check_apptainer_gpu_memory",
    "check_apptainer_image_inventory",
    "check_apptainer_infiniband",
    "check_apptainer_invalid_sif",
    "check_apptainer_job_array",
    "check_apptainer_ldap_job",
    "check_apptainer_ldap_readability",
    "check_apptainer_missing_image_contract",
    "check_apptainer_multi_node_job",
    "check_apptainer_nfs_visibility",
    "check_apptainer_non_root_execution",
    "check_apptainer_pulp_policy",
    "check_apptainer_reboot_artifacts",
    "check_apptainer_reboot_job",
    "check_apptainer_reboot_storage",
    "check_apptainer_restricted_sif",
    "check_apptainer_runtime",
    "check_apptainer_shared_artifacts",
    "check_apptainer_shared_storage",
    "check_apptainer_sif_format",
    "check_apptainer_sif_integrity",
    "check_apptainer_sif_permissions",
    "check_apptainer_single_node_job",
    "check_apptainer_slurm_environment",
    "check_boot_configurations",
    "check_boot_nodes",
    "check_clean_baseline",
    "check_cleanup_artifacts",
    "check_cleanup_credentials",
    "check_cleanup_idempotency",
    "check_cleanup_kubernetes",
    "check_cleanup_openchami",
    "check_cleanup_openldap",
    "check_cleanup_slurm",
    "check_credential_file_permissions",
    "check_kubernetes_control_plane",
    "check_kubernetes_control_plane_recovery",
    "check_kubernetes_csi_dynamic_provisioning",
    "check_kubernetes_default_storage_class",
    "check_kubernetes_etcd_health",
    "check_kubernetes_etcd_topology",
    "check_kubernetes_local_etcd",
    "check_kubernetes_local_etcd_integrity",
    "check_kubernetes_local_etcd_recovery",
    "check_kubernetes_nfs_dynamic_provisioning",
    "check_kubernetes_node_services",
    "check_kubernetes_nodes",
    "check_kubernetes_snapshot_controller",
    "check_kubernetes_storage",
    "check_kubernetes_system_pods",
    "check_kubernetes_version_compatibility",
    "check_kubernetes_virtual_ip",
    "check_kubernetes_workload_scheduling",
    "check_lifecycle_fresh_install",
    "check_lifecycle_performance",
    "check_log_file_permissions",
    "check_metadata_groups",
    "check_metadata_instances",
    "check_network_inventory",
    "check_node_cloud_init",
    "check_node_hostname_ssh",
    "check_node_ping",
    "check_node_ssh",
    "check_precheck_admin_ipv4",
    "check_precheck_dependencies",
    "check_precheck_hostname_domain",
    "check_precheck_idempotency",
    "check_precheck_inputs",
    "check_precheck_nfs_servers",
    "check_precheck_repositories",
    "check_precheck_s3_artifacts",
    "check_prepare_idempotency",
    "check_prepare_postgresql_readiness",
    "check_provision_reports",
    "check_slurm_cluster_recovery",
    "check_slurm_compiler_ldap_authentication",
    "check_slurm_compiler_ldap_invalid_password",
    "check_slurm_compiler_ldap_jobs",
    "check_slurm_compiler_node_jobs",
    "check_slurm_compiler_pam_job_access",
    "check_slurm_concurrent_jobs",
    "check_slurm_configless_mode",
    "check_slurm_configuration_consistency",
    "check_slurm_control_ldap_authentication",
    "check_slurm_control_ldap_invalid_password",
    "check_slurm_control_ldap_jobs",
    "check_slurm_control_node_jobs",
    "check_slurm_control_pam_job_access",
    "check_slurm_cross_node_ssh",
    "check_slurm_custom_configuration",
    "check_slurm_drain_queue_recovery",
    "check_slurm_gpu_inventory",
    "check_slurm_gpu_job",
    "check_slurm_gpu_memory_stress",
    "check_slurm_hardware_discovery",
    "check_slurm_infiniband_configuration",
    "check_slurm_infiniband_connectivity",
    "check_slurm_insufficient_resources",
    "check_slurm_invalid_ldap_identity",
    "check_slurm_job_queueing",
    "check_slurm_login_ldap_authentication",
    "check_slurm_login_ldap_invalid_password",
    "check_slurm_login_ldap_jobs",
    "check_slurm_login_node_jobs",
    "check_slurm_login_pam_job_access",
    "check_slurm_membership",
    "check_slurm_openmpi_installation",
    "check_slurm_openmpi_job",
    "check_slurm_pam_no_job_access",
    "check_slurm_pam_policy",
    "check_slurm_reconfigure",
    "check_slurm_scheduler",
    "check_slurm_services",
    "check_slurm_ucx_transport",
    "check_smd_groups",
    "check_smd_identity",
    "check_ssh_private_key_permissions",
    "check_vault_encryption",
    "cleanup_extra_vars",
    "cleanup_selection_fields",
    "persistent_changed_count",
    "resolve_nft_thresholds",
    "run_playbook",
]
