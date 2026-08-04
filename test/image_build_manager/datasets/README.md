# Datasets

Each dataset is a directory under `datasets/` representing a test configuration
for `image_build_manager`. The automation framework syncs these files to the
target server before running tests.

In monorepo mode, host settings (hostname, IP, domain) come from **environment
variables** on the target (set via `omnia.env` / `omnia.sh -s`), not from a
config file in the dataset.

## Dataset Structure

```
datasets/
  <dataset_name>/
    input/                              # Synced to: <OMNIA_DATA_PATH>/image_build_manager/input/<project>/
      image_build_config.yml            # Image build domain input file
      image_build_credentials.yml       # Vault-encrypted S3 credentials
    repo_manager_output/                # Synced to repo_manager_output_dir (when sync_output: true)
      repo_status.yml
      functional_group_packages.yml
      certs/
```

### Required Files

| File | Description |
|------|-------------|
| `input/image_build_config.yml` | S3 backend, repo_manager output path, functional groups, ARM host IP |
| `input/image_build_credentials.yml` | S3 and provision credentials (Vault-encrypted) |

### Sync Behavior

| Setting in `test_config.yml` | What gets synced |
|------------------------------|------------------|
| `sync_image_build_input: true` | `input/` → `<OMNIA_DATA_PATH>/image_build_manager/input/<project>/` |
| `sync_output: true` | `repo_manager_output/` → `<repo_manager_output_dir>/` from `image_build_config.yml` |

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the target
server's `/etc/omnia/omnia.env` to resolve the sync destination. Directories
are created automatically if they don't exist.

## Default Dataset: `data_set_01`

See [`data_set_01/README.md`](data_set_01/README.md) for field details.

## Creating a New Dataset

```bash
mkdir -p datasets/my_dataset/{input,repo_manager_output/certs}
# Copy and edit:
cp datasets/data_set_01/input/image_build_config.yml datasets/my_dataset/input/
cp datasets/data_set_01/input/image_build_credentials.yml datasets/my_dataset/input/
cp -r datasets/data_set_01/repo_manager_output/* datasets/my_dataset/repo_manager_output/
# Update test_config.yml:
#   dataset: "my_dataset"
```
