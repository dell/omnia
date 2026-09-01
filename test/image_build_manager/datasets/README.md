# Datasets

Test input configuration for the `image_build_manager` automation framework.

## Default Mode (Recommended)

By default (`dataset: ""` in `test_config.yml`), no generated dataset folder is
needed. The target keeps using its existing runtime files. If a sync option is
enabled, the corresponding local sync source comes directly from `src/`:

| File | Source |
|------|--------|
| `image_build_config.yml` | `src/image_build_manager/input/` |
| `package_groups.yml` | `src/image_build_manager/input/` |
| `repo_status.yml` | `src/image_build_manager/samples/repo_manager_output/` |

With both sync flags disabled, nothing is copied and execution reads the files
already present on the target under `$OMNIA_DATA_PATH`.

## Custom Datasets

Set `dataset: "my_ds"` in `test_config.yml` to select a custom local sync
source from `datasets/<name>/`. Generate one with the source-first generator:

```bash
cd datasets/generator/
./generate_dataset.py profiles
./generate_dataset.py profiles internet-config
./generate_dataset.py create my_ds --profile internet-config --dry-run
./generate_dataset.py create my_ds --profile internet-config
```

The recommended `internet-config` profile uses public repositories and minimal
public package groups. For an offline dataset, supply one real Repo Manager
host for every generated URL:

```bash
./generate_dataset.py create my_offline --profile offline-config \
  --repo-host repo.company.internal
```

Replace `repo.company.internal` with the real Repo Manager hostname or IP
reachable from the execution environment.

Generated YAML retains applicable source headings and guidance. Stale source
comments are normalized when they no longer match the current consumer
contract. Environment-specific dummy values have inline
`# REPLACE WITH REAL VALUE` guidance; the dataset README repeats the same
checklist.

Enable `sync_image_build_input` and/or `sync_output` when the selected files
must be copied to the execution target. Setting `dataset` alone does not replace
files that already exist on the target.

See [`generator/README.md`](generator/README.md) for full usage.

### Custom Dataset Structure

```
datasets/<name>/
  input/
    image_build_config.yml
    package_groups.yml
  repo_manager_output/
    repo_status.yml
  dataset_manifest.yml
  README.md
```

Datasets never contain credentials. From `test/image_build_manager` on the
execution OIM, create the separate encrypted runtime pair with
`./setup_env.sh --set-domain-creds`. The framework never transfers that YAML,
its vault key, or backups. For remote execution, run the command on the target
OIM.

## Switching Datasets

### Edit `test_config.yml`
```yaml
dataset: "my_custom_ds"    # Use custom dataset
dataset: ""                # Use src/ only as an optional sync source
```

### Per-scenario override in `test_run_config.yml`
```yaml
fvt_image_build_manager:
  prepare:
    dataset: "my_custom_ds"
    sync_input: true
```

### Environment variable (one-off)
```bash
OMNIA_DATASET_OVERRIDE=my_custom_ds \
  ./run_validation.sh fvt_image_build_manager build verify
```

For a direct invocation, `OMNIA_DATASET_OVERRIDE` takes priority over the
`test_config.yml` default. For a batch run, the priority is top-level
`dataset_override`, per-FVT `dataset`, the inherited environment override, and
then the `test_config.yml` default.

## Sync Behavior

| Setting | What gets synced |
|---------|------------------|
| `sync_image_build_input: true`, named dataset | Only `datasets/<name>/input/` → execution OIM; credential artifacts are excluded |
| `sync_image_build_input: true`, empty dataset | Canonical `src/image_build_manager/input/` → execution OIM; credential artifacts are excluded |
| `sync_output: true`, named dataset | Only `datasets/<name>/repo_manager_output/` → execution OIM |
| `sync_output: true`, empty dataset | `src/image_build_manager/samples/repo_manager_output/` → execution OIM |

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the
target server to resolve sync destinations.
