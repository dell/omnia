# Omnia Image Build Manager

**Ansible Galaxy Collection: `omnia.image_build`**

Build OS images (x86_64 + aarch64) for HPC cluster provisioning using OpenCHAMI.
Deploys MinIO (S3) + local container registry, builds base and compute images,
and writes `build_status.yml` with S3 artifact paths.

**Runs directly on a RHEL host** with Ansible + Python.
No container runtime required for the playbook itself (Podman is used for image builds).

## Prerequisites

| Requirement | Minimum | Validated |
|------------|---------|-----------|
| OS | RHEL 10.x, Rocky 10.x | RHEL 10.0 |
| Python | 3.12+ | 3.12.8 |
| Ansible | ansible-core 2.20+ | 2.20.0 |
| Container runtime | Podman 5.0+ | 5.3.1 |
| Disk space | 50 GB free | — |

### Ansible Installation (Common Omnia Venv)

**Recommended — use the shared Omnia venv**:

```bash
# From the Omnia repo root:
./src/main/omnia.sh --setup-venv
source /opt/omnia/venv/bin/activate
```

**Manual install** (if not using the shared venv):

```bash
python3 -m venv ~/.venvs/omnia
source ~/.venvs/omnia/bin/activate
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

**Verify**:

```bash
ansible --version          # ansible-core 2.20+
ansible-galaxy collection list | grep containers.podman
```

## Quick Start

```bash
# 1. Configure omnia.env (REQUIRED — do this first)
vi src/main/omnia.env        # Set OMNIA_ADMIN_NIC_IP at minimum

# 2. Set up the shared Omnia venv (one-time)
./src/main/omnia.sh --setup-venv
source /opt/omnia/venv/bin/activate

# 3. Ensure repo_manager output is ready
./src/main/omnia-cli repo-manager             # Check repo_manager status
# If repo_manager was NOT run, manually set up:
#   mkdir -p /opt/omnia/repo_manager/output/project_default
#   cp src/image_build_manager/samples/repo_manager_output/repo_status.yml \
#      /opt/omnia/repo_manager/output/project_default/
#   cp src/image_build_manager/samples/repo_manager_output/functional_group_packages.yml \
#      /opt/omnia/repo_manager/output/project_default/
# Edit repo_status.yml with your actual Pulp URLs and cert paths

# 4. Edit image_build_config.yml — enable functional groups to build
vi src/image_build_manager/input/project_default/image_build_config.yml

# 5. Run playbooks (cd into the playbooks directory)
cd src/image_build_manager/playbooks
ansible-playbook image_build_manager.yml --tags validate   # Validate config
ansible-playbook image_build_manager.yml --tags prepare    # Deploy MinIO + Registry
ansible-playbook image_build_manager.yml --tags build      # Build OS images
ansible-playbook image_build_manager.yml --tags cleanup    # Remove everything

# Or run sub-playbooks directly from their directory:
cd build    && ansible-playbook build_image_x86_64.yml
cd validate && ansible-playbook validate_image_build_config.yml
cd prepare  && ansible-playbook prepare_image_build_manager.yml
cd cleanup  && ansible-playbook cleanup_image_build_manager.yml
```

## Input Files

| File | Location | Required | Description |
|------|----------|----------|-------------|
| `omnia.env` | `src/main/` | Yes | Common environment variables (OMNIA_DATA_PATH, OMNIA_ADMIN_NIC_IP, etc.) |
| `image_build_config.yml` | `input/project_default/` | Yes | S3 config, functional groups, build settings |
| `repo_status.yml` | Full path via `repo_manager_output_path` | Yes | RPM repo URLs + OS metadata + cert paths + `package_list` |
| `functional_group_packages.yml` | Path from `repo_manager.package_list` in repo_status.yml | Yes | **Functional group → RPM package mapping** |
| `image_build_credentials.yml` | Auto-generated in project dir | Yes (except validate/cleanup) | S3 + aarch64 SSH credentials |

### Certificate Handling

Certificates are referenced by **absolute paths** in `repo_status.yml`:

```yaml
repo_manager:
  port: 2225
  certificates:
    server_crt: /opt/omnia/pulp/settings/certs/pulp_webserver.crt
    server_key: /opt/omnia/pulp/settings/certs/pulp_webserver.key
    certs_dir: /opt/omnia/pulp/settings/certs
