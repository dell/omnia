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

"""Canonical registry for Orchestrator lifecycle test cases."""

PRECHECK_TEST_CASES: dict[str, dict[str, str]] = {
    "deploy_precheck": {
        "id": "ORCH_FVT_PRECHECK_E001",
        "title": "Execute Orchestrator precheck lifecycle",
    },
    "precheck_hostname_domain": {
        "id": "ORCH_FVT_PRECHECK_V001",
        "title": "Verify OIM hostname and domain identity",
        "component": "OIM hostname and domain",
    },
    "precheck_admin_ipv4": {
        "id": "ORCH_FVT_PRECHECK_V002",
        "title": "Verify OIM administrative IPv4 assignment",
        "component": "OIM administrative IPv4",
    },
    "precheck_nfs_servers": {
        "id": "ORCH_FVT_PRECHECK_V003",
        "title": "Verify configured NFS server reachability",
        "component": "NFS server reachability",
    },
    "precheck_dependencies": {
        "id": "ORCH_FVT_PRECHECK_V004",
        "title": "Verify Orchestrator dependency status files",
        "component": "Dependency status files",
    },
    "precheck_inputs": {
        "id": "ORCH_FVT_PRECHECK_V005",
        "title": "Verify required Orchestrator input files",
        "component": "Orchestrator input files",
    },
    "precheck_s3_artifacts": {
        "id": "ORCH_FVT_PRECHECK_V006",
        "title": "Verify S3 boot-artifact reachability",
        "component": "S3 boot artifacts",
    },
    "precheck_repositories": {
        "id": "ORCH_FVT_PRECHECK_V007",
        "title": "Verify published repository reachability",
        "component": "Published repositories",
    },
}

PREPARE_TEST_CASES: dict[str, dict[str, str]] = {
    "deploy_prepare": {
        "id": "ORCH_FVT_PREPARE_E001",
        "title": "Deploy Orchestrator prepare lifecycle",
    },
    "openchami_containers": {
        "id": "ORCH_FVT_PREPARE_V001",
        "title": "Verify OpenCHAMI containers are running",
    },
    "openchami_services": {
        "id": "ORCH_FVT_PREPARE_V002",
        "title": "Verify OpenCHAMI services and initialization",
    },
    "openchami_apis": {
        "id": "ORCH_FVT_PREPARE_V003",
        "title": "Verify authenticated OpenCHAMI APIs",
    },
    "openchami_storage": {
        "id": "ORCH_FVT_PREPARE_V004",
        "title": "Verify OpenCHAMI persistent volumes and TLS material",
    },
    "openchami_artifacts": {
        "id": "ORCH_FVT_PREPARE_V005",
        "title": "Verify OpenCHAMI packages and configuration artifacts",
    },
    "firewall_network": {
        "id": "ORCH_FVT_PREPARE_V006",
        "title": "Verify Orchestrator firewall and Podman network policy",
    },
    "coredhcp_network": {
        "id": "ORCH_FVT_PREPARE_V007",
        "title": "Verify CoreDHCP and CoreDNS match network_spec.yml",
    },
    "external_ldap_proxy": {
        "id": "ORCH_FVT_PREPARE_V008",
        "title": "Reconcile and verify the external LDAP proxy",
    },
    "openldap_runtime": {
        "id": "ORCH_FVT_PREPARE_V009",
        "title": "Verify OpenLDAP service and container health",
    },
    "openldap_artifacts": {
        "id": "ORCH_FVT_PREPARE_V010",
        "title": "Verify OpenLDAP configuration and TLS artifacts",
    },
    "openldap_endpoint": {
        "id": "ORCH_FVT_PREPARE_V011",
        "title": "Verify OpenLDAP listeners and local endpoint",
    },
    "external_ldap_backend": {
        "id": "ORCH_FVT_PREPARE_V012",
        "title": "Verify external LDAP backend reachability",
    },
    "postgresql_readiness": {
        "id": "ORCH_FVT_PREPARE_V013",
        "title": "Verify PostgreSQL and SMD database readiness",
    },
}

