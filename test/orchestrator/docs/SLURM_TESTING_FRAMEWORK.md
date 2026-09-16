# Slurm testing framework

Slurm follows the same platform split introduced for Kubernetes in PR #5220:

- `fvt/provision/slurm/` owns the public `provision` lifecycle execution.
- `fvt/check/slurm/` owns recursive post-deployment verification.
- the generated dataset profile is `slurm_only`.

## Complete run

```bash
cd test/orchestrator/datasets/generator
./generate_dataset.py slurm_only slurm_only
cd ../..
./run_validation.sh fvt_orchestrator provision exec --suite slurm
./run_validation.sh fvt_orchestrator check verify --suite slurm
```

The check suite covers:

- Slurm services, configuration, nodes, partitions, SSH, and jobs;
- additional cloud-init rendering;
- HPC benchmark staging and optional executable smoke tests;
- Apptainer installation, registry mirror, assets, and optional SIF smoke;
- GPU/CUDA/GRES/DCGM and optional GPU job execution;
- generated platform and provisioning artifacts;
- network, module, and role contracts;
- configured VAST and PowerVault storage.

Feature tests skip only when the corresponding optional configuration or
runtime artifact is absent. Required configured state fails with a specific
node or artifact in the assertion.

Use marker filters for focused verification:

```bash
./run_validation.sh fvt_orchestrator check verify --suite slurm --marker sanity
./run_validation.sh fvt_orchestrator check verify --suite slurm --marker functional
./run_validation.sh fvt_orchestrator check verify --suite slurm --marker hpc_benchmarks
./run_validation.sh fvt_orchestrator check verify --suite slurm --marker apptainer
./run_validation.sh fvt_orchestrator check verify --suite slurm --marker gpu
./run_validation.sh fvt_orchestrator check verify --suite slurm --marker vast
./run_validation.sh fvt_orchestrator check verify --suite slurm --marker powervault
```

VAST and PowerVault I/O round trips are marked destructive and require a
separate explicit `--marker destructive` run.
