# Orchestrator Functional Verification Tests

The FVT tree follows the supported Orchestrator lifecycle. Each lifecycle owns
one execution case and one or more independent verification suites. Test files
contain case selection and ordering; reusable behavior belongs in
`library/functions`, messages in `library/messages`, and immutable commands
and IDs in `library/vars`.

## Test-case identification

IDs use this format:

```text
ORCH_FVT_<LIFECYCLE>_<TYPE><NUMBER>
```

- `E` identifies a product execution case.
- `V` identifies a verification case.
- IDs and titles are registered centrally in
  `library/vars/test_case_vars.py`.
- File names and pytest function names may change without changing a public
  test-case ID.

## Lifecycle registry

| Lifecycle | Execution ID | Verification IDs | Suites |
|---|---|---|---|
| `precheck` | `ORCH_FVT_PRECHECK_E001` | `V001`–`V012`, `V100`–`V109` | `environment`, `storage`, `dependencies`, `inputs`, `oim_readiness` |
| `prepare` | `ORCH_FVT_PREPARE_E001` | `V001`–`V013` | `openchami`, `network`, `openldap` |
| `provision` | `ORCH_FVT_PROVISION_E001` | `V001`–`V008` | `openchami` |
| `pxeboot` | `ORCH_FVT_PXEBOOT_E001` | `V001`–`V103`, `V200`–`V299`, `V400`–`V431`, `V501`–`V518` | `connectivity`, `cloudinit`, `kubernetes_*`, `slurm_*`, `slurm_dcgm`, `additional_cloud_init`, `powervault` |
| `cleanup` | `ORCH_FVT_CLEANUP_E001` | `V001`–`V006` | `openchami`, `openldap`, `slurm`, `kubernetes`, `artifacts`, `credentials` |

The detailed registry below is the authoritative inventory. Its `Order`
column defines execution sequence independently of the stable public test-case
IDs, so files and test functions can be reorganized without renumbering IDs.

## Effective execution order

The default non-cleanup lifecycle is:

```text
precheck -> prepare -> provision -> pxeboot
```

Within a lifecycle, pytest follows each case's `order` marker. This preserves
dependency order: connectivity and cloud-init before workload clusters,
cluster health before temporary jobs, and non-disruptive checks before any
explicit recovery operation.

PXE capability suites are flat directories. Kubernetes runs as
`kubernetes_cluster`, `kubernetes_etcd`, `kubernetes_storage`, and
`kubernetes_recovery`. Slurm runs as `slurm_cluster`, `slurm_jobs`,
`slurm_ldap`, `slurm_gpu`, `slurm_openmpi`, `slurm_ucx`,
`slurm_infiniband`, `slurm_recovery`, `slurm_apptainer`, and `slurm_dcgm`.

Cleanup is never part of an implicit lifecycle run.

## Precheck test cases

These cases execute and verify OIM identity, selected storage, dependency
outputs, required inputs, boot artifacts, and published repositories.

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 0 | `ORCH_FVT_PRECHECK_E001` | `test_deploy_precheck` | `root` | `deploy`, `sanity` | Run ``orchestrator.yml --tags precheck`` exactly once. | The selected Orchestrator lifecycle exits successfully. |
| 1 | `ORCH_FVT_PRECHECK_V001` | `test_precheck_hostname_domain` | `environment` | `sanity` | Require the host identity to match omnia.env exactly. | Every required item satisfies the stated condition. |
| 2 | `ORCH_FVT_PRECHECK_V002` | `test_precheck_admin_ipv4` | `environment` | `sanity` | Require the configured administrative IPv4 on a global interface. | Every required item satisfies the stated condition. |
| 3 | `ORCH_FVT_PRECHECK_V003` | `test_precheck_nfs_servers` | `storage` | `sanity` | Require every mapping-selected NFS server to answer ICMP from the OIM. | Every required item satisfies the stated condition. |
| 4 | `ORCH_FVT_PRECHECK_V004` | `test_precheck_dependencies` | `dependencies` | `sanity` | Require both configured/default dependency outputs to be usable. | Every required item satisfies the stated condition. |
| 5 | `ORCH_FVT_PRECHECK_V005` | `test_precheck_inputs` | `inputs` | `sanity` | Require every source-selected Orchestrator input to be non-empty. | Every required item satisfies the stated condition. |
| 6 | `ORCH_FVT_PRECHECK_V006` | `test_precheck_s3_artifacts` | `dependencies` | `sanity` | Require every kernel, initrd, and rootfs artifact to be reachable. | Every required item satisfies the stated condition. |
| 7 | `ORCH_FVT_PRECHECK_V007` | `test_precheck_repositories` | `dependencies` | `sanity` | Require every published RPM and file repository to be reachable. | Every required item satisfies the stated condition. |

The NFS case mirrors the production mount-selection contract. It evaluates
`functional_group_prefix` against mapped functional groups, evaluates
`groups` against mapped PXE `GROUP_NAME` values, and excludes the stock
`vast_storage` entry unless `omnia_config.yml` selects it. Unrelated storage
entries are reported as ignored, not as validated.

### OIM readiness (oim_readiness)

Hardware, network-interface, and prerequisite checks that bring parity with
the Omnia 2.2 automation prerequisite runner. Every check is read-only and
never mutates the target environment. Negative tests use impossible
thresholds or bogus names to validate structured failure reporting.

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 10 | `ORCH_FVT_PRECHECK_V100` | `test_oim_cpu_threshold` | `oim_readiness` | `sanity` | Require OIM CPU core count to meet the configured minimum. | Every required item satisfies the stated condition. |
| 11 | `ORCH_FVT_PRECHECK_V101` | `test_oim_memory_threshold` | `oim_readiness` | `sanity` | Require OIM memory to meet the configured minimum. | Every required item satisfies the stated condition. |
| 12 | `ORCH_FVT_PRECHECK_V102` | `test_oim_disk_threshold` | `oim_readiness` | `sanity` | Require OIM root filesystem to meet the configured minimum. | Every required item satisfies the stated condition. |
| 13 | `ORCH_FVT_PRECHECK_V103` | `test_oim_pxe_nic_present` | `oim_readiness` | `sanity` | Require the configured admin NIC to exist and be UP. | Every required item satisfies the stated condition. |
| 14 | `ORCH_FVT_PRECHECK_V104` | `test_oim_public_nic_present` | `oim_readiness` | `sanity` | Require the public/default-route NIC to exist and be UP. | Every required item satisfies the stated condition. |
| 15 | `ORCH_FVT_PRECHECK_V105` | `test_oim_pxe_nic_ipv4` | `oim_readiness` | `sanity` | Require the admin NIC to carry the configured IPv4 address. | Every required item satisfies the stated condition. |
| 16 | `ORCH_FVT_PRECHECK_V107` | `test_oim_ssh_preflight` | `oim_readiness` | `sanity` | Require passwordless SSH from OIM to a mapped target node. | Every required item satisfies the stated condition. |
| 18 | `ORCH_FVT_PRECHECK_V108` | `test_oim_internet_reachability` | `oim_readiness` | `sanity` | Require internet reachability when not in air-gapped mode. | Every required item satisfies the stated condition. |
| 19 | `ORCH_FVT_PRECHECK_V109` | `test_oim_os_version` | `oim_readiness` | `sanity` | Require the OIM OS to match the expected distribution and version. | Every required item satisfies the stated condition. |
| 20 | `ORCH_FVT_PRECHECK_V100` | `test_neg_cpu_below_threshold` | `oim_readiness` | `sanity`, `negative` | Detect failure when CPU threshold exceeds actual cores. | The expected rejection occurs and no prohibited state is accepted. |
| 21 | `ORCH_FVT_PRECHECK_V101` | `test_neg_memory_below_threshold` | `oim_readiness` | `sanity`, `negative` | Detect failure when memory threshold exceeds actual RAM. | The expected rejection occurs and no prohibited state is accepted. |
| 22 | `ORCH_FVT_PRECHECK_V102` | `test_neg_disk_below_threshold` | `oim_readiness` | `sanity`, `negative` | Detect failure when disk threshold exceeds actual capacity. | The expected rejection occurs and no prohibited state is accepted. |
| 23 | `ORCH_FVT_PRECHECK_V103` | `test_neg_pxe_nic_missing` | `oim_readiness` | `sanity`, `negative` | Detect failure when a nonexistent NIC name is checked. | The expected rejection occurs and no prohibited state is accepted. |
| 24 | `ORCH_FVT_PRECHECK_V105` | `test_neg_pxe_public_overlap` | `oim_readiness` | `sanity`, `negative` | Detect overlap when PXE NIC is forced to match the public NIC. | The expected rejection occurs and no prohibited state is accepted. |
| 25 | `ORCH_FVT_PRECHECK_V108` | `test_neg_internet_airgapped` | `oim_readiness` | `sanity`, `negative` | Verify air-gapped mode passes even without internet. | The expected rejection occurs and no prohibited state is accepted. |
| 27 | `ORCH_FVT_PRECHECK_V107` | `test_neg_ssh_unreachable_target` | `oim_readiness` | `sanity`, `negative` | Detect SSH failure to a bogus target address. | The expected rejection occurs and no prohibited state is accepted. |
| 28 | `ORCH_FVT_PRECHECK_V109` | `test_neg_os_version_mismatch` | `oim_readiness` | `sanity`, `negative` | Detect failure when expected OS version does not match actual. | The expected rejection occurs and no prohibited state is accepted. |

