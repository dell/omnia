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
| `precheck` | `ORCH_FVT_PRECHECK_E001` | `V001`–`V012`, `V100`–`V105`, `V107`–`V117` | `environment`, `oim_readiness`, `storage`, `dependencies`, `inputs` |
| `prepare` | `ORCH_FVT_PREPARE_E001` | `V001`–`V007`, `V009`–`V011`, `V013` | `openchami`, `network`, `openldap` |
| `provision` | `ORCH_FVT_PROVISION_E001` | `V001`–`V010` | `openchami` |
| `pxeboot` | `ORCH_FVT_PXEBOOT_E001` | `V001`–`V115`, `V117`–`V121`, `V200`–`V218`, `V300`–`V308`, `V400`–`V429`, `V500`–`V525` | see `SUITES` in `library/vars/domain_vars.py` |
| `cleanup` | `ORCH_FVT_CLEANUP_E001` | `V001`–`V006` | `openchami`, `openldap`, `slurm`, `kubernetes`, `artifacts`, `credentials` |

The detailed tables below are the authoritative inventory. Each test's
`Order` defines execution sequence independently of its stable public ID, so
files and functions can be reorganized without renumbering IDs.

### Retired and reassigned IDs

Retired IDs are never reused.

| Test | Previous ID | Current ID | Reason |
|---|---|---|---|
| `test_external_ldap_proxy` | `ORCH_FVT_PREPARE_V008` (retired) | `ORCH_FVT_PXEBOOT_V524` | Moved from prepare to the pxeboot `slurm_ldap` suite. |
| `test_external_ldap_backend` | `ORCH_FVT_PREPARE_V012` (retired) | `ORCH_FVT_PXEBOOT_V525` | Moved from prepare to the pxeboot `slurm_ldap` suite. |
| `test_kubernetes_configured_versions` | `ORCH_FVT_PXEBOOT_V101` (duplicate) | `ORCH_FVT_PXEBOOT_V519` | V101 remains with `test_mount_config_mount_point`, which registered it first. |
| `test_kubernetes_local_etcd_provisioning` | `ORCH_FVT_PXEBOOT_V102` (duplicate) | `ORCH_FVT_PXEBOOT_V520` | V102 remains with `test_mount_config_volume_mounted`. |
| `test_kubernetes_nfs_provisioner_contract` | `ORCH_FVT_PXEBOOT_V103` (duplicate) | `ORCH_FVT_PXEBOOT_V521` | V103 remains with `test_mount_config_mount_options`. |
| `test_dcgm_cuda_validation` | `ORCH_FVT_PXEBOOT_V501` (duplicate) | `ORCH_FVT_PXEBOOT_V522` | V501 remains with `test_slurm_node_add`, which registered it first. |

### Omnia 2.2 Kubernetes etcd and reboot traceability

The 2.2 `molecule/kubernetes` cases below are covered by these 2.3 cases.
2.3 performs one reboot per recovery case and reports every 2.2 step as a
named field of that case instead of sharing state between tests.

| 2.2 test | 2.3 test | 2.3 ID | Covered by |
|---|---|---|---|
| `test_tc_f03_disk_partitioning` | `test_kubernetes_local_etcd_provisioning` | `ORCH_FVT_PXEBOOT_V520` | GPT partition table on the selected disk, which is not the root disk |
| `test_tc_f04_filesystem_creation` | `test_kubernetes_local_etcd_integrity` | `ORCH_FVT_PXEBOOT_V015` | ext4 filesystem labelled `etcd_data` |
| `test_tc_f05_fstab_update_and_mount` | `test_kubernetes_local_etcd_integrity` | `ORCH_FVT_PXEBOOT_V015` | One UUID-based fstab entry and an active mount |
| `test_tc_f06_etcd_configuration_to_local_disk` | `test_kubernetes_local_etcd`, `test_kubernetes_local_etcd_integrity` | `ORCH_FVT_PXEBOOT_V014`, `V015` | Non-NFS ext4 mount, `etcd:etcd 700`, and the etcd manifest data directory |
| `test_tc_f01_boss_card_detection`, `test_tc_f07_fallback_disk_detection` | `test_kubernetes_local_etcd_provisioning` | `ORCH_FVT_PXEBOOT_V520` | BOSS disk selected when present, otherwise a fallback non-root disk, and the selection is logged |
| `test_tc_f08_first_boot_disk_setup` | `test_kubernetes_local_etcd_provisioning` | `ORCH_FVT_PXEBOOT_V520` | Both scripts executable and this boot's script finished with `DONE` |
| `test_tc_f10_ssd_disk_support`, `test_tc_f11_hdd_disk_support`, `test_tc_f12_nvme_disk_support` | `test_kubernetes_local_etcd_media` | `ORCH_FVT_PXEBOOT_V523` | Every control plane uses the `expected_etcd_disk_media` media |
| `test_etcd_reboot_control_plane`, `test_etcd_wait_node_online`, `test_etcd_wait_cloud_init` | `test_kubernetes_local_etcd_recovery` | `ORCH_FVT_PXEBOOT_V021` | Reboot, new boot ID, and cloud-init completion |
| `test_tc_f09_subsequent_boot_post_reboot` | `test_kubernetes_local_etcd_recovery` | `ORCH_FVT_PXEBOOT_V021` | `etcd-fstab-update.sh` finished with `DONE` on the new boot and `etcd-disk-setup.sh` did not run again |
| `test_tc_f05_fstab_mount_post_reboot`, `test_tc_f06_etcd_local_disk_post_reboot` | `test_kubernetes_local_etcd_recovery` | `ORCH_FVT_PXEBOOT_V021` | Local-etcd integrity after reboot and unchanged mount source and UUID |
| `test_etcd_cluster_health_post_reboot` | `test_kubernetes_local_etcd_recovery`, `test_kubernetes_control_plane_recovery` | `ORCH_FVT_PXEBOOT_V021`, `V022` | Every etcd endpoint healthy within `ETCD_HEALTH_WAIT_TIMEOUT_SECONDS` |
| `test_reboot_vip_control_plane`, `test_verify_vip_failover` | `test_kubernetes_control_plane_recovery` | `ORCH_FVT_PXEBOOT_V022` | VIP owner rebooted and the VIP moves to exactly one other control plane |
| `test_verify_cloud_init_after_reboot` | `test_kubernetes_control_plane_recovery` | `ORCH_FVT_PXEBOOT_V022` | Cloud-init completes on the rebooted node |
| `test_verify_node_ready_after_reboot` | `test_kubernetes_control_plane_recovery` | `ORCH_FVT_PXEBOOT_V022` | Rebooted node returns to Ready, observed from another control plane |

## Execution order blocks

The default non-cleanup lifecycle is:

```text
precheck -> prepare -> provision -> pxeboot
```

Every `@pytest.mark.order` value lies in its suite's block, defined by
`TEST_ORDER_BLOCKS` in `library/vars/test_case_vars.py`:

```text
order = lifecycle base + suite slot * 100 + position in suite
```

| Lifecycle | Base | Block of the execution case |
|---|---:|---:|
| `precheck` | 10000 | 10000 |
| `prepare` | 20000 | 20000 |
| `provision` | 30000 | 30000 |
| `pxeboot` | 40000 | 40000 |
| `cleanup` | 50000 | 50000 |
| NFT | 60000 | — |

Each suite owns 100 numbers, so a new test takes the next free number in its
own suite and never renumbers another suite. A new suite appends a block.
Suites run in dependency order: reachability and node state first, then
cluster health, temporary workloads, and finally the reboot, drain, and
node-removal suites (`kubernetes_recovery`, `slurm_recovery`,
`slurm_lifecycle`). Within a suite, disruptive and destructive cases come
last. Never reuse an order value.

Cleanup is never part of an implicit lifecycle run.

## Precheck test cases

These cases execute and verify OIM identity and readiness, selected storage, dependency outputs, required inputs, boot artifacts, and published repositories.

### Lifecycle execution

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 10000 | `ORCH_FVT_PRECHECK_E001` | `test_deploy_precheck` | `root` | `deploy`, `sanity` | Run ``orchestrator.yml --tags precheck`` exactly once. | The selected Orchestrator lifecycle exits successfully. |

### Environment (`environment`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 10101 | `ORCH_FVT_PRECHECK_V001` | `test_precheck_hostname_domain` | `environment` | `sanity` | Require the host identity to match omnia.env exactly. | Every required item satisfies the stated condition. |
| 10102 | `ORCH_FVT_PRECHECK_V002` | `test_precheck_admin_ipv4` | `environment` | `sanity` | Require the configured administrative IPv4 on a global interface. | Every required item satisfies the stated condition. |

