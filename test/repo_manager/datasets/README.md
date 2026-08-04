# Datasets

Each dataset is a directory under `datasets/` representing a test configuration
for `repo_manager`. The automation framework syncs these files to the
target server before running tests.

In monorepo mode, host settings (hostname, IP, domain) come from **environment
variables** on the target (set via `omnia.env` / `omnia.sh -s`), not from a
config file in the dataset.

## Dataset Structure

```
datasets/
  <dataset_name>/
    input/                                      # Synced to: <OMNIA_DATA_PATH>/repo_manager/input/<project>/
      repo_manager_config.yml                   # Repo manager domain input file
      repo_manager_config_credentials.yml       # Pulp and Docker credentials
      repo_manager_endpoint_config.yml          # Pulp server endpoint configuration
      software_config.json                      # Software and OS configuration
```

### Required Files

| File | Description |
|------|-------------|
| `input/repo_manager_config.yml` | Repository URLs, user registries, RHEL OS repos, omnia repo URLs |
| `input/repo_manager_config_credentials.yml` | Pulp and Docker registry credentials |
| `input/repo_manager_endpoint_config.yml` | Pulp server IP, port, protocol, SSL certificates |
| `input/software_config.json` | Cluster OS type/version, repo sync policy, software list |

### Sync Behavior

| Setting in `test_config.yml` | What gets synced |
|------------------------------|------------------|
| `sync_repo_manager_input: true` | `input/` → `<OMNIA_DATA_PATH>/repo_manager/input/<project>/` |

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the target
server's `/etc/omnia/omnia.env` to resolve the sync destination. Directories
are created automatically if they don't exist.

## Default Dataset: `data_set_01`

See [`data_set_01/README.md`](data_set_01/README.md) for field details.

## Creating a New Dataset

```bash
mkdir -p datasets/my_dataset/input
# Copy and edit:
cp datasets/data_set_01/input/repo_manager_config.yml datasets/my_dataset/input/
cp datasets/data_set_01/input/repo_manager_config_credentials.yml datasets/my_dataset/input/
cp datasets/data_set_01/input/repo_manager_endpoint_config.yml datasets/my_dataset/input/
cp datasets/data_set_01/input/software_config.json datasets/my_dataset/input/
# Update test_config.yml:
#   dataset: "my_dataset"
```
