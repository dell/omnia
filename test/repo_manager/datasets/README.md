# Datasets

Test input configuration for the `repo_manager` automation framework.

## Default Mode (Recommended)

By default (`dataset: ""` in `test_config.yml`), the framework reads input
files **directly from the deployed system**:

| File | Source |
|------|--------|
| `repo_manager_config.yml` | `/opt/omnia/repo_manager/input/<project_name>/` |
| `repo_manager_endpoint_config.yml` | `/opt/omnia/repo_manager/input/<project_name>/` |

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
    repo_manager_config.yml
    repo_manager_endpoint_config.yml
  README.md
```

## Switching Datasets

### Edit `test_config.yml`
```yaml
dataset: "my_custom_ds"    # Use custom dataset
dataset: ""                # Use deployed system config (default)
```

### Environment variable (one-off)
```bash
OMNIA_DATASET_OVERRIDE=my_custom_ds ./run_validation.sh scenario verify
```

**Priority**: env var > `test_config.yml` default.

## Sync Behavior

| Setting | What gets synced |
|---------|------------------|
| `sync_repo_manager_input: true` | `input/` → target server |

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the
target server to resolve sync destinations.

## Available Profiles

The dataset generator supports the following profiles:

| Profile | Description |
|---------|-------------|
| `defaults` | Base profile with standard configuration |
| `rhel10` | RHEL 10 specific configuration |
| `minimal` | Minimal configuration for basic testing |

Generate with different profiles:
```bash
python generate_dataset.py my_ds defaults
python generate_dataset.py my_ds rhel10
python generate_dataset.py my_ds minimal
```