PROVISION_TEST_CASES: dict[str, dict[str, str]] = {
    "deploy_provision": {
        "id": "ORCH_FVT_PROVISION_E001",
        "title": "Deploy Orchestrator provision lifecycle",
    },
    "provision_reports": {
        "id": "ORCH_FVT_PROVISION_V001",
        "title": "Verify provisioning report and generated inventory",
        "component": "Provision report and inventory",
    },
    "smd_identity": {
        "id": "ORCH_FVT_PROVISION_V002",
        "title": "Verify SMD node and administrative interface identity",
        "component": "SMD identity",
    },
    "smd_groups": {
        "id": "ORCH_FVT_PROVISION_V003",
        "title": "Verify SMD functional-group membership",
        "component": "SMD functional-group membership",
    },
    "boot_configurations": {
        "id": "ORCH_FVT_PROVISION_V004",
        "title": "Verify Boot Service configurations",
        "component": "Boot Service configurations",
    },
    "boot_nodes": {
        "id": "ORCH_FVT_PROVISION_V005",
        "title": "Verify Boot Service node identity",
        "component": "Boot Service node identity",
    },
    "metadata_groups": {
        "id": "ORCH_FVT_PROVISION_V006",
        "title": "Verify Metadata Service functional-group data",
        "component": "Metadata Service groups",
    },
    "metadata_instances": {
        "id": "ORCH_FVT_PROVISION_V007",
        "title": "Verify Metadata Service instance identity",
        "component": "Metadata Service instances",
    },
    "network_inventory": {
        "id": "ORCH_FVT_PROVISION_V008",
        "title": "Verify CoreDHCP and CoreDNS inventory inputs",
        "component": "CoreDHCP/CoreDNS inventory",
    },
}

