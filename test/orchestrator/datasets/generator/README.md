# Orchestrator Dataset Generator

`generate_dataset.py` creates a repeatable snapshot from the current
`src/orchestrator/input/` tree and the current Orchestrator sample handoffs.
Profiles select which source files and sample directories are copied.

The generator does not render Jinja templates and has no `--from-src` mode;
copying the source tree is its only generation mode.

## Quick start

Run from `test/orchestrator/datasets/generator`:

```bash
# Inspect the available profiles.
./generate_dataset.py --list-profiles

# Validate generation without publishing a dataset.
./generate_dataset.py lab_k8s k8s_only --dry-run

# Publish a new dataset.
./generate_dataset.py lab_k8s k8s_only

# Confirm that a published dataset still matches its source/profile recipe.
./generate_dataset.py lab_k8s k8s_only --check
```

## Command syntax

```text
generate_dataset.py <dataset_name> <profile> [options]
generate_dataset.py --list-profiles
```

| Argument or option | Behavior |
|---|---|
| `dataset_name` | Directory name created below `datasets/` |
| `profile` | `defaults`, `k8s_only`, `slurm_only`, `k8s_and_slurm`, or another profile YAML present in `profiles/` |
| `--list-profiles` | Print available profiles and exit |
| `--dry-run` | Generate and validate in staging, publish nothing, then remove staging |
| `--check` | Regenerate in staging and fail if the published dataset differs |
| `--force` | Replace an existing dataset after staging generation succeeds |
| `--var KEY=VALUE` | Override an in-memory profile value; repeatable |

`--var` does not edit the copied YAML or CSV files. Of the current variables,
only `dcgm_enabled` is emitted in the generated README. To change product
input, create the dataset, review the generated files, and maintain an
intentional custom dataset or custom source/profile workflow. Do not assume a
variable override changed the runtime configuration.

## Profiles

| Profile | Current file selection | Profile metadata |
|---|---|---|
| `defaults` | Every `.yml` and `.csv` in `src/orchestrator/input/`, plus Repo Manager sample output | Defaults from `profiles/defaults.yml` |
| `k8s_only` | Nine named input files and both standard sample directories | `dcgm_enabled: false` |
| `slurm_only` | Nine named input files and both standard sample directories | `dcgm_enabled: true` |
| `k8s_and_slurm` | Nine named input files and both standard sample directories | `dcgm_enabled: true` |

The shipped workload profiles currently select the same files and include both
dependency handoffs. Their names and `dcgm_enabled` metadata do not rewrite
`omnia_config.yml` or `pxe_mapping_file.csv`. Therefore, the copied source
content determines the actual Kubernetes/Slurm topology. Inspect it before
synchronization.

The current unfiltered `defaults` path does not publish
`image_build_manager_output/`. Use a named profile whenever the dataset must
supply both dependency handoffs, and verify the generated file list before
enabling synchronization.

See [profiles/README.md](profiles/README.md) for the profile schema.

## Source and output

The generator reads:

```text
src/orchestrator/input/
src/orchestrator/samples/repo_manager_output/
src/orchestrator/samples/image_build_manager_output/
```

A shipped filtered profile produces:

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

The generated README records the profile, `dcgm_enabled`, copied files, and
the command needed to regenerate the dataset.

## Publication behavior

Generation occurs in a temporary staging directory below `datasets/`.

- A new dataset is copied into its final directory only after source copying
  and README generation succeed.
- An existing dataset is not replaced unless `--force` is supplied.
- `--check` compares file names, sizes, and bytes with a newly staged result.
- `--dry-run` proves that staging succeeds but does not leave the staging
  directory available for inspection.

Examples:

```bash
# Replace an existing snapshot with current source content.
./generate_dataset.py lab_k8s k8s_only --force

# Detect source/profile drift without modifying the published dataset.
./generate_dataset.py lab_k8s k8s_only --check
```

## Custom profiles

Add `<name>.yml` under `profiles/`. A profile inherits metadata from
`defaults.yml` and may define:

```yaml
dcgm_enabled: true

include_files:
  input:
    - orchestrator_config.yml
    - omnia_config.yml
    - network_spec.yml
    - pxe_mapping_file.csv
  samples:
    - repo_manager_output
    - image_build_manager_output
```

Paths in `input` are relative to `src/orchestrator/input/`. Sample names are
relative to `src/orchestrator/samples/`. A missing selected source is warned
about rather than synthesized, so review generator output and the generated
file list.

## Use the generated dataset

Set the dataset name and the desired sync flags in `test_config.yml`:

```yaml
dataset: "lab_k8s"
sync_orchestrator_input: true
sync_repo_manager_output: true
sync_image_build_manager_output: true
```

Selection alone does not copy anything. See [../README.md](../README.md) for
the destination rules and one-run overrides.