### OIM readiness (`oim_readiness`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 10201 | `ORCH_FVT_PRECHECK_V100` | `test_oim_cpu_threshold` | `oim_readiness` | `sanity` | Require OIM CPU core count to meet the configured minimum. | Every required item satisfies the stated condition. |
| 10202 | `ORCH_FVT_PRECHECK_V101` | `test_oim_memory_threshold` | `oim_readiness` | `sanity` | Require OIM memory to meet the configured minimum. | Every required item satisfies the stated condition. |
| 10203 | `ORCH_FVT_PRECHECK_V102` | `test_oim_disk_threshold` | `oim_readiness` | `sanity` | Require OIM root filesystem to meet the configured minimum. | Every required item satisfies the stated condition. |
| 10204 | `ORCH_FVT_PRECHECK_V103` | `test_oim_pxe_nic_present` | `oim_readiness` | `sanity` | Require the configured admin NIC to exist and be UP. | Every required item satisfies the stated condition. |
| 10205 | `ORCH_FVT_PRECHECK_V104` | `test_oim_public_nic_present` | `oim_readiness` | `sanity` | Require the public/default-route NIC to exist and be UP. | Every required item satisfies the stated condition. |
| 10206 | `ORCH_FVT_PRECHECK_V105` | `test_oim_pxe_nic_ipv4` | `oim_readiness` | `sanity` | Require the admin NIC to carry the configured IPv4 address. | Every required item satisfies the stated condition. |
| 10207 | `ORCH_FVT_PRECHECK_V107` | `test_oim_ssh_preflight` | `oim_readiness` | `sanity` | Require passwordless SSH from OIM to a mapped target node. | Every required item satisfies the stated condition. |
| 10208 | `ORCH_FVT_PRECHECK_V108` | `test_oim_internet_reachability` | `oim_readiness` | `sanity` | Require internet reachability when not in air-gapped mode. | Every required item satisfies the stated condition. |
| 10209 | `ORCH_FVT_PRECHECK_V109` | `test_oim_os_version` | `oim_readiness` | `sanity` | Require the OIM OS to match the expected distribution and version. | Every required item satisfies the stated condition. |
| 10210 | `ORCH_FVT_PRECHECK_V110` | `test_neg_cpu_below_threshold` | `oim_readiness` | `negative` | Detect failure when CPU threshold exceeds actual cores. | The expected rejection occurs and no prohibited state is accepted. |
| 10211 | `ORCH_FVT_PRECHECK_V111` | `test_neg_memory_below_threshold` | `oim_readiness` | `negative` | Detect failure when memory threshold exceeds actual RAM. | The expected rejection occurs and no prohibited state is accepted. |
| 10212 | `ORCH_FVT_PRECHECK_V112` | `test_neg_disk_below_threshold` | `oim_readiness` | `negative` | Detect failure when disk threshold exceeds actual capacity. | The expected rejection occurs and no prohibited state is accepted. |
| 10213 | `ORCH_FVT_PRECHECK_V113` | `test_neg_pxe_nic_missing` | `oim_readiness` | `negative` | Detect failure when a nonexistent NIC name is checked. | The expected rejection occurs and no prohibited state is accepted. |
| 10214 | `ORCH_FVT_PRECHECK_V114` | `test_neg_pxe_public_overlap` | `oim_readiness` | `negative` | Detect overlap when PXE NIC is forced to match the public NIC. | The expected rejection occurs and no prohibited state is accepted. |
| 10215 | `ORCH_FVT_PRECHECK_V115` | `test_neg_internet_airgapped` | `oim_readiness` | `negative` | Verify air-gapped mode passes even without internet. | The expected rejection occurs and no prohibited state is accepted. |
| 10216 | `ORCH_FVT_PRECHECK_V116` | `test_neg_ssh_unreachable_target` | `oim_readiness` | `negative` | Detect SSH failure to a bogus target address. | The expected rejection occurs and no prohibited state is accepted. |
| 10217 | `ORCH_FVT_PRECHECK_V117` | `test_neg_os_version_mismatch` | `oim_readiness` | `negative` | Detect failure when expected OS version does not match actual. | The expected rejection occurs and no prohibited state is accepted. |

Every check is read-only. Thresholds default to CPU >= 4, RAM >= 16 GB, and
root disk >= 100 GB. Negative cases use the unattainable inputs in
`OIM_NEGATIVE_INPUTS` (`library/vars/precheck_vars.py`) and pass only when
the checker rejects them with an actionable error.

### Storage (`storage`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 10301 | `ORCH_FVT_PRECHECK_V003` | `test_precheck_nfs_servers` | `storage` | `sanity` | Require every mapping-selected NFS server to answer ICMP from the OIM. | Every required item satisfies the stated condition. |
| 10302 | `ORCH_FVT_PRECHECK_V008` | `test_mount_missing_mount_point` | `storage` | `mount_config`, `negative` | TC-CI-NEG-001: Every mount entry must have a valid absolute mount_point. | The expected rejection occurs and no prohibited state is accepted. |
| 10303 | `ORCH_FVT_PRECHECK_V009` | `test_mount_missing_targeting` | `storage` | `mount_config`, `negative` | TC-CI-NEG-002: Every mount entry must have targeting (prefix or groups). | The expected rejection occurs and no prohibited state is accepted. |
| 10304 | `ORCH_FVT_PRECHECK_V010` | `test_mount_invalid_mount_params` | `storage` | `mount_config`, `negative` | TC-CI-NEG-003: mount_params must reference an existing profile. | The expected rejection occurs and no prohibited state is accepted. |
| 10305 | `ORCH_FVT_PRECHECK_V011` | `test_mount_missing_source` | `storage` | `mount_config`, `negative` | TC-CI-NEG-004: Every mount entry must have a non-empty source. | The expected rejection occurs and no prohibited state is accepted. |
| 10306 | `ORCH_FVT_PRECHECK_V012` | `test_mount_node_key_without_mount_point` | `storage` | `mount_config`, `negative` | TC-CI-NEG-005: node_mount_point is mandatory when node_key is set. | The expected rejection occurs and no prohibited state is accepted. |

The NFS case mirrors the production mount-selection contract. It evaluates
`functional_group_prefix` against mapped functional groups, evaluates
`groups` against mapped PXE `GROUP_NAME` values, and excludes the stock
`vast_storage` entry unless `omnia_config.yml` selects it.

### Dependencies (`dependencies`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 10401 | `ORCH_FVT_PRECHECK_V004` | `test_precheck_dependencies` | `dependencies` | `sanity` | Require both configured/default dependency outputs to be usable. | Every required item satisfies the stated condition. |
| 10402 | `ORCH_FVT_PRECHECK_V006` | `test_precheck_s3_artifacts` | `dependencies` | `sanity` | Require every kernel, initrd, and rootfs artifact to be reachable. | Every required item satisfies the stated condition. |
| 10403 | `ORCH_FVT_PRECHECK_V007` | `test_precheck_repositories` | `dependencies` | `sanity` | Require every published RPM and file repository to be reachable. | Every required item satisfies the stated condition. |

### Inputs (`inputs`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 10501 | `ORCH_FVT_PRECHECK_V005` | `test_precheck_inputs` | `inputs` | `sanity` | Require every source-selected Orchestrator input to be non-empty. | Every required item satisfies the stated condition. |

## Prepare test cases

These cases verify the infrastructure created by the `prepare` lifecycle.

### Lifecycle execution

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 20000 | `ORCH_FVT_PREPARE_E001` | `test_deploy_prepare` | `root` | `deploy`, `sanity` | Run ``orchestrator.yml --tags prepare``. | The selected Orchestrator lifecycle exits successfully. |

### OpenCHAMI (`openchami`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 20101 | `ORCH_FVT_PREPARE_V001` | `test_openchami_containers_running` | `openchami` | `sanity` | Verify all long-running OpenCHAMI containers. | All stated checks pass for every applicable target. |
| 20102 | `ORCH_FVT_PREPARE_V002` | `test_openchami_services_ready` | `openchami` | `sanity` | Verify OpenCHAMI units and successful SMD initialization. | All stated checks pass for every applicable target. |
| 20103 | `ORCH_FVT_PREPARE_V003` | `test_openchami_apis_ready` | `openchami` | `functional`, `sanity` | Verify the authenticated SMD, Boot and Metadata APIs. | All stated checks pass for every applicable target. |
| 20104 | `ORCH_FVT_PREPARE_V004` | `test_openchami_persistent_storage_and_tls` | `openchami` | `sanity` | Verify persistent data volumes and HAProxy certificates. | All stated checks pass for every applicable target. |
| 20105 | `ORCH_FVT_PREPARE_V005` | `test_openchami_packages_and_artifacts` | `openchami` | `sanity` | Verify installed packages and generated configuration files. | All stated checks pass for every applicable target. |
| 20106 | `ORCH_FVT_PREPARE_V013` | `test_postgresql_readiness` | `openchami` | `functional`, `sanity` | Verify PostgreSQL and its required SMD database contract. | All stated checks pass for every applicable target. |

### Network (`network`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 20201 | `ORCH_FVT_PREPARE_V006` | `test_firewall_and_podman_network_policy` | `network` | `sanity` | Verify OpenCHAMI ports and trusted Podman interfaces. | All stated checks pass for every applicable target. |
| 20202 | `ORCH_FVT_PREPARE_V007` | `test_coredhcp_and_coredns_configuration` | `network` | `functional`, `sanity` | Verify rendered DHCP/DNS configuration and additional routes. | All stated checks pass for every applicable target. |

### OpenLDAP (`openldap`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 20301 | `ORCH_FVT_PREPARE_V009` | `test_openldap_runtime` | `openldap` | `openldap`, `sanity` | Verify the enabled service and container are healthy. | All stated checks pass for every applicable target. |
| 20302 | `ORCH_FVT_PREPARE_V010` | `test_openldap_artifacts` | `openldap` | `openldap`, `sanity` | Verify configuration modes, syntax and TLS lifetime. | All stated checks pass for every applicable target. |
| 20303 | `ORCH_FVT_PREPARE_V011` | `test_openldap_endpoint` | `openldap` | `functional`, `openldap`, `sanity` | Verify the local LDAP endpoint and published listeners. | All stated checks pass for every applicable target. |

OpenLDAP runtime, artifacts, and local endpoint checks follow authoritative
generated `openldap_support` state. The prepare lifecycle only starts the
local `omnia_auth` container; the external LDAP proxy cases run in the
pxeboot `slurm_ldap` suite.

## Provision test cases

These controller-side cases compare generated reports and live OpenCHAMI state with the active PXE mapping.

### Lifecycle execution

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 30000 | `ORCH_FVT_PROVISION_E001` | `test_deploy_provision` | `root` | `deploy`, `sanity` | Run ``orchestrator.yml --tags provision``. | The selected Orchestrator lifecycle exits successfully. |

### OpenCHAMI (`openchami`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 30101 | `ORCH_FVT_PROVISION_V001` | `test_provision_reports` | `openchami` | `sanity` | Verify the provision report and generated inventory contracts. | All stated checks pass for every applicable target. |
| 30102 | `ORCH_FVT_PROVISION_V002` | `test_smd_identity` | `openchami` | `sanity` | Verify XNAME, administrative MAC, and IP identity in SMD. | All stated checks pass for every applicable target. |
| 30103 | `ORCH_FVT_PROVISION_V003` | `test_smd_group_membership` | `openchami` | `sanity` | Verify expected groups and reject competing cloud-init groups. | All stated checks pass for every applicable target. |
| 30104 | `ORCH_FVT_PROVISION_V004` | `test_boot_service_configurations` | `openchami` | `sanity` | Verify BootConfigurations and their mapped administrative MACs. | All stated checks pass for every applicable target. |
| 30105 | `ORCH_FVT_PROVISION_V005` | `test_boot_service_node_identity` | `openchami` | `sanity` | Verify synchronized XNAME-to-bootMac records. | All stated checks pass for every applicable target. |
| 30106 | `ORCH_FVT_PROVISION_V006` | `test_metadata_service_groups` | `openchami` | `sanity` | Verify one usable cloud-init template per functional group. | All stated checks pass for every applicable target. |
| 30107 | `ORCH_FVT_PROVISION_V007` | `test_metadata_service_instances` | `openchami` | `sanity` | Verify unique per-node hostname metadata. | All stated checks pass for every applicable target. |
| 30108 | `ORCH_FVT_PROVISION_V008` | `test_coredhcp_and_coredns_inventory` | `openchami` | `sanity` | Verify the SMD identity records consumed by CoreDHCP/CoreDNS. | All stated checks pass for every applicable target. |
| 30109 | `ORCH_FVT_PROVISION_V009` | `test_boot_image_identity` | `openchami` | `boot_image` | Verify Boot Service kernel/initrd paths match build_status.yml. | All stated checks pass for every applicable target. |
| 30110 | `ORCH_FVT_PROVISION_V010` | `test_boot_image_architecture` | `openchami` | `boot_image` | Verify build_status.yml architecture keys match functional group names. | All stated checks pass for every applicable target. |