PXEBOOT_TEST_CASES: dict[str, dict[str, str]] = {
    "deploy_pxeboot": {
        "id": "ORCH_FVT_PXEBOOT_E001",
        "title": "Execute Orchestrator PXE boot lifecycle",
    },
    "node_ping": {
        "id": "ORCH_FVT_PXEBOOT_V001",
        "title": "Verify node ICMP reachability from the OIM",
        "component": "Node ping",
    },
    "node_ssh": {
        "id": "ORCH_FVT_PXEBOOT_V002",
        "title": "Verify passwordless node SSH from the OIM",
        "component": "OIM-to-node SSH",
    },
    "node_hostname_ssh": {
        "id": "ORCH_FVT_PXEBOOT_V003",
        "title": "Verify node hostname resolution and SSH from the OIM",
        "component": "OIM hostname resolution and SSH",
    },
    "node_cloud_init": {
        "id": "ORCH_FVT_PXEBOOT_V004",
        "title": "Verify fresh boot and cloud-init completion",
        "component": "Cloud-init",
    },
    "kubernetes_nodes": {
        "id": "ORCH_FVT_PXEBOOT_V005",
        "title": "Verify Kubernetes membership and node readiness",
        "component": "Kubernetes nodes",
    },
    "kubernetes_services": {
        "id": "ORCH_FVT_PXEBOOT_V006",
        "title": "Verify Kubernetes node services",
        "component": "Kubernetes services",
    },
    "kubernetes_versions": {
        "id": "ORCH_FVT_PXEBOOT_V007",
        "title": "Verify Kubernetes component version compatibility",
        "component": "Kubernetes version compatibility",
    },
    "kubernetes_control_plane": {
        "id": "ORCH_FVT_PXEBOOT_V008",
        "title": "Verify Kubernetes API and control-plane readiness",
        "component": "Kubernetes control plane",
    },
    "kubernetes_system_pods": {
        "id": "ORCH_FVT_PXEBOOT_V009",
        "title": "Verify Kubernetes system workloads",
        "component": "Kubernetes system workloads",
    },
    "kubernetes_virtual_ip": {
        "id": "ORCH_FVT_PXEBOOT_V010",
        "title": "Verify Kubernetes virtual IP ownership",
        "component": "Kubernetes virtual IP",
    },
    "kubernetes_workload": {
        "id": "ORCH_FVT_PXEBOOT_V011",
        "title": "Verify Kubernetes workload scheduling",
        "component": "Kubernetes workload scheduling",
    },
    "kubernetes_etcd_health": {
        "id": "ORCH_FVT_PXEBOOT_V012",
        "title": "Verify Kubernetes etcd endpoint health",
        "component": "Kubernetes etcd endpoint health",
    },
    "kubernetes_etcd_topology": {
        "id": "ORCH_FVT_PXEBOOT_V013",
        "title": "Verify Kubernetes etcd membership and consistency",
        "component": "Kubernetes etcd topology",
    },
    "kubernetes_local_etcd": {
        "id": "ORCH_FVT_PXEBOOT_V014",
        "title": "Verify Kubernetes local-disk etcd",
        "component": "Kubernetes local etcd",
    },
    "kubernetes_local_etcd_integrity": {
        "id": "ORCH_FVT_PXEBOOT_V015",
        "title": "Verify Kubernetes local-etcd disk integrity",
        "component": "Kubernetes local-etcd disk integrity",
    },
    "kubernetes_storage": {
        "id": "ORCH_FVT_PXEBOOT_V016",
        "title": "Verify Kubernetes NFS and CSI storage",
        "component": "Kubernetes storage",
    },
    "kubernetes_default_storage": {
        "id": "ORCH_FVT_PXEBOOT_V017",
        "title": "Verify Kubernetes default StorageClass",
        "component": "Kubernetes default storage",
    },
    "kubernetes_snapshot_controller": {
        "id": "ORCH_FVT_PXEBOOT_V018",
        "title": "Verify Kubernetes PowerScale snapshot components",
        "component": "Kubernetes snapshot components",
    },
    "kubernetes_nfs_dynamic": {
        "id": "ORCH_FVT_PXEBOOT_V019",
        "title": "Verify Kubernetes NFS dynamic provisioning",
        "component": "Kubernetes NFS provisioning",
    },
    "kubernetes_csi_dynamic": {
        "id": "ORCH_FVT_PXEBOOT_V020",
        "title": "Verify Kubernetes PowerScale dynamic provisioning",
        "component": "Kubernetes PowerScale provisioning",
    },
    "kubernetes_local_etcd_recovery": {
        "id": "ORCH_FVT_PXEBOOT_V021",
        "title": "Verify Kubernetes local-etcd reboot persistence",
        "component": "Kubernetes local-etcd reboot persistence",
    },
    "kubernetes_recovery": {
        "id": "ORCH_FVT_PXEBOOT_V022",
        "title": "Verify Kubernetes control-plane reboot recovery",
        "component": "Kubernetes control-plane recovery",
    },
    "slurm_membership": {
        "id": "ORCH_FVT_PXEBOOT_V023",
        "title": "Verify Slurm membership and discovered hardware",
        "component": "Slurm membership",
    },
    "slurm_scheduler": {
        "id": "ORCH_FVT_PXEBOOT_V024",
        "title": "Verify Slurm compute partition readiness",
        "component": "Slurm partitions",
    },
    "slurm_services": {
        "id": "ORCH_FVT_PXEBOOT_V025",
        "title": "Verify Slurm services by node role",
        "component": "Slurm services",
    },
    "slurm_cross_ssh": {
        "id": "ORCH_FVT_PXEBOOT_V026",
        "title": "Verify Slurm cross-node passwordless SSH",
        "component": "Slurm cross-node SSH",
    },
    "slurm_configless": {
        "id": "ORCH_FVT_PXEBOOT_V027",
        "title": "Verify Slurm configless access and cluster identity",
        "component": "Slurm configless cluster identity",
    },
    "slurm_config_consistency": {
        "id": "ORCH_FVT_PXEBOOT_V028",
        "title": "Verify Slurm configuration consistency",
        "component": "Slurm configuration consistency",
    },
    "slurm_reconfigure": {
        "id": "ORCH_FVT_PXEBOOT_V029",
        "title": "Verify Slurm configuration reconfigure",
        "component": "Slurm reconfigure",
    },
    "slurm_hardware_discovery": {
        "id": "ORCH_FVT_PXEBOOT_V030",
        "title": "Verify Slurm hardware discovery policy",
        "component": "Slurm hardware discovery",
    },
    "slurm_custom_configuration": {
        "id": "ORCH_FVT_PXEBOOT_V031",
        "title": "Verify custom Slurm configuration end to end",
        "component": "Slurm custom configuration",
    },
    "slurm_basic_jobs": {
        "id": "ORCH_FVT_PXEBOOT_V032",
        "title": "Verify Slurm control-node job submission",
        "component": "Slurm control-node jobs",
    },
    "slurm_login_jobs": {
        "id": "ORCH_FVT_PXEBOOT_V033",
        "title": "Verify Slurm login-node job submission",
        "component": "Slurm login-node jobs",
    },
    "slurm_compiler_jobs": {
        "id": "ORCH_FVT_PXEBOOT_V034",
        "title": "Verify Slurm login-compiler job submission",
        "component": "Slurm login-compiler jobs",
    },
    "slurm_concurrent_jobs": {
        "id": "ORCH_FVT_PXEBOOT_V035",
        "title": "Verify Slurm concurrent batch jobs",
        "component": "Slurm concurrent jobs",
    },
    "slurm_insufficient_resources": {
        "id": "ORCH_FVT_PXEBOOT_V036",
        "title": "Verify Slurm insufficient-resource handling",
        "component": "Slurm resource rejection",
    },
    "slurm_job_queueing": {
        "id": "ORCH_FVT_PXEBOOT_V037",
        "title": "Verify Slurm full-capacity job queueing",
        "component": "Slurm job queueing",
    },
    "slurm_drain_queue": {
        "id": "ORCH_FVT_PXEBOOT_V038",
        "title": "Verify Slurm drain queue and resume behavior",
        "component": "Slurm drain and queue",
    },
    "slurm_pam": {
        "id": "ORCH_FVT_PXEBOOT_V039",
        "title": "Verify Slurm pam_slurm_adopt integration",
        "component": "Slurm pam_slurm_adopt integration",
    },
    "slurm_control_ldap_auth": {
        "id": "ORCH_FVT_PXEBOOT_V040",
        "title": "Verify Slurm control-node valid LDAP authentication",
        "component": "Slurm control-node valid LDAP authentication",
    },
    "slurm_control_ldap_invalid_password": {
        "id": "ORCH_FVT_PXEBOOT_V041",
        "title": "Verify Slurm control-node invalid LDAP password rejection",
        "component": "Slurm control-node invalid LDAP password",
    },
    "slurm_login_ldap_auth": {
        "id": "ORCH_FVT_PXEBOOT_V042",
        "title": "Verify Slurm login-node valid LDAP authentication",
        "component": "Slurm login-node valid LDAP authentication",
    },
    "slurm_login_ldap_invalid_password": {
        "id": "ORCH_FVT_PXEBOOT_V043",
        "title": "Verify Slurm login-node invalid LDAP password rejection",
        "component": "Slurm login-node invalid LDAP password",
    },
    "slurm_compiler_ldap_auth": {
        "id": "ORCH_FVT_PXEBOOT_V044",
        "title": "Verify Slurm login-compiler valid LDAP authentication",
        "component": "Slurm login-compiler valid LDAP authentication",
    },
    "slurm_compiler_ldap_invalid_password": {
        "id": "ORCH_FVT_PXEBOOT_V045",
        "title": "Verify Slurm login-compiler invalid LDAP password rejection",
        "component": "Slurm login-compiler invalid LDAP password",
    },
    "slurm_pam_no_job": {
        "id": "ORCH_FVT_PXEBOOT_V046",
        "title": "Verify Slurm PAM denial without an active job",
        "component": "Slurm PAM no-job access",
    },
    "slurm_invalid_ldap": {
        "id": "ORCH_FVT_PXEBOOT_V047",
        "title": "Verify Slurm invalid LDAP identity rejection",
        "component": "Slurm LDAP rejection",
    },
    "slurm_control_ldap_jobs": {
        "id": "ORCH_FVT_PXEBOOT_V048",
        "title": "Verify Slurm control-node LDAP job submission",
        "component": "Slurm control-node LDAP jobs",
    },
    "slurm_control_pam_job_access": {
        "id": "ORCH_FVT_PXEBOOT_V049",
        "title": "Verify Slurm control-node PAM job-access lifecycle",
        "component": "Slurm control-node PAM access",
    },
    "slurm_login_ldap_jobs": {
        "id": "ORCH_FVT_PXEBOOT_V050",
        "title": "Verify Slurm login-node LDAP job submission",
        "component": "Slurm login-node LDAP jobs",
    },
    "slurm_login_pam_job_access": {
        "id": "ORCH_FVT_PXEBOOT_V051",
        "title": "Verify Slurm login-node PAM job-access lifecycle",
        "component": "Slurm login-node PAM access",
    },
    "slurm_compiler_ldap_jobs": {
        "id": "ORCH_FVT_PXEBOOT_V052",
        "title": "Verify Slurm login-compiler LDAP job submission",
        "component": "Slurm login-compiler LDAP jobs",
    },
    "slurm_compiler_pam_job_access": {
        "id": "ORCH_FVT_PXEBOOT_V053",
        "title": "Verify Slurm login-compiler PAM job-access lifecycle",
        "component": "Slurm login-compiler PAM access",
    },
    "slurm_gpu_inventory": {
        "id": "ORCH_FVT_PXEBOOT_V054",
        "title": "Verify Slurm NVIDIA GPU inventory",
        "component": "Slurm NVIDIA GPU inventory",
    },
    "slurm_gpu_job": {
        "id": "ORCH_FVT_PXEBOOT_V055",
        "title": "Verify Slurm GPU allocation",
        "component": "Slurm GPU allocation",
    },
    "slurm_gpu_memory": {
        "id": "ORCH_FVT_PXEBOOT_V056",
        "title": "Verify Slurm GPU memory workload",
        "component": "Slurm GPU memory workload",
    },
    "slurm_openmpi_installation": {
        "id": "ORCH_FVT_PXEBOOT_V057",
        "title": "Verify Slurm OpenMPI installation",
        "component": "Slurm OpenMPI installation",
    },
    "slurm_openmpi_job": {
        "id": "ORCH_FVT_PXEBOOT_V058",
        "title": "Verify Slurm OpenMPI job",
        "component": "Slurm OpenMPI job",
    },
    "slurm_ucx_transport": {
        "id": "ORCH_FVT_PXEBOOT_V059",
        "title": "Verify Slurm UCX InfiniBand transport",
        "component": "Slurm UCX transport",
    },
    "slurm_ib_configuration": {
        "id": "ORCH_FVT_PXEBOOT_V060",
        "title": "Verify Slurm InfiniBand configuration",
        "component": "Slurm InfiniBand configuration",
    },
    "slurm_ib_connectivity": {
        "id": "ORCH_FVT_PXEBOOT_V061",
        "title": "Verify Slurm InfiniBand peer connectivity",
        "component": "Slurm InfiniBand connectivity",
    },
    "slurm_recovery": {
        "id": "ORCH_FVT_PXEBOOT_V062",
        "title": "Verify Slurm cluster reboot recovery",
        "component": "Slurm cluster recovery",
    },
    "apptainer_runtime": {
        "id": "ORCH_FVT_PXEBOOT_V063",
        "title": "Verify Apptainer runtime availability",
        "component": "Apptainer runtime",
    },
    "apptainer_shared_artifacts": {
        "id": "ORCH_FVT_PXEBOOT_V064",
        "title": "Verify Apptainer shared artifacts",
        "component": "Apptainer shared artifacts",
    },
    "apptainer_pulp_policy": {
        "id": "ORCH_FVT_PXEBOOT_V065",
        "title": "Verify Apptainer Pulp-only download policy",
        "component": "Apptainer Pulp download policy",
    },
    "apptainer_shared_storage": {
        "id": "ORCH_FVT_PXEBOOT_V066",
        "title": "Verify Apptainer shared storage",
        "component": "Apptainer shared storage",
    },
    "apptainer_download": {
        "id": "ORCH_FVT_PXEBOOT_V067",
        "title": "Verify Apptainer image download",
        "component": "Apptainer image download",
    },
    "apptainer_download_idempotency": {
        "id": "ORCH_FVT_PXEBOOT_V068",
        "title": "Verify Apptainer image download idempotency",
        "component": "Apptainer image download idempotency",
    },
    "apptainer_download_memory": {
        "id": "ORCH_FVT_PXEBOOT_V069",
        "title": "Verify Apptainer download memory use",
        "component": "Apptainer download memory",
    },
    "apptainer_image_inventory": {
        "id": "ORCH_FVT_PXEBOOT_V070",
        "title": "Verify Apptainer SIF inventory consistency",
        "component": "Apptainer SIF inventory",
    },
    "apptainer_sif_format": {
        "id": "ORCH_FVT_PXEBOOT_V071",
        "title": "Verify Apptainer SIF format",
        "component": "Apptainer SIF format",
    },
    "apptainer_sif_permissions": {
        "id": "ORCH_FVT_PXEBOOT_V072",
        "title": "Verify Apptainer SIF permissions",
        "component": "Apptainer SIF permissions",
    },
    "apptainer_sif_integrity": {
        "id": "ORCH_FVT_PXEBOOT_V073",
        "title": "Verify Apptainer SIF checksum consistency",
        "component": "Apptainer SIF checksum consistency",
    },
    "apptainer_ldap_readability": {
        "id": "ORCH_FVT_PXEBOOT_V074",
        "title": "Verify LDAP access to Apptainer images",
        "component": "Apptainer LDAP image access",
    },
    "apptainer_non_root_execution": {
        "id": "ORCH_FVT_PXEBOOT_V075",
        "title": "Verify unprivileged Apptainer execution",
        "component": "Apptainer unprivileged execution",
    },
    "apptainer_missing_image_contract": {
        "id": "ORCH_FVT_PXEBOOT_V076",
        "title": "Verify Apptainer missing-image failure contract",
        "component": "Apptainer missing-image handling",
    },
    "apptainer_single_node_job": {
        "id": "ORCH_FVT_PXEBOOT_V077",
        "title": "Verify targeted Apptainer jobs",
        "component": "Apptainer targeted jobs",
    },
    "apptainer_multi_node_job": {
        "id": "ORCH_FVT_PXEBOOT_V078",
        "title": "Verify multi-node Apptainer job",
        "component": "Apptainer multi-node job",
    },
    "apptainer_ldap_job": {
        "id": "ORCH_FVT_PXEBOOT_V079",
        "title": "Verify LDAP-user Apptainer jobs",
        "component": "Apptainer LDAP-user jobs",
    },
    "apptainer_concurrent_jobs": {
        "id": "ORCH_FVT_PXEBOOT_V080",
        "title": "Verify concurrent Apptainer jobs",
        "component": "Apptainer concurrent jobs",
    },
    "apptainer_invalid_sif": {
        "id": "ORCH_FVT_PXEBOOT_V081",
        "title": "Verify invalid SIF rejection",
        "component": "Apptainer invalid-SIF rejection",
    },
    "apptainer_restricted_sif": {
        "id": "ORCH_FVT_PXEBOOT_V082",
        "title": "Verify restricted SIF rejection",
        "component": "Apptainer restricted-SIF rejection",
    },
    "apptainer_nfs_visibility": {
        "id": "ORCH_FVT_PXEBOOT_V083",
        "title": "Verify Apptainer shared-storage visibility",
        "component": "Apptainer shared-storage visibility",
    },
    "apptainer_slurm_environment": {
        "id": "ORCH_FVT_PXEBOOT_V084",
        "title": "Verify Slurm environment inside Apptainer",
        "component": "Apptainer Slurm environment",
    },
    "apptainer_job_array": {
        "id": "ORCH_FVT_PXEBOOT_V085",
        "title": "Verify Apptainer Slurm job array",
        "component": "Apptainer Slurm job array",
    },
    "apptainer_failure_cleanup": {
        "id": "ORCH_FVT_PXEBOOT_V086",
        "title": "Verify Apptainer failed-job cleanup",
        "component": "Apptainer failed-job cleanup",
    },
    "apptainer_gpu_access": {
        "id": "ORCH_FVT_PXEBOOT_V087",
        "title": "Verify GPU visibility inside Apptainer",
        "component": "Apptainer GPU visibility",
    },
    "apptainer_gpu_count": {
        "id": "ORCH_FVT_PXEBOOT_V088",
        "title": "Verify Apptainer GPU count",
        "component": "Apptainer GPU count",
    },
    "apptainer_cuda_workload": {
        "id": "ORCH_FVT_PXEBOOT_V089",
        "title": "Verify NVIDIA workload inside Apptainer",
        "component": "Apptainer NVIDIA workload",
    },
    "apptainer_gpu_memory": {
        "id": "ORCH_FVT_PXEBOOT_V090",
        "title": "Verify Apptainer GPU memory release",
        "component": "Apptainer GPU memory release",
    },
    "apptainer_infiniband": {
        "id": "ORCH_FVT_PXEBOOT_V091",
        "title": "Verify InfiniBand visibility inside Apptainer",
        "component": "Apptainer InfiniBand visibility",
    },
    "apptainer_reboot_storage": {
        "id": "ORCH_FVT_PXEBOOT_V092",
        "title": "Verify Apptainer storage after compute reboot",
        "component": "Apptainer storage recovery",
    },
    "apptainer_reboot_job": {
        "id": "ORCH_FVT_PXEBOOT_V093",
        "title": "Verify Apptainer job after compute reboot",
        "component": "Apptainer post-reboot job",
    },
    "apptainer_reboot_artifacts": {
        "id": "ORCH_FVT_PXEBOOT_V094",
        "title": "Verify Apptainer artifacts after compute reboot",
        "component": "Apptainer artifact recovery",
    },
}