```

The playbook reads the cert path directly from `repo_status.yml` and validates the file
exists on the host. No staging or copying is needed — the cert is used as-is.

## Package Resolution Flow

```
image_build_config.yml                functional_group_packages.yml
┌──────────────────────────┐          ┌──────────────────────────────────┐
│ functional_groups:       │          │ base_packages:                   │
│   - name: slurm_node_x86 │──────┐   │   - systemd                      │
│   - name: slurm_ctrl_x86 │      │   │   - kernel                       │
│   - name: os_x86_64      │      │   │   - dracut                       │
└──────────────────────────┘      │   │   - ...                          │
                                  │   │ functional_groups:               │
                                  └──>│   slurm_node_x86_64:             │
                                      │     packages:                    │
                                      │       - munge                    │
                                      │       - slurm-slurmd             │
                                      │       - ...                      │
                                      └──────────────────────────────────┘
                                                  │
                                                  ▼
                                      base_image_packages  (all images)
                                      compute_images_dict  (per functional group)
                                                  │
                                                  ▼
                                      OpenCHAMI image-build → S3 upload
```

**No `software_config.json` needed.** The `functional_group_packages.yml` file is the
single source of truth for which RPM packages belong to each functional group.

## Configuration Reference

### Environment Variables (`omnia.env`)

Host and project settings are configured via environment variables in `src/main/omnia.env`.
You can also `export` them directly in your shell.

| Variable | Description | Default |
|----------|-------------|---------|
| `OMNIA_DATA_PATH` | Root data directory for all Omnia persistent data | `/opt/omnia` |
| `OMNIA_PROJECT_NAME` | Project name (maps to input/output dirs) | `project_default` |
| `OMNIA_HOSTNAME` | OIM hostname (NOT FQDN) | `oim` |
| `OMNIA_DOMAIN_NAME` | Domain name of the OIM host | `omnia.cluster` |
| `OMNIA_ADMIN_NIC_IP` | Admin NIC IP (Pulp and S3 endpoint) | `172.16.107.254` |
| `IMAGE_BUILD_MANAGER_DATA_PATH` | Override image_build_manager data path | `${OMNIA_DATA_PATH}/image_build_manager` |
| `OMNIA_VENV_PATH` | Path to the shared Omnia Python venv | `/opt/omnia/venv` |

### `image_build_config.yml`

Per-domain configuration. Key sections:
- **`s3_configurations`** — S3 provider (minio or powerscale)
- **`repo_manager_output_path`** — full path to `repo_status.yml` (default: `/opt/omnia/repo_manager/output/project_default/repo_status.yml`)
- **`functional_groups`** — image variants to build (e.g., `os_x86_64`, `slurm_node_x86_64`)
- **`aarch64_inventory_host_ip`** — ARM build host (leave empty to skip aarch64)
- **`build_image`** — async/retry/delay settings

### `functional_group_packages.yml`

**Single source of truth** for RPM package mapping per functional group.
Located in `repo_manager_output/`. Structure:

```yaml
base_packages:         # RPMs installed in EVERY image (base OS layer)
  - systemd
  - kernel
  - ...

functional_groups:     # Additional RPMs per functional group
  slurm_node_x86_64:
    packages:
      - munge
      - slurm-slurmd
      - ...
  os_x86_64:
    packages: []       # Only base packages
```

**To customize**: Add or remove RPM package names under the appropriate functional group.
Package names must match what is available in the Pulp RPM repos defined in `repo_status.yml`.

### `repo_status.yml`

Produced by `repo_manager` at `/opt/omnia/repo_manager/output/<project_name>/repo_status.yml`.
Contains RPM repo URLs, OS metadata, certificate paths (absolute), and package list path.

Key fields consumed by image_build_manager:
- **`overall_status`** — must be `"success"` for image_build_manager to proceed
- **`cluster_os_type`** / **`cluster_os_version`** — build target OS
- **`rpm_repos.x86_64`** / **`rpm_repos.aarch64`** — RPM repository URLs
- **`repo_manager.port`** — Pulp HTTPS port (default: 2225)
- **`repo_manager.certificates.server_crt`** — absolute path to Pulp TLS cert
- **`repo_manager.package_list`** — absolute path to `functional_group_packages.yml`

See `samples/repo_manager_output/repo_status.yml` for the full structure and sample values.

**Manual setup** (if repo_manager was not run):
```bash
# Copy sample files to the runtime output directory
mkdir -p /opt/omnia/repo_manager/output/project_default
cp samples/repo_manager_output/repo_status.yml /opt/omnia/repo_manager/output/project_default/
cp samples/repo_manager_output/functional_group_packages.yml /opt/omnia/repo_manager/output/project_default/

