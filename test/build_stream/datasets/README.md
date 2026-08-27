# Datasets

Test input configuration for the `build_stream` automation framework.

## Default Mode (Recommended)

By default (`dataset: ""` in `test_config.yml`), the framework reads input
files **directly from the deployed system**:

| File | Source |
|------|--------|
| `build_stream_config.yml` | `/opt/omnia/build_stream/input/<project_name>/` |

This reads the live configuration from the target server.

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
    build_stream_config.yml
    build_stream_credentials.yml
  README.md
```

## Switching Datasets

### Edit `test_config.yml`
```yaml
dataset: "my_custom_ds"    # Use custom dataset
dataset: ""                # Use deployed system config (default)
```

### Per-scenario override in `test_run_config.yml`
```yaml
scenarios:
  gitlab_install:
    dataset: "my_custom_ds"
    sync_input: true
```

### Environment variable (one-off)
```bash
OMNIA_DATASET_OVERRIDE=my_custom_ds ./run_validation.sh gitlab_install verify
```

**Priority**: env var > per-scenario override > `test_config.yml` default.

## Sync Behavior

| Setting | What gets synced |
|---------|------------------|
| `sync_build_stream_input: true` | `input/` → target server |

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the
target server to resolve sync destinations.