CLEANUP_TEST_CASES: dict[str, dict[str, str]] = {
    "deploy_cleanup": {
        "id": "ORCH_FVT_CLEANUP_E001",
        "title": "Execute full Orchestrator cleanup",
    },
    "cleanup_openchami": {
        "id": "ORCH_FVT_CLEANUP_V001",
        "title": "Verify OpenCHAMI removal",
    },
    "cleanup_openldap": {
        "id": "ORCH_FVT_CLEANUP_V002",
        "title": "Verify OpenLDAP removal",
    },
    "cleanup_slurm": {
        "id": "ORCH_FVT_CLEANUP_V003",
        "title": "Verify Slurm shared-data and storage cleanup",
    },
    "cleanup_kubernetes": {
        "id": "ORCH_FVT_CLEANUP_V004",
        "title": "Verify Kubernetes shared-data and storage cleanup",
    },
    "cleanup_artifacts": {
        "id": "ORCH_FVT_CLEANUP_V005",
        "title": "Verify cleanup artifacts and preserved inputs",
    },
    "cleanup_credentials": {
        "id": "ORCH_FVT_CLEANUP_V006",
        "title": "Verify cleanup credential policy",
    },
}

NFT_TEST_CASES: dict[str, dict[str, str]] = {
    "precheck_performance": {
        "id": "ORCH_NFT_001",
        "title": "Measure Orchestrator precheck duration",
    },
    "prepare_performance": {
        "id": "ORCH_NFT_002",
        "title": "Measure Orchestrator prepare duration",
    },
    "provision_performance": {
        "id": "ORCH_NFT_003",
        "title": "Measure Orchestrator provision duration",
    },
    "cleanup_performance": {
        "id": "ORCH_NFT_004",
        "title": "Measure Orchestrator cleanup duration",
    },
    "prepare_idempotency": {
        "id": "ORCH_NFT_005",
        "title": "Verify Orchestrator prepare idempotency",
    },
    "precheck_idempotency": {
        "id": "ORCH_NFT_006",
        "title": "Verify Orchestrator precheck idempotency",
    },
    "cleanup_idempotency": {
        "id": "ORCH_NFT_007",
        "title": "Verify Orchestrator cleanup idempotency",
    },
    "credential_file_permissions": {
        "id": "ORCH_NFT_008",
        "title": "Verify Orchestrator credential-file permissions",
    },
    "ssh_private_key_permissions": {
        "id": "ORCH_NFT_009",
        "title": "Verify OIM SSH private-key permissions",
    },
    "log_file_permissions": {
        "id": "ORCH_NFT_010",
        "title": "Verify Orchestrator log-file permissions",
    },
    "vault_encryption": {
        "id": "ORCH_NFT_011",
        "title": "Verify Orchestrator vault encryption",
    },
    "clean_baseline": {
        "id": "ORCH_NFT_012",
        "title": "Verify clean OIM baseline before fresh install",
    },
    "lifecycle_fresh_install": {
        "id": "ORCH_NFT_013",
        "title": "Verify complete fresh-install lifecycle from clean baseline",
    },
}

TEST_CASES: dict[str, dict[str, str]] = {
    **PRECHECK_TEST_CASES,
    **PREPARE_TEST_CASES,
    **PROVISION_TEST_CASES,
    **PXEBOOT_TEST_CASES,
    **CLEANUP_TEST_CASES,
    **NFT_TEST_CASES,
}