Thresholds default to CPU >= 4, RAM >= 16 GB, root disk >= 100 GB (matching
Omnia 2.2 automation defaults). Negative tests set impossible thresholds to
validate structured failure messages without mutating the environment.

## Prepare test cases

These cases verify the infrastructure created by the `prepare` lifecycle.

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 0 | `ORCH_FVT_PREPARE_E001` | `test_deploy_prepare` | `root` | `deploy`, `sanity` | Run ``orchestrator.yml --tags prepare``. | The selected Orchestrator lifecycle exits successfully. |
| 1 | `ORCH_FVT_PREPARE_V001` | `test_openchami_containers_running` | `openchami` | `sanity` | Verify all long-running OpenCHAMI containers. | All stated checks pass for every applicable target. |
| 2 | `ORCH_FVT_PREPARE_V002` | `test_openchami_services_ready` | `openchami` | `sanity` | Verify OpenCHAMI units and successful SMD initialization. | All stated checks pass for every applicable target. |
| 3 | `ORCH_FVT_PREPARE_V003` | `test_openchami_apis_ready` | `openchami` | `functional`, `sanity` | Verify the authenticated SMD, Boot and Metadata APIs. | All stated checks pass for every applicable target. |
| 4 | `ORCH_FVT_PREPARE_V004` | `test_openchami_persistent_storage_and_tls` | `openchami` | `sanity` | Verify persistent data volumes and HAProxy certificates. | All stated checks pass for every applicable target. |
| 5 | `ORCH_FVT_PREPARE_V005` | `test_openchami_packages_and_artifacts` | `openchami` | `sanity` | Verify installed packages and generated configuration files. | All stated checks pass for every applicable target. |
| 6 | `ORCH_FVT_PREPARE_V006` | `test_firewall_and_podman_network_policy` | `network` | `sanity` | Verify OpenCHAMI ports and trusted Podman interfaces. | All stated checks pass for every applicable target. |
| 7 | `ORCH_FVT_PREPARE_V007` | `test_coredhcp_and_coredns_configuration` | `network` | `functional`, `sanity` | Verify rendered DHCP/DNS configuration and additional routes. | All stated checks pass for every applicable target. |
| 8 | `ORCH_FVT_PREPARE_V008` | `test_external_ldap_proxy` | `openldap` | `openldap`, `sanity` | Reconcile and verify the explicitly enabled LDAP meta-proxy. | Reconciliation is idempotent and every postcondition passes. |
| 9 | `ORCH_FVT_PREPARE_V009` | `test_openldap_runtime` | `openldap` | `openldap`, `sanity` | Verify the enabled service and container are healthy. | All stated checks pass for every applicable target. |
| 10 | `ORCH_FVT_PREPARE_V010` | `test_openldap_artifacts` | `openldap` | `openldap`, `sanity` | Verify configuration modes, syntax and TLS lifetime. | All stated checks pass for every applicable target. |
| 11 | `ORCH_FVT_PREPARE_V011` | `test_openldap_endpoint` | `openldap` | `functional`, `openldap`, `sanity` | Verify the local LDAP endpoint and published listeners. | All stated checks pass for every applicable target. |
| 12 | `ORCH_FVT_PREPARE_V012` | `test_external_ldap_backend` | `openldap` | `functional`, `openldap`, `sanity` | Verify external LDAP reachability from the omnia_auth container. | All stated checks pass for every applicable target. |
| 13 | `ORCH_FVT_PREPARE_V013` | `test_postgresql_readiness` | `openchami` | `functional`, `sanity` | Verify PostgreSQL and its required SMD database contract. | All stated checks pass for every applicable target. |

OpenLDAP runtime, artifacts, and local endpoint checks follow authoritative
generated `openldap_support` state. External LDAP V008 and V012 additionally
require `validate_external_ldap: true`; otherwise they skip before mutation.
`configure_external_ldap` controls only whether V008 may reconcile
`slapd.conf`. With validation enabled and reconciliation disabled, V008
checks the existing deployed proxy and reports mismatches as failures.

## Provision test cases

These controller-side cases compare generated reports and live OpenCHAMI
state with the active PXE mapping.

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 100 | `ORCH_FVT_PROVISION_E001` | `test_deploy_provision` | `root` | `deploy`, `sanity` | Run ``orchestrator.yml --tags provision``. | The selected Orchestrator lifecycle exits successfully. |
| 101 | `ORCH_FVT_PROVISION_V001` | `test_provision_reports` | `openchami` | `sanity` | Verify the provision report and generated inventory contracts. | All stated checks pass for every applicable target. |
| 102 | `ORCH_FVT_PROVISION_V002` | `test_smd_identity` | `openchami` | `sanity` | Verify XNAME, administrative MAC, and IP identity in SMD. | All stated checks pass for every applicable target. |
| 103 | `ORCH_FVT_PROVISION_V003` | `test_smd_group_membership` | `openchami` | `sanity` | Verify expected groups and reject competing cloud-init groups. | All stated checks pass for every applicable target. |
| 104 | `ORCH_FVT_PROVISION_V004` | `test_boot_service_configurations` | `openchami` | `sanity` | Verify BootConfigurations and their mapped administrative MACs. | All stated checks pass for every applicable target. |
| 105 | `ORCH_FVT_PROVISION_V005` | `test_boot_service_node_identity` | `openchami` | `sanity` | Verify synchronized XNAME-to-bootMac records. | All stated checks pass for every applicable target. |
| 106 | `ORCH_FVT_PROVISION_V006` | `test_metadata_service_groups` | `openchami` | `sanity` | Verify one usable cloud-init template per functional group. | All stated checks pass for every applicable target. |
| 107 | `ORCH_FVT_PROVISION_V007` | `test_metadata_service_instances` | `openchami` | `sanity` | Verify unique per-node hostname metadata. | All stated checks pass for every applicable target. |
| 108 | `ORCH_FVT_PROVISION_V008` | `test_coredhcp_and_coredns_inventory` | `openchami` | `sanity` | Verify the SMD identity records consumed by CoreDHCP/CoreDNS. | All stated checks pass for every applicable target. |
| 109 | `ORCH_FVT_PROVISION_V009` | `test_boot_image_identity` | `openchami` | `sanity` | Verify Boot Service kernel/initrd paths match build_status.yml per functional group. | All stated checks pass for every applicable target. |
| 110 | `ORCH_FVT_PROVISION_V010` | `test_boot_image_architecture` | `openchami` | `sanity` | Verify build_status.yml architecture keys are consistent with functional group name suffixes. | All stated checks pass for every applicable target. |

Provision verification is read-only. It resolves XNAMEs from live SMD
interfaces and groups and obtains fresh OpenCHAMI credentials for API reads.

## PXE post-boot test cases

The following tables are in effective pytest `order` sequence. Optional role
and feature cases skip only when the active mapping or catalog proves that the
target is not applicable. Negative cases pass only when the invalid operation
is rejected. Reboot and scheduler-state cases require their explicit markers.

### PXE lifecycle execution

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 200 | `ORCH_FVT_PXEBOOT_E001` | `test_deploy_pxeboot` | `root` | `deploy`, `sanity` | Run ``orchestrator.yml --tags pxeboot``. | The selected Orchestrator lifecycle exits successfully. |

### Connectivity

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 201 | `ORCH_FVT_PXEBOOT_V001` | `test_node_ping` | `connectivity` | `connectivity`, `sanity` | Verify ping from the OIM to every mapped administrative IP. | All stated checks pass for every applicable target. |
| 202 | `ORCH_FVT_PXEBOOT_V002` | `test_node_ssh` | `connectivity` | `connectivity`, `sanity` | Verify passwordless root SSH from the OIM to every mapped node. | All stated checks pass for every applicable target. |
| 203 | `ORCH_FVT_PXEBOOT_V003` | `test_node_hostname_ssh` | `connectivity` | `connectivity`, `sanity` | Verify mapped hostnames resolve and support passwordless root SSH. | All stated checks pass for every applicable target. |

