# Slurm tests

The authoritative Slurm verification tree is `fvt/check/slurm/`. It includes
core cluster tests and all non-Kubernetes feature suites.

Run deployment and verification separately:

```bash
cd test/orchestrator
./run_validation.sh fvt_orchestrator provision exec --suite slurm
./run_validation.sh fvt_orchestrator check verify --suite slurm
```

This mirrors PR #5220’s Kubernetes structure (`provision/kubernetes` plus
`check/kubernetes`) and prevents a platform suite from executing the generic
root provision trigger a second time.

See [`SLURM_TESTING_FRAMEWORK.md`](SLURM_TESTING_FRAMEWORK.md) for feature
filters and [`TEST_CASES.md`](TEST_CASES.md) for IDs and collection commands.