Provision verification is read-only. It resolves XNAMEs from live SMD
interfaces and groups and obtains fresh OpenCHAMI credentials for API reads.

## PXE post-boot test cases

Optional role and feature cases skip only when the active mapping, catalog, or `test_config.yml` proves that the target is not applicable. Negative cases pass only when the invalid operation is rejected. Reboot, drain, and node-removal suites run last and require their explicit markers.

### Lifecycle execution

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 40000 | `ORCH_FVT_PXEBOOT_E001` | `test_deploy_pxeboot` | `root` | `buildstream`, `deploy`, `sanity` | Run ``orchestrator.yml --tags pxeboot``. | The selected Orchestrator lifecycle exits successfully. |

### Connectivity (`connectivity`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 40101 | `ORCH_FVT_PXEBOOT_V001` | `test_node_ping` | `connectivity` | `buildstream`, `connectivity`, `sanity` | Verify ping from the OIM to every mapped administrative IP. | All stated checks pass for every applicable target. |
| 40102 | `ORCH_FVT_PXEBOOT_V002` | `test_node_ssh` | `connectivity` | `buildstream`, `connectivity`, `sanity` | Verify passwordless root SSH from the OIM to every mapped node. | All stated checks pass for every applicable target. |
| 40103 | `ORCH_FVT_PXEBOOT_V003` | `test_node_hostname_ssh` | `connectivity` | `buildstream`, `connectivity`, `sanity` | Verify mapped hostnames resolve and support passwordless root SSH. | All stated checks pass for every applicable target. |
| 40104 | `ORCH_FVT_PXEBOOT_V097` | `test_node_architecture` | `connectivity` | `buildstream`, `connectivity`, `sanity` | Verify each node's live architecture matches its functional group. | All stated checks pass for every applicable target. |
| 40105 | `ORCH_FVT_PXEBOOT_V098` | `test_node_os_version` | `connectivity` | `buildstream`, `connectivity`, `sanity` | Verify each node's live OS version matches its functional group. | All stated checks pass for every applicable target. |

### Cloud-init (`cloudinit`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 40201 | `ORCH_FVT_PXEBOOT_V004` | `test_node_cloud_init` | `cloudinit` | `buildstream`, `cloudinit`, `sanity` | Verify PXE report freshness and direct cloud-init JSON state. | All stated checks pass for every applicable target. |

Cloud-init is accepted only when its structured status satisfies the
product contract. A generated script success message is not treated as
authoritative cloud-init state.

### Additional cloud-init (`additional_cloud_init`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 40301 | `ORCH_FVT_PXEBOOT_V095` | `test_additional_cloud_init_smd_groups` | `additional_cloud_init` | `additional_cloud_init`, `buildstream`, `non_disruptive`, `sanity` | Verify SMD groups exist for additional cloud-init configuration. | All stated checks pass for every applicable target. |
| 40302 | `ORCH_FVT_PXEBOOT_V096` | `test_additional_cloud_init_metadata_groups` | `additional_cloud_init` | `additional_cloud_init`, `buildstream`, `non_disruptive`, `sanity` | Verify metadata-service groups and templates for additional cloud-init. | All stated checks pass for every applicable target. |
| 40303 | `ORCH_FVT_PXEBOOT_V099` | `test_additional_cloud_init_write_files` | `additional_cloud_init` | `additional_cloud_init`, `buildstream`, `non_disruptive`, `sanity` | Verify write_files entries were applied on provisioned nodes. | All stated checks pass for every applicable target. |
| 40304 | `ORCH_FVT_PXEBOOT_V100` | `test_additional_cloud_init_runcmd` | `additional_cloud_init` | `additional_cloud_init`, `buildstream`, `non_disruptive`, `sanity` | Verify runcmd entries executed during cloud-init on provisioned nodes. | All stated checks pass for every applicable target. |

These cases skip when `additional_cloud_init_config_file` is empty or not
configured in `orchestrator_config.yml`.

### Mount configuration (`mount_config`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 40401 | `ORCH_FVT_PXEBOOT_V101` | `test_mount_config_mount_point` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify NFS mount point directories exist on all target nodes. | All stated checks pass for every applicable target. |
| 40402 | `ORCH_FVT_PXEBOOT_V102` | `test_mount_config_volume_mounted` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify NFS volumes are actively mounted on all target nodes. | All stated checks pass for every applicable target. |
| 40403 | `ORCH_FVT_PXEBOOT_V103` | `test_mount_config_mount_options` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify NFS mount options match storage_config.yml on target nodes. | All stated checks pass for every applicable target. |
| 40404 | `ORCH_FVT_PXEBOOT_V104` | `test_mount_config_fstab` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify NFS fstab entries are persistent on all target nodes. | All stated checks pass for every applicable target. |
| 40405 | `ORCH_FVT_PXEBOOT_V105` | `test_mount_config_bind_mounts` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify NFS bind mount targets are active on all target nodes. | All stated checks pass for every applicable target. |
| 40406 | `ORCH_FVT_PXEBOOT_V106` | `test_mount_config_bind_fstab` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify NFS bind mount fstab entries are persistent on target nodes. | All stated checks pass for every applicable target. |
| 40407 | `ORCH_FVT_PXEBOOT_V107` | `test_mount_config_node_subdirectory` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify per-node subdirectory exists under NFS mount point. | All stated checks pass for every applicable target. |
| 40408 | `ORCH_FVT_PXEBOOT_V108` | `test_mount_config_permissions` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify NFS mount permissions match storage_config.yml on nodes. | All stated checks pass for every applicable target. |
| 40409 | `ORCH_FVT_PXEBOOT_V109` | `test_mount_config_fg_targeting` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify NFS mounts are present on target FGs and absent on others. | All stated checks pass for every applicable target. |
| 40410 | `ORCH_FVT_PXEBOOT_V110` | `test_mount_config_no_duplicate_fstab` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify no duplicate NFS fstab entries on target nodes. | All stated checks pass for every applicable target. |
| 40411 | `ORCH_FVT_PXEBOOT_V111` | `test_mount_config_writable` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify all configured NFS mounts are writable on target nodes. | All stated checks pass for every applicable target. |
| 40412 | `ORCH_FVT_PXEBOOT_V112` | `test_mount_config_oim_mount` | `mount_config` | `buildstream`, `mount_config`, `sanity` | Verify NFS storage is mounted on the OIM when mount_on_oim is true. | All stated checks pass for every applicable target. |

### Minimal OS (`minimal_os`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 40501 | `ORCH_FVT_PXEBOOT_V113` | `test_minimal_os_base_packages` | `minimal_os` | `buildstream`, `minimal_os`, `sanity` | Verify base OS packages are installed on all OS-only nodes. | All stated checks pass for every applicable target. |
| 40502 | `ORCH_FVT_PXEBOOT_V114` | `test_minimal_os_ldms_packages` | `minimal_os` | `buildstream`, `minimal_os`, `sanity` | Verify LDMS monitoring packages and binary on OS-only nodes. | All stated checks pass for every applicable target. |
| 40503 | `ORCH_FVT_PXEBOOT_V115` | `test_minimal_os_required_services` | `minimal_os` | `buildstream`, `minimal_os`, `sanity` | Verify required services are active on all OS-only nodes. | All stated checks pass for every applicable target. |
| 40504 | `ORCH_FVT_PXEBOOT_V117` | `test_minimal_os_excluded_packages` | `minimal_os` | `buildstream`, `minimal_os`, `sanity` | Verify workload-specific packages are NOT installed on OS-only nodes. | All stated checks pass for every applicable target. |
| 40505 | `ORCH_FVT_PXEBOOT_V118` | `test_minimal_os_excluded_services` | `minimal_os` | `buildstream`, `minimal_os`, `sanity` | Verify workload-specific services are NOT active on OS-only nodes. | All stated checks pass for every applicable target. |
| 40506 | `ORCH_FVT_PXEBOOT_V119` | `test_minimal_os_package_manager` | `minimal_os` | `buildstream`, `minimal_os`, `sanity` | Verify package manager is functional on OS-only nodes. | All stated checks pass for every applicable target. |
| 40507 | `ORCH_FVT_PXEBOOT_V120` | `test_minimal_os_kernel_version` | `minimal_os` | `buildstream`, `minimal_os`, `sanity` | Verify kernel version is consistent across OS-only nodes per FG. | All stated checks pass for every applicable target. |
| 40508 | `ORCH_FVT_PXEBOOT_V121` | `test_minimal_os_network_identity` | `minimal_os` | `buildstream`, `minimal_os`, `sanity` | Verify admin IP is configured on all OS-only nodes. | All stated checks pass for every applicable target. |

