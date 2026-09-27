# Orchestrator Non-Functional Tests

The NFT suite measures lifecycle duration, repeat-execution behavior, and
protection of sensitive runtime artifacts. These cases execute real
Orchestrator playbooks against the configured OIM. They are not offline unit
tests.

## Test registry

| Order | TC ID | Test | Marker | Contract |
|---:|---|---|---|---|
| 10 | `ORCH_NFT_001` | `test_precheck_performance` | `performance` | Precheck completes within its configured threshold. |
| 20 | `ORCH_NFT_002` | `test_prepare_performance` | `performance`, `destructive` | Prepare completes within its configured threshold. |
| 30 | `ORCH_NFT_005` | `test_prepare_idempotency` | `idempotency`, `destructive` | The second prepare has no persistent changes, preserves container identity, and leaves all required OpenCHAMI services ready. |
| 40 | `ORCH_NFT_003` | `test_provision_performance` | `performance`, `destructive` | Provision completes within its configured threshold. |
| 50 | `ORCH_NFT_006` | `test_precheck_idempotency` | `idempotency` | The second precheck succeeds without persistent changes. |
| 60 | `ORCH_NFT_008` | `test_credential_file_permissions` | `security` | The encrypted credential file is root-owned and mode `0600` or `0640`. |
| 61 | `ORCH_NFT_009` | `test_ssh_private_key_permissions` | `security` | `/root/.ssh/oim_rsa` is root-owned and mode `0600`. |
| 62 | `ORCH_NFT_010` | `test_log_file_permissions` | `security` | Orchestrator log files are root-owned and have no permissions for other users. |
| 63 | `ORCH_NFT_011` | `test_vault_encryption` | `security` | Product credentials have a supported Ansible Vault header and a root-owned mode-`0600` key. |
| 90 | `ORCH_NFT_004` | `test_cleanup_performance` | `performance`, `destructive` | Full cleanup completes within its configured threshold. |
| 91 | `ORCH_NFT_007` | `test_cleanup_idempotency` | `idempotency`, `destructive` | Two cleanup executions succeed, the second has no persistent changes, and every cleanup FVT postcondition passes. |

`ORCH_NFT_001` and `ORCH_NFT_006` use the current `precheck` lifecycle. They
retain the stable IDs formerly associated with the retired standalone
validation operation.

## Performance thresholds

`test_config.yml` defines the accepted wall-clock limits in seconds:

```yaml
nft_performance_threshold_seconds:
  precheck: 60
  prepare: 300
  provision: 1800
  cleanup: 180
```

These values describe the supported reference OIM using the active project
input and its current mapped-node inventory. The report records the configured
limit and measured duration. Change a limit only when the supported reference
environment or acceptance requirement changes, and document the rationale in
the same change.

## Execution

Run NFT separately from normal lifecycle FVT:

```bash
cd test/orchestrator

# Complete suite. This provisions state and finishes with full cleanup.
./run_validation.sh nft_orchestrator test

# One quality contract only.
./run_validation.sh nft_orchestrator test --marker performance
./run_validation.sh nft_orchestrator test --marker idempotency
./run_validation.sh nft_orchestrator test --marker security
```

The complete, performance, and idempotency flows mutate the target. Cleanup
uses `cleanup_credentials`, `cleanup_slurm`, and `cleanup_k8s` from
`test_config.yml`. Review those values and back up required cluster data before
execution. Do not enable FVT cleanup and NFT in the same unattended batch.

Security-only execution is observational, but required artifacts fail when
missing; absence is not reported as a successful skip.
