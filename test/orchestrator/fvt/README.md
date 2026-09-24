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
| `precheck` | `ORCH_FVT_PRECHECK_E001` | `V001`–`V007` | `environment`, `storage`, `dependencies`, `inputs` |
| `prepare` | `ORCH_FVT_PREPARE_E001` | `V001`–`V013` | `openchami`, `network`, `openldap` |
| `provision` | `ORCH_FVT_PROVISION_E001` | `V001`–`V008` | `openchami` |
| `pxeboot` | `ORCH_FVT_PXEBOOT_E001` | `V001`–`V094` | `connectivity`, `cloudinit`, `kubernetes`, `slurm`, `apptainer` |
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

Cloud-init is accepted only when its structured status satisfies the
product contract. A generated script success message is not treated as
authoritative cloud-init state.

### Kubernetes

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 205 | `ORCH_FVT_PXEBOOT_V005` | `test_kubernetes_nodes` | `kubernetes` | `kubernetes`, `sanity` | Verify mapped Kubernetes membership and Ready state. | All stated checks pass for every applicable target. |
| 206 | `ORCH_FVT_PXEBOOT_V006` | `test_kubernetes_node_services` | `kubernetes` | `kubernetes`, `sanity` | Verify required services on every Kubernetes role. | All stated checks pass for every applicable target. |
| 207 | `ORCH_FVT_PXEBOOT_V007` | `test_kubernetes_version_compatibility` | `kubernetes` | `kubernetes`, `sanity` | Verify Kubernetes, kubeadm, and CRI-O version alignment. | All stated checks pass for every applicable target. |
| 208 | `ORCH_FVT_PXEBOOT_V008` | `test_kubernetes_control_plane` | `kubernetes` | `kubernetes`, `sanity` | Verify API readiness and the configured control plane. | All stated checks pass for every applicable target. |
| 209 | `ORCH_FVT_PXEBOOT_V009` | `test_kubernetes_system_pods` | `kubernetes` | `kubernetes`, `sanity` | Verify required system, CNI, storage, and HA workloads. | All stated checks pass for every applicable target. |
| 210 | `ORCH_FVT_PXEBOOT_V010` | `test_kubernetes_virtual_ip` | `kubernetes` | `kubernetes`, `sanity` | Verify exactly one owner for the configured Kubernetes VIP. | All stated checks pass for every applicable target. |
| 211 | `ORCH_FVT_PXEBOOT_V011` | `test_kubernetes_etcd_health` | `kubernetes` | `kubernetes`, `sanity` | Verify health for all etcd endpoints. | All stated checks pass for every applicable target. |
| 212 | `ORCH_FVT_PXEBOOT_V012` | `test_kubernetes_etcd_topology` | `kubernetes` | `kubernetes`, `sanity` | Verify etcd membership, leader election, and raft consistency. | All stated checks pass for every applicable target. |
| 213 | `ORCH_FVT_PXEBOOT_V013` | `test_kubernetes_storage` | `kubernetes` | `kubernetes`, `sanity` | Verify configured NFS and PowerScale storage objects. | All stated checks pass for every applicable target. |
| 214 | `ORCH_FVT_PXEBOOT_V014` | `test_kubernetes_default_storage_class` | `kubernetes` | `kubernetes`, `sanity` | Verify exactly one expected default StorageClass. | All stated checks pass for every applicable target. |
| 215 | `ORCH_FVT_PXEBOOT_V015` | `test_kubernetes_snapshot_controller` | `kubernetes` | `kubernetes`, `sanity` | Verify PowerScale snapshot components when configured. | All stated checks pass for every applicable target. |
| 216 | `ORCH_FVT_PXEBOOT_V016` | `test_kubernetes_local_etcd` | `kubernetes` | `kubernetes`, `sanity` | Verify each control plane has the configured etcd mount. | All stated checks pass for every applicable target. |
| 217 | `ORCH_FVT_PXEBOOT_V017` | `test_kubernetes_local_etcd_integrity` | `kubernetes` | `kubernetes`, `sanity` | Verify disk selection, ext4 label, UUID fstab, and boot persistence. | All stated checks pass for every applicable target. |
| 218 | `ORCH_FVT_PXEBOOT_V018` | `test_kubernetes_workload_scheduling` | `kubernetes` | `functional`, `kubernetes`, `sanity` | Create, verify, and remove an isolated scheduling probe. | The isolated probe becomes ready, satisfies the stated contract, and is removed. |
| 219 | `ORCH_FVT_PXEBOOT_V019` | `test_kubernetes_nfs_dynamic_provisioning` | `kubernetes` | `functional`, `kubernetes`, `sanity` | Create and remove an isolated NFS-backed workload. | All stated checks pass for every applicable target. |
| 220 | `ORCH_FVT_PXEBOOT_V020` | `test_kubernetes_csi_dynamic_provisioning` | `kubernetes` | `functional`, `kubernetes`, `sanity` | Create and remove an isolated PowerScale-backed workload. | All stated checks pass for every applicable target. |
| 221 | `ORCH_FVT_PXEBOOT_V021` | `test_kubernetes_local_etcd_recovery` | `kubernetes` | `disruptive`, `kubernetes`, `reboot` | Reboot a control plane and prove its local-etcd UUID is preserved. | The node returns within the bounded wait and every stated post-reboot check passes. |
| 222 | `ORCH_FVT_PXEBOOT_V022` | `test_kubernetes_control_plane_recovery` | `kubernetes` | `disruptive`, `kubernetes`, `reboot` | Reboot the VIP owner and verify control-plane recovery. | The node returns within the bounded wait and every stated post-reboot check passes. |