### PowerVault iSCSI storage (`powervault`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 40601 | `ORCH_FVT_PXEBOOT_V400` | `test_powervault_iscsi_service` | `powervault` | `buildstream`, `powervault_infrastructure`, `sanity` | Verify iscsid is active and enabled on all PowerVault target nodes. | All stated checks pass for every applicable target. |
| 40602 | `ORCH_FVT_PXEBOOT_V401` | `test_powervault_iscsi_initiator_name` | `powervault` | `buildstream`, `powervault_infrastructure`, `sanity` | Verify iSCSI initiator name matches config on all target nodes. | All stated checks pass for every applicable target. |
| 40603 | `ORCH_FVT_PXEBOOT_V402` | `test_powervault_iscsi_discovery` | `powervault` | `buildstream`, `powervault_infrastructure`, `sanity` | Verify iSCSI target discovery succeeds from all portal IPs. | All stated checks pass for every applicable target. |
| 40604 | `ORCH_FVT_PXEBOOT_V403` | `test_powervault_iscsi_sessions` | `powervault` | `buildstream`, `powervault_infrastructure`, `sanity` | Verify iSCSI sessions are active on all target nodes. | All stated checks pass for every applicable target. |
| 40605 | `ORCH_FVT_PXEBOOT_V404` | `test_powervault_iscsi_startup_automatic` | `powervault` | `buildstream`, `powervault_infrastructure`, `sanity` | Verify iSCSI node startup is automatic on all target nodes. | All stated checks pass for every applicable target. |
| 40606 | `ORCH_FVT_PXEBOOT_V405` | `test_powervault_portal_reachability` | `powervault` | `buildstream`, `powervault_infrastructure`, `sanity` | Verify iSCSI portal ports are reachable and sessions healthy. | All stated checks pass for every applicable target. |
| 40607 | `ORCH_FVT_PXEBOOT_V406` | `test_powervault_multipath_service` | `powervault` | `buildstream`, `powervault_infrastructure`, `sanity` | Verify multipathd is active and enabled on all target nodes. | All stated checks pass for every applicable target. |
| 40608 | `ORCH_FVT_PXEBOOT_V407` | `test_powervault_multipath_device` | `powervault` | `buildstream`, `powervault_infrastructure`, `sanity` | Verify multipath device exists and matches volume_id. | All stated checks pass for every applicable target. |
| 40609 | `ORCH_FVT_PXEBOOT_V408` | `test_powervault_multipath_redundancy` | `powervault` | `buildstream`, `powervault_infrastructure`, `sanity` | Verify multipath device has multiple paths for redundancy. | All stated checks pass for every applicable target. |
| 40610 | `ORCH_FVT_PXEBOOT_V409` | `test_powervault_gpt_partition` | `powervault` | `buildstream`, `powervault_mounts`, `sanity` | Verify GPT partition exists on multipath device. | All stated checks pass for every applicable target. |
| 40611 | `ORCH_FVT_PXEBOOT_V410` | `test_powervault_filesystem_type` | `powervault` | `buildstream`, `powervault_mounts`, `sanity` | Verify filesystem formatted with correct type. | All stated checks pass for every applicable target. |
| 40612 | `ORCH_FVT_PXEBOOT_V411` | `test_powervault_mount_point_directory` | `powervault` | `buildstream`, `powervault_mounts`, `sanity` | Verify mount point directory exists on all target nodes. | All stated checks pass for every applicable target. |
| 40613 | `ORCH_FVT_PXEBOOT_V412` | `test_powervault_volume_mounted` | `powervault` | `buildstream`, `powervault_mounts`, `sanity` | Verify PowerVault volume is actively mounted on all target nodes. | All stated checks pass for every applicable target. |
| 40614 | `ORCH_FVT_PXEBOOT_V413` | `test_powervault_mount_options` | `powervault` | `buildstream`, `powervault_mounts`, `sanity` | Verify mount options applied correctly on all target nodes. | All stated checks pass for every applicable target. |
| 40615 | `ORCH_FVT_PXEBOOT_V414` | `test_powervault_fstab_entry` | `powervault` | `buildstream`, `powervault_mounts`, `sanity` | Verify persistent fstab entry created on all target nodes. | All stated checks pass for every applicable target. |
| 40616 | `ORCH_FVT_PXEBOOT_V415` | `test_powervault_node_subdirectory` | `powervault` | `buildstream`, `powervault_binds`, `sanity` | Verify per-node subdirectory exists under mount point. | All stated checks pass for every applicable target. |
| 40617 | `ORCH_FVT_PXEBOOT_V416` | `test_powervault_bind_mounts` | `powervault` | `buildstream`, `powervault_binds`, `sanity` | Verify bind mount targets are active on all target nodes. | All stated checks pass for every applicable target. |
| 40618 | `ORCH_FVT_PXEBOOT_V417` | `test_powervault_bind_fstab_entries` | `powervault` | `buildstream`, `powervault_binds`, `sanity` | Verify bind mount fstab entries are persistent on all target nodes. | All stated checks pass for every applicable target. |
| 40619 | `ORCH_FVT_PXEBOOT_V418` | `test_powervault_bind_isolation` | `powervault` | `buildstream`, `powervault_binds`, `sanity` | Verify per-node data separation via bind mounts. | All stated checks pass for every applicable target. |
| 40620 | `ORCH_FVT_PXEBOOT_V419` | `test_powervault_functional_group_targeting` | `powervault` | `buildstream`, `powervault_binds`, `sanity` | Verify PV mount only on correct functional groups. | All stated checks pass for every applicable target. |
| 40621 | `ORCH_FVT_PXEBOOT_V420` | `test_powervault_multiple_prefix_targeting` | `powervault` | `buildstream`, `powervault_binds`, `sanity` | Verify multiple prefixes target all groups correctly. | All stated checks pass for every applicable target. |
| 40622 | `ORCH_FVT_PXEBOOT_V421` | `test_powervault_setup_log` | `powervault` | `buildstream`, `powervault_cloudinit`, `sanity` | Verify cloud-init runcmd log exists and shows completion. | All stated checks pass for every applicable target. |
| 40623 | `ORCH_FVT_PXEBOOT_V422` | `test_powervault_cloud_init_groups_dict` | `powervault` | `buildstream`, `powervault_cloudinit`, `sanity` | Verify rendered iSCSI setup scripts deployed on target nodes. | All stated checks pass for every applicable target. |
| 40624 | `ORCH_FVT_PXEBOOT_V423` | `test_powervault_no_duplicate_fstab` | `powervault` | `buildstream`, `powervault_cloudinit`, `sanity` | Verify no duplicate fstab entries on all target nodes. | All stated checks pass for every applicable target. |
| 40625 | `ORCH_FVT_PXEBOOT_V424` | `test_powervault_all_mounts_writable` | `powervault` | `buildstream`, `powervault_cloudinit`, `sanity` | Verify all PV mounts (main + bind) are writable. | All stated checks pass for every applicable target. |
| 40626 | `ORCH_FVT_PXEBOOT_V425` | `test_powervault_permissions` | `powervault` | `buildstream`, `powervault_cloudinit`, `sanity` | Verify permissions on mount point match config. | All stated checks pass for every applicable target. |
| 40627 | `ORCH_FVT_PXEBOOT_V426` | `test_powervault_io_write_read` | `powervault` | `buildstream`, `powervault_mounts`, `sanity` | Verify write-read I/O succeeds on every PV mount point. | All stated checks pass for every applicable target. |
| 40628 | `ORCH_FVT_PXEBOOT_V427` | `test_powervault_bind_io` | `powervault` | `buildstream`, `powervault_binds`, `sanity` | Verify bind-mount I/O reaches the PV backing store. | All stated checks pass for every applicable target. |
| 40629 | `ORCH_FVT_PXEBOOT_V428` | `test_powervault_slurm_mandatory_bind_mounts` | `powervault` | `buildstream`, `powervault_binds`, `sanity` | Verify /var/lib/mysql and /var/spool/slurm configured as bind targets. | All stated checks pass for every applicable target. |
| 40630 | `ORCH_FVT_PXEBOOT_V429` | `test_powervault_mysql_data_on_mount` | `powervault` | `buildstream`, `powervault_binds`, `sanity` | Verify MySQL/MariaDB datadir is on a PowerVault mount. | All stated checks pass for every applicable target. |

PowerVault cases skip when `powervault_config` is absent or empty in
`storage_config.yml`.

### CoreDNS/CoreDHCP (`coredns_coredhcp`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 40701 | `ORCH_FVT_PXEBOOT_V300` | `test_coredns_container_state` | `coredns_coredhcp` | `buildstream`, `non_disruptive`, `sanity` | TC-01: coresmd containers match the dns_enabled dataset (enabled+disabled). | All stated checks pass for every applicable target. |
| 40702 | `ORCH_FVT_PXEBOOT_V301` | `test_coredns_forward_resolution` | `coredns_coredhcp` | `buildstream`, `functional`, `non_disruptive`, `sanity` | TC-02: dig FQDN from OIM for every mapped node; compare to ADMIN_IP. | All stated checks pass for every applicable target. |
| 40703 | `ORCH_FVT_PXEBOOT_V302` | `test_coredns_reverse_resolution` | `coredns_coredhcp` | `buildstream`, `functional`, `non_disruptive`, `sanity` | TC-03: dig -x from OIM for every mapped ADMIN_IP; compare to FQDN. | All stated checks pass for every applicable target. |
| 40704 | `ORCH_FVT_PXEBOOT_V303` | `test_coredhcp_multisubnet_running_image` | `coredns_coredhcp` | `buildstream`, `non_disruptive`, `sanity` | TC-04: multi-subnet dataset -> coresmd containers use expected image. | All stated checks pass for every applicable target. |
| 40705 | `ORCH_FVT_PXEBOOT_V306` | `test_coredns_idempotency` | `coredns_coredhcp` | `buildstream`, `non_disruptive`, `sanity` | TC-07: coresmd state stability (no-drift) across a settle window. | State is identical across the settle window with no spontaneous changes. |
| 40706 | `ORCH_FVT_PXEBOOT_V304` | `test_dns_compute_resolv_conf` | `coredns_coredhcp` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | TC-05: /etc/resolv.conf on every compute has CoreDNS as primary. | All stated checks pass for every applicable target. |
| 40707 | `ORCH_FVT_PXEBOOT_V305` | `test_dns_compute_forward_getent` | `coredns_coredhcp` | `buildstream`, `functional`, `non_disruptive`, `sanity`, `slurm` | TC-06: getent hosts on every compute resolves every mapped peer. | All stated checks pass for every applicable target. |
| 40708 | `ORCH_FVT_PXEBOOT_V307` | `test_dns_node_addition_pipeline` | `coredns_coredhcp` | `destructive`, `functional` | TC-08: prove SMD-to-CoreDNS pipeline resolves every mapped node. | The operation completes successfully and returns the expected result. |
| 40709 | `ORCH_FVT_PXEBOOT_V308` | `test_dns_smd_unreachable_cached_resolution` | `coredns_coredhcp` | `destructive`, `functional` | TC-09: pause SMD briefly; CoreDNS must keep serving cached records. | The node returns within the bounded wait and every stated postcondition check passes. |

