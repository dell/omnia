# Datasets

Each dataset is a directory under `datasets/` representing a test configuration
for `repo_manager`. The automation framework syncs these files to the
target server before running tests.

In monorepo mode, host settings (hostname, IP, domain) come from **environment
variables** on the target (set via `omnia.env` / `omnia.sh -s`), not from a
config file in the dataset.

## Dataset Generation

Datasets are generated using the generator tool in `generator/`. This avoids
duplicated configuration files and allows creating datasets for different
`repo_config` sync policy modes.

```bash
cd generator

# List available profiles (partial, always, never)
python generate_dataset.py --list-profiles

# Generate a dataset for partial sync mode (most common)
python generate_dataset.py repo_manager_partial partial

# Generate a dataset for always sync mode (full mirror)
python generate_dataset.py repo_manager_always always

# Generate a dataset for never sync mode (no repo sync)
python generate_dataset.py repo_manager_never never

# Override specific variables
python generate_dataset.py my_custom partial --var pulp_server_port=2226
```

See [`generator/README.md`](generator/README.md) for complete documentation.

## Dataset Structure

```
datasets/
  <dataset_name>/
    input/                                      # Synced to: <OMNIA_DATA_PATH>/repo_manager/input/<project>/
      repo_manager_config.yml                   # Catalog-based repository and registry configuration
      repo_manager_config_credentials.yml       # Pulp and Docker credentials
      repo_manager_endpoint_config.yml          # Pulp server endpoint configuration
      software_config.json                      # Software and OS configuration
```

### Required Files

| File | Description |
|------|-------------|
| `input/repo_manager_config.yml` | Catalog-based repository and registry configuration (repo_config, registries, repositories) |
| `input/repo_manager_config_credentials.yml` | Pulp and Docker registry credentials |
| `input/repo_manager_endpoint_config.yml` | Pulp server port, protocol, SSL certificates |
| `input/software_config.json` | Cluster OS type/version, repo sync policy, software list |

### Sync Behavior

| Setting in `test_config.yml` | What gets synced |
|------------------------------|------------------|
| `sync_repo_manager_input: true` | `input/` → `<OMNIA_DATA_PATH>/repo_manager/input/<project>/` |

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the target
server's `/etc/omnia/omnia.env` to resolve the sync destination. Directories
are created automatically if they don't exist.

## Default Mode (No Dataset)

If `dataset: ""` is set in `test_config.yml`, the framework uses files directly from
`src/repo_manager/input/` instead of a dataset. This is the recommended mode for
development as it always stays in sync with the source code.

## Profile Modes

The generator supports profiles based on `repo_config` sync policy:

| Profile | repo_config | Description |
|---------|-------------|-------------|
| `partial` | `partial` | Sync only catalog packages (most common) |
| `always` | `always` | Sync all packages from all repos (full mirror) |
| `never` | `never` | Do not sync any repositories |