Temporary Kubernetes resources use unique namespaces and are removed by
the creating test. CSI, snapshot, and local-etcd checks are selected from
the active configuration.

### Slurm

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 223 | `ORCH_FVT_PXEBOOT_V023` | `test_slurm_membership` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify mapped membership, healthy state, and basic hardware fields. | All stated checks pass for every applicable target. |
| 224 | `ORCH_FVT_PXEBOOT_V024` | `test_slurm_scheduler` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify mapped compute nodes have healthy, available partitions. | All stated checks pass for every applicable target. |
| 225 | `ORCH_FVT_PXEBOOT_V025` | `test_slurm_services` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify role and feature-specific Slurm services. | All stated checks pass for every applicable target. |
| 226 | `ORCH_FVT_PXEBOOT_V026` | `test_slurm_pam_policy` | `slurm` | `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify SSHD, the PAM module, and pam_slurm_adopt account policy. | All stated checks pass for every applicable target. |
| 227 | `ORCH_FVT_PXEBOOT_V027` | `test_slurm_cross_node_ssh` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify every mapped Slurm role can reach every peer over root SSH. | All stated checks pass for every applicable target. |
| 228 | `ORCH_FVT_PXEBOOT_V028` | `test_slurm_configless_mode` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify configless controller access and expected cluster identity. | All stated checks pass for every applicable target. |
| 229 | `ORCH_FVT_PXEBOOT_V029` | `test_slurm_configuration_consistency` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Compare authoritative Slurm files with every configless client cache. | Every compared value matches its authoritative source. |
| 230 | `ORCH_FVT_PXEBOOT_V030` | `test_slurm_control_node_jobs` | `slurm` | `functional`, `non_disruptive`, `sanity`, `slurm` | Run one targeted job per compute from every Slurm control node. | The operation completes successfully and returns the expected result. |
| 231 | `ORCH_FVT_PXEBOOT_V031` | `test_slurm_login_node_jobs` | `slurm` | `functional`, `non_disruptive`, `sanity`, `slurm` | Run one targeted job per compute from every mapped login node. | The operation completes successfully and returns the expected result. |
| 232 | `ORCH_FVT_PXEBOOT_V032` | `test_slurm_compiler_node_jobs` | `slurm` | `functional`, `non_disruptive`, `sanity`, `slurm` | Run one targeted job per compute from every login compiler node. | The operation completes successfully and returns the expected result. |
| 233 | `ORCH_FVT_PXEBOOT_V033` | `test_slurm_control_ldap_authentication` | `slurm` | `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify a valid LDAP password on the Slurm control node. | All stated checks pass for every applicable target. |
| 234 | `ORCH_FVT_PXEBOOT_V034` | `test_slurm_control_ldap_invalid_password` | `slurm` | `negative`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify an invalid LDAP password is rejected on the control node. | The expected rejection occurs and no prohibited state is accepted. |
| 235 | `ORCH_FVT_PXEBOOT_V035` | `test_slurm_login_ldap_authentication` | `slurm` | `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify a valid LDAP password on every mapped login node. | All stated checks pass for every applicable target. |
| 236 | `ORCH_FVT_PXEBOOT_V036` | `test_slurm_login_ldap_invalid_password` | `slurm` | `negative`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify an invalid LDAP password is rejected on every login node. | The expected rejection occurs and no prohibited state is accepted. |
| 237 | `ORCH_FVT_PXEBOOT_V037` | `test_slurm_compiler_ldap_authentication` | `slurm` | `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify a valid LDAP password on every login-compiler node. | All stated checks pass for every applicable target. |
| 238 | `ORCH_FVT_PXEBOOT_V038` | `test_slurm_compiler_ldap_invalid_password` | `slurm` | `negative`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify invalid LDAP passwords are rejected on login-compiler nodes. | The expected rejection occurs and no prohibited state is accepted. |
| 239 | `ORCH_FVT_PXEBOOT_V039` | `test_slurm_pam_no_job_access` | `slurm` | `negative`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify LDAP compute login is denied without an active job. | The expected rejection occurs and no prohibited state is accepted. |
| 240 | `ORCH_FVT_PXEBOOT_V040` | `test_slurm_control_ldap_jobs` | `slurm` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Submit and complete an LDAP-owned job from the control node. | The submission completes with the expected final state and output. |
| 241 | `ORCH_FVT_PXEBOOT_V041` | `test_slurm_control_pam_job_access` | `slurm` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify control-submitted PAM access during and after a job. | All stated checks pass for every applicable target. |
| 242 | `ORCH_FVT_PXEBOOT_V042` | `test_slurm_login_ldap_jobs` | `slurm` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Submit and complete an LDAP-owned job from every login node. | The submission completes with the expected final state and output. |
| 243 | `ORCH_FVT_PXEBOOT_V043` | `test_slurm_login_pam_job_access` | `slurm` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify login-node PAM access during and after a job. | All stated checks pass for every applicable target. |
| 244 | `ORCH_FVT_PXEBOOT_V044` | `test_slurm_compiler_ldap_jobs` | `slurm` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Submit an LDAP-owned job from every login-compiler node. | The submission completes with the expected final state and output. |
| 245 | `ORCH_FVT_PXEBOOT_V045` | `test_slurm_compiler_pam_job_access` | `slurm` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify login-compiler PAM access during and after a job. | All stated checks pass for every applicable target. |
| 246 | `ORCH_FVT_PXEBOOT_V046` | `test_slurm_invalid_ldap_identity` | `slurm` | `negative`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify a generated missing directory identity is rejected. | The expected rejection occurs and no prohibited state is accepted. |
| 247 | `ORCH_FVT_PXEBOOT_V047` | `test_slurm_openmpi_installation` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify OpenMPI discovery and version on every compute node. | All stated checks pass for every applicable target. |
| 248 | `ORCH_FVT_PXEBOOT_V048` | `test_slurm_gpu_inventory` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify NVIDIA runtime state on scheduler-declared GPU nodes. | All stated checks pass for every applicable target. |
| 249 | `ORCH_FVT_PXEBOOT_V049` | `test_slurm_concurrent_jobs` | `slurm` | `functional`, `non_disruptive`, `sanity`, `slurm` | Submit concurrent jobs and verify final accounting state. | The submission completes with the expected final state and output. |
| 250 | `ORCH_FVT_PXEBOOT_V050` | `test_slurm_insufficient_resources` | `slurm` | `functional`, `negative`, `non_disruptive`, `sanity`, `slurm` | Verify an impossible immediate allocation is rejected. | The expected rejection occurs and no prohibited state is accepted. |
| 251 | `ORCH_FVT_PXEBOOT_V051` | `test_slurm_openmpi_job` | `slurm` | `functional`, `non_disruptive`, `sanity`, `slurm` | Run an OpenMPI-backed job when OpenMPI is configured. | The operation completes successfully and returns the expected result. |
| 252 | `ORCH_FVT_PXEBOOT_V052` | `test_slurm_gpu_job` | `slurm` | `functional`, `non_disruptive`, `sanity`, `slurm` | Allocate a GPU through Slurm and query the device. | The allocation succeeds and the requested device is visible. |
| 253 | `ORCH_FVT_PXEBOOT_V053` | `test_slurm_infiniband_configuration` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify mapped IB interface, address, prefix, link, MTU, and OFED. | All stated checks pass for every applicable target. |
| 254 | `ORCH_FVT_PXEBOOT_V054` | `test_slurm_infiniband_connectivity` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify every mapped IB endpoint can reach every mapped peer. | All stated checks pass for every applicable target. |
| 255 | `ORCH_FVT_PXEBOOT_V055` | `test_slurm_ucx_transport` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify UCX exposes an InfiniBand-capable transport. | All stated checks pass for every applicable target. |
| 256 | `ORCH_FVT_PXEBOOT_V056` | `test_slurm_reconfigure` | `slurm` | `functional`, `non_disruptive`, `sanity`, `slurm` | Reconfigure Slurm and verify membership remains healthy. | All stated checks pass for every applicable target. |
| 257 | `ORCH_FVT_PXEBOOT_V057` | `test_slurm_hardware_discovery` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify runtime hardware matches the configured discovery strategy. | All stated checks pass for every applicable target. |
| 258 | `ORCH_FVT_PXEBOOT_V058` | `test_slurm_custom_configuration` | `slurm` | `non_disruptive`, `sanity`, `slurm` | Verify custom values, NFS delivery, and effective visibility. | All stated checks pass for every applicable target. |
| 259 | `ORCH_FVT_PXEBOOT_V059` | `test_slurm_gpu_memory_stress` | `slurm` | `functional`, `non_disruptive`, `sanity`, `slurm` | Compile and run a bounded GPU memory workload through Slurm. | Compilation and bounded workload execution complete successfully. |
| 260 | `ORCH_FVT_PXEBOOT_V060` | `test_slurm_job_queueing` | `slurm` | `functional`, `non_disruptive`, `sanity`, `slurm` | Saturate idle computes and verify one follower queues then completes. | The follower is pending under saturation and completes after resources are released. |
| 261 | `ORCH_FVT_PXEBOOT_V061` | `test_slurm_drain_queue_recovery` | `slurm` | `disruptive`, `sanity`, `scheduler_state`, `slurm` | Drain one compute node, verify queuing, and restore it. | The job queues while the node is drained, then the node is resumed and the job completes. |
| 262 | `ORCH_FVT_PXEBOOT_V062` | `test_slurm_cluster_recovery` | `slurm` | `disruptive`, `functional`, `reboot`, `slurm` | Reboot mapped Slurm nodes and verify scheduler and workload recovery. | The node returns within the bounded wait and every stated post-reboot check passes. |