### Kubernetes cluster (`kubernetes_cluster`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 40801 | `ORCH_FVT_PXEBOOT_V005` | `test_kubernetes_nodes` | `kubernetes_cluster` | `buildstream`, `kubernetes`, `sanity` | Verify mapped Kubernetes membership and Ready state. | All stated checks pass for every applicable target. |
| 40802 | `ORCH_FVT_PXEBOOT_V006` | `test_kubernetes_node_services` | `kubernetes_cluster` | `buildstream`, `kubernetes`, `sanity` | Verify required services on every Kubernetes role. | All stated checks pass for every applicable target. |
| 40803 | `ORCH_FVT_PXEBOOT_V007` | `test_kubernetes_version_compatibility` | `kubernetes_cluster` | `buildstream`, `kubernetes`, `sanity` | Verify Kubernetes, kubeadm, and CRI-O version alignment. | All stated checks pass for every applicable target. |
| 40804 | `ORCH_FVT_PXEBOOT_V519` | `test_kubernetes_configured_versions` | `kubernetes_cluster` | `buildstream`, `kubernetes`, `sanity` | Verify deployed component versions against the selected catalog. | Kubernetes components match the configured version and CRI-O matches its major/minor release. |
| 40805 | `ORCH_FVT_PXEBOOT_V008` | `test_kubernetes_control_plane` | `kubernetes_cluster` | `buildstream`, `kubernetes`, `sanity` | Verify API readiness and the configured control plane. | All stated checks pass for every applicable target. |
| 40806 | `ORCH_FVT_PXEBOOT_V009` | `test_kubernetes_system_pods` | `kubernetes_cluster` | `buildstream`, `kubernetes`, `sanity` | Verify required system, CNI, storage, and HA workloads. | All stated checks pass for every applicable target. |
| 40807 | `ORCH_FVT_PXEBOOT_V010` | `test_kubernetes_virtual_ip` | `kubernetes_cluster` | `buildstream`, `kubernetes`, `sanity` | Verify exactly one owner for the configured Kubernetes VIP. | All stated checks pass for every applicable target. |
| 40808 | `ORCH_FVT_PXEBOOT_V011` | `test_kubernetes_workload_scheduling` | `kubernetes_cluster` | `buildstream`, `functional`, `kubernetes`, `sanity` | Create, verify, and remove an isolated scheduling probe. | The isolated probe becomes ready, satisfies the stated contract, and is removed. |

### Kubernetes etcd (`kubernetes_etcd`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 40901 | `ORCH_FVT_PXEBOOT_V012` | `test_kubernetes_etcd_health` | `kubernetes_etcd` | `buildstream`, `kubernetes`, `sanity` | Verify health for all etcd endpoints. | All stated checks pass for every applicable target. |
| 40902 | `ORCH_FVT_PXEBOOT_V013` | `test_kubernetes_etcd_topology` | `kubernetes_etcd` | `buildstream`, `kubernetes`, `sanity` | Verify etcd membership, leader election, and raft consistency. | All stated checks pass for every applicable target. |
| 40903 | `ORCH_FVT_PXEBOOT_V014` | `test_kubernetes_local_etcd` | `kubernetes_etcd` | `buildstream`, `kubernetes`, `sanity` | Verify each control plane has the configured etcd mount. | All stated checks pass for every applicable target. |
| 40904 | `ORCH_FVT_PXEBOOT_V015` | `test_kubernetes_local_etcd_integrity` | `kubernetes_etcd` | `buildstream`, `kubernetes`, `sanity` | Verify disk selection, ext4 label, UUID fstab, and boot persistence. | All stated checks pass for every applicable target. |
| 40905 | `ORCH_FVT_PXEBOOT_V520` | `test_kubernetes_local_etcd_provisioning` | `kubernetes_etcd` | `kubernetes` | Verify GPT selection and local-etcd scripts, logs, and selected disk. | Every enabled control plane satisfies the provisioning contract. |
| 40906 | `ORCH_FVT_PXEBOOT_V523` | `test_kubernetes_local_etcd_media` | `kubernetes_etcd` | `kubernetes` | Verify every control plane places etcd on the configured disk media. | All stated checks pass for every applicable target. |

Local-etcd cases skip when `etcd_on_local_disk` is disabled. Integrity and
provisioning require the boot script for the current boot to finish with
`===== DONE =====`: `etcd-disk-setup.sh` on first boot, or
`etcd-fstab-update.sh` on later boots. The media case skips unless
`expected_etcd_disk_media` is set to `ssd`, `hdd`, or `nvme`.

### Kubernetes storage (`kubernetes_storage`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 41001 | `ORCH_FVT_PXEBOOT_V016` | `test_kubernetes_storage` | `kubernetes_storage` | `buildstream`, `kubernetes`, `sanity` | Verify configured NFS and PowerScale storage objects. | All stated checks pass for every applicable target. |
| 41002 | `ORCH_FVT_PXEBOOT_V017` | `test_kubernetes_default_storage_class` | `kubernetes_storage` | `buildstream`, `kubernetes`, `sanity` | Verify exactly one expected default StorageClass. | All stated checks pass for every applicable target. |
| 41003 | `ORCH_FVT_PXEBOOT_V018` | `test_kubernetes_snapshot_controller` | `kubernetes_storage` | `buildstream`, `kubernetes`, `sanity` | Verify PowerScale snapshot components when configured. | All stated checks pass for every applicable target. |
| 41004 | `ORCH_FVT_PXEBOOT_V019` | `test_kubernetes_nfs_dynamic_provisioning` | `kubernetes_storage` | `buildstream`, `functional`, `kubernetes`, `sanity` | Create and remove an isolated NFS-backed workload. | All stated checks pass for every applicable target. |
| 41005 | `ORCH_FVT_PXEBOOT_V020` | `test_kubernetes_csi_dynamic_provisioning` | `kubernetes_storage` | `buildstream`, `functional`, `kubernetes`, `sanity` | Create and remove an isolated PowerScale-backed workload. | All stated checks pass for every applicable target. |

Temporary Kubernetes resources use unique namespaces and are removed by
the creating test. CSI and snapshot checks are selected from the active
configuration.

### Slurm cluster (`slurm_cluster`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 41101 | `ORCH_FVT_PXEBOOT_V023` | `test_slurm_membership` | `slurm_cluster` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify mapped membership, healthy state, and basic hardware fields. | All stated checks pass for every applicable target. |
| 41102 | `ORCH_FVT_PXEBOOT_V024` | `test_slurm_scheduler` | `slurm_cluster` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify mapped compute nodes have healthy, available partitions. | All stated checks pass for every applicable target. |
| 41103 | `ORCH_FVT_PXEBOOT_V025` | `test_slurm_services` | `slurm_cluster` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify role and feature-specific Slurm services. | All stated checks pass for every applicable target. |
| 41104 | `ORCH_FVT_PXEBOOT_V026` | `test_slurm_cross_node_ssh` | `slurm_cluster` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify every mapped Slurm role can reach every peer over root SSH. | All stated checks pass for every applicable target. |
| 41105 | `ORCH_FVT_PXEBOOT_V027` | `test_slurm_configless_mode` | `slurm_cluster` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify configless controller access and expected cluster identity. | All stated checks pass for every applicable target. |
| 41106 | `ORCH_FVT_PXEBOOT_V028` | `test_slurm_configuration_consistency` | `slurm_cluster` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Compare authoritative Slurm files with every configless client cache. | Every compared value matches its authoritative source. |
| 41107 | `ORCH_FVT_PXEBOOT_V029` | `test_slurm_reconfigure` | `slurm_cluster` | `buildstream`, `functional`, `non_disruptive`, `sanity`, `slurm` | Reconfigure Slurm and verify membership remains healthy. | All stated checks pass for every applicable target. |
| 41108 | `ORCH_FVT_PXEBOOT_V030` | `test_slurm_hardware_discovery` | `slurm_cluster` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify runtime hardware matches the configured discovery strategy. | All stated checks pass for every applicable target. |
| 41109 | `ORCH_FVT_PXEBOOT_V031` | `test_slurm_custom_configuration` | `slurm_cluster` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify custom values, NFS delivery, and effective visibility. | All stated checks pass for every applicable target. |

### Slurm jobs (`slurm_jobs`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 41201 | `ORCH_FVT_PXEBOOT_V032` | `test_slurm_control_node_jobs` | `slurm_jobs` | `buildstream`, `functional`, `non_disruptive`, `sanity`, `slurm` | Run one targeted job per compute from every Slurm control node. | The operation completes successfully and returns the expected result. |
| 41202 | `ORCH_FVT_PXEBOOT_V033` | `test_slurm_login_node_jobs` | `slurm_jobs` | `buildstream`, `functional`, `non_disruptive`, `sanity`, `slurm` | Run one targeted job per compute from every mapped login node. | The operation completes successfully and returns the expected result. |
| 41203 | `ORCH_FVT_PXEBOOT_V034` | `test_slurm_compiler_node_jobs` | `slurm_jobs` | `buildstream`, `functional`, `non_disruptive`, `sanity`, `slurm` | Run one targeted job per compute from every login compiler node. | The operation completes successfully and returns the expected result. |
| 41204 | `ORCH_FVT_PXEBOOT_V035` | `test_slurm_concurrent_jobs` | `slurm_jobs` | `buildstream`, `functional`, `non_disruptive`, `sanity`, `slurm` | Submit concurrent jobs and verify final accounting state. | The submission completes with the expected final state and output. |
| 41205 | `ORCH_FVT_PXEBOOT_V036` | `test_slurm_insufficient_resources` | `slurm_jobs` | `buildstream`, `functional`, `negative`, `non_disruptive`, `slurm` | Verify an impossible immediate allocation is rejected. | The expected rejection occurs and no prohibited state is accepted. |
| 41206 | `ORCH_FVT_PXEBOOT_V037` | `test_slurm_job_queueing` | `slurm_jobs` | `buildstream`, `functional`, `non_disruptive`, `sanity`, `slurm` | Saturate idle computes and verify one follower queues then completes. | The follower is pending under saturation and completes after resources are released. |
| 41207 | `ORCH_FVT_PXEBOOT_V038` | `test_slurm_drain_queue_recovery` | `slurm_jobs` | `buildstream`, `disruptive`, `sanity`, `scheduler_state`, `slurm` | Drain one compute node, verify queuing, and restore it. | The job queues while the node is drained, then the node is resumed and the job completes. |

