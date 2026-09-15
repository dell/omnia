# Orchestrator test-case registry

The filesystem and pytest collection are the source of truth for this suite.
Every test function has a unique ID checked by `ORCH_UT_047`; the runner,
suite, and dataset contracts are checked by the remaining unit tests.

## Layout

| Scope | Deployment owner | Verification scope | Dataset profile |
|---|---|---|---|
| Kubernetes | `fvt/provision/kubernetes/` | `fvt/check/kubernetes/` | `k8s_only` |
| Slurm | `fvt/provision/slurm/` | `fvt/check/slurm/` | `slurm_only` |
| Slurm features | same Slurm provision owner | nested below `fvt/check/slurm/` | `slurm_only` |

The Slurm feature tree includes additional cloud-init, HPC benchmarks,
Apptainer, GPU, platform artifacts, VAST, and PowerVault. Feature checks are
not deployment owners; they verify the state produced by the public
`provision`/`execute` lifecycle.

Other FVT areas remain available at their lifecycle paths: `precheck`,
`validate`, `prepare`, `deploy`, `execute`, `pxeboot`, `cleanup`, and
`rollback`. Source-contract tests are in `playbooks` and invalid-input tests
are in `negative`.

## ID convention

- Non-Kubernetes FVT: `ORCH_FVT_<AREA>_E###` for execution and
  `ORCH_FVT_<AREA>_V###` for verification.
- Kubernetes IDs inherited from PR #5220 remain `TC_K8_###`.
- NFT: `ORCH_NFT_###`.
- Unit tests: `ORCH_UT_###`.

IDs are gap-free within each family and unique across test functions.

## Live inventory

Use collection rather than maintaining a second hand-written test list:

```bash
cd test/orchestrator
./run_validation.sh fvt_orchestrator list
./run_validation.sh nft_orchestrator list
./run_validation.sh ut_orchestrator list
python3 -m pytest fvt --collect-only -q
```

At this revision, pytest collects 273 FVT cases, 11 NFT cases, and 143 unit
test invocations. Parameterized tests account for the difference between
function count and collected-case count.

## Slurm flow

Generate the dataset supplied by PR #5220, deploy through the Slurm provision
suite, and verify the complete Slurm tree:

```bash
cd test/orchestrator/datasets/generator
./generate_dataset.py slurm_only slurm_only
cd ../..
./run_validation.sh fvt_orchestrator provision exec --suite slurm
./run_validation.sh fvt_orchestrator check verify --suite slurm
```

The same flow can be enabled in `test_run_config.yml` and run with
`./run_validation.sh --config`. Dataset content is generated locally and is
not committed by this change.

Destructive `cleanup`, `pxeboot`, and `rollback` execution requires the
explicit `--marker destructive` opt-in.
