# Datasets

Test input configuration for the `image_build_manager` automation framework.

## Default Mode (Recommended)

By default (`dataset: ""` in `test_config.yml`), the framework reads input
files **directly from `src/`** — no dataset folder is needed:

| File | Source |
|------|--------|
| `image_build_config.yml` | `src/image_build_manager/input/` |
| `package_groups.yml` | `src/image_build_manager/input/` |
| `repo_status.yml` | `src/image_build_manager/samples/repo_manager_output/` |

This keeps test inputs in sync with the source code automatically.

## Custom Datasets

Set `dataset: "my_ds"` in `test_config.yml` to use a custom dataset
from `datasets/<name>/`. Generate one with the dataset generator:

```bash
cd datasets/generator/
python generate_dataset.py my_ds defaults
python generate_dataset.py my_ds --from-src
```

See [`generator/README.md`](generator/README.md) for full usage.

### Custom Dataset Structure

```
datasets/<name>/
  input/
    image_build_config.yml
    image_build_credentials.yml
    package_groups.yml
  repo_manager_output/
    repo_status.yml
```

## Switching Datasets

### Edit `test_config.yml`
```yaml
dataset: "my_custom_ds"    # Use custom dataset
dataset: ""                # Use src/ (default)
```

### Per-scenario override in `test_run_config.yml`
```yaml
scenarios:
  prepare:
    dataset: "my_custom_ds"
    sync_input: true
```

### Environment variable (one-off)
```bash
OMNIA_DATASET_OVERRIDE=my_custom_ds ./run_validation.sh build verify
```

**Priority**: env var > per-scenario override > `test_config.yml` default.

## Sync Behavior

| Setting | What gets synced |
|---------|------------------|
| `sync_image_build_input: true` | `input/` → target server |
| `sync_output: true` | `repo_manager_output/` → target server |

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the
target server to resolve sync destinations.