### Slurm LDAP (`slurm_ldap`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 41301 | `ORCH_FVT_PXEBOOT_V524` | `test_external_ldap_proxy` | `slurm_ldap` | `non_disruptive`, `openldap`, `sanity`, `slurm` | Reconcile and verify the explicitly enabled LDAP meta-proxy. | Reconciliation is idempotent and every postcondition passes. |
| 41302 | `ORCH_FVT_PXEBOOT_V525` | `test_external_ldap_backend` | `slurm_ldap` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify external LDAP reachability from the omnia_auth container. | All stated checks pass for every applicable target. |
| 41303 | `ORCH_FVT_PXEBOOT_V039` | `test_slurm_pam_policy` | `slurm_ldap` | `buildstream`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify SSHD, the PAM module, and pam_slurm_adopt account policy. | All stated checks pass for every applicable target. |
| 41304 | `ORCH_FVT_PXEBOOT_V040` | `test_slurm_control_ldap_authentication` | `slurm_ldap` | `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify a valid LDAP password on the Slurm control node. | All stated checks pass for every applicable target. |
| 41305 | `ORCH_FVT_PXEBOOT_V041` | `test_slurm_control_ldap_invalid_password` | `slurm_ldap` | `negative`, `non_disruptive`, `openldap`, `slurm` | Verify an invalid LDAP password is rejected on the control node. | The expected rejection occurs and no prohibited state is accepted. |
| 41306 | `ORCH_FVT_PXEBOOT_V042` | `test_slurm_login_ldap_authentication` | `slurm_ldap` | `buildstream`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify a valid LDAP password on every mapped login node. | All stated checks pass for every applicable target. |
| 41307 | `ORCH_FVT_PXEBOOT_V043` | `test_slurm_login_ldap_invalid_password` | `slurm_ldap` | `buildstream`, `negative`, `non_disruptive`, `openldap`, `slurm` | Verify an invalid LDAP password is rejected on every login node. | The expected rejection occurs and no prohibited state is accepted. |
| 41308 | `ORCH_FVT_PXEBOOT_V044` | `test_slurm_compiler_ldap_authentication` | `slurm_ldap` | `buildstream`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify a valid LDAP password on every login-compiler node. | All stated checks pass for every applicable target. |
| 41309 | `ORCH_FVT_PXEBOOT_V045` | `test_slurm_compiler_ldap_invalid_password` | `slurm_ldap` | `buildstream`, `negative`, `non_disruptive`, `openldap`, `slurm` | Verify invalid LDAP passwords are rejected on login-compiler nodes. | The expected rejection occurs and no prohibited state is accepted. |
| 41310 | `ORCH_FVT_PXEBOOT_V046` | `test_slurm_pam_no_job_access` | `slurm_ldap` | `negative`, `non_disruptive`, `openldap`, `slurm` | Verify LDAP compute login is denied without an active job. | The expected rejection occurs and no prohibited state is accepted. |
| 41311 | `ORCH_FVT_PXEBOOT_V047` | `test_slurm_invalid_ldap_identity` | `slurm_ldap` | `buildstream`, `negative`, `non_disruptive`, `openldap`, `slurm` | Verify a generated missing directory identity is rejected. | The expected rejection occurs and no prohibited state is accepted. |
| 41312 | `ORCH_FVT_PXEBOOT_V048` | `test_slurm_control_ldap_jobs` | `slurm_ldap` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Submit and complete an LDAP-owned job from the control node. | The submission completes with the expected final state and output. |
| 41313 | `ORCH_FVT_PXEBOOT_V049` | `test_slurm_control_pam_job_access` | `slurm_ldap` | `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify control-submitted PAM access during and after a job. | All stated checks pass for every applicable target. |
| 41314 | `ORCH_FVT_PXEBOOT_V050` | `test_slurm_login_ldap_jobs` | `slurm_ldap` | `buildstream`, `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Submit and complete an LDAP-owned job from every login node. | The submission completes with the expected final state and output. |
| 41315 | `ORCH_FVT_PXEBOOT_V051` | `test_slurm_login_pam_job_access` | `slurm_ldap` | `buildstream`, `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify login-node PAM access during and after a job. | All stated checks pass for every applicable target. |
| 41316 | `ORCH_FVT_PXEBOOT_V052` | `test_slurm_compiler_ldap_jobs` | `slurm_ldap` | `buildstream`, `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Submit an LDAP-owned job from every login-compiler node. | The submission completes with the expected final state and output. |
| 41317 | `ORCH_FVT_PXEBOOT_V053` | `test_slurm_compiler_pam_job_access` | `slurm_ldap` | `buildstream`, `functional`, `non_disruptive`, `openldap`, `sanity`, `slurm` | Verify login-compiler PAM access during and after a job. | All stated checks pass for every applicable target. |

The two external LDAP cases run first because the LDAP authentication and
job cases depend on the proxied directory. Every case that logs in or runs
jobs as the LDAP test identity skips unless OpenLDAP is enabled and
`validate_external_ldap: true`. `configure_external_ldap` controls only
whether the proxy case may reconcile `slapd.conf`; with it false, the case
checks the existing deployed proxy and reports mismatches as failures.
`test_slurm_pam_policy` verifies only the PAM/SSHD configuration and runs
whenever OpenLDAP is enabled.

### Slurm GPU (`slurm_gpu`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 41401 | `ORCH_FVT_PXEBOOT_V054` | `test_slurm_gpu_inventory` | `slurm_gpu` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify NVIDIA runtime state on scheduler-declared GPU nodes. | All stated checks pass for every applicable target. |
| 41402 | `ORCH_FVT_PXEBOOT_V055` | `test_slurm_gpu_job` | `slurm_gpu` | `buildstream`, `functional`, `non_disruptive`, `sanity`, `slurm` | Allocate a GPU through Slurm and query the device. | The allocation succeeds and the requested device is visible. |
| 41403 | `ORCH_FVT_PXEBOOT_V056` | `test_slurm_gpu_memory_stress` | `slurm_gpu` | `buildstream`, `functional`, `non_disruptive`, `sanity`, `slurm` | Compile and run a bounded GPU memory workload through Slurm. | Compilation and bounded workload execution complete successfully. |

### DCGM / CUDA (`slurm_dcgm`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 41501 | `ORCH_FVT_PXEBOOT_V522` | `test_dcgm_cuda_validation` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify NVIDIA driver and CUDA toolkit are installed on GPU nodes. | All stated checks pass for every applicable target. |
| 41502 | `ORCH_FVT_PXEBOOT_V502` | `test_dcgm_cuda_atomic_lock` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify CUDA toolkit is installed to /hpc_tools/cuda via atomic lock. | All stated checks pass for every applicable target. |
| 41503 | `ORCH_FVT_PXEBOOT_V508` | `test_dcgm_cuda_compute_node` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify both CUDA toolkit and CUDA driver on compute nodes. | All stated checks pass for every applicable target. |
| 41504 | `ORCH_FVT_PXEBOOT_V507` | `test_dcgm_cuda_login_compiler` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify CUDA toolkit accessible on login_compiler nodes. | All stated checks pass for every applicable target. |
| 41505 | `ORCH_FVT_PXEBOOT_V503` | `test_dcgm_package_installed` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify datacenter-gpu-manager RPM and dcgmi binary on GPU nodes. | All stated checks pass for every applicable target. |
| 41506 | `ORCH_FVT_PXEBOOT_V504` | `test_dcgm_daemon_running` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify nvidia-dcgm service is active and enabled on GPU nodes. | All stated checks pass for every applicable target. |
| 41507 | `ORCH_FVT_PXEBOOT_V505` | `test_dcgm_gpu_discovery` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify dcgmi discovery enumerates GPUs with unique UUIDs. | All stated checks pass for every applicable target. |
| 41508 | `ORCH_FVT_PXEBOOT_V506` | `test_dcgm_gpu_metrics` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify dcgmi dmon returns metric samples for each GPU node. | All stated checks pass for every applicable target. |
| 41509 | `ORCH_FVT_PXEBOOT_V509` | `test_dcgm_multi_gpu_discovery` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify dcgmi discovery on multi-GPU nodes. | All stated checks pass for every applicable target. |
| 41510 | `ORCH_FVT_PXEBOOT_V510` | `test_dcgm_multi_gpu_no_login_compiler` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify GPU nodes work without login_compiler present. | All stated checks pass for every applicable target. |
| 41511 | `ORCH_FVT_PXEBOOT_V511` | `test_dcgm_multi_login_compiler_lock` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify CUDA toolkit install uses atomic lock with multiple login_compilers. | All stated checks pass for every applicable target. |
| 41512 | `ORCH_FVT_PXEBOOT_V512` | `test_dcgm_toolkit_nfs_storage` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify /hpc_tools is NFS-mounted and CUDA toolkit accessible. | All stated checks pass for every applicable target. |
| 41513 | `ORCH_FVT_PXEBOOT_V513` | `test_dcgm_rhel_compatibility` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify GPU node OS is a supported RHEL version. | All stated checks pass for every applicable target. |
| 41514 | `ORCH_FVT_PXEBOOT_V514` | `test_dcgm_cuda_version_compatibility` | `slurm_dcgm` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify CUDA toolkit and DCGM daemon version compatibility. | All stated checks pass for every applicable target. |
| 41515 | `ORCH_FVT_PXEBOOT_V515` | `test_dcgm_neg_cuda_prerequisite` | `slurm_dcgm` | `buildstream`, `functional`, `slurm` | Verify DCGM deployment requires CUDA driver as a prerequisite. | All stated checks pass for every applicable target. |
| 41516 | `ORCH_FVT_PXEBOOT_V516` | `test_dcgm_neg_daemon_recovery` | `slurm_dcgm` | `buildstream`, `functional`, `slurm` | Simulate DCGM daemon crash via SIGKILL and verify systemd restarts it. | The node returns within the bounded wait and every stated postcondition check passes. |
| 41517 | `ORCH_FVT_PXEBOOT_V517` | `test_dcgm_neg_socket_inaccessible` | `slurm_dcgm` | `buildstream`, `functional`, `slurm` | Remove DCGM Unix socket and verify dcgmi returns a clear error. | The expected rejection occurs and no prohibited state is accepted. |
| 41518 | `ORCH_FVT_PXEBOOT_V518` | `test_dcgm_neg_package_install_failure` | `slurm_dcgm` | `buildstream`, `functional`, `slurm` | Verify error handling when datacenter-gpu-manager package is unavailable. | The expected rejection occurs and no prohibited state is accepted. |

DCGM cases skip when no GPU GRES nodes are found in the Slurm inventory.

### Slurm OpenMPI (`slurm_openmpi`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 41601 | `ORCH_FVT_PXEBOOT_V057` | `test_slurm_openmpi_installation` | `slurm_openmpi` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify OpenMPI discovery and version on every compute node. | All stated checks pass for every applicable target. |
| 41602 | `ORCH_FVT_PXEBOOT_V058` | `test_slurm_openmpi_job` | `slurm_openmpi` | `buildstream`, `functional`, `non_disruptive`, `sanity`, `slurm` | Run an OpenMPI-backed job when OpenMPI is configured. | The operation completes successfully and returns the expected result. |

### Slurm UCX (`slurm_ucx`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 41701 | `ORCH_FVT_PXEBOOT_V059` | `test_slurm_ucx_transport` | `slurm_ucx` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify UCX exposes an InfiniBand-capable transport. | All stated checks pass for every applicable target. |

### Slurm InfiniBand (`slurm_infiniband`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 41801 | `ORCH_FVT_PXEBOOT_V060` | `test_slurm_infiniband_configuration` | `slurm_infiniband` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify mapped IB interface, address, prefix, link, MTU, and OFED. | All stated checks pass for every applicable target. |
| 41802 | `ORCH_FVT_PXEBOOT_V061` | `test_slurm_infiniband_connectivity` | `slurm_infiniband` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | Verify every mapped IB endpoint can reach every mapped peer. | All stated checks pass for every applicable target. |

### Slurm Apptainer (`slurm_apptainer`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 41901 | `ORCH_FVT_PXEBOOT_V063` | `test_apptainer_runtime` | `slurm_apptainer` | `apptainer`, `buildstream`, `non_disruptive`, `sanity` | Verify the Apptainer executable and version on every compute node. | All stated checks pass for every applicable target. |
| 41902 | `ORCH_FVT_PXEBOOT_V064` | `test_apptainer_shared_artifacts` | `slurm_apptainer` | `apptainer`, `buildstream`, `non_disruptive`, `sanity` | Verify shared image directories and downloader artifacts. | All stated checks pass for every applicable target. |
| 41903 | `ORCH_FVT_PXEBOOT_V065` | `test_apptainer_pulp_policy` | `slurm_apptainer` | `apptainer`, `buildstream`, `non_disruptive`, `sanity` | Verify the generated downloader uses only the configured Pulp source. | All stated checks pass for every applicable target. |
| 41904 | `ORCH_FVT_PXEBOOT_V066` | `test_apptainer_shared_storage` | `slurm_apptainer` | `apptainer`, `buildstream`, `non_disruptive`, `sanity` | Verify /hpc_tools is a shared mounted filesystem on every compute. | All stated checks pass for every applicable target. |
| 41905 | `ORCH_FVT_PXEBOOT_V067` | `test_apptainer_download` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `image_download`, `non_disruptive`, `sanity` | Run the deployed downloader and require at least one usable SIF. | The operation completes successfully and returns the expected result. |
| 41906 | `ORCH_FVT_PXEBOOT_V068` | `test_apptainer_download_idempotency` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `image_download`, `non_disruptive`, `sanity` | Rerun the downloader and verify existing image metadata is unchanged. | The repeated operation succeeds without changing protected state. |
| 41907 | `ORCH_FVT_PXEBOOT_V069` | `test_apptainer_download_memory` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `image_download`, `non_disruptive`, `sanity` | Run the downloader and enforce a bounded peak resident-memory use. | The operation completes successfully and returns the expected result. |
| 41908 | `ORCH_FVT_PXEBOOT_V070` | `test_apptainer_image_inventory` | `slurm_apptainer` | `apptainer`, `buildstream`, `non_disruptive`, `sanity` | Verify every compute sees one consistent non-empty SIF inventory. | All stated checks pass for every applicable target. |
| 41909 | `ORCH_FVT_PXEBOOT_V071` | `test_apptainer_sif_format` | `slurm_apptainer` | `apptainer`, `buildstream`, `non_disruptive`, `sanity` | Verify each discovered image is a valid inspectable SIF. | All stated checks pass for every applicable target. |
| 41910 | `ORCH_FVT_PXEBOOT_V072` | `test_apptainer_sif_permissions` | `slurm_apptainer` | `apptainer`, `buildstream`, `non_disruptive`, `sanity` | Verify shared SIF files are non-empty and world-readable. | All stated checks pass for every applicable target. |
| 41911 | `ORCH_FVT_PXEBOOT_V073` | `test_apptainer_sif_integrity` | `slurm_apptainer` | `apptainer`, `buildstream`, `non_disruptive`, `sanity` | Verify the selected SIF has the same checksum on every compute. | All stated checks pass for every applicable target. |
| 41912 | `ORCH_FVT_PXEBOOT_V074` | `test_apptainer_ldap_readability` | `slurm_apptainer` | `apptainer`, `non_disruptive`, `sanity` | Verify the LDAP test identity can read a shared SIF when enabled. | All stated checks pass for every applicable target. |
| 41913 | `ORCH_FVT_PXEBOOT_V075` | `test_apptainer_non_root_execution` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Verify an unprivileged local identity can execute a shared SIF. | All stated checks pass for every applicable target. |
| 41914 | `ORCH_FVT_PXEBOOT_V076` | `test_apptainer_missing_image_contract` | `slurm_apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify the downloader records pull failures and exits non-zero. | The expected rejection occurs and no prohibited state is accepted. |
| 41915 | `ORCH_FVT_PXEBOOT_V077` | `test_apptainer_single_node_job` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `non_disruptive`, `sanity` | Run one exact-node container job on every mapped compute. | The operation completes successfully and returns the expected result. |
| 41916 | `ORCH_FVT_PXEBOOT_V078` | `test_apptainer_multi_node_job` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `non_disruptive`, `sanity` | Run one container allocation spanning all mapped computes. | The operation completes successfully and returns the expected result. |
| 41917 | `ORCH_FVT_PXEBOOT_V079` | `test_apptainer_ldap_job` | `slurm_apptainer` | `apptainer`, `functional`, `non_disruptive`, `sanity` | Run targeted container jobs as the configured LDAP test identity. | The operation completes successfully and returns the expected result. |
| 41918 | `ORCH_FVT_PXEBOOT_V080` | `test_apptainer_concurrent_jobs` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `non_disruptive`, `sanity` | Run bounded concurrent container jobs on distinct computes. | The operation completes successfully and returns the expected result. |
| 41919 | `ORCH_FVT_PXEBOOT_V081` | `test_apptainer_invalid_sif` | `slurm_apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify a nonexistent SIF fails through the Slurm execution path. | The expected rejection occurs and no prohibited state is accepted. |
| 41920 | `ORCH_FVT_PXEBOOT_V082` | `test_apptainer_restricted_sif` | `slurm_apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify an unprivileged identity cannot execute a mode-0600 SIF. | The expected rejection occurs and no prohibited state is accepted. |
| 41921 | `ORCH_FVT_PXEBOOT_V083` | `test_apptainer_nfs_visibility` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `non_disruptive`, `sanity` | Verify containers can read the shared image path on every compute. | All stated checks pass for every applicable target. |
| 41922 | `ORCH_FVT_PXEBOOT_V084` | `test_apptainer_slurm_environment` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `non_disruptive`, `sanity` | Verify Slurm allocation variables propagate into containers. | All stated checks pass for every applicable target. |
| 41923 | `ORCH_FVT_PXEBOOT_V085` | `test_apptainer_job_array` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `non_disruptive`, `sanity` | Submit and wait for a bounded Apptainer Slurm job array. | The submission completes with the expected final state and output. |
| 41924 | `ORCH_FVT_PXEBOOT_V086` | `test_apptainer_failure_cleanup` | `slurm_apptainer` | `apptainer`, `functional`, `negative`, `non_disruptive` | Verify a failed image launch leaves no matching runtime process. | The expected rejection occurs and no prohibited state is accepted. |
| 41925 | `ORCH_FVT_PXEBOOT_V087` | `test_apptainer_gpu_access` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `non_disruptive`, `sanity` | Verify scheduler-declared GPU nodes expose GPUs in the container. | All stated checks pass for every applicable target. |
| 41926 | `ORCH_FVT_PXEBOOT_V088` | `test_apptainer_gpu_count` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `non_disruptive`, `sanity` | Verify each container sees the same GPU count as its host. | All stated checks pass for every applicable target. |
| 41927 | `ORCH_FVT_PXEBOOT_V089` | `test_apptainer_cuda_workload` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `non_disruptive`, `sanity` | Execute a bounded NVIDIA device query in each GPU container. | The operation completes successfully and returns the expected result. |
| 41928 | `ORCH_FVT_PXEBOOT_V090` | `test_apptainer_gpu_memory` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `non_disruptive`, `sanity` | Verify the GPU query leaves no material device-memory allocation. | All stated checks pass for every applicable target. |
| 41929 | `ORCH_FVT_PXEBOOT_V091` | `test_apptainer_infiniband` | `slurm_apptainer` | `apptainer`, `buildstream`, `functional`, `non_disruptive`, `sanity` | Verify mapped compute nodes expose InfiniBand devices in containers. | All stated checks pass for every applicable target. |
| 41930 | `ORCH_FVT_PXEBOOT_V092` | `test_apptainer_reboot_storage` | `slurm_apptainer` | `apptainer`, `disruptive`, `reboot` | Reboot one compute and verify the shared mount and SIF checksum. | The node returns within the bounded wait and every stated post-reboot check passes. |
| 41931 | `ORCH_FVT_PXEBOOT_V093` | `test_apptainer_reboot_job` | `slurm_apptainer` | `apptainer`, `disruptive`, `reboot` | Run an exact-node container job after the authorized reboot. | The node returns within the bounded wait and every stated post-reboot check passes. |
| 41932 | `ORCH_FVT_PXEBOOT_V094` | `test_apptainer_reboot_artifacts` | `slurm_apptainer` | `apptainer`, `disruptive`, `reboot` | Verify downloader artifacts and policy after the authorized reboot. | The node returns within the bounded wait and every stated post-reboot check passes. |

