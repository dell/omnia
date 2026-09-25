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
```

Unit tests must remain isolated: mock external commands at the helper boundary
and do not add requirements for cluster credentials, target files, or network
access.
