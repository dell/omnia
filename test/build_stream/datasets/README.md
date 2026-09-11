# Datasets

Test input configuration for the `build_stream` automation framework.

## Default Mode (Recommended)

By default (`dataset: ""`), input synchronization is disabled and the target
is left unchanged. If `sync_build_stream_input: true`, the source is:

| File | Source |
|------|--------|
| `build_stream_config.yml` | `src/build_stream/input/` |

The destination is resolved from `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME`
on the execution OIM.

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
  README.md
```

## Switching Datasets

### Edit `test_config.yml`
```yaml
dataset: "my_custom_ds"    # Use custom dataset
dataset: ""                # Use canonical src input when sync is enabled
```

### Per-scenario override in `test_run_config.yml`
```yaml
fvt_build_stream:
  buildstream_install:
    dataset: "my_custom_ds"
    sync_input: true
```

### Environment variable (one-off)
```bash
OMNIA_DATASET_OVERRIDE=my_custom_ds \
  ./run_validation.sh fvt_build_stream buildstream_install verify
```

**Priority**: env var > per-scenario override > `test_config.yml` default.

## Sync Behavior

| Setting | What gets synced |
|---------|------------------|
| `sync_build_stream_input: true` | `input/` → target server |

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the
target server to resolve sync destinations.

Credential files and vault keys are not dataset artifacts and are excluded
from synchronization. Configure them on the execution OIM with
`./setup_env.sh --set-domain-creds`.
