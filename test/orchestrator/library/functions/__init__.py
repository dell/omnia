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
Orchestrator — Functions

Common utilities come from the omnia_auto package.
Module-specific functions remain here.
"""

# --- Common (from omnia_auto package) ---
from omnia_auto import (
    Colors,
    Symbols,
    log,
    set_debug_mode,
    TestLogger,
    get_test_output,
    get_testinfra_host,
    load_test_config,
    load_test_credentials,
    get_module_root,
    run_on_host,
    run_ssh_command,
    is_local_execution,
    TestReport,
    get_current_report,
    set_current_report,
    build_report_name,
    record_playbook_failure,
    run_playbook as _run_playbook,
)
from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

# --- Orchestrator verification ---
from .orchestrator_func import (
    check_input_config_exists,
    check_omnia_config_exists,
    check_network_spec_exists,
    check_credentials_present,
    check_repo_status_exists,
    check_container_running,
    check_openchami_containers,
    check_services_active,
    check_openchami_api_reachable,
    check_containers_removed,
    check_services_removed,
    check_firewall_ports_closed,
    check_clone_status,
)

# --- Validation ---
from .validation_func import (
    validate_test_config,
    validate_all,
    ConfigValidationError,
)

# --- Slurm verification ---
from .slurm_func import (
    # Basic SLURM functions (for old tests)
    check_slurm_enabled,
    check_slurm_service_running,
    check_slurm_services_running,
    check_slurm_directories_exist,
    check_slurm_config_files_exist,
    check_slurm_config_integrity,
    check_slurm_nodes_registered,
    check_slurm_partitions_exist,
    check_munge_service_running,
    check_slurmctld_responding,
    check_slurm_job_submission,
    check_all_pxe_nodes_in_slurm_cluster,
    check_slurm_nodes_idle,
    check_login_nodes_idle,
    check_passwordless_ssh,
    # Enhanced SLURM functions (from automation-v2.2.0.0)
    get_nodes_by_functional_group,
    get_slurm_control_nodes,
    get_slurm_compute_nodes,
    get_login_nodes,
    get_login_compiler_nodes,
    get_node_ip_from_pxe_mapping,
    check_slurmctld_on_control_nodes,
    check_slurmd_on_compute_nodes,
    check_munge_on_required_nodes,
    check_srun_execution,
    check_sbatch_job_submission,
    check_job_queueing,
    check_drain_undrain_nodes,
    check_ldap_user_login,
    check_ldap_job_submission,
    check_gpu_available,
    check_gpu_job_execution,
    check_infiniband_available,
    check_mpi_available,
    check_mpi_job_execution,
)

# --- Kubernetes verification ---
from .k8s_func import (
    # Node discovery
    get_k8s_nodes_from_pxe,
    get_k8s_control_plane_nodes,
    get_k8s_worker_nodes,
    get_k8s_all_nodes,
    get_node_ip_from_pxe,
    # K8s enabled check
    check_k8s_enabled,
    # Node status checks
    check_k8s_nodes_ready,
    check_k8s_control_plane_nodes,
    check_k8s_worker_nodes,
    # Service checks
    check_kubelet_running,
    check_containerd_running,
    # Pod and component checks
    check_k8s_system_pods,
    check_k8s_apiserver_responding,
    check_k8s_etcd_healthy,
    check_k8s_coredns_running,
    check_k8s_kube_proxy_running,
    check_k8s_static_pod,
    check_k8s_cluster_info,
    # Directory/file checks
    check_k8s_directories_exist,
    check_k8s_config_files_exist,
    check_k8s_pki_certs_exist,
    check_k8s_nfs_config_exists,
    # SSH checks
    check_k8s_ssh,
    # Workload tests
    check_k8s_pod_create,
    check_k8s_dns_resolution,
    check_k8s_service_create,
    # Node metadata
    check_k8s_node_labels,
    check_k8s_node_taints,
    # SMD/Metadata checks
    check_k8s_smd_groups,
    check_k8s_metadata_configured,
    # LDAP integration
    check_k8s_ldap_integration,
)

# --- OpenCHAMI configuration verification ---
from .openchami_config_func import (
    check_openchami_config_files,
    check_tokensmith_config,
    check_postgres_init_script,
    check_rpm_file_integrity,
)

# --- Orchestrator testing utilities ---
from .orchestrator_module_tester import (
    validate_module_structure,
    validate_orchestrator_config_module,
    validate_generate_functional_groups_module,
    validate_slurm_conf_module,
    validate_module_schema,
    check_module_dependencies,
)

from .orchestrator_role_tester import (
    check_role_structure,
    check_role_tasks,
    check_role_vars,
    check_role_defaults,
    check_role_metadata,
    test_role_dependencies,
    validate_role_syntax,
)

from .orchestrator_playbook_tester import (
    check_playbook_exists,
    check_playbook_syntax,
    get_playbook_tags,
    deploy_playbook_tag,
    verify_playbook_execution,
    check_playbook_dependencies,
    test_playbook_dry_run,
    measure_playbook_execution_time,
)


_NONINTERACTIVE_PXE_TAGS = {"execute", "pxeboot"}


def run_playbook(tag=None, **kwargs):
    """Inject Orchestrator defaults and disable its TTY-only PXE delay.

    Automated pytest execution streams Ansible through pipes, so the timed
    ``ansible.builtin.pause`` cannot safely access a controlling terminal.
    Starting the existing bounded node-registration polling immediately keeps
    the same verification contract without requiring interactive input.
    """
    tag_values = set(tag) if isinstance(tag, list) else {tag}
    extra_vars = kwargs.pop("extra_vars", None)
    if tag_values & _NONINTERACTIVE_PXE_TAGS and (
        extra_vars is None or isinstance(extra_vars, dict)
    ):
        resolved_extra_vars = dict(extra_vars or {})
        resolved_extra_vars["node_registration_pause_minutes"] = 0
        kwargs["extra_vars"] = resolved_extra_vars
    elif extra_vars is not None:
        kwargs["extra_vars"] = extra_vars
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag,
        **kwargs,
    )