Image download has a 20-minute ceiling with polling progress every 20
seconds. The reboot cases share one reboot state and run last in the suite.

### Slurm HPC benchmarks (`slurm_hpc_benchmarks`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 42001 | `ORCH_FVT_PXEBOOT_V200` | `test_hpc_benchmarks_json_declaration` | `slurm_hpc_benchmarks` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | TC-01: Verify benchmark_tools.list is deployed and non-empty per arch. | All stated checks pass for every applicable target. |
| 42002 | `ORCH_FVT_PXEBOOT_V201` | `test_hpc_benchmarks_local_repo_sync` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | TC-02: Verify each declared tool has files under the Pulp offline URL. | All stated checks pass for every applicable target. |
| 42003 | `ORCH_FVT_PXEBOOT_V202` | `test_hpc_benchmarks_tools_dir_creation` | `slurm_hpc_benchmarks` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | TC-03: Verify /hpc_tools directory layout and 0755 permissions. | All stated checks pass for every applicable target. |
| 42004 | `ORCH_FVT_PXEBOOT_V203` | `test_hpc_benchmarks_artifact_copy` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | TC-04: Verify declared benchmark artifacts are staged per tool. | The operation completes successfully and returns the expected result. |
| 42005 | `ORCH_FVT_PXEBOOT_V204` | `test_hpc_benchmarks_msr_safe_arch_boundary` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | TC-05: Verify msr-safe is staged only for x86_64 nodes. | All stated checks pass for every applicable target. |
| 42006 | `ORCH_FVT_PXEBOOT_V211` | `test_hpc_benchmarks_post_staging_validation` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | TC-12: Verify post-staging validation of benchmark tool directories. | All stated checks pass for every applicable target. |
| 42007 | `ORCH_FVT_PXEBOOT_V212` | `test_hpc_benchmarks_rhel_compatibility` | `slurm_hpc_benchmarks` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | TC-13: Verify every compute node runs the targeted RHEL major. | All stated checks pass for every applicable target. |
| 42008 | `ORCH_FVT_PXEBOOT_V205` | `test_hpc_benchmarks_container_first_guidance` | `slurm_hpc_benchmarks` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | TC-06: Verify pull_benchmarks.sh and benchmark_tools.list are deployed. | All stated checks pass for every applicable target. |
| 42009 | `ORCH_FVT_PXEBOOT_V206` | `test_hpc_benchmarks_source_only_delivery` | `slurm_hpc_benchmarks` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | TC-07: Verify no compile/build commands are staged with the artifacts. | All stated checks pass for every applicable target. |
| 42010 | `ORCH_FVT_PXEBOOT_V209` | `test_hpc_benchmarks_nfs_accessibility` | `slurm_hpc_benchmarks` | `buildstream`, `non_disruptive`, `sanity`, `slurm` | TC-10: Verify /hpc_tools NFS is mounted and readable on compute nodes. | All stated checks pass for every applicable target. |
| 42011 | `ORCH_FVT_PXEBOOT_V208` | `test_hpc_benchmarks_e2e_provisioning` | `slurm_hpc_benchmarks` | `non_disruptive`, `sanity`, `slurm` | TC-09: Verify the end-to-end benchmark provisioning pipeline. | All stated checks pass for every applicable target. |
| 42012 | `ORCH_FVT_PXEBOOT_V213` | `test_hpc_benchmarks_cuda_flow_unaffected` | `slurm_hpc_benchmarks` | `destructive`, `functional`, `slurm` | TC-14: Verify /hpc_tools/cuda is unchanged after benchmark staging. | All stated checks pass for every applicable target. |
| 42013 | `ORCH_FVT_PXEBOOT_V214` | `test_hpc_benchmarks_nvhpc_flow_unaffected` | `slurm_hpc_benchmarks` | `destructive`, `functional`, `slurm` | TC-15: Verify /hpc_tools/nvidia_sdk is unchanged after staging. | All stated checks pass for every applicable target. |
| 42014 | `ORCH_FVT_PXEBOOT_V215` | `test_hpc_benchmarks_container_image_unaffected` | `slurm_hpc_benchmarks` | `destructive`, `functional`, `slurm` | TC-16: Verify /hpc_tools/container_images is unchanged after staging. | All stated checks pass for every applicable target. |
| 42015 | `ORCH_FVT_PXEBOOT_V216` | `test_hpc_benchmarks_openmpi_unaffected` | `slurm_hpc_benchmarks` | `destructive`, `functional`, `slurm` | TC-17: Verify OpenMPI/UCX discovery is stable across a staging run. | All stated checks pass for every applicable target. |
| 42016 | `ORCH_FVT_PXEBOOT_V207` | `test_hpc_benchmarks_per_tool_staging_report` | `slurm_hpc_benchmarks` | `destructive`, `slurm` | TC-08: Rerun pull_benchmarks.sh and verify per-tool SUCCESS/SKIP report. | All stated checks pass for every applicable target. |
| 42017 | `ORCH_FVT_PXEBOOT_V210` | `test_hpc_benchmarks_airgapped_staging` | `slurm_hpc_benchmarks` | `destructive`, `slurm` | TC-11: Verify staging succeeds while external egress is unavailable. | All stated checks pass for every applicable target. |
| 42018 | `ORCH_FVT_PXEBOOT_V217` | `test_hpc_benchmarks_existing_dirs_preserved` | `slurm_hpc_benchmarks` | `destructive`, `slurm` | TC-18: Verify pre-existing /hpc_tools subdirs survive a staging run. | The operation completes successfully and returns the expected result. |
| 42019 | `ORCH_FVT_PXEBOOT_V218` | `test_hpc_benchmarks_staging_idempotency` | `slurm_hpc_benchmarks` | `destructive`, `slurm` | TC-19: Verify a second staging run keeps the /hpc_tools snapshot stable. | The repeated operation succeeds without changing protected state. |