### Cloud-init

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 204 | `ORCH_FVT_PXEBOOT_V004` | `test_node_cloud_init` | `cloudinit` | `cloudinit`, `sanity` | Verify PXE report freshness and direct cloud-init JSON state. | All stated checks pass for every applicable target. |

### Architecture and OS identity

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 298 | `ORCH_FVT_PXEBOOT_V097` | `test_node_architecture` | `connectivity` | `connectivity`, `sanity` | Verify each node's live architecture matches its functional group name suffix. | All stated checks pass for every applicable target. |
| 299 | `ORCH_FVT_PXEBOOT_V098` | `test_node_os_version` | `connectivity` | `connectivity`, `sanity` | Verify each node's live OS version matches the expected image from build_status.yml. | All stated checks pass for every applicable target. |

Cloud-init is accepted only when its structured status satisfies the
product contract. A generated script success message is not treated as
authoritative cloud-init state.

### Kubernetes

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 205 | `ORCH_FVT_PXEBOOT_V005` | `test_kubernetes_nodes` | `kubernetes_cluster` | `kubernetes`, `sanity` | Verify mapped Kubernetes membership and Ready state. | All stated checks pass for every applicable target. |
| 206 | `ORCH_FVT_PXEBOOT_V006` | `test_kubernetes_node_services` | `kubernetes_cluster` | `kubernetes`, `sanity` | Verify required services on every Kubernetes role. | All stated checks pass for every applicable target. |
| 207 | `ORCH_FVT_PXEBOOT_V007` | `test_kubernetes_version_compatibility` | `kubernetes_cluster` | `kubernetes`, `sanity` | Verify Kubernetes, kubeadm, and CRI-O version alignment. | All stated checks pass for every applicable target. |
| 208 | `ORCH_FVT_PXEBOOT_V101` | `test_kubernetes_configured_versions` | `kubernetes_cluster` | `kubernetes`, `sanity` | Compare deployed Kubernetes components with the selected catalog version. | Kubernetes components match the configured version and CRI-O matches its major/minor release. |
| 209 | `ORCH_FVT_PXEBOOT_V008` | `test_kubernetes_control_plane` | `kubernetes_cluster` | `kubernetes`, `sanity` | Verify API readiness and the configured control plane. | All stated checks pass for every applicable target. |
| 210 | `ORCH_FVT_PXEBOOT_V009` | `test_kubernetes_system_pods` | `kubernetes_cluster` | `kubernetes`, `sanity` | Verify required system, CNI, storage, and HA workloads. | All stated checks pass for every applicable target. |
| 211 | `ORCH_FVT_PXEBOOT_V010` | `test_kubernetes_virtual_ip` | `kubernetes_cluster` | `kubernetes`, `sanity` | Verify exactly one owner for the configured Kubernetes VIP. | All stated checks pass for every applicable target. |
| 212 | `ORCH_FVT_PXEBOOT_V011` | `test_kubernetes_workload_scheduling` | `kubernetes_cluster` | `functional`, `kubernetes`, `sanity` | Create, verify, and remove an isolated scheduling probe. | The isolated probe becomes ready, satisfies the stated contract, and is removed. |
| 213 | `ORCH_FVT_PXEBOOT_V012` | `test_kubernetes_etcd_health` | `kubernetes_etcd` | `kubernetes`, `sanity` | Verify health for all etcd endpoints. | All stated checks pass for every applicable target. |
| 214 | `ORCH_FVT_PXEBOOT_V013` | `test_kubernetes_etcd_topology` | `kubernetes_etcd` | `kubernetes`, `sanity` | Verify etcd membership, leader election, and raft consistency. | All stated checks pass for every applicable target. |
| 215 | `ORCH_FVT_PXEBOOT_V014` | `test_kubernetes_local_etcd` | `kubernetes_etcd` | `kubernetes`, `sanity` | Verify each control plane has the configured etcd mount. | All stated checks pass for every applicable target. |
| 216 | `ORCH_FVT_PXEBOOT_V015` | `test_kubernetes_local_etcd_integrity` | `kubernetes_etcd` | `kubernetes`, `sanity` | Verify disk selection, ext4 label, UUID fstab, and boot persistence. | All stated checks pass for every applicable target. |
| 217 | `ORCH_FVT_PXEBOOT_V102` | `test_kubernetes_local_etcd_provisioning` | `kubernetes_etcd` | `kubernetes`, `sanity` | Verify GPT selection and local-etcd scripts, logs, and selected disk. | Every enabled control plane satisfies the provisioning contract. |
| 218 | `ORCH_FVT_PXEBOOT_V016` | `test_kubernetes_storage` | `kubernetes_storage` | `kubernetes`, `sanity` | Verify configured NFS and PowerScale storage objects. | All stated checks pass for every applicable target. |
| 219 | `ORCH_FVT_PXEBOOT_V017` | `test_kubernetes_default_storage_class` | `kubernetes_storage` | `kubernetes`, `sanity` | Verify exactly one expected default StorageClass. | All stated checks pass for every applicable target. |
| 220 | `ORCH_FVT_PXEBOOT_V018` | `test_kubernetes_snapshot_controller` | `kubernetes_storage` | `kubernetes`, `sanity` | Verify PowerScale snapshot components when configured. | All stated checks pass for every applicable target. |
| 221 | `ORCH_FVT_PXEBOOT_V103` | `test_kubernetes_nfs_provisioner_contract` | `kubernetes_storage` | `kubernetes`, `sanity` | Compare the NFS StorageClass, provisioner backend, and node mounts with active configuration. | Every NFS contract field and mapped-node mount matches the selected storage entry. |
| 222 | `ORCH_FVT_PXEBOOT_V019` | `test_kubernetes_nfs_dynamic_provisioning` | `kubernetes_storage` | `functional`, `kubernetes`, `sanity` | Create and remove an isolated NFS-backed workload. | All stated checks pass for every applicable target. |
| 223 | `ORCH_FVT_PXEBOOT_V020` | `test_kubernetes_csi_dynamic_provisioning` | `kubernetes_storage` | `functional`, `kubernetes`, `sanity` | Create and remove an isolated PowerScale-backed workload. | All stated checks pass for every applicable target. |
| 224 | `ORCH_FVT_PXEBOOT_V021` | `test_kubernetes_local_etcd_recovery` | `kubernetes_recovery` | `disruptive`, `kubernetes`, `reboot` | Reboot a control plane and prove its local-etcd UUID is preserved. | The node returns within the bounded wait and every stated post-reboot check passes. |
| 225 | `ORCH_FVT_PXEBOOT_V022` | `test_kubernetes_control_plane_recovery` | `kubernetes_recovery` | `disruptive`, `kubernetes`, `reboot` | Reboot the VIP owner and verify control-plane recovery. | The node returns within the bounded wait and every stated post-reboot check passes. |

Temporary Kubernetes resources use unique namespaces and are removed by
the creating test. CSI, snapshot, and local-etcd checks are selected from
the active configuration.

