# Orchestrator Unit Tests

These tests exercise deterministic automation contracts without connecting to
an OIM, calling OpenCHAMI, or executing an Orchestrator playbook.

## Covered contracts

| Module | Coverage |
|---|---|
| `test_prepare_contracts.py` | Required container/service/API failure behavior, SMD initialization, PostgreSQL initialization and readiness, and optional OpenLDAP enablement |
| `test_pxeboot_contracts.py` | Kubernetes version parsing/skew, Slurm parsers and shared-storage selection, catalog feature resolution, mutation authorization, cloud-init interpretation, and Apptainer image-path validation |
| `test_cleanup_contracts.py` | Cleanup after Kubernetes apply failure and Slurm drain-test restoration |
| `test_nft_contracts.py` | NFT threshold validation and Ansible idempotency-recap interpretation |
| `test_k8s_ha_config_contract.py` | Kubernetes HA field typing in the `omnia_config.yml` schema, workload-aware required fields, and VIP collision/subnet checks on the deployed cluster |
| `test_additional_cloud_init_contracts.py` | Additional cloud-init input validation: disabled paths, allowed sections, prohibited keys, list types, and functional-group names |
| `test_hpc_platform_scripts.py` | Per-node RHEL HPC storage and Pulp paths, OS-dependent Slurm scripts, and offline benchmark downloads |
| `test_orchestrator_status_reconcile.py` | Lifecycle status reconciliation for external and platform-managed PXE boot results |
| `test_input_validation_fail_closed.py` | Vault-encrypted inputs are decrypted and validated with masked values, or reported unvalidated when no key exists (`ORCH_UT_102`–`104`) |
| `test_powerscale_mount_options_contract.py` | `csi_powerscale_mount_options` rsize/wsize L2 range checks, schema rsize/wsize pairing, shipped defaults, and `ps_nfsmount_conf.j2` rendering (`ORCH_UT_180`–`186`) |
| `test_kubernetes_etcd_contracts.py` | Local-etcd boot-script DONE detection, disk-media classification, root-disk exclusion, post-reboot setup-rerun detection, media expectation, and the external-LDAP identity gate |
| `test_local_storage_validation.py` | `local_storage` schema and semantic rules (ER-ORCH-011 TC-UT-001, TC-UT-004): Kafka without `fs_type` or `mount_point`, entry name in schema errors, name length boundary, etcd `mount_point` fixed at `/var/lib/etcd`, the removed `etcd_on_local_disk` key and its hint, group targeting, `nofail`, node overrides, and all errors listed together (`ORCH_UT_390`–`401`) |
| `test_local_disk_map.py` | Approved disk map built from the declaration with no row state, checksum, missing node, `kafka_disk_mapping` folder, and per-node status files (TC-UT-003, `ORCH_UT_402`–`407`) |
| `test_local_disk_prep_script.py` | `local-disk-prep.sh` with stubbed disk, LVM, mount and API commands (TC-UT-002, TC-UT-005, node logic of TC-FVT-030): selection and refusal cases C, G, H, I, J, L, Kafka and etcd fresh and reboot paths, NFS and map failures, unsafe arguments, and the label step with the disable marker (`ORCH_UT_410`–`444`) |

Parameterized cases count as separate pytest results. Function names and
docstrings carry `ORCH_UT_*` identifiers where a stable unit contract has been
assigned.

## Run through the supported runner

```bash
cd test/orchestrator
./run_validation.sh ut_orchestrator test
```

The UT category accepts `exec`, `verify`, and `test` for runner consistency;
all three execute the offline unit suite. Use `test` as the normal command.

## Run pytest directly

```bash
cd test/orchestrator
python3 -m pytest --confcutdir=ut ut -q
```

The `--confcutdir=ut` boundary is required. It prevents the parent FVT
`conftest.py` from validating target configuration, opening an OIM connection,
synchronizing datasets, or creating an FVT report during an offline unit run.

Useful development commands:

```bash
python3 -m pytest --confcutdir=ut ut/test_prepare_contracts.py -q
python3 -m pytest --confcutdir=ut ut/test_pxeboot_contracts.py -q
python3 -m pytest --confcutdir=ut ut/test_cleanup_contracts.py -q
python3 -m pytest --confcutdir=ut ut/test_nft_contracts.py -q
python3 -m pytest --confcutdir=ut ut/test_k8s_ha_config_contract.py -q
python3 -m pytest --confcutdir=ut ut/test_additional_cloud_init_contracts.py -q
python3 -m pytest --confcutdir=ut ut/test_hpc_platform_scripts.py -q
python3 -m pytest --confcutdir=ut ut/test_orchestrator_status_reconcile.py -q
python3 -m pytest --confcutdir=ut ut/test_kubernetes_etcd_contracts.py -q
python3 -m pytest --confcutdir=ut ut/test_powerscale_mount_options_contract.py -q
```

Unit tests must remain isolated: mock external commands at the helper boundary
and do not add requirements for cluster credentials, target files, or network
access.
