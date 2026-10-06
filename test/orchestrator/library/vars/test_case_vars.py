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

# pylint: disable=too-many-lines
# This is a data registry file that grows with test cases; the line count
# reflects the number of test cases, not code complexity.

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
    "precheck_mount_missing_mount_point": {
        "id": "ORCH_FVT_PRECHECK_V008",
        "title": "Verify mount entries have valid mount_point",
        "component": "Mount config mount_point",
    },
    "precheck_mount_missing_targeting": {
        "id": "ORCH_FVT_PRECHECK_V009",
        "title": "Verify mount entries have targeting configured",
        "component": "Mount config targeting",
    },
    "precheck_mount_invalid_mount_params": {
        "id": "ORCH_FVT_PRECHECK_V010",
        "title": "Verify mount_params profiles resolve correctly",
        "component": "Mount config mount_params",
    },
    "precheck_mount_missing_source": {
        "id": "ORCH_FVT_PRECHECK_V011",
        "title": "Verify mount entries have non-empty source",
        "component": "Mount config source",
    },
    "precheck_mount_node_key_without_mount_point": {
        "id": "ORCH_FVT_PRECHECK_V012",
        "title": "Verify node_mount_point is set when node_key is specified",
        "component": "Mount config node_key consistency",
    },
    # ── OIM readiness (V100-V118) ───────────────────────────────────
    "oim_cpu_threshold": {
        "id": "ORCH_FVT_PRECHECK_V100",
        "title": "Verify OIM CPU core count meets minimum threshold",
        "component": "OIM CPU threshold",
    },
    "oim_memory_threshold": {
        "id": "ORCH_FVT_PRECHECK_V101",
        "title": "Verify OIM memory meets minimum threshold",
        "component": "OIM memory threshold",
    },
    "oim_disk_threshold": {
        "id": "ORCH_FVT_PRECHECK_V102",
        "title": "Verify OIM root filesystem meets minimum threshold",
        "component": "OIM disk threshold",
    },
    "oim_pxe_nic_present": {
        "id": "ORCH_FVT_PRECHECK_V103",
        "title": "Verify configured admin NIC exists and is UP",
        "component": "OIM admin NIC presence",
    },
    "oim_public_nic_present": {
        "id": "ORCH_FVT_PRECHECK_V104",
        "title": "Verify public/default-route NIC exists and is UP",
        "component": "OIM public NIC presence",
    },
    "oim_pxe_nic_ipv4": {
        "id": "ORCH_FVT_PRECHECK_V105",
        "title": "Verify admin NIC carries the configured IPv4 address",
        "component": "OIM admin NIC IPv4",
    },
    "oim_ssh_preflight": {
        "id": "ORCH_FVT_PRECHECK_V107",
        "title": "Verify passwordless SSH from OIM to mapped target node",
        "component": "OIM SSH preflight",
    },
    "oim_internet_reachability": {
        "id": "ORCH_FVT_PRECHECK_V108",
        "title": "Verify internet reachability via ICMP ping",
        "component": "Internet reachability",
    },
    "oim_os_version": {
        "id": "ORCH_FVT_PRECHECK_V109",
        "title": "Verify OIM OS matches expected distribution and version",
        "component": "OIM OS version",
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
    "boot_image_identity": {
        "id": "ORCH_FVT_PROVISION_V009",
        "title": "Verify Boot Service image paths match build_status.yml",
        "component": "Boot image identity",
    },
    "boot_image_architecture": {
        "id": "ORCH_FVT_PROVISION_V010",
        "title": "Verify build_status.yml architecture key consistency",
        "component": "Boot image architecture",
    },
}