### Slurm

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 226 | `ORCH_FVT_PXEBOOT_V023` | `test_slurm_membership` | `slurm_cluster` | `non_disruptive`, `sanity`, `slurm` | Verify mapped membership, healthy state, and basic hardware fields. | All stated checks pass for every applicable target. |
| 227 | `ORCH_FVT_PXEBOOT_V024` | `test_slurm_scheduler` | `slurm_cluster` | `non_disruptive`, `sanity`, `slurm` | Verify mapped compute nodes have healthy, available partitions. | All stated checks pass for every applicable target. |
| 228 | `ORCH_FVT_PXEBOOT_V025` | `test_slurm_services` | `slurm_cluster` | `non_disruptive`, `sanity`, `slurm` | Verify role and feature-specific Slurm services. | All stated checks pass for every applicable target. |
| 229 | `ORCH_FVT_PXEBOOT_V026` | `test_slurm_cross_node_ssh` | `slurm_cluster` | `non_disruptive`, `sanity`, `slurm` | Verify every mapped Slurm role can reach every peer over root SSH. | All stated checks pass for every applicable target. |
| 230 | `ORCH_FVT_PXEBOOT_V027` | `test_slurm_configless_mode` | `slurm_cluster` | `non_disruptive`, `sanity`, `slurm` | Verify configless controller access and expected cluster identity. | All stated checks pass for every applicable target. |
| 231 | `ORCH_FVT_PXEBOOT_V028` | `test_slurm_configuration_consistency` | `slurm_cluster` | `non_disruptive`, `sanity`, `slurm` | Compare authoritative Slurm files with every configless client cache. | Every compared value matches its authoritative source. |
| 232 | `ORCH_FVT_PXEBOOT_V029` | `test_slurm_reconfigure` | `slurm_cluster` | `functional`, `non_disruptive`, `sanity`, `slurm` | Reconfigure Slurm and verify membership remains healthy. | All stated checks pass for every applicable target. |
| 233 | `ORCH_FVT_PXEBOOT_V030` | `test_slurm_hardware_discovery` | `slurm_cluster` | `non_disruptive`, `sanity`, `slurm` | Verify runtime hardware matches the configured discovery strategy. | All stated checks pass for every applicable target. |
| 234 | `ORCH_FVT_PXEBOOT_V031` | `test_slurm_custom_configuration` | `slurm_cluster` | `non_disruptive`, `sanity`, `slurm` | Verify custom values, NFS delivery, and effective visibility. | All stated checks pass for every applicable target. |
| 235 | `ORCH_FVT_PXEBOOT_V032` | `test_slurm_control_node_jobs` | `slurm_jobs` | `functional`, `non_disruptive`, `sanity`, `slurm` | Run one targeted job per compute from every Slurm control node. | The operation completes successfully and returns the expected result. |
| 236 | `ORCH_FVT_PXEBOOT_V033` | `test_slurm_login_node_jobs` | `slurm_jobs` | `functional`, `non_disruptive`, `sanity`, `slurm` | Run one targeted job per compute from every mapped login node. | The operation completes successfully and returns the expected result. |
| 237 | `ORCH_FVT_PXEBOOT_V034` | `test_slurm_compiler_node_jobs` | `slurm_jobs` | `functional`, `non_disruptive`, `sanity`, `slurm` | Run one targeted job per compute from every login compiler node. | The operation completes successfully and returns the expected result. |
| 238 | `ORCH_FVT_PXEBOOT_V035` | `test_slurm_concurrent_jobs` | `slurm_jobs` | `functional`, `non_disruptive`, `sanity`, `slurm` | Submit concurrent jobs and verify final accounting state. | The submission completes with the expected final state and output. |
| 239 | `ORCH_FVT_PXEBOOT_V036` | `test_slurm_insufficient_resources` | `slurm_jobs` | `functional`, `negative`, `non_disruptive`, `sanity`, `slurm` | Verify an impossible immediate allocation is rejected. | The expected rejection occurs and no prohibited state is accepted. |
| 240 | `ORCH_FVT_PXEBOOT_V037` | `test_slurm_job_queueing` | `slurm_jobs` | `functional`, `non_disruptive`, `sanity`, `slurm` | Saturate idle computes and verify one follower queues then completes. | The follower is pending under saturation and completes after resources are released. |
| 241 | `ORCH_FVT_PXEBOOT_V038` | `test_slurm_drain_queue_recovery` | `slurm_jobs` | `disruptive`, `sanity`, `scheduler_state`, `slurm` | Drain one compute node, verify queuing, and restore it. | The job queues while the node is drained, then the node is resumed and the job completes. |
| 242 | `ORCH_FVT_PXEBOOT_V039` | `test_slurm_pam_policy` | `slurm_ldap` | `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify SSHD, the PAM module, and pam_slurm_adopt account policy. | All stated checks pass for every applicable target. |
| 243 | `ORCH_FVT_PXEBOOT_V040` | `test_slurm_control_ldap_authentication` | `slurm_ldap` | `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify a valid LDAP password on the Slurm control node. | All stated checks pass for every applicable target. |
| 244 | `ORCH_FVT_PXEBOOT_V041` | `test_slurm_control_ldap_invalid_password` | `slurm_ldap` | `negative`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify an invalid LDAP password is rejected on the control node. | The expected rejection occurs and no prohibited state is accepted. |
| 245 | `ORCH_FVT_PXEBOOT_V042` | `test_slurm_login_ldap_authentication` | `slurm_ldap` | `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify a valid LDAP password on every mapped login node. | All stated checks pass for every applicable target. |
| 246 | `ORCH_FVT_PXEBOOT_V043` | `test_slurm_login_ldap_invalid_password` | `slurm_ldap` | `negative`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify an invalid LDAP password is rejected on every login node. | The expected rejection occurs and no prohibited state is accepted. |
| 247 | `ORCH_FVT_PXEBOOT_V044` | `test_slurm_compiler_ldap_authentication` | `slurm_ldap` | `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify a valid LDAP password on every login-compiler node. | All stated checks pass for every applicable target. |
| 248 | `ORCH_FVT_PXEBOOT_V045` | `test_slurm_compiler_ldap_invalid_password` | `slurm_ldap` | `negative`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify invalid LDAP passwords are rejected on login-compiler nodes. | The expected rejection occurs and no prohibited state is accepted. |
| 249 | `ORCH_FVT_PXEBOOT_V046` | `test_slurm_pam_no_job_access` | `slurm_ldap` | `negative`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify LDAP compute login is denied without an active job. | The expected rejection occurs and no prohibited state is accepted. |
| 250 | `ORCH_FVT_PXEBOOT_V047` | `test_slurm_invalid_ldap_identity` | `slurm_ldap` | `negative`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify a generated missing directory identity is rejected. | The expected rejection occurs and no prohibited state is accepted. |
| 251 | `ORCH_FVT_PXEBOOT_V048` | `test_slurm_control_ldap_jobs` | `slurm_ldap` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Submit and complete an LDAP-owned job from the control node. | The submission completes with the expected final state and output. |
| 252 | `ORCH_FVT_PXEBOOT_V049` | `test_slurm_control_pam_job_access` | `slurm_ldap` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify control-submitted PAM access during and after a job. | All stated checks pass for every applicable target. |
| 253 | `ORCH_FVT_PXEBOOT_V050` | `test_slurm_login_ldap_jobs` | `slurm_ldap` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Submit and complete an LDAP-owned job from every login node. | The submission completes with the expected final state and output. |
| 254 | `ORCH_FVT_PXEBOOT_V051` | `test_slurm_login_pam_job_access` | `slurm_ldap` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify login-node PAM access during and after a job. | All stated checks pass for every applicable target. |
| 255 | `ORCH_FVT_PXEBOOT_V052` | `test_slurm_compiler_ldap_jobs` | `slurm_ldap` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Submit an LDAP-owned job from every login-compiler node. | The submission completes with the expected final state and output. |
| 256 | `ORCH_FVT_PXEBOOT_V053` | `test_slurm_compiler_pam_job_access` | `slurm_ldap` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify login-compiler PAM access during and after a job. | All stated checks pass for every applicable target. |
| 257 | `ORCH_FVT_PXEBOOT_V054` | `test_slurm_gpu_inventory` | `slurm_gpu` | `non_disruptive`, `sanity`, `slurm` | Verify NVIDIA runtime state on scheduler-declared GPU nodes. | All stated checks pass for every applicable target. |
| 258 | `ORCH_FVT_PXEBOOT_V055` | `test_slurm_gpu_job` | `slurm_gpu` | `functional`, `non_disruptive`, `sanity`, `slurm` | Allocate a GPU through Slurm and query the device. | The allocation succeeds and the requested device is visible. |
| 259 | `ORCH_FVT_PXEBOOT_V056` | `test_slurm_gpu_memory_stress` | `slurm_gpu` | `functional`, `non_disruptive`, `sanity`, `slurm` | Compile and run a bounded GPU memory workload through Slurm. | Compilation and bounded workload execution complete successfully. |
| 260 | `ORCH_FVT_PXEBOOT_V057` | `test_slurm_openmpi_installation` | `slurm_openmpi` | `non_disruptive`, `sanity`, `slurm` | Verify OpenMPI discovery and version on every compute node. | All stated checks pass for every applicable target. |
| 261 | `ORCH_FVT_PXEBOOT_V058` | `test_slurm_openmpi_job` | `slurm_openmpi` | `functional`, `non_disruptive`, `sanity`, `slurm` | Run an OpenMPI-backed job when OpenMPI is configured. | The operation completes successfully and returns the expected result. |
| 262 | `ORCH_FVT_PXEBOOT_V059` | `test_slurm_ucx_transport` | `slurm_ucx` | `non_disruptive`, `sanity`, `slurm` | Verify UCX exposes an InfiniBand-capable transport. | All stated checks pass for every applicable target. |
| 263 | `ORCH_FVT_PXEBOOT_V060` | `test_slurm_infiniband_configuration` | `slurm_infiniband` | `non_disruptive`, `sanity`, `slurm` | Verify mapped IB interface, address, prefix, link, MTU, and OFED. | All stated checks pass for every applicable target. |
| 264 | `ORCH_FVT_PXEBOOT_V061` | `test_slurm_infiniband_connectivity` | `slurm_infiniband` | `non_disruptive`, `sanity`, `slurm` | Verify every mapped IB endpoint can reach every mapped peer. | All stated checks pass for every applicable target. |
| 265 | `ORCH_FVT_PXEBOOT_V062` | `test_slurm_cluster_recovery` | `slurm_recovery` | `disruptive`, `functional`, `reboot`, `slurm` | Reboot mapped Slurm nodes and verify scheduler and workload recovery. | The node returns within the bounded wait and every stated post-reboot check passes. |