### Kubernetes recovery (`kubernetes_recovery`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 42101 | `ORCH_FVT_PXEBOOT_V021` | `test_kubernetes_local_etcd_recovery` | `kubernetes_recovery` | `disruptive`, `kubernetes`, `reboot` | Reboot a control plane and prove its local-etcd UUID is preserved. | The node returns within the bounded wait and every stated post-reboot check passes. |
| 42102 | `ORCH_FVT_PXEBOOT_V022` | `test_kubernetes_control_plane_recovery` | `kubernetes_recovery` | `disruptive`, `kubernetes`, `reboot` | Reboot the VIP owner and verify control-plane recovery. | The node returns within the bounded wait and every stated post-reboot check passes. |

Both cases require two control planes and observe readiness from a node
that is not rebooted. After the reboot they wait, within bounded limits,
for a new boot ID, cloud-init, Kubernetes Ready, and healthy etcd
endpoints. The local-etcd case also requires `etcd-fstab-update.sh` to
finish on the new boot, `etcd-disk-setup.sh` not to run again, and the
mount source and UUID to be unchanged.

### Slurm recovery (`slurm_recovery`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 42201 | `ORCH_FVT_PXEBOOT_V062` | `test_slurm_cluster_recovery` | `slurm_recovery` | `disruptive`, `functional`, `reboot`, `slurm` | Reboot mapped Slurm nodes and verify scheduler and workload recovery. | The node returns within the bounded wait and every stated post-reboot check passes. |

### Slurm node lifecycle (`slurm_lifecycle`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 42301 | `ORCH_FVT_PXEBOOT_V500` | `test_slurm_node_remove` | `slurm_lifecycle` | `disruptive`, `functional`, `slurm` | Remove Slurm compute node(s) from PXE mapping, provision, verify. | The operation completes successfully and returns the expected result. |
| 42302 | `ORCH_FVT_PXEBOOT_V501` | `test_slurm_node_add` | `slurm_lifecycle` | `disruptive`, `functional`, `slurm` | Restore removed node(s) to PXE mapping, provision, verify re-addition. | The operation completes successfully and returns the expected result. |

Node removal and re-addition use `slurm_lifecycle_remove_add_nodes` from
`test_config.yml` and require the `disruptive` marker.

## Cleanup test cases

These cases execute the explicitly selected full cleanup and verify each component against the configured deletion or preservation policy.

### Lifecycle execution

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 50000 | `ORCH_FVT_CLEANUP_E001` | `test_deploy_cleanup` | `root` | `deploy`, `destructive`, `sanity` | Run ``orchestrator.yml --tags cleanup`` exactly once. | The selected Orchestrator lifecycle exits successfully. |

### OpenCHAMI (`openchami`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 50101 | `ORCH_FVT_CLEANUP_V001` | `test_openchami_removed` | `openchami` | `destructive`, `sanity` | Verify OpenCHAMI runtime, volumes, packages and state are removed. | All stated checks pass for every applicable target. |

### OpenLDAP (`openldap`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 50201 | `ORCH_FVT_CLEANUP_V002` | `test_openldap_removed` | `openldap` | `destructive`, `sanity` | Verify the OpenLDAP proxy service, container and state are removed. | All stated checks pass for every applicable target. |

### Slurm (`slurm`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 50301 | `ORCH_FVT_CLEANUP_V003` | `test_slurm_cleanup` | `slurm` | `destructive`, `sanity` | Verify Slurm's selected data policy and configured storage detachment. | All stated checks pass for every applicable target. |

### Kubernetes (`kubernetes`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 50401 | `ORCH_FVT_CLEANUP_V004` | `test_kubernetes_cleanup` | `kubernetes` | `destructive`, `sanity` | Verify Kubernetes's selected data policy and storage detachment. | All stated checks pass for every applicable target. |

### Artifacts (`artifacts`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 50501 | `ORCH_FVT_CLEANUP_V005` | `test_artifacts_removed_and_inputs_preserved` | `artifacts` | `destructive`, `sanity` | Verify generated state is removed without deleting required inputs. | All stated checks pass for every applicable target. |

### Credentials (`credentials`)

| Order | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|---:|---|---|---|---|---|---|
| 50601 | `ORCH_FVT_CLEANUP_V006` | `test_credentials_follow_selected_policy` | `credentials` | `destructive`, `sanity` | Verify credentials are removed or preserved as selected. | All stated checks pass for every applicable target. |

Cleanup verification follows the configured policy; it does not assume every
input file, credential, or externally managed data path must always be deleted.

## Markers and authorization

| Marker | Purpose |
|---|---|
| `sanity` | Default positive PXE and lifecycle coverage |
| `buildstream` | BuildStream validation subset |
| `functional` | Temporary workload or job behavior |
| `openldap`, `connectivity`, `cloudinit`, `kubernetes`, `slurm`, `apptainer`, `additional_cloud_init`, `mount_config`, `minimal_os`, `boot_image` | Capability selectors |
| `powervault_infrastructure`, `powervault_mounts`, `powervault_binds`, `powervault_cloudinit` | PowerVault subset selectors |
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