PXEBOOT_TEST_CASES: dict[str, dict[str, str]] = {  # pylint: disable=syntax-error
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
    "kubernetes_configured_versions": {
        "id": "ORCH_FVT_PXEBOOT_V101",
        "title": "Verify configured Kubernetes component versions",
        "component": "Kubernetes configured versions",
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
    "kubernetes_local_etcd_provisioning": {
        "id": "ORCH_FVT_PXEBOOT_V102",
        "title": "Verify Kubernetes local-etcd provisioning contract",
        "component": "Kubernetes local-etcd provisioning",
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
    "kubernetes_nfs_contract": {
        "id": "ORCH_FVT_PXEBOOT_V103",
        "title": "Verify Kubernetes NFS provisioner and backend contract",
        "component": "Kubernetes NFS provisioner",
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
    "hpc_benchmarks_json_declaration": {
        "id": "ORCH_FVT_PXEBOOT_V200",
        "title": "Verify HPC benchmarks tool declaration (benchmark_tools.list)",
        "component": "HPC benchmarks tool declaration",
    },
    "hpc_benchmarks_local_repo_sync": {
        "id": "ORCH_FVT_PXEBOOT_V201",
        "title": "Verify benchmark tarballs reachable via Pulp offline repo URL",
        "component": "HPC benchmarks Pulp sync",
    },
    "hpc_benchmarks_tools_dir_creation": {
        "id": "ORCH_FVT_PXEBOOT_V202",
        "title": "Verify /hpc_tools directory layout and permissions",
        "component": "HPC benchmarks directory creation",
    },
    "hpc_benchmarks_artifact_copy": {
        "id": "ORCH_FVT_PXEBOOT_V203",
        "title": "Verify declared benchmark artifacts are staged per tool",
        "component": "HPC benchmarks artifact copy",
    },
    "hpc_benchmarks_msr_safe_arch_boundary": {
        "id": "ORCH_FVT_PXEBOOT_V204",
        "title": "Verify msr-safe is staged only for x86_64",
        "component": "HPC benchmarks msr-safe arch boundary",
    },
    "hpc_benchmarks_container_first_guidance": {
        "id": "ORCH_FVT_PXEBOOT_V205",
        "title": "Verify pull_benchmarks.sh and benchmark_tools.list are deployed",
        "component": "HPC benchmarks staging artifacts",
    },
    "hpc_benchmarks_source_only_delivery": {
        "id": "ORCH_FVT_PXEBOOT_V206",
        "title": "Verify no compile or build commands are staged",
        "component": "HPC benchmarks source-only delivery",
    },
    "hpc_benchmarks_per_tool_staging_report": {
        "id": "ORCH_FVT_PXEBOOT_V207",
        "title": "Verify per-tool staging report from pull_benchmarks.sh",
        "component": "HPC benchmarks per-tool staging report",
    },
    "hpc_benchmarks_e2e_provisioning": {
        "id": "ORCH_FVT_PXEBOOT_V208",
        "title": "Verify end-to-end benchmark provisioning pipeline",
        "component": "HPC benchmarks end-to-end provisioning",
    },
    "hpc_benchmarks_nfs_accessibility": {
        "id": "ORCH_FVT_PXEBOOT_V209",
        "title": "Verify /hpc_tools NFS is mounted and readable on compute nodes",
        "component": "HPC benchmarks NFS accessibility",
    },
    "hpc_benchmarks_airgapped_staging": {
        "id": "ORCH_FVT_PXEBOOT_V210",
        "title": "Verify benchmark staging completes without external egress",
        "component": "HPC benchmarks air-gapped staging",
    },
    "hpc_benchmarks_post_staging_validation": {
        "id": "ORCH_FVT_PXEBOOT_V211",
        "title": "Verify post-staging validation of benchmark tool directories",
        "component": "HPC benchmarks post-staging validation",
    },
    "hpc_benchmarks_rhel_compatibility": {
        "id": "ORCH_FVT_PXEBOOT_V212",
        "title": "Verify benchmark staging on RHEL 10.x",
        "component": "HPC benchmarks RHEL compatibility",
    },
    "hpc_benchmarks_cuda_flow_unaffected": {
        "id": "ORCH_FVT_PXEBOOT_V213",
        "title": "Verify CUDA flow is unaffected by benchmark staging",
        "component": "HPC benchmarks CUDA flow invariance",
    },
    "hpc_benchmarks_nvhpc_flow_unaffected": {
        "id": "ORCH_FVT_PXEBOOT_V214",
        "title": "Verify NVIDIA HPC SDK flow is unaffected by benchmark staging",
        "component": "HPC benchmarks NVIDIA SDK flow invariance",
    },
    "hpc_benchmarks_container_image_unaffected": {
        "id": "ORCH_FVT_PXEBOOT_V215",
        "title": "Verify container image flow is unaffected by benchmark staging",
        "component": "HPC benchmarks container image flow invariance",
    },
    "hpc_benchmarks_openmpi_unaffected": {
        "id": "ORCH_FVT_PXEBOOT_V216",
        "title": "Verify OpenMPI/UCX are unaffected by benchmark staging",
        "component": "HPC benchmarks OpenMPI invariance",
    },
    "hpc_benchmarks_existing_dirs_preserved": {
        "id": "ORCH_FVT_PXEBOOT_V217",
        "title": "Verify pre-existing /hpc_tools directories are preserved",
        "component": "HPC benchmarks existing directory preservation",
    },
    "hpc_benchmarks_staging_idempotency": {
        "id": "ORCH_FVT_PXEBOOT_V218",
        "title": "Verify benchmark staging is idempotent",
        "component": "HPC benchmarks staging idempotency",
    },
    "coredns_container_state": {
        "id": "ORCH_FVT_PXEBOOT_V300",
        "title": "Verify coresmd container state matches dns_enabled dataset",
        "component": "CoreDNS/CoreDHCP container state",
    },
    "coredns_forward_resolution": {
        "id": "ORCH_FVT_PXEBOOT_V301",
        "title": "Verify CoreDNS forward resolution from OIM for mapped nodes",
        "component": "CoreDNS forward resolution",
    },
    "coredns_reverse_resolution": {
        "id": "ORCH_FVT_PXEBOOT_V302",
        "title": "Verify CoreDNS reverse resolution from OIM for mapped admin IPs",
        "component": "CoreDNS reverse resolution",
    },
    "coredhcp_multisubnet_running_image": {
        "id": "ORCH_FVT_PXEBOOT_V303",
        "title": (
            "Verify multi-subnet coresmd containers and rendered subnet "
            "configuration (defect 843 open for live subnet validation)"
        ),
        "component": "CoreDHCP multi-subnet image and config",
    },
    "dns_compute_resolv_conf": {
        "id": "ORCH_FVT_PXEBOOT_V304",
        "title": "Verify /etc/resolv.conf on every compute uses CoreDNS as primary",
        "component": "Compute /etc/resolv.conf",
    },
    "dns_compute_forward_getent": {
        "id": "ORCH_FVT_PXEBOOT_V305",
        "title": "Verify every compute resolves peers via getent hosts",
        "component": "Compute getent hosts resolution",
    },
    "coredns_idempotency": {
        "id": "ORCH_FVT_PXEBOOT_V306",
        "title": "Verify CoreDNS/CoreDHCP state stability (no-drift)",
        "component": "CoreDNS state stability",
    },
    "dns_node_addition_pipeline": {
        "id": "ORCH_FVT_PXEBOOT_V307",
        "title": (
            "Verify SMD-to-CoreDNS pipeline readiness (existing registrations "
            "only; defect 843 open for live add-node)"
        ),
        "component": "CoreDNS node-addition pipeline readiness",
    },
    "dns_smd_unreachable_cached_resolution": {
        "id": "ORCH_FVT_PXEBOOT_V308",
        "title": "Verify CoreDNS serves cached records when SMD is unavailable",
        "component": "CoreDNS SMD-unavailable cached resolution",
    },
    "powervault_iscsi_service": {
        "id": "ORCH_FVT_PXEBOOT_V400",
        "title": "Verify iscsid is active and enabled on all PowerVault target nodes",
        "component": "PowerVault iSCSI service",
    },
    "powervault_iscsi_initiator_name": {
        "id": "ORCH_FVT_PXEBOOT_V401",
        "title": "Verify iSCSI initiator name matches config on all target nodes",
        "component": "PowerVault iSCSI initiator name",
    },
    "powervault_iscsi_discovery": {
        "id": "ORCH_FVT_PXEBOOT_V402",
        "title": "Verify iSCSI target discovery succeeds from all portal IPs",
        "component": "PowerVault iSCSI target discovery",
    },
    "powervault_iscsi_sessions": {
        "id": "ORCH_FVT_PXEBOOT_V403",
        "title": "Verify iSCSI sessions are active on all target nodes",
        "component": "PowerVault iSCSI sessions",
    },
    "powervault_iscsi_startup_automatic": {
        "id": "ORCH_FVT_PXEBOOT_V404",
        "title": "Verify iSCSI node startup is automatic on all target nodes",
        "component": "PowerVault iSCSI startup automatic",
    },
    "powervault_portal_reachability": {
        "id": "ORCH_FVT_PXEBOOT_V405",
        "title": "Verify iSCSI portal ports are reachable and sessions healthy",
        "component": "PowerVault portal reachability",
    },
    "powervault_multipath_service": {
        "id": "ORCH_FVT_PXEBOOT_V406",
        "title": "Verify multipathd is active and enabled on all target nodes",
        "component": "PowerVault multipathd service",
    },
    "powervault_multipath_device": {
        "id": "ORCH_FVT_PXEBOOT_V407",
        "title": "Verify multipath device exists and matches volume_id",
        "component": "PowerVault multipath device",
    },
    "powervault_multipath_redundancy": {
        "id": "ORCH_FVT_PXEBOOT_V408",
        "title": "Verify multipath device has multiple paths for redundancy",
        "component": "PowerVault multipath redundancy",
    },
    "powervault_gpt_partition": {
        "id": "ORCH_FVT_PXEBOOT_V409",
        "title": "Verify GPT partition exists on multipath device",
        "component": "PowerVault GPT partition",
    },
    "powervault_filesystem_type": {
        "id": "ORCH_FVT_PXEBOOT_V410",
        "title": "Verify filesystem formatted with correct type",
        "component": "PowerVault filesystem type",
    },
    "powervault_mount_point_directory": {
        "id": "ORCH_FVT_PXEBOOT_V411",
        "title": "Verify mount point directory exists on all target nodes",
        "component": "PowerVault mount point directory",
    },
    "powervault_volume_mounted": {
        "id": "ORCH_FVT_PXEBOOT_V412",
        "title": "Verify PowerVault volume is actively mounted on all target nodes",
        "component": "PowerVault volume mounted",
    },
    "powervault_mount_options": {
        "id": "ORCH_FVT_PXEBOOT_V413",
        "title": "Verify mount options applied correctly on all target nodes",
        "component": "PowerVault mount options",
    },
    "powervault_fstab_entry": {
        "id": "ORCH_FVT_PXEBOOT_V414",
        "title": "Verify persistent fstab entry created on all target nodes",
        "component": "PowerVault fstab entry",
    },
    "powervault_node_subdirectory": {
        "id": "ORCH_FVT_PXEBOOT_V415",
        "title": "Verify per-node subdirectory exists under mount point",
        "component": "PowerVault node subdirectory",
    },
    "powervault_bind_mounts": {
        "id": "ORCH_FVT_PXEBOOT_V416",
        "title": "Verify bind mount targets are active on all target nodes",
        "component": "PowerVault bind mounts",
    },
    "powervault_bind_fstab_entries": {
        "id": "ORCH_FVT_PXEBOOT_V417",
        "title": "Verify bind mount fstab entries are persistent on all target nodes",
        "component": "PowerVault bind fstab entries",
    },
    "powervault_bind_isolation": {
        "id": "ORCH_FVT_PXEBOOT_V418",
        "title": "Verify per-node data separation via bind mounts",
        "component": "PowerVault bind isolation",
    },
    "powervault_functional_group_targeting": {
        "id": "ORCH_FVT_PXEBOOT_V419",
        "title": "Verify PV mount only on correct functional groups",
        "component": "PowerVault functional group targeting",
    },
    "powervault_multiple_prefix_targeting": {
        "id": "ORCH_FVT_PXEBOOT_V420",
        "title": "Verify multiple prefixes target all groups correctly",
        "component": "PowerVault multiple prefix targeting",
    },
    "powervault_setup_log": {
        "id": "ORCH_FVT_PXEBOOT_V421",
        "title": "Verify cloud-init runcmd log exists and shows completion",
        "component": "PowerVault setup log",
    },
    "powervault_cloud_init_groups_dict": {
        "id": "ORCH_FVT_PXEBOOT_V422",
        "title": "Verify rendered iSCSI setup scripts deployed on target nodes",
        "component": "PowerVault metadata-service scripts",
    },
    "powervault_no_duplicate_fstab": {
        "id": "ORCH_FVT_PXEBOOT_V423",
        "title": "Verify no duplicate fstab entries on all target nodes",
        "component": "PowerVault no duplicate fstab",
    },
    "powervault_all_mounts_writable": {
        "id": "ORCH_FVT_PXEBOOT_V424",
        "title": "Verify all PV mounts (main + bind) are writable",
        "component": "PowerVault mounts writable",
    },
    "powervault_permissions": {
        "id": "ORCH_FVT_PXEBOOT_V425",
        "title": "Verify permissions on mount point match config",
        "component": "PowerVault permissions",
    },
    "powervault_io_write_read": {
        "id": "ORCH_FVT_PXEBOOT_V426",
        "title": "Verify write-read I/O on PV mount points",
        "component": "PowerVault I/O write-read",
    },
    "powervault_bind_io": {
        "id": "ORCH_FVT_PXEBOOT_V427",
        "title": "Verify bind-mount I/O reaches PV backing store",
        "component": "PowerVault bind I/O",
    },
    "powervault_slurm_mandatory_bind_mounts": {
        "id": "ORCH_FVT_PXEBOOT_V428",
        "title": (
            "Verify /var/lib/mysql and /var/spool/slurm "
            "configured as bind targets"
        ),
        "component": "PowerVault mandatory Slurm bind mounts",
    },
    "powervault_mysql_data_on_mount": {
        "id": "ORCH_FVT_PXEBOOT_V429",
        "title": "Verify MySQL datadir is on PowerVault mount",
        "component": "PowerVault MySQL datadir",
    },
    # ── PowerVault negative tests (V430-V431) ───────────────────────────
    "powervault_gpt_missing_label": {
        "id": "ORCH_FVT_PXEBOOT_V430",
        "title": "Verify GPT partition check correctly detects missing GPT label",
        "component": "PowerVault GPT negative validation",
    },
    "powervault_duplicate_fstab": {
        "id": "ORCH_FVT_PXEBOOT_V431",
        "title": "Verify duplicate fstab entry detection works correctly",
        "component": "PowerVault duplicate fstab negative validation",
    },
    "slurm_node_remove": {
        "id": "ORCH_FVT_PXEBOOT_V500",
        "title": "Verify Slurm compute node removal lifecycle",
        "component": "Slurm node removal",
    },
    "slurm_node_add": {
        "id": "ORCH_FVT_PXEBOOT_V501",
        "title": "Verify Slurm compute node re-addition lifecycle",
        "component": "Slurm node re-addition",
    },
    # ── DCGM / CUDA verification (ORCH_FVT_PXEBOOT_V501-V518) ─────────
    "dcgm_cuda_validation": {
        "id": "ORCH_FVT_PXEBOOT_V501",
        "title": "Verify NVIDIA driver and CUDA toolkit on GPU nodes",
        "component": "CUDA driver and toolkit validation",
    },
    "dcgm_cuda_atomic_lock": {
        "id": "ORCH_FVT_PXEBOOT_V502",
        "title": "Verify CUDA toolkit installed via atomic lock",
        "component": "CUDA atomic lock installation",
    },
    "dcgm_package_installed": {
        "id": "ORCH_FVT_PXEBOOT_V503",
        "title": "Verify datacenter-gpu-manager RPM and DCGM binaries",
        "component": "DCGM package installation",
    },
    "dcgm_daemon_running": {
        "id": "ORCH_FVT_PXEBOOT_V504",
        "title": "Verify nvidia-dcgm service is active and enabled",
        "component": "DCGM daemon status",
    },
    "dcgm_gpu_discovery": {
        "id": "ORCH_FVT_PXEBOOT_V505",
        "title": "Verify dcgmi discovery enumerates GPUs with unique UUIDs",
        "component": "DCGM GPU discovery",
    },
    "dcgm_gpu_metrics": {
        "id": "ORCH_FVT_PXEBOOT_V506",
        "title": "Verify dcgmi dmon returns metric samples for each GPU",
        "component": "DCGM GPU metrics monitoring",
    },
    "dcgm_cuda_login_compiler": {
        "id": "ORCH_FVT_PXEBOOT_V507",
        "title": "Verify CUDA toolkit accessible on login_compiler nodes",
        "component": "CUDA login_compiler installation",
    },
    "dcgm_cuda_compute_node": {
        "id": "ORCH_FVT_PXEBOOT_V508",
        "title": "Verify CUDA toolkit and driver on compute nodes",
        "component": "CUDA compute node installation",
    },
    "dcgm_multi_gpu_discovery": {
        "id": "ORCH_FVT_PXEBOOT_V509",
        "title": "Verify dcgmi discovery on multi-GPU nodes",
        "component": "DCGM multi-GPU discovery",
    },
    "dcgm_multi_gpu_no_login_compiler": {
        "id": "ORCH_FVT_PXEBOOT_V510",
        "title": "Verify GPU nodes work without login_compiler present",
        "component": "Multi-GPU without login_compiler",
    },
    "dcgm_multi_login_compiler_lock": {
        "id": "ORCH_FVT_PXEBOOT_V511",
        "title": "Verify CUDA toolkit install uses atomic lock with multiple login_compilers",
        "component": "Multi login_compiler atomic lock",
    },
    "dcgm_toolkit_nfs_storage": {
        "id": "ORCH_FVT_PXEBOOT_V512",
        "title": "Verify /hpc_tools is NFS-mounted and CUDA toolkit accessible",
        "component": "CUDA NFS shared storage",
    },
    "dcgm_rhel_compatibility": {
        "id": "ORCH_FVT_PXEBOOT_V513",
        "title": "Verify GPU node OS is a supported RHEL version",
        "component": "GPU RHEL compatibility",
    },
    "dcgm_cuda_version_compatibility": {
        "id": "ORCH_FVT_PXEBOOT_V514",
        "title": "Verify CUDA toolkit and DCGM daemon version compatibility",
        "component": "CUDA version compatibility",
    },
    "dcgm_neg_cuda_prerequisite": {
        "id": "ORCH_FVT_PXEBOOT_V515",
        "title": "Verify DCGM deployment requires CUDA prerequisites",
        "component": "CUDA prerequisite enforcement",
    },
    "dcgm_neg_daemon_recovery": {
        "id": "ORCH_FVT_PXEBOOT_V516",
        "title": "Verify DCGM daemon auto-recovery after SIGKILL",
        "component": "DCGM daemon crash recovery",
    },
    "dcgm_neg_socket_inaccessible": {
        "id": "ORCH_FVT_PXEBOOT_V517",
        "title": "Verify dcgmi returns clear error when socket is removed",
        "component": "DCGM socket inaccessible",
    },
    "dcgm_neg_package_install_failure": {
        "id": "ORCH_FVT_PXEBOOT_V518",
        "title": "Verify error handling when DCGM package is unavailable",
        "component": "DCGM package install failure",
    },
    "additional_cloud_init_smd_groups": {
        "id": "ORCH_FVT_PXEBOOT_V095",
        "title": "Verify additional cloud-init SMD groups",
        "component": "Additional cloud-init SMD groups",
    },
    "additional_cloud_init_metadata_groups": {
        "id": "ORCH_FVT_PXEBOOT_V096",
        "title": "Verify additional cloud-init metadata-service groups",
        "component": "Additional cloud-init metadata-service groups",
    },
    "node_architecture": {
        "id": "ORCH_FVT_PXEBOOT_V097",
        "title": "Verify live node architecture matches functional group",
        "component": "Node architecture",
    },
    "node_os_version": {
        "id": "ORCH_FVT_PXEBOOT_V098",
        "title": "Verify live node OS version matches functional group",
        "component": "Node OS version",
    },
    "additional_cloud_init_write_files": {
        "id": "ORCH_FVT_PXEBOOT_V099",
        "title": "Verify additional cloud-init write_files on nodes",
        "component": "Additional cloud-init write_files",
    },
    "additional_cloud_init_runcmd": {
        "id": "ORCH_FVT_PXEBOOT_V100",
        "title": "Verify additional cloud-init runcmd on nodes",
        "component": "Additional cloud-init runcmd",
    },
    # mount_config NFS test cases (order 500+)
    "mount_config_mount_point": {
        "id": "ORCH_FVT_PXEBOOT_V101",
        "title": "Verify NFS mount point directories exist on target nodes",
        "component": "NFS mount point directory",
    },
    "mount_config_volume_mounted": {
        "id": "ORCH_FVT_PXEBOOT_V102",
        "title": "Verify NFS volumes are actively mounted on target nodes",
        "component": "NFS volume mounted",
    },
    "mount_config_mount_options": {
        "id": "ORCH_FVT_PXEBOOT_V103",
        "title": "Verify NFS mount options match storage_config.yml",
        "component": "NFS mount options",
    },
    "mount_config_fstab": {
        "id": "ORCH_FVT_PXEBOOT_V104",
        "title": "Verify NFS fstab entries are persistent on target nodes",
        "component": "NFS fstab entry",
    },
    "mount_config_bind_mounts": {
        "id": "ORCH_FVT_PXEBOOT_V105",
        "title": "Verify NFS bind mount targets are active on target nodes",
        "component": "NFS bind mounts",
    },
    "mount_config_bind_fstab": {
        "id": "ORCH_FVT_PXEBOOT_V106",
        "title": "Verify NFS bind mount fstab entries are persistent",
        "component": "NFS bind fstab entries",
    },
    "mount_config_node_subdirectory": {
        "id": "ORCH_FVT_PXEBOOT_V107",
        "title": "Verify per-node subdirectory exists under NFS mount",
        "component": "NFS per-node subdirectory",
    },
    "mount_config_permissions": {
        "id": "ORCH_FVT_PXEBOOT_V108",
        "title": "Verify NFS mount permissions match storage_config.yml",
        "component": "NFS mount permissions",
    },
    "mount_config_fg_targeting": {
        "id": "ORCH_FVT_PXEBOOT_V109",
        "title": "Verify NFS mounts are present on target FGs and absent on others",
        "component": "NFS functional-group targeting",
    },
    "mount_config_no_duplicate_fstab": {
        "id": "ORCH_FVT_PXEBOOT_V110",
        "title": "Verify no duplicate NFS fstab entries on target nodes",
        "component": "NFS fstab uniqueness",
    },
    "mount_config_writable": {
        "id": "ORCH_FVT_PXEBOOT_V111",
        "title": "Verify NFS mounts are writable on target nodes",
        "component": "NFS mount writability",
    },
    "mount_config_oim_mount": {
        "id": "ORCH_FVT_PXEBOOT_V112",
        "title": "Verify NFS storage is mounted on the OIM",
        "component": "OIM NFS mount",
    },
    # minimal_os test cases (order 600+)
    "minimal_os_base_packages": {
        "id": "ORCH_FVT_PXEBOOT_V113",
        "title": "Verify base OS packages on OS-only nodes",
        "component": "Minimal OS base packages",
    },
    "minimal_os_ldms_packages": {
        "id": "ORCH_FVT_PXEBOOT_V114",
        "title": "Verify LDMS monitoring packages on OS-only nodes",
        "component": "Minimal OS LDMS packages",
    },
    "minimal_os_required_services": {
        "id": "ORCH_FVT_PXEBOOT_V115",
        "title": "Verify required services are active on OS-only nodes",
        "component": "Minimal OS required services",
    },

    "minimal_os_excluded_packages": {
        "id": "ORCH_FVT_PXEBOOT_V117",
        "title": "Verify workload packages are absent on OS-only nodes",
        "component": "Minimal OS excluded packages",
    },
    "minimal_os_excluded_services": {
        "id": "ORCH_FVT_PXEBOOT_V118",
        "title": "Verify workload services are inactive on OS-only nodes",
        "component": "Minimal OS excluded services",
    },
    "minimal_os_package_manager": {
        "id": "ORCH_FVT_PXEBOOT_V119",
        "title": "Verify package manager is functional on OS-only nodes",
        "component": "Minimal OS package manager",
    },
    "minimal_os_kernel_version": {
        "id": "ORCH_FVT_PXEBOOT_V120",
        "title": "Verify kernel version consistency on OS-only nodes",
        "component": "Minimal OS kernel version",
    },
    "minimal_os_network_identity": {
        "id": "ORCH_FVT_PXEBOOT_V121",
        "title": "Verify admin IP is configured on OS-only nodes",
        "component": "Minimal OS network identity",
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
    "lifecycle_provision_verify": {
        "id": "ORCH_NFT_014",
        "title": "Verify provision and node state after fresh-install lifecycle",
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
