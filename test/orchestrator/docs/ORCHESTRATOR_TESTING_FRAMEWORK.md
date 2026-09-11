# Orchestrator testing framework

The Orchestrator tests follow the shared Omnia validation-runner contract:

- `exec` runs only deploy-marked lifecycle tests.
- `verify` runs tests without changing deployment state.
- `test` runs `exec` followed by `verify` in the same selected scope.
- `--suite` selects one immediate suite directory and recursively collects it.
- `--marker` accepts one marker, comma-separated OR, or plus-separated AND.

## Structure

```text
test/orchestrator/
├── fvt/
│   ├── provision/
│   │   ├── kubernetes/       # Kubernetes deployment owner from PR #5220
│   │   └── slurm/            # Slurm deployment owner
│   ├── check/
│   │   ├── kubernetes/       # Kubernetes verification from PR #5220
│   │   ├── slurm/            # Slurm and non-K8 feature verification
│   │   └── status/
│   ├── precheck/ prepare/ deploy/ execute/ pxeboot/ cleanup/ rollback/
│   ├── playbooks/            # source/playbook contracts
│   └── negative/             # invalid-input and failure contracts
├── nft/                      # performance, idempotency, permissions
├── ut/                       # deterministic source/framework contracts
├── datasets/                 # supplied by PR #5220; unchanged here
├── library/                  # Orchestrator-specific helpers
├── _run.py
├── conftest.py
├── test_config.yml
└── test_run_config.yml
```

Module, role, and network checks are under `fvt/check/slurm/platform/`, so a
single recursive Slurm verification includes them. This follows the platform
suite model instead of adding unrelated top-level runner tags.

## Dataset handoff

The PR #5220 generator provides `slurm_only`, `k8s_only`, and
`k8s_and_slurm` profiles. Orchestrator can synchronize three inputs from a
generated dataset:

1. `input/`
2. `repo_manager_output/repo_status.yml`
3. `image_build_manager_output/build_status.yml`

Generate a local Slurm dataset with:

```bash
cd test/orchestrator/datasets/generator
./generate_dataset.py slurm_only slurm_only
```

The dataset generator and profiles are consumed as supplied by PR #5220; this
test change does not modify or commit generated dataset content.

## Safe execution

```bash
cd test/orchestrator
./run_validation.sh fvt_orchestrator provision exec --suite slurm
./run_validation.sh fvt_orchestrator check verify --suite slurm
./run_validation.sh ut_orchestrator test --marker unit
```

`check`, `playbooks`, and `negative` are verification-only. Cleanup, PXE boot,
rollback, and reversible storage I/O checks require `--marker destructive`.
The runner rejects unknown options, unsafe dataset/suite paths, invalid YAML
booleans, and ambiguous destructive commands.

## Extension rules

- Put a platform deployment trigger in `fvt/provision/<platform>/`.
- Put platform verification recursively under `fvt/check/<platform>/`.
- Give each test a unique `ORCH_FVT_<AREA>_[EV]###` ID. Existing Kubernetes
  cases retain their `TC_K8_###` IDs.
- Register new markers in both `domain_vars.py` and `conftest.py`.
- Add deterministic source or runner behavior to `ut/`.
- Keep credentials out of datasets and reports.

The unit suite enforces directory registration, suite ownership, marker
alignment, ID uniqueness/sequences, dataset handoffs, and Python/source
contracts.