Login and login-compiler cases skip before credential loading when the
corresponding role is absent. Feature checks use only catalog layers
selected by mapped functional groups.

### Apptainer

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 263 | `ORCH_FVT_PXEBOOT_V063` | `test_apptainer_runtime` | `apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify the Apptainer executable and version on every compute node. | All stated checks pass for every applicable target. |
| 264 | `ORCH_FVT_PXEBOOT_V064` | `test_apptainer_shared_artifacts` | `apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify shared image directories and downloader artifacts. | All stated checks pass for every applicable target. |
| 265 | `ORCH_FVT_PXEBOOT_V065` | `test_apptainer_pulp_policy` | `apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify the generated downloader uses only the configured Pulp source. | All stated checks pass for every applicable target. |
| 266 | `ORCH_FVT_PXEBOOT_V066` | `test_apptainer_shared_storage` | `apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify /hpc_tools is a shared mounted filesystem on every compute. | All stated checks pass for every applicable target. |
| 267 | `ORCH_FVT_PXEBOOT_V067` | `test_apptainer_download` | `apptainer` | `apptainer`, `functional`, `image_download`, `non_disruptive`, `sanity` | Run the deployed downloader and require at least one usable SIF. | The operation completes successfully and returns the expected result. |
| 268 | `ORCH_FVT_PXEBOOT_V068` | `test_apptainer_download_idempotency` | `apptainer` | `apptainer`, `functional`, `image_download`, `non_disruptive`, `sanity` | Rerun the downloader and verify existing image metadata is unchanged. | The repeated operation succeeds without changing protected state. |
| 269 | `ORCH_FVT_PXEBOOT_V069` | `test_apptainer_download_memory` | `apptainer` | `apptainer`, `functional`, `image_download`, `non_disruptive`, `sanity` | Run the downloader and enforce a bounded peak resident-memory use. | The operation completes successfully and returns the expected result. |
| 270 | `ORCH_FVT_PXEBOOT_V070` | `test_apptainer_image_inventory` | `apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify every compute sees one consistent non-empty SIF inventory. | All stated checks pass for every applicable target. |
| 271 | `ORCH_FVT_PXEBOOT_V071` | `test_apptainer_sif_format` | `apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify each discovered image is a valid inspectable SIF. | All stated checks pass for every applicable target. |
| 272 | `ORCH_FVT_PXEBOOT_V072` | `test_apptainer_sif_permissions` | `apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify shared SIF files are non-empty and world-readable. | All stated checks pass for every applicable target. |
| 273 | `ORCH_FVT_PXEBOOT_V073` | `test_apptainer_sif_integrity` | `apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify the selected SIF has the same checksum on every compute. | All stated checks pass for every applicable target. |
| 274 | `ORCH_FVT_PXEBOOT_V074` | `test_apptainer_ldap_readability` | `apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify the LDAP test identity can read a shared SIF when enabled. | All stated checks pass for every applicable target. |
| 275 | `ORCH_FVT_PXEBOOT_V075` | `test_apptainer_non_root_execution` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify an unprivileged local identity can execute a shared SIF. | All stated checks pass for every applicable target. |
| 279 | `ORCH_FVT_PXEBOOT_V076` | `test_apptainer_missing_image_contract` | `apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify the downloader records pull failures and exits non-zero. | The expected rejection occurs and no prohibited state is accepted. |
| 280 | `ORCH_FVT_PXEBOOT_V077` | `test_apptainer_single_node_job` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Run one exact-node container job on every mapped compute. | The operation completes successfully and returns the expected result. |
| 281 | `ORCH_FVT_PXEBOOT_V078` | `test_apptainer_multi_node_job` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Run one container allocation spanning all mapped computes. | The operation completes successfully and returns the expected result. |
| 282 | `ORCH_FVT_PXEBOOT_V079` | `test_apptainer_ldap_job` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Run targeted container jobs as the configured LDAP test identity. | The operation completes successfully and returns the expected result. |
| 283 | `ORCH_FVT_PXEBOOT_V080` | `test_apptainer_concurrent_jobs` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Run bounded concurrent container jobs on distinct computes. | The operation completes successfully and returns the expected result. |
| 284 | `ORCH_FVT_PXEBOOT_V081` | `test_apptainer_invalid_sif` | `apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify a nonexistent SIF fails through the Slurm execution path. | The expected rejection occurs and no prohibited state is accepted. |
| 285 | `ORCH_FVT_PXEBOOT_V082` | `test_apptainer_restricted_sif` | `apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify an unprivileged identity cannot execute a mode-0600 SIF. | The expected rejection occurs and no prohibited state is accepted. |
| 286 | `ORCH_FVT_PXEBOOT_V083` | `test_apptainer_nfs_visibility` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify containers can read the shared image path on every compute. | All stated checks pass for every applicable target. |
| 287 | `ORCH_FVT_PXEBOOT_V084` | `test_apptainer_slurm_environment` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify Slurm allocation variables propagate into containers. | All stated checks pass for every applicable target. |
| 288 | `ORCH_FVT_PXEBOOT_V085` | `test_apptainer_job_array` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Submit and wait for a bounded Apptainer Slurm job array. | The submission completes with the expected final state and output. |
| 289 | `ORCH_FVT_PXEBOOT_V086` | `test_apptainer_failure_cleanup` | `apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify a failed image launch leaves no matching runtime process. | The expected rejection occurs and no prohibited state is accepted. |
| 290 | `ORCH_FVT_PXEBOOT_V087` | `test_apptainer_gpu_access` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify scheduler-declared GPU nodes expose GPUs in the container. | All stated checks pass for every applicable target. |
| 291 | `ORCH_FVT_PXEBOOT_V088` | `test_apptainer_gpu_count` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify each container sees the same GPU count as its host. | All stated checks pass for every applicable target. |
| 292 | `ORCH_FVT_PXEBOOT_V089` | `test_apptainer_cuda_workload` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Execute a bounded NVIDIA device query in each GPU container. | The operation completes successfully and returns the expected result. |
| 293 | `ORCH_FVT_PXEBOOT_V090` | `test_apptainer_gpu_memory` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify the GPU query leaves no material device-memory allocation. | All stated checks pass for every applicable target. |
| 294 | `ORCH_FVT_PXEBOOT_V091` | `test_apptainer_infiniband` | `apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify mapped compute nodes expose InfiniBand devices in containers. | All stated checks pass for every applicable target. |
| 295 | `ORCH_FVT_PXEBOOT_V092` | `test_apptainer_reboot_storage` | `apptainer` | `apptainer`, `disruptive`, `reboot` | Reboot one compute and verify the shared mount and SIF checksum. | The node returns within the bounded wait and every stated post-reboot check passes. |
| 296 | `ORCH_FVT_PXEBOOT_V093` | `test_apptainer_reboot_job` | `apptainer` | `apptainer`, `disruptive`, `reboot` | Run an exact-node container job after the authorized reboot. | The node returns within the bounded wait and every stated post-reboot check passes. |
| 297 | `ORCH_FVT_PXEBOOT_V094` | `test_apptainer_reboot_artifacts` | `apptainer` | `apptainer`, `disruptive`, `reboot` | Verify downloader artifacts and policy after the authorized reboot. | The node returns within the bounded wait and every stated post-reboot check passes. |

