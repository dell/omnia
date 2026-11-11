# Orchestrator Dataset Profiles

Profiles are YAML recipes consumed by `generate_dataset.py`. They merge
metadata over `defaults.yml` and optionally restrict the source files copied
into a dataset.

Profiles do not render or patch Orchestrator input. The source YAML and CSV
content is copied byte-for-byte.

## Shipped profiles

| Profile | Input selection | Samples | Metadata |
|---|---|---|---|
| `defaults` | All top-level `.yml` and `.csv` files in `src/orchestrator/input/` | Repo Manager output in the current unfiltered path | `dcgm_enabled: true` |
| `k8s_only` | Explicit nine-file list | Repo Manager and Image Build Manager output | `dcgm_enabled: false` |
| `slurm_only` | Explicit nine-file list | Repo Manager and Image Build Manager output | `dcgm_enabled: true` |
| `k8s_and_slurm` | Explicit nine-file list | Repo Manager and Image Build Manager output | `dcgm_enabled: true` |

The three workload profiles currently select identical files. Their names do
not remove roles from `pxe_mapping_file.csv` or clusters from
`omnia_config.yml`. Always inspect the copied input before using the dataset.
They also explicitly select both dependency handoffs; use one of these named
profiles when Image Build Manager output must be present in the dataset.

## Profile schema

```yaml
# Metadata inherited from or overriding defaults.yml.
dcgm_enabled: true

# Optional source-selection filter.
include_files:
  input:
    - additional_cloud_init.yml
    - high_availability_config.yml
    - network_spec.yml
    - omnia_config.yml
    - orchestrator_config.yml
    - pxe_mapping_file.csv
    - security_config.yml
    - set_pxe_boot_config.yml
    - storage_config.yml
  samples:
    - repo_manager_output
    - image_build_manager_output
```

`input` entries are relative to `src/orchestrator/input/`. `samples` entries
are relative to `src/orchestrator/samples/`.

If `include_files` is absent, the generator copies every top-level `.yml` and
`.csv` input. The current unfiltered implementation publishes Repo Manager
sample output but omits Image Build Manager sample output. If `include_files`
is present, only named entries are considered. A missing selected source
produces a warning; it is not generated from a template.

## Commands

Run from `test/orchestrator/datasets/generator`:

```bash
./generate_dataset.py --list-profiles

./generate_dataset.py k8s_dataset_01 k8s_only --dry-run
./generate_dataset.py k8s_dataset_01 k8s_only
./generate_dataset.py k8s_dataset_01 k8s_only --check
./generate_dataset.py k8s_dataset_01 k8s_only --force
```

`--check` compares a published dataset with a fresh staging result. `--force`
replaces an existing dataset. `--dry-run` publishes nothing and removes its
temporary staging directory before exit.

## Create a custom profile

1. Copy the closest profile to `<new_name>.yml` in this directory.
2. Keep the Dell copyright and Apache license header.
3. Select only source files and sample directories required by the scenario.
4. Run `--dry-run` and review every copied-file message.
5. Publish the dataset and inspect its generated README and input content.

Example:

```yaml
---
dcgm_enabled: false

include_files:
  input:
    - orchestrator_config.yml
    - omnia_config.yml
    - network_spec.yml
    - pxe_mapping_file.csv
    - storage_config.yml
  samples:
    - repo_manager_output
    - image_build_manager_output
```

File selection alone does not make a workload-specific scenario. The selected
source `omnia_config.yml`, PXE mapping, network specification, and storage
configuration must already describe a consistent scenario.

## Related documentation

- [Generator CLI](../README.md)
- [Dataset selection and synchronization](../../README.md)
- [Orchestrator test automation](../../../README.md)
