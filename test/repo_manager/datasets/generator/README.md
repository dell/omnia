# Dataset Generator

Generates test datasets from Jinja2 templates and YAML variable profiles.

## Overview

The generator replaces duplicated YAML configuration files across datasets with:
- A single set of Jinja2 templates in `templates/`
- YAML variable profiles in `profiles/` that define what changes between datasets
- A Python script that renders templates with profile variables

## Profiles

Profiles define different `repo_config` sync policy modes:

| Profile | repo_config | Description |
|---------|-------------|-------------|
| `defaults` | `partial` | Base profile — used when no override needed |
| `partial` | `partial` | Sync only catalog packages (most common) |
| `always` | `always` | Sync all packages from all repos (full mirror) |
| `never` | `never` | Do not sync any repositories |

## Usage

```bash
cd datasets/generator

# List available profiles
python generate_dataset.py --list-profiles

# Generate a dataset for partial sync mode
python generate_dataset.py repo_manager_partial partial

# Generate a dataset for always sync mode
python generate_dataset.py repo_manager_always always

# Generate a dataset for never sync mode
python generate_dataset.py repo_manager_never never

# Override a specific variable
python generate_dataset.py my_custom partial --var pulp_server_port=2226

# Regenerate an existing dataset (overwrites files)
python generate_dataset.py repo_manager_partial partial --force

# Copy files directly from src/ (no template rendering)
python generate_dataset.py repo_manager_from_src --from-src
```

## Output

Generated datasets are created in `../<dataset_name>/`:

```
datasets/
├── repo_manager_partial/
│   ├── README.md
│   └── input/
│       ├── repo_manager_config.yml
│       ├── repo_manager_endpoint_config.yml
│       ├── repo_manager_config_credentials.yml
│       └── software_config.json
```

## Using a Dataset

Edit `test_config.yml` to use the generated dataset:

```yaml
dataset: "repo_manager_partial"
```

Then run tests:

```bash
./run_validation.sh repo_manager test
```

## Template Variables

The following variables can be overridden via profiles or `--var`:

- `repo_config`: Global sync policy (`always`, `partial`, `never`)
- `pulp_server_port`: Pulp server port (default: `2225`)
- `pulp_server_crt`: Path to Pulp server certificate
- `pulp_server_key`: Path to Pulp server key
- `pulp_certs_dir`: Path to Pulp certificates directory
- `pulp_username`: Pulp admin username
- `pulp_password`: Pulp admin password
- `docker_username`: Docker Hub username
- `docker_password`: Docker Hub password
- `user_registry_credentials`: List of private registry credentials
- `cluster_os_type`: OS type (default: `rhel`)
- `cluster_os_version`: OS version (default: `10.0`)
- `registries`: Container registry configurations
- `repositories`: RPM repository configurations

## Profile Structure

Profiles use a merge strategy:
1. Load `defaults.yml` (base configuration)
2. Merge with specified profile (e.g., `partial.yml`)
3. Apply CLI `--var` overrides
4. Render templates with final variables

## From-src Mode

The `--from-src` mode copies configuration files directly from `src/repo_manager/input/` without template rendering. This is useful when you want to test with the exact source configuration without any modifications.