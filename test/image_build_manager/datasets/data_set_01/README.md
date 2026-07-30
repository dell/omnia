# Dataset: data_set_01

Default dataset for image_build_manager test automation.
Contains the input files and repo_manager output that the playbook needs.

---

## Structure

```
data_set_01/
├── input/                              # Synced to target: <clone_path>/src/input/<project>/
│   ├── config.yml                      # Host and project settings (also synced to <clone_path>/config.yml)
│   ├── image_build_config.yml          # Image build domain configuration
│   └── image_build_credentials.yml     # S3 and provision credentials (Vault-encrypted)
└── repo_manager_output/                # Synced to repo_manager_output_dir (from image_build_config.yml)
    ├── repo_status.yml                 # RPM repo URLs, OS version, cert paths
    ├── functional_group_packages.yml   # Package lists per functional group
    └── certs/
        ├── pulp_webserver.crt
        └── pulp_webserver.key
```

---

## input/config.yml

Top-level build configuration (legacy — monorepo uses env vars instead).

| Field | Description | Example |
|-------|-------------|---------|
| `project_name` | Project name for input/output paths | `project_default` |
| `host.hostname` | Short hostname (NOT FQDN) | `oim` |
| `host.shared_path` | Persistent storage for MinIO, registry, logs | `/opt/omnia/image_build_manager` |
| `host.domain_name` | Domain suffix. Registry = hostname.domain:5000 | `omnia.cluster` |
| `host.admin_nic_ip` | Admin NIC IP — Pulp and S3 endpoint | `<your_ip>` |

---

## input/image_build_config.yml

Image build domain input file. Controls what gets built and how.

| Section | Key Fields | Description |
|---------|------------|-------------|
| `s3_configurations` | `provider`, `endpoint_url` | S3 backend: `minio` (local) or `powerscale` (external) |
| `repo_manager_output_dir` | path | Where repo_manager output lives on target |
| `aarch64_inventory_host_ip` | IP or empty | ARM build host. Empty = skip aarch64 builds |
| `functional_groups` | list of `{name, arch}` | Groups to build (e.g., `slurm_node_x86_64`) |
| `build_image` | `job_async`, `job_retry`, `job_delay` | Async timeouts for build jobs |

---

## input/image_build_credentials.yml

Credentials for S3 and provisioning. **Reset to empty before committing.**

| Field | Description |
|-------|-------------|
| `s3_access_id` | S3 access key ID |
| `s3_secret_key` | S3 secret key |
| `provision_password` | SSH password for ARM build host (aarch64 only) |

---

## repo_manager_output/

Upstream dependency files from the `repo_manager` domain.
Synced to the path specified by `repo_manager_output_dir` in `image_build_config.yml`.

| File | Description |
|------|-------------|
| `repo_status.yml` | RPM repo URLs, OS version, cert paths, Pulp URL |
| `functional_group_packages.yml` | Package lists per functional group |
| `certs/pulp_webserver.crt` | Pulp webserver TLS certificate |
| `certs/pulp_webserver.key` | Pulp webserver TLS private key |

### Sync behavior

| Config | Target Path |
|--------|-------------|
| `sync_image_build_input: true` | `input/` → `<clone_path>/src/input/<project_name>/` |
| `sync_output: true` | `repo_manager_output/` → `<repo_manager_output_dir>/` (default: `/opt/omnia/repo_manager/output/<project_name>/`) |

> **Note:** If the target server already has repo_manager output,
> set `sync_output: false` in `test_config.yml`.
