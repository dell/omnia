# Dataset Generator — Repo Manager

Renders Jinja2 templates into test dataset directories for repo_manager FVT.

## Quick Start

```bash
# Generate from a profile
python generate_dataset.py my_ds defaults

# Copy directly from src/repo_manager/input/
python generate_dataset.py my_ds --from-src

# List available profiles
python generate_dataset.py --list-profiles

# Regenerate with overrides
python generate_dataset.py my_ds defaults --var pulp_server_port=2225 --force
```

## Profiles

| Profile | Description |
|---------|-------------|
| `defaults` | Base profile with placeholder values |
| `rhel10` | RHEL 10 specific configuration |
| `minimal` | Minimal configuration for basic testing |

Override any key with `--var KEY=VALUE` (repeatable).

## Generated Files

```
datasets/<name>/
  input/
    repo_manager_config.yml      # Repository configuration
    repo_manager_endpoint_config.yml # Endpoint configuration
  README.md                      # Auto-generated summary
```

## Adding New Profiles

1. Create `profiles/<name>.yml` with overrides
2. `defaults.yml` is always loaded first as the base
3. Profile values override defaults (deep-merge)

Example `profiles/my_env.yml`:
```yaml
pulp_server_port: 2226
repo_config: "always"
caching_policy: false
```

## Alignment

This generator follows the same pattern as:
- `test/build_stream/datasets/generator/`
- `test/orchestrator/datasets/generator/`

## Usage in Testing

After generating a dataset, update `test_config.yml`:

```yaml
dataset: "my_custom_ds"    # Use custom dataset
dataset: ""                # Use deployed system config (default)
```

## Dataset Synchronization

When `dataset` is set and `sync_repo_manager_input: true`, the framework automatically syncs the dataset to the target server before test execution.