Image download has a 20-minute ceiling with polling progress every 20
seconds. The reboot cases share one reboot state instead of rebooting the
same compute node independently for each postcondition.

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
| `openldap`, `connectivity`, `cloudinit`, `kubernetes`, `slurm`, `apptainer` | Capability selectors |
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
./run_validation.sh fvt_orchestrator prepare verify --suite openchami
./run_validation.sh fvt_orchestrator provision verify --suite openchami
./run_validation.sh fvt_orchestrator pxeboot verify --suite kubernetes
./run_validation.sh fvt_orchestrator pxeboot verify --suite slurm
./run_validation.sh fvt_orchestrator pxeboot verify --suite apptainer

# Marker examples.
./run_validation.sh fvt_orchestrator pxeboot verify --marker sanity,functional
./run_validation.sh fvt_orchestrator pxeboot verify \
  --suite slurm --marker slurm+non_disruptive
./run_validation.sh fvt_orchestrator pxeboot verify \
  --suite apptainer --marker functional+image_download
./run_validation.sh fvt_orchestrator pxeboot verify \
  --marker disruptive+reboot

# Explicit full cleanup.
./run_validation.sh fvt_orchestrator cleanup test --marker sanity
```

Run `provision test`, `pxeboot test`, or cleanup only against the intended
active project and with the corresponding operational authorization. A failed
execution case prevents the verification phase from being reported as a
successful lifecycle run.