Login and login-compiler cases skip before credential loading when the
corresponding role is absent. Feature checks use only catalog layers
selected by mapped functional groups.

### Slurm Apptainer

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 266 | `ORCH_FVT_PXEBOOT_V063` | `test_apptainer_runtime` | `slurm_apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify the Apptainer executable and version on every compute node. | All stated checks pass for every applicable target. |
| 267 | `ORCH_FVT_PXEBOOT_V064` | `test_apptainer_shared_artifacts` | `slurm_apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify shared image directories and downloader artifacts. | All stated checks pass for every applicable target. |
| 268 | `ORCH_FVT_PXEBOOT_V065` | `test_apptainer_pulp_policy` | `slurm_apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify the generated downloader uses only the configured Pulp source. | All stated checks pass for every applicable target. |
| 269 | `ORCH_FVT_PXEBOOT_V066` | `test_apptainer_shared_storage` | `slurm_apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify /hpc_tools is a shared mounted filesystem on every compute. | All stated checks pass for every applicable target. |
| 270 | `ORCH_FVT_PXEBOOT_V067` | `test_apptainer_download` | `slurm_apptainer` | `apptainer`, `functional`, `image_download`, `non_disruptive`, `sanity` | Run the deployed downloader and require at least one usable SIF. | The operation completes successfully and returns the expected result. |
| 271 | `ORCH_FVT_PXEBOOT_V068` | `test_apptainer_download_idempotency` | `slurm_apptainer` | `apptainer`, `functional`, `image_download`, `non_disruptive`, `sanity` | Rerun the downloader and verify existing image metadata is unchanged. | The repeated operation succeeds without changing protected state. |
| 272 | `ORCH_FVT_PXEBOOT_V069` | `test_apptainer_download_memory` | `slurm_apptainer` | `apptainer`, `functional`, `image_download`, `non_disruptive`, `sanity` | Run the downloader and enforce a bounded peak resident-memory use. | The operation completes successfully and returns the expected result. |
| 273 | `ORCH_FVT_PXEBOOT_V070` | `test_apptainer_image_inventory` | `slurm_apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify every compute sees one consistent non-empty SIF inventory. | All stated checks pass for every applicable target. |
| 274 | `ORCH_FVT_PXEBOOT_V071` | `test_apptainer_sif_format` | `slurm_apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify each discovered image is a valid inspectable SIF. | All stated checks pass for every applicable target. |
| 275 | `ORCH_FVT_PXEBOOT_V072` | `test_apptainer_sif_permissions` | `slurm_apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify shared SIF files are non-empty and world-readable. | All stated checks pass for every applicable target. |
| 276 | `ORCH_FVT_PXEBOOT_V073` | `test_apptainer_sif_integrity` | `slurm_apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify the selected SIF has the same checksum on every compute. | All stated checks pass for every applicable target. |
| 277 | `ORCH_FVT_PXEBOOT_V074` | `test_apptainer_ldap_readability` | `slurm_apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify the LDAP test identity can read a shared SIF when enabled. | All stated checks pass for every applicable target. |
| 278 | `ORCH_FVT_PXEBOOT_V075` | `test_apptainer_non_root_execution` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify an unprivileged local identity can execute a shared SIF. | All stated checks pass for every applicable target. |
| 279 | `ORCH_FVT_PXEBOOT_V076` | `test_apptainer_missing_image_contract` | `slurm_apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify the downloader records pull failures and exits non-zero. | The expected rejection occurs and no prohibited state is accepted. |
| 280 | `ORCH_FVT_PXEBOOT_V077` | `test_apptainer_single_node_job` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Run one exact-node container job on every mapped compute. | The operation completes successfully and returns the expected result. |
| 281 | `ORCH_FVT_PXEBOOT_V078` | `test_apptainer_multi_node_job` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Run one container allocation spanning all mapped computes. | The operation completes successfully and returns the expected result. |
| 282 | `ORCH_FVT_PXEBOOT_V079` | `test_apptainer_ldap_job` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Run targeted container jobs as the configured LDAP test identity. | The operation completes successfully and returns the expected result. |
| 283 | `ORCH_FVT_PXEBOOT_V080` | `test_apptainer_concurrent_jobs` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Run bounded concurrent container jobs on distinct computes. | The operation completes successfully and returns the expected result. |
| 284 | `ORCH_FVT_PXEBOOT_V081` | `test_apptainer_invalid_sif` | `slurm_apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify a nonexistent SIF fails through the Slurm execution path. | The expected rejection occurs and no prohibited state is accepted. |
| 285 | `ORCH_FVT_PXEBOOT_V082` | `test_apptainer_restricted_sif` | `slurm_apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify an unprivileged identity cannot execute a mode-0600 SIF. | The expected rejection occurs and no prohibited state is accepted. |
| 286 | `ORCH_FVT_PXEBOOT_V083` | `test_apptainer_nfs_visibility` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify containers can read the shared image path on every compute. | All stated checks pass for every applicable target. |
| 287 | `ORCH_FVT_PXEBOOT_V084` | `test_apptainer_slurm_environment` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify Slurm allocation variables propagate into containers. | All stated checks pass for every applicable target. |
| 288 | `ORCH_FVT_PXEBOOT_V085` | `test_apptainer_job_array` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Submit and wait for a bounded Apptainer Slurm job array. | The submission completes with the expected final state and output. |
| 289 | `ORCH_FVT_PXEBOOT_V086` | `test_apptainer_failure_cleanup` | `slurm_apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify a failed image launch leaves no matching runtime process. | The expected rejection occurs and no prohibited state is accepted. |
| 290 | `ORCH_FVT_PXEBOOT_V087` | `test_apptainer_gpu_access` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify scheduler-declared GPU nodes expose GPUs in the container. | All stated checks pass for every applicable target. |
| 291 | `ORCH_FVT_PXEBOOT_V088` | `test_apptainer_gpu_count` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify each container sees the same GPU count as its host. | All stated checks pass for every applicable target. |
| 292 | `ORCH_FVT_PXEBOOT_V089` | `test_apptainer_cuda_workload` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Execute a bounded NVIDIA device query in each GPU container. | The operation completes successfully and returns the expected result. |
| 293 | `ORCH_FVT_PXEBOOT_V090` | `test_apptainer_gpu_memory` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify the GPU query leaves no material device-memory allocation. | All stated checks pass for every applicable target. |
| 294 | `ORCH_FVT_PXEBOOT_V091` | `test_apptainer_infiniband` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify mapped compute nodes expose InfiniBand devices in containers. | All stated checks pass for every applicable target. |
| 295 | `ORCH_FVT_PXEBOOT_V092` | `test_apptainer_reboot_storage` | `slurm_apptainer` | `apptainer`, `disruptive`, `reboot` | Reboot one compute and verify the shared mount and SIF checksum. | The node returns within the bounded wait and every stated post-reboot check passes. |
| 296 | `ORCH_FVT_PXEBOOT_V093` | `test_apptainer_reboot_job` | `slurm_apptainer` | `apptainer`, `disruptive`, `reboot` | Run an exact-node container job after the authorized reboot. | The node returns within the bounded wait and every stated post-reboot check passes. |
| 297 | `ORCH_FVT_PXEBOOT_V094` | `test_apptainer_reboot_artifacts` | `slurm_apptainer` | `apptainer`, `disruptive`, `reboot` | Verify downloader artifacts and policy after the authorized reboot. | The node returns within the bounded wait and every stated post-reboot check passes. |

Image download has a 20-minute ceiling with polling progress every 20
seconds. The reboot cases share one reboot state instead of rebooting the
same compute node independently for each postcondition.

### Slurm HPC Benchmarks

|| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
||---:|---|---|---|---|---|---|
|| 331 | `ORCH_FVT_PXEBOOT_V200` | `test_hpc_benchmarks_json_declaration` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify benchmark_tools.list JSON syntax and required fields. | All stated checks pass for every applicable target. |
|| 332 | `ORCH_FVT_PXEBOOT_V201` | `test_hpc_benchmarks_nfs_accessibility` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify Pulp server reachability from a compute node. | All stated checks pass for every applicable target. |
|| 333 | `ORCH_FVT_PXEBOOT_V202` | `test_hpc_benchmarks_local_repo_sync` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify offline repo sync status on the OIM. | All stated checks pass for every applicable target. |
|| 334 | `ORCH_FVT_PXEBOOT_V203` | `test_hpc_benchmarks_tools_dir_creation` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify /hpc_tools directory structure on compute nodes. | All stated checks pass for every applicable target. |
|| 335 | `ORCH_FVT_PXEBOOT_V204` | `test_hpc_benchmarks_post_staging_validation` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify staged tools match benchmark_tools.list. | All stated checks pass for every applicable target. |
|| 336 | `ORCH_FVT_PXEBOOT_V205` | `test_hpc_benchmarks_per_tool_staging_report` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify per-tool staging report markers and content. | All stated checks pass for every applicable target. |
|| 337 | `ORCH_FVT_PXEBOOT_V206` | `test_hpc_benchmarks_staging_idempotency` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify repeated staging leaves consistent state. | The repeated operation succeeds without changing protected state. |
|| 338 | `ORCH_FVT_PXEBOOT_V207` | `test_hpc_benchmarks_e2e_provisioning` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify full provisioning lifecycle with benchmark tools. | All stated checks pass for every applicable target. |
|| 339 | `ORCH_FVT_PXEBOOT_V208` | `test_hpc_benchmarks_airgapped_staging` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify airgapped staging from offline repo. | All stated checks pass for every applicable target. |
|| 340 | `ORCH_FVT_PXEBOOT_V209` | `test_hpc_benchmarks_source_only_delivery` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify source-only delivery skips framework-owned directories. | All stated checks pass for every applicable target. |
|| 341 | `ORCH_FVT_PXEBOOT_V210` | `test_hpc_benchmarks_rhel_compatibility` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify RHEL 10.x compatibility constraints. | All stated checks pass for every applicable target. |
|| 342 | `ORCH_FVT_PXEBOOT_V211` | `test_hpc_benchmarks_container_first_guidance` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify container image first guidance is correct. | All stated checks pass for every applicable target. |
|| 343 | `ORCH_FVT_PXEBOOT_V212` | `test_hpc_benchmarks_container_image_unaffected` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify container images are not modified by staging. | All stated checks pass for every applicable target. |
|| 344 | `ORCH_FVT_PXEBOOT_V213` | `test_hpc_benchmarks_cuda_flow_unaffected` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify CUDA flow is not modified by staging. | All stated checks pass for every applicable target. |
|| 345 | `ORCH_FVT_PXEBOOT_V214` | `test_hpc_benchmarks_nvhpc_flow_unaffected` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify NVHPC flow is not modified by staging. | All stated checks pass for every applicable target. |
|| 346 | `ORCH_FVT_PXEBOOT_V215` | `test_hpc_benchmarks_openmpi_unaffected` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify OpenMPI flow is not modified by staging. | All stated checks pass for every applicable target. |
|| 347 | `ORCH_FVT_PXEBOOT_V216` | `test_hpc_benchmarks_msr_safe_arch_boundary` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | Verify MSR-safe tools are not staged on x86_64. | All stated checks pass for every applicable target. |
|| 348 | `ORCH_FVT_PXEBOOT_V217` | `test_hpc_benchmarks_artifact_copy` | `slurm_hpc_benchmarks` | `destructive`, `sanity`, `slurm` | Verify artifact copy from OIM to compute nodes. | The operation completes successfully and returns the expected result. |
|| 349 | `ORCH_FVT_PXEBOOT_V218` | `test_hpc_benchmarks_existing_dirs_preserved` | `slurm_hpc_benchmarks` | `destructive`, `sanity`, `slurm` | Verify existing directories are preserved during staging. | The operation completes successfully and returns the expected result. |

### CoreDNS/CoreDHCP

|| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
||---:|---|---|---|---|---|---|
|| 350 | `ORCH_FVT_PXEBOOT_V300` | `test_coredns_container_state` | `coredns_coredhcp` | `non_disruptive`, `sanity` | Verify coresmd containers run with expected image; observe dns_enabled. | All stated checks pass for every applicable target. |
|| 351 | `ORCH_FVT_PXEBOOT_V301` | `test_coredns_forward_resolution` | `coredns_coredhcp` | `non_disruptive`, `sanity` | Query CoreDNS on the OIM for every SMD-mapped node. | All stated checks pass for every applicable target. |
|| 352 | `ORCH_FVT_PXEBOOT_V302` | `test_coredns_reverse_resolution` | `coredns_coredhcp` | `non_disruptive`, `sanity` | Query CoreDNS on the OIM for PTR records. | All stated checks pass for every applicable target. |
|| 353 | `ORCH_FVT_PXEBOOT_V303` | `test_coredhcp_multisubnet_running_image` | `coredns_coredhcp` | `non_disruptive`, `sanity` | Verify the running coresmd-coredhcp image on multi-subnet datasets. | All stated checks pass for every applicable target. |
|| 354 | `ORCH_FVT_PXEBOOT_V304` | `test_dns_compute_resolv_conf` | `coredns_coredhcp` | `non_disruptive`, `sanity` | Verify every mapped compute node has CoreDNS as primary nameserver. | All stated checks pass for every applicable target. |
|| 355 | `ORCH_FVT_PXEBOOT_V305` | `test_dns_compute_forward_getent` | `coredns_coredhcp` | `non_disruptive`, `sanity` | Run `getent hosts` on every compute for SMD-derived candidate FQDNs. | All stated checks pass for every applicable target. |
|| 356 | `ORCH_FVT_PXEBOOT_V306` | `test_coredns_idempotency` | `coredns_coredhcp` | `non_disruptive`, `sanity` | Verify CoreDNS/CoreDHCP state stability (no-drift). | State is identical across the settle window with no spontaneous changes. |
|| 357 | `ORCH_FVT_PXEBOOT_V307` | `test_dns_node_addition_pipeline` | `coredns_coredhcp` | `destructive`, `sanity` | Prove the SMD-to-CoreDNS pipeline resolves every SMD-registered mapped node. | The operation completes successfully and returns the expected result. |
|| 358 | `ORCH_FVT_PXEBOOT_V308` | `test_dns_smd_unreachable_cached_resolution` | `coredns_coredhcp` | `destructive`, `sanity` | Pause the SMD container briefly; require CoreDNS to keep serving cached. | The node returns within the bounded wait and every stated postcondition check passes. |

### PowerVault iSCSI Storage

|| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
||---:|---|---|---|---|---|---|
|| 301 | `ORCH_FVT_PXEBOOT_V400` | `test_powervault_iscsi_service` | `powervault` | `non_disruptive`, `sanity` | Verify iscsid is active and enabled on all PowerVault target nodes. | All stated checks pass for every applicable target. |
|| 302 | `ORCH_FVT_PXEBOOT_V401` | `test_powervault_iscsi_initiator_name` | `powervault` | `non_disruptive`, `sanity` | Verify iSCSI initiator name matches config on all target nodes. | All stated checks pass for every applicable target. |
|| 303 | `ORCH_FVT_PXEBOOT_V402` | `test_powervault_iscsi_discovery` | `powervault` | `non_disruptive`, `sanity` | Verify iSCSI target discovery succeeds from all portal IPs. | All stated checks pass for every applicable target. |
|| 304 | `ORCH_FVT_PXEBOOT_V403` | `test_powervault_iscsi_sessions` | `powervault` | `non_disruptive`, `sanity` | Verify iSCSI sessions are active on all target nodes. | All stated checks pass for every applicable target. |
|| 305 | `ORCH_FVT_PXEBOOT_V404` | `test_powervault_iscsi_startup_automatic` | `powervault` | `non_disruptive`, `sanity` | Verify iSCSI node startup is automatic on all target nodes. | All stated checks pass for every applicable target. |
|| 306 | `ORCH_FVT_PXEBOOT_V405` | `test_powervault_portal_reachability` | `powervault` | `non_disruptive`, `sanity` | Verify iSCSI portal ports are reachable and sessions healthy. | All stated checks pass for every applicable target. |
|| 307 | `ORCH_FVT_PXEBOOT_V406` | `test_powervault_multipath_service` | `powervault` | `non_disruptive`, `sanity` | Verify multipathd is active and enabled on all target nodes. | All stated checks pass for every applicable target. |
|| 308 | `ORCH_FVT_PXEBOOT_V407` | `test_powervault_multipath_device` | `powervault` | `non_disruptive`, `sanity` | Verify multipath device exists and matches volume_id. | All stated checks pass for every applicable target. |
|| 309 | `ORCH_FVT_PXEBOOT_V408` | `test_powervault_multipath_redundancy` | `powervault` | `non_disruptive`, `sanity` | Verify multipath device has multiple paths for redundancy. | All stated checks pass for every applicable target. |
|| 310 | `ORCH_FVT_PXEBOOT_V409` | `test_powervault_gpt_partition` | `powervault` | `non_disruptive`, `sanity` | Verify GPT partition exists on multipath device. | All stated checks pass for every applicable target. |
|| 311 | `ORCH_FVT_PXEBOOT_V410` | `test_powervault_filesystem_type` | `powervault` | `non_disruptive`, `sanity` | Verify filesystem formatted with correct type. | All stated checks pass for every applicable target. |
|| 312 | `ORCH_FVT_PXEBOOT_V411` | `test_powervault_mount_point_directory` | `powervault` | `non_disruptive`, `sanity` | Verify mount point directory exists on all target nodes. | All stated checks pass for every applicable target. |
|| 313 | `ORCH_FVT_PXEBOOT_V412` | `test_powervault_volume_mounted` | `powervault` | `non_disruptive`, `sanity` | Verify PowerVault volume is actively mounted on all target nodes. | All stated checks pass for every applicable target. |
|| 314 | `ORCH_FVT_PXEBOOT_V413` | `test_powervault_mount_options` | `powervault` | `non_disruptive`, `sanity` | Verify mount options applied correctly on all target nodes. | All stated checks pass for every applicable target. |
|| 315 | `ORCH_FVT_PXEBOOT_V414` | `test_powervault_fstab_entry` | `powervault` | `non_disruptive`, `sanity` | Verify persistent fstab entry created on all target nodes. | All stated checks pass for every applicable target. |
|| 316 | `ORCH_FVT_PXEBOOT_V415` | `test_powervault_node_subdirectory` | `powervault` | `non_disruptive`, `sanity` | Verify per-node subdirectory exists under mount point. | All stated checks pass for every applicable target. |
|| 317 | `ORCH_FVT_PXEBOOT_V416` | `test_powervault_bind_mounts` | `powervault` | `non_disruptive`, `sanity` | Verify bind mount targets are active on all target nodes. | All stated checks pass for every applicable target. |
|| 318 | `ORCH_FVT_PXEBOOT_V417` | `test_powervault_bind_fstab_entries` | `powervault` | `non_disruptive`, `sanity` | Verify bind mount fstab entries are persistent on all target nodes. | All stated checks pass for every applicable target. |
|| 319 | `ORCH_FVT_PXEBOOT_V418` | `test_powervault_bind_isolation` | `powervault` | `non_disruptive`, `sanity` | Verify per-node data separation via bind mounts. | All stated checks pass for every applicable target. |
|| 320 | `ORCH_FVT_PXEBOOT_V419` | `test_powervault_functional_group_targeting` | `powervault` | `non_disruptive`, `sanity` | Verify PV mount only on correct functional groups. | All stated checks pass for every applicable target. |
|| 321 | `ORCH_FVT_PXEBOOT_V420` | `test_powervault_multiple_prefix_targeting` | `powervault` | `non_disruptive`, `sanity` | Verify multiple prefixes target all groups correctly. | All stated checks pass for every applicable target. |
|| 322 | `ORCH_FVT_PXEBOOT_V421` | `test_powervault_setup_log` | `powervault` | `non_disruptive`, `sanity` | Verify cloud-init runcmd log exists and shows completion. | All stated checks pass for every applicable target. |
|| 323 | `ORCH_FVT_PXEBOOT_V422` | `test_powervault_cloud_init_groups_dict` | `powervault` | `non_disruptive`, `sanity` | Verify rendered iSCSI setup scripts deployed on target nodes. | All stated checks pass for every applicable target. |
|| 324 | `ORCH_FVT_PXEBOOT_V423` | `test_powervault_no_duplicate_fstab` | `powervault` | `non_disruptive`, `sanity` | Verify no duplicate fstab entries on all target nodes. | All stated checks pass for every applicable target. |
|| 325 | `ORCH_FVT_PXEBOOT_V424` | `test_powervault_all_mounts_writable` | `powervault` | `non_disruptive`, `sanity` | Verify all PV mounts (main + bind) are writable. | All stated checks pass for every applicable target. |
|| 326 | `ORCH_FVT_PXEBOOT_V425` | `test_powervault_permissions` | `powervault` | `non_disruptive`, `sanity` | Verify permissions on mount point match config. | All stated checks pass for every applicable target. |
|| 327 | `ORCH_FVT_PXEBOOT_V426` | `test_powervault_io_write_read` | `powervault` | `non_disruptive`, `sanity` | Verify write-read I/O on PV mount points. | All stated checks pass for every applicable target. |
|| 328 | `ORCH_FVT_PXEBOOT_V427` | `test_powervault_bind_io` | `powervault` | `non_disruptive`, `sanity` | Verify bind-mount I/O reaches PV backing store. | All stated checks pass for every applicable target. |
|| 329 | `ORCH_FVT_PXEBOOT_V428` | `test_powervault_slurm_mandatory_bind_mounts` | `powervault` | `non_disruptive`, `sanity` | Verify /var/lib/mysql and /var/spool/slurm configured as bind targets. | All stated checks pass for every applicable target. |
|| 330 | `ORCH_FVT_PXEBOOT_V429` | `test_powervault_mysql_data_on_mount` | `powervault` | `non_disruptive`, `sanity` | Verify MySQL datadir is on PowerVault mount. | All stated checks pass for every applicable target. |
|| 331 | `ORCH_FVT_PXEBOOT_V430` | `test_neg_powervault_gpt_missing_label` | `powervault` | `negative`, `sanity` | Verify GPT partition check correctly detects missing GPT label. | The expected rejection occurs and no prohibited state is accepted. |
|| 332 | `ORCH_FVT_PXEBOOT_V431` | `test_neg_powervault_duplicate_fstab` | `powervault` | `negative`, `sanity` | Verify duplicate fstab entry detection works correctly. | The expected rejection occurs and no prohibited state is accepted. |

PowerVault tests skip when `powervault_config` is absent or empty in `storage_config.yml`. The suite validates the iSCSI/multipath/bind-mount contract deployed by `setup_iscsi_storage.sh.j2` and functional_group_prefix targeting. Negative tests skip when the infrastructure is in normal operational state (has GPT, no duplicates) to avoid destructive cluster modifications.
### Additional cloud-init

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 300 | `ORCH_FVT_PXEBOOT_V095` | `test_additional_cloud_init_smd_groups` | `additional_cloud_init` | `additional_cloud_init`, `non_disruptive`, `sanity` | Verify SMD groups exist for additional cloud-init configuration. | All stated checks pass for every applicable target. |
| 301 | `ORCH_FVT_PXEBOOT_V096` | `test_additional_cloud_init_metadata_groups` | `additional_cloud_init` | `additional_cloud_init`, `non_disruptive`, `sanity` | Verify metadata-service groups and templates for additional cloud-init. | All stated checks pass for every applicable target. |
| 302 | `ORCH_FVT_PXEBOOT_V099` | `test_additional_cloud_init_write_files` | `additional_cloud_init` | `additional_cloud_init`, `non_disruptive`, `sanity` | Verify write_files entries were applied on provisioned nodes. | All stated checks pass for every applicable target. |
| 303 | `ORCH_FVT_PXEBOOT_V100` | `test_additional_cloud_init_runcmd` | `additional_cloud_init` | `additional_cloud_init`, `non_disruptive`, `sanity` | Verify runcmd entries executed during cloud-init on provisioned nodes. | All stated checks pass for every applicable target. |

Additional cloud-init tests skip automatically when
`additional_cloud_init_config_file` is empty or not configured in
`orchestrator_config.yml`. When enabled, V095 and V096 verify controller-side
state (SMD groups and metadata-service templates); V099 and V100 verify
node-side artifacts (files created by `write_files` and cloud-init completion
confirming `runcmd` execution).

### DCGM / CUDA

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 501 | `ORCH_FVT_PXEBOOT_V501` | `test_dcgm_cuda_validation` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify NVIDIA driver and CUDA toolkit on GPU nodes. | All stated checks pass for every applicable target. |
| 502 | `ORCH_FVT_PXEBOOT_V502` | `test_dcgm_cuda_atomic_lock` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify CUDA toolkit installed via atomic lock. | All stated checks pass for every applicable target. |
| 503 | `ORCH_FVT_PXEBOOT_V503` | `test_dcgm_package_installed` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify datacenter-gpu-manager RPM and DCGM binaries. | All stated checks pass for every applicable target. |
| 504 | `ORCH_FVT_PXEBOOT_V504` | `test_dcgm_daemon_running` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify nvidia-dcgm service is active and enabled. | All stated checks pass for every applicable target. |
| 505 | `ORCH_FVT_PXEBOOT_V505` | `test_dcgm_gpu_discovery` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify dcgmi discovery enumerates GPUs with unique UUIDs. | All stated checks pass for every applicable target. |
| 506 | `ORCH_FVT_PXEBOOT_V506` | `test_dcgm_gpu_metrics` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify dcgmi dmon returns metric samples for each GPU. | All stated checks pass for every applicable target. |
| 507 | `ORCH_FVT_PXEBOOT_V507` | `test_dcgm_cuda_login_compiler` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify CUDA toolkit accessible on login_compiler nodes. | All stated checks pass for every applicable target. |
| 508 | `ORCH_FVT_PXEBOOT_V508` | `test_dcgm_cuda_compute_node` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify CUDA toolkit and driver on compute nodes. | All stated checks pass for every applicable target. |
| 509 | `ORCH_FVT_PXEBOOT_V509` | `test_dcgm_multi_gpu_discovery` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify dcgmi discovery on multi-GPU nodes. | All stated checks pass for every applicable target. |
| 510 | `ORCH_FVT_PXEBOOT_V510` | `test_dcgm_multi_gpu_no_login_compiler` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify GPU nodes work without login_compiler present. | All stated checks pass for every applicable target. |
| 511 | `ORCH_FVT_PXEBOOT_V511` | `test_dcgm_multi_login_compiler_lock` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify CUDA toolkit install uses atomic lock with multiple login_compilers. | All stated checks pass for every applicable target. |
| 512 | `ORCH_FVT_PXEBOOT_V512` | `test_dcgm_toolkit_nfs_storage` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify CUDA toolkit is NFS-mounted and accessible. | All stated checks pass for every applicable target. |
| 513 | `ORCH_FVT_PXEBOOT_V513` | `test_dcgm_rhel_compatibility` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify GPU node OS is a supported RHEL version. | All stated checks pass for every applicable target. |
| 514 | `ORCH_FVT_PXEBOOT_V514` | `test_dcgm_cuda_version_compatibility` | `slurm_dcgm` | `non_disruptive`, `sanity`, `slurm` | Verify CUDA toolkit and DCGM daemon version compatibility. | All stated checks pass for every applicable target. |
| 515 | `ORCH_FVT_PXEBOOT_V515` | `test_dcgm_neg_cuda_prerequisite` | `slurm_dcgm` | `negative`, `non_disruptive`, `sanity`, `slurm` | Verify DCGM deployment requires CUDA prerequisites. | All stated checks pass for every applicable target. |
| 516 | `ORCH_FVT_PXEBOOT_V516` | `test_dcgm_neg_daemon_recovery` | `slurm_dcgm` | `destructive`, `sanity`, `slurm` | Verify DCGM daemon auto-recovery after SIGKILL. | The node returns within the bounded wait and every stated postcondition check passes. |
| 517 | `ORCH_FVT_PXEBOOT_V517` | `test_dcgm_neg_socket_inaccessible` | `slurm_dcgm` | `destructive`, `sanity`, `slurm` | Verify dcgmi returns clear error when socket is removed. | The expected rejection occurs and no prohibited state is accepted. |
| 518 | `ORCH_FVT_PXEBOOT_V518` | `test_dcgm_neg_package_install_failure` | `slurm_dcgm` | `negative`, `non_disruptive`, `sanity`, `slurm` | Verify error handling when DCGM package is unavailable. | The expected rejection occurs and no prohibited state is accepted. |

DCGM tests use platform-aware CUDA toolkit paths resolved via
`omnia_platform.sh`. Compute nodes access the toolkit through the
`/usr/local/cuda` bind mount; the login_compiler accesses it directly
from the NFS-shared platform path. Tests skip when no GPU GRES nodes
are found in the Slurm inventory.

## Cleanup test cases

These cases execute the explicitly selected full cleanup and verify each
component against the configured deletion or preservation policy.

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 0 | `ORCH_FVT_CLEANUP_E001` | `test_deploy_cleanup` | `root` | `deploy`, `destructive`, `sanity` | Run ``orchestrator.yml --tags cleanup`` exactly once. | The selected Orchestrator lifecycle exits successfully. |
| 1 | `ORCH_FVT_CLEANUP_V001` | `test_openchami_removed` | `openchami` | `destructive`, `sanity` | Verify OpenCHAMI runtime, volumes, packages and state are removed. | All stated checks pass for every applicable target. |
| 2 | `ORCH_FVT_CLEANUP_V002` | `test_openldap_removed` | `openldap` | `destructive`, `sanity` | Verify the OpenLDAP proxy service, container and state are removed. | All stated checks pass for every applicable target. |
| 3 | `ORCH_FVT_CLEANUP_V003` | `test_slurm_cleanup` | `slurm` | `destructive`, `sanity` | Verify Slurm's selected data policy and configured storage detachment. | All stated checks pass for every applicable target. |
| 4 | `ORCH_FVT_CLEANUP_V004` | `test_kubernetes_cleanup` | `kubernetes` | `destructive`, `sanity` | Verify Kubernetes's selected data policy and storage detachment. | All stated checks pass for every applicable target. |
| 5 | `ORCH_FVT_CLEANUP_V005` | `test_artifacts_removed_and_inputs_preserved` | `artifacts` | `destructive`, `sanity` | Verify generated state is removed without deleting required inputs. | All stated checks pass for every applicable target. |
| 6 | `ORCH_FVT_CLEANUP_V006` | `test_credentials_follow_selected_policy` | `credentials` | `destructive`, `sanity` | Verify credentials are removed or preserved as selected. | All stated checks pass for every applicable target. |

Cleanup verification follows the configured policy; it does not assume every
input file, credential, or externally managed data path must always be deleted.

## Markers and authorization

| Marker | Purpose |
|---|---|
| `sanity` | Default positive PXE and lifecycle coverage |
| `functional` | Temporary workload or job behavior |
| `openldap`, `connectivity`, `cloudinit`, `kubernetes`, `slurm`, `apptainer`, `additional_cloud_init` | Capability selectors |
| `image_download` | Explicit authorization to modify shared Apptainer image storage |
| `negative` | Expected rejection and error-path behavior |
| `non_disruptive` | Work that does not reboot or drain cluster nodes |
| `disruptive` | Maintenance-window recovery behavior |
| `reboot` | Reboot subset of disruptive cases |
| `scheduler_state` | Scheduler drain/resume subset of disruptive cases |
| `destructive` | Destructive cleanup selector |

A comma is OR; a plus is AND. For example, `sanity,functional` selects either
class, while `slurm+non_disruptive` selects tests carrying both markers.

## Commands

```bash
# Discover current lifecycle and suite names.
./run_validation.sh fvt_orchestrator list

