# Orchestrator test automation

This module provides functional (FVT), non-functional (NFT), and deterministic
unit/contract tests for `src/orchestrator` using the shared `omnia-auto`
runner.

## Setup

```bash
cd test/orchestrator
./setup_env.sh --venv
source .venv/bin/activate
```

Configure the target in `test_config.yml`. Leave `oim_server_ip` empty only
when running directly on the OIM.

## Slurm flow aligned with PR #5220

Kubernetes and Slurm use the same two-part structure:

| Platform | Deployment | Verification |
|---|---|---|
| Kubernetes | `fvt/provision/kubernetes/` | `fvt/check/kubernetes/` |
| Slurm | `fvt/provision/slurm/` | `fvt/check/slurm/` |

Generate the dataset supplied by PR #5220, deploy once, then verify the
complete recursive Slurm suite:

```bash
cd datasets/generator
./generate_dataset.py slurm_only slurm_only
cd ../..
./run_validation.sh fvt_orchestrator provision exec --suite slurm
./run_validation.sh fvt_orchestrator check verify --suite slurm
```

`check/slurm` includes core Slurm, additional cloud-init, HPC benchmarks,
Apptainer, GPU, platform/network/source contracts, VAST, and PowerVault.
Feature-specific filters are also available, for example:

```bash
./run_validation.sh fvt_orchestrator check verify --suite slurm --marker hpc_benchmarks
./run_validation.sh fvt_orchestrator check verify --suite slurm --marker apptainer
./run_validation.sh fvt_orchestrator check verify --suite slurm --marker storage
```

`test` means execute and then verify the selected lifecycle scope. Platform
deployment and post-deployment checks are intentionally separate, matching
the Kubernetes layout in PR #5220.

## Other commands

```bash
./run_validation.sh fvt_orchestrator list
./run_validation.sh fvt_orchestrator playbooks verify
./run_validation.sh fvt_orchestrator negative verify --marker negative
./run_validation.sh nft_orchestrator test --marker nft
./run_validation.sh ut_orchestrator test --marker unit
./run_validation.sh --config
```

State-changing cleanup, PXE boot, rollback, and storage I/O checks require an
explicit `--marker destructive` run.

Reports are written to `reports/` in local/unit mode or to the configured
`report_path` for a remote target. See [`docs/TEST_CASES.md`](docs/TEST_CASES.md)
for the live inventory and naming convention.