# Edit repo_status.yml with your actual Pulp server URLs and cert paths
vi /opt/omnia/repo_manager/output/project_default/repo_status.yml

# Verify setup
./src/main/omnia-cli repo-manager
```

## Tags

| Tag | Description |
|-----|-------------|
| `validate` | Validate configuration only (no credentials required) |
| `prepare` | Deploy MinIO S3 + local container registry |
| `build` | Build x86_64 + aarch64 OS images |
| `cleanup` | Remove MinIO, registry, build artifacts, credentials |
| `upgrade` | Upgrade flow (placeholder — future release) |
| `rollback` | Rollback flow (placeholder — future release) |

## Output Paths

All runtime output goes to `<shared_path>/` (default: `/opt/omnia/image_build_manager/`):

| Path | Purpose |
|------|---------|
| `<shared_path>/output/<project_name>/` | Build output (`build_status.yml`) |
| `<shared_path>/log/<project_name>/` | Build logs (base/compute image logs) |
| `<shared_path>/log/playbooks/` | Ansible playbook logs (per-subdirectory) |
| `<shared_path>/s3/` | MinIO S3 data |
| `<shared_path>/registry/` | Local container registry storage |
| `<shared_path>/oci/` | OCI image data |
| `<shared_path>/workdir/` | OpenCHAMI image build workdir |

## CI/CD Pipeline

The `.github/workflows/ci.yml` runs on push/PR to `main`:

- **lint** — `ansible-lint` on all playbooks
- **test** — `pytest` on unit tests
- **validate-standalone** — Sets env vars, creates input dirs, runs `--tags validate --check`

## Collection Structure

```
image_build_manager/                 # omnia.image_build collection
├── galaxy.yml                       # Collection metadata (namespace: omnia, name: image_build)
├── meta/runtime.yml                 # Ansible version compatibility
├── requirements.txt                 # Python dependencies
├── requirements.yml                 # Ansible Galaxy collections
├── ansible.cfg                      # FQCN config (no path hacks)
├── plugins/                         # Galaxy-standard plugin layout
│   ├── modules/                     # Custom Ansible modules (FQCN: omnia.image_build.*)
│   ├── module_utils/                # Shared Python utilities for modules
│   └── callback/                    # Callback plugins (omnia.image_build.omnia_default)
├── roles/                           # All Ansible roles
├── playbooks/                       # All playbooks (entry point + sub-playbooks)
│   ├── image_build_manager.yml       # Entry point
│   ├── validate/                     # Input validation
│   ├── credentials/                  # Credential management
│   ├── prepare/                      # MinIO + Registry deployment
│   ├── build/                        # OS image builds (x86_64 + aarch64)
│   ├── cleanup/                      # Service and artifact cleanup
│   ├── upgrade/                      # Upgrade flow (placeholder)
│   └── rollback/                     # Rollback flow (placeholder)
├── containers/                      # Container build files (image_builder)
├── vars/                            # Shared variables
├── input/                           # User input (excluded from build)
│   └── project_default/
│       └── image_build_config.yml   # User configuration
├── samples/                         # Reference files for manual setup/testing
│   └── repo_manager_output/         # Sample repo_status.yml + functional_group_packages.yml
├── docs/                            # Domain-specific documentation
│   ├── architecture.md              # Architecture overview
│   ├── package-mapping-guide.md     # RPM package customization guide
│   ├── troubleshooting.md           # Common issues and fixes
│   ├── contracts/                   # Input/output YAML contracts
│   └── design/                      # Design documents
└── README.md                        # This file
```

### Runtime Output (auto-created at `/opt/omnia/image_build_manager/`)

```
/opt/omnia/image_build_manager/
├── output/project_default/      # build_status.yml, versioned copies
├── log/project_default/         # Base/compute image build logs
├── log/playbooks/              # Ansible playbook logs (validate.log, build.log, etc.)
├── s3/                          # MinIO S3 data
├── registry/                    # Local container registry storage
├── oci/                         # OCI image data
└── workdir/                     # OpenCHAMI image build workdir
```

## License

Apache License, Version 2.0