# Execute one lifecycle and verify it.
./run_validation.sh fvt_orchestrator precheck test
./run_validation.sh fvt_orchestrator prepare test
./run_validation.sh fvt_orchestrator provision test
./run_validation.sh fvt_orchestrator pxeboot test

# Read-only focused reruns.
./run_validation.sh fvt_orchestrator precheck verify --suite storage
./run_validation.sh fvt_orchestrator precheck verify --suite oim_readiness
./run_validation.sh fvt_orchestrator prepare verify --suite openchami
./run_validation.sh fvt_orchestrator provision verify --suite openchami
./run_validation.sh fvt_orchestrator pxeboot verify --suite kubernetes_cluster
./run_validation.sh fvt_orchestrator pxeboot verify --suite kubernetes_etcd
./run_validation.sh fvt_orchestrator pxeboot verify --suite kubernetes_storage
./run_validation.sh fvt_orchestrator pxeboot verify --suite slurm_cluster
./run_validation.sh fvt_orchestrator pxeboot verify --suite slurm_ldap
./run_validation.sh fvt_orchestrator pxeboot verify --suite slurm_apptainer
./run_validation.sh fvt_orchestrator pxeboot verify --suite slurm_dcgm
./run_validation.sh fvt_orchestrator pxeboot verify --suite additional_cloud_init

# Marker examples.
./run_validation.sh fvt_orchestrator pxeboot verify --marker sanity,functional
./run_validation.sh fvt_orchestrator pxeboot verify \
  --marker slurm+non_disruptive
./run_validation.sh fvt_orchestrator pxeboot verify \
  --suite slurm_apptainer --marker functional+image_download
./run_validation.sh fvt_orchestrator pxeboot verify \
  --marker disruptive+reboot

# Explicit full cleanup.
./run_validation.sh fvt_orchestrator cleanup test --marker sanity
```

Run `provision test`, `pxeboot test`, or cleanup only against the intended
active project and with the corresponding operational authorization. A failed
execution case prevents the verification phase from being reported as a
successful lifecycle run.
