# Orchestrator Test Datasets

Datasets are named, local snapshots of Orchestrator input plus the Repo
Manager and Image Build Manager handoff files used by FVT synchronization.
They are useful for repeatable lab scenarios; they are not required when the
execution OIM already contains the desired project state.

## Default mode

The safest default is:

```yaml
dataset: ""
sync_orchestrator_input: false
sync_repo_manager_output: false
sync_image_build_manager_output: false
```

This preserves the target OIM's active input and dependency outputs. A
verification-only run then observes the existing project without replacing
its files.

When a synchronization flag is enabled while `dataset` remains empty, the
framework uses the canonical source tree:

| Flag | Local source |
|---|---|
| `sync_orchestrator_input` | `src/orchestrator/input/` |
| `sync_repo_manager_output` | `src/orchestrator/samples/repo_manager_output/` |
| `sync_image_build_manager_output` | `src/orchestrator/samples/image_build_manager_output/` |

## Generate a dataset

Use the generator instead of manually assembling a dataset:

```bash
cd test/orchestrator/datasets/generator

./generate_dataset.py --list-profiles
./generate_dataset.py my_k8s_dataset k8s_only --dry-run
./generate_dataset.py my_k8s_dataset k8s_only
```

Other shipped profiles are `slurm_only`, `k8s_and_slurm`, and `defaults`.
See [generator/README.md](generator/README.md) for the exact CLI and an
important description of what profiles do and do not change.

## Select and synchronize a dataset

Set the dataset name and enable only the data classes that the test is allowed
to replace:

```yaml
dataset: "my_k8s_dataset"
sync_orchestrator_input: true
sync_repo_manager_output: true
sync_image_build_manager_output: true
```

Selecting a dataset without a sync flag validates its structure but does not
copy that data class to the OIM. Domain credentials are never dataset content
and are never synchronized by this mechanism.

The destination project is resolved from the target's environment:

- Orchestrator input uses `ORCHESTRATOR_DATA_PATH` when set, otherwise
  `$OMNIA_DATA_PATH/orchestrator`.
- Repo Manager output uses `REPO_MANAGER_DATA_PATH` when set, otherwise
  `$OMNIA_DATA_PATH/repo_manager`.
- Image Build Manager output uses `IMAGE_BUILD_MANAGER_DATA_PATH` when set,
  otherwise `$OMNIA_DATA_PATH/image_build_manager`.
- Every destination is scoped by `OMNIA_PROJECT_NAME`.

## One-run overrides

The same selection can be supplied without editing `test_config.yml`:

```bash
OMNIA_DATASET_OVERRIDE=my_k8s_dataset \
OMNIA_SYNC_INPUT_OVERRIDE=true \
OMNIA_SYNC_OUTPUT_OVERRIDE=true \
OMNIA_SYNC_IMAGE_OUTPUT_OVERRIDE=true \
./run_validation.sh fvt_orchestrator precheck test
```

Batch scenarios in `test_run_config.yml` expose equivalent `dataset`,
`sync_input`, `sync_output`, and `sync_image_output` fields.

## Dataset structure

```text
datasets/<dataset_name>/
├── input/
│   ├── additional_cloud_init.yml
│   ├── high_availability_config.yml
│   ├── network_spec.yml
│   ├── omnia_config.yml
│   ├── orchestrator_config.yml
│   ├── pxe_mapping_file.csv
│   ├── security_config.yml
│   ├── set_pxe_boot_config.yml
│   └── storage_config.yml
├── repo_manager_output/
│   └── repo_status.yml
├── image_build_manager_output/
│   └── build_status.yml
└── README.md
```

This is the structure selected by the shipped profiles at the time of this
writing. The generator reads the profile's `include_files` list, so the
generated README and directory contents are authoritative if a profile later
changes.

## Validation and safety

Before session startup, the framework validates the selected dataset and the
enabled synchronization contracts. Dataset names cannot traverse outside this
directory, and dataset directories or content symlinks are rejected.

Synchronization is an explicit write to the target project. Review the
selected dataset, project name, target OIM, and sync flags before using a
`test` or `exec` command.
