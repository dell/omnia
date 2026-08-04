# Image Build Manager

**Collection**: `omnia.image_build` v3.0.0

Builds OS images (RHEL/Rocky x86_64 + aarch64) for HPC cluster provisioning
using OpenCHAMI. Deploys MinIO S3 + local OCI registry, builds per-functional-group
images, and writes `build_status.yml` for downstream consumption by `orchestrator`.

---

## Prerequisites

| Requirement | Minimum | Validated |
|------------|---------|-----------|
| OS | RHEL 10.x, Rocky 10.x | RHEL 10.0 |
| Python | 3.12+ | 3.12.8 |
| Ansible | ansible-core 2.20+ | 2.20.0 |
| Podman | 5.0+ | 5.3.1 |
| Disk | 50 GB free | -- |

---

## Quick Start

```bash
# 1. Set up environment
export SYSTEM_ADMIN_NIC_IPV4=<your_admin_ip>

# 2. Ensure repo_manager output exists
#    (run repo_manager first, or copy sample files)
mkdir -p /opt/omnia/repo_manager/output/project_default
cp samples/repo_manager_output/repo_status.yml \
   /opt/omnia/repo_manager/output/project_default/

# 2b. For catalog mode: copy catalog JSON
mkdir -p /opt/omnia/catalog
cp samples/repo_manager_output/catalog_rhel.json \
   /opt/omnia/catalog/

# 3. Initialize domain (creates log dir + copies input files)
vi input/project_default/image_build_config.yml
sudo ./domain-init.sh

# 4. Run
cd playbooks
ansible-playbook image_build_manager.yml --tags validate
ansible-playbook image_build_manager.yml --tags prepare
ansible-playbook image_build_manager.yml --tags build
ansible-playbook image_build_manager.yml --tags cleanup
```

---

## Tags

| Tag | Description | Credentials |
|-----|-------------|-------------|
| `precheck` | Environment and connectivity check | No |
| `validate` | L1 schema + L2 logic config validation | No |
| `prepare` | Deploy MinIO S3 + OCI container registry | Yes |
| `build` / `execute` | Build x86_64 + aarch64 OS images | Yes |
| `cleanup` | Remove services, artifacts, credentials | No |
| `upgrade` | Upgrade flow (placeholder) | Yes |
| `rollback` | Rollback flow (placeholder) | Yes |

Sub-tags: `x86_64`, `aarch64` (run specific architecture only).

---

## Input / Output

### Input

| File | Source | Required |
|------|--------|----------|
| `image_build_config.yml` | `input/project_default/` | Yes |
| `repo_status.yml` | repo_manager output | Yes |
| `package_groups.yml` | `input/project_default/` | When `functional_groups_source: "config"` |
| `catalog_rhel.json` | `CATALOG_FILE_PATH` env var | When `functional_groups_source: "catalog"` |
| `image_build_credentials.yml` | Auto-generated (Vault) | Yes (except validate/cleanup) |

### Output

| File | Location | Consumer |
|------|----------|----------|
| `build_status.yml` | `output/<project>/` | orchestrator |

See `docs/contracts/` for full contract specifications.

---

## Configuration

### `image_build_config.yml`

| Section | Key Fields |
|---------|-----------|
| **S3 storage** | `s3_configurations.provider` (minio / powerscale), `endpoint_url` |
| **Upstream** | `repo_manager_output_path` (path to `repo_status.yml`) |
| **Builder** | `image_build_type` (image-builder / image-thrillhouse) |
| **Groups** | `functional_groups_source` (`config` / `catalog`) |
| **Concurrency** | `build_image.max_parallel`, `job_async`, `job_retry`, `job_delay` |
| **ARM** | `aarch64_inventory_host_ip`, `aarch64_ssh_user` |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SYSTEM_ADMIN_NIC_IPV4` | **required** | Admin NIC IPv4 (S3 + registry endpoint) |
| `OMNIA_DATA_PATH` | `/opt/omnia` | Root data directory |
| `OMNIA_PROJECT_NAME` | `project_default` | Project name |
| `CATALOG_FILE_PATH` | `${OMNIA_DATA_PATH}/catalog/catalog_rhel.json` | Catalog JSON path (when `functional_groups_source: "catalog"`) |

---

## Collection Structure

```
image_build_manager/
+-- galaxy.yml
+-- meta/runtime.yml
+-- CHANGELOG.md
+-- ansible.cfg
+-- domain-init.sh
+-- plugins/
|   +-- modules/                          10 modules (FQCN: omnia.image_build.*)
|   |   +-- validate_image_build_config.py    L1+L2 config validation
|   |   +-- validate_system_environment.py    Env var + system validation
|   |   +-- validate_yaml_schema.py           Generic JSON Schema validator
|   |   +-- image_build_orchestrator.py       Parallel build with concurrency
|   |   +-- image_package_collector.py        RPM packages per functional group
|   |   +-- base_image_package_collector.py   Base image RPM packages
|   |   +-- generate_functional_groups.py     Functional groups from CSV
|   |   +-- functional_group_parser.py        Normalize group input
|   |   +-- parse_catalog.py                  Catalog JSON → RPM package resolution (layer-name classification)
|   |   +-- parse_repo_status.py              repo_status.yml → repo lists + OS facts
|   +-- module_utils/
|   |   +-- input_validation/             L1+L2 validation framework
|   |   |   +-- core/                     Config, file utils, validation engine
|   |   |   +-- messages/                 Centralized error messages
|   |   |   +-- schema/                   JSON Schema files (4 schemas)
|   |   |   +-- validators/              L2 business logic validators
|   |   +-- build_image/                  Build constants, config, helpers
|   +-- callback/
|       +-- omnia_default.py              Custom callback plugin
+-- roles/                                10 roles
|   +-- image_build_setup                 Setup: load env, validate prereqs, parse repo_status
|   +-- validate_image_build_input        L1+L2 config validation
|   +-- validate_build_runtime            Runtime environment checks
|   +-- collect_build_credentials         S3 + SSH credential prompts (Vault)
|   +-- deploy_minio                      MinIO S3 via Podman Quadlet
|   +-- deploy_registry                   OCI registry via Podman Quadlet + regctl
|   +-- fetch_build_packages              Dual-mode package resolution (config/catalog)
|   +-- prepare_aarch64_node              Prepare ARM build host
|   +-- build_os_images                   OpenCHAMI image builds + S3 upload + regctl verify
|   +-- cleanup_build_artifacts           Remove services + artifacts
+-- playbooks/
|   +-- image_build_manager.yml           Entry point
|   +-- validate/                         Config validation sub-playbook
|   +-- credentials/                      Credential collection sub-playbook
|   +-- prepare/                          MinIO + Registry sub-playbook
|   +-- build/                            x86_64 + aarch64 build sub-playbooks
|   +-- cleanup/                          Cleanup sub-playbook
|   +-- upgrade/                          Upgrade sub-playbook (placeholder)
|   +-- rollback/                         Rollback sub-playbook (placeholder)
+-- input/project_default/               Default input config
+-- samples/repo_manager_output/         Sample upstream contract files
+-- containers/image_builder/            Image builder container (Dockerfile)
+-- vars/                                Shared variables (S3 buckets, commands)
+-- docs/                                Domain documentation
```

---

## Functional Groups

### Config Mode (`functional_groups_source: "config"`)

Functional groups derived from `package_groups.yml` keys (filtered by architecture suffix).
OS type and version from `os` / `os_version` fields in `package_groups.yml`.

Available groups in default `package_groups.yml`:

| x86_64 | aarch64 |
|--------|---------|
| `os_x86_64` | `os_aarch64` |
| `slurm_node_x86_64` | `slurm_node_aarch64` |
| `slurm_control_node_x86_64` | `login_node_aarch64` |
| `login_node_x86_64` | `login_compiler_node_aarch64` |
| `login_compiler_node_x86_64` | |
| `service_kube_control_plane_first_x86_64` | |
| `service_kube_control_plane_x86_64` | |
| `service_kube_node_x86_64` | |

### Catalog Mode (`functional_groups_source: "catalog"`)

Full names auto-detected from `catalog.functionallayer[]`.
OS type from baseos group's `os` field; version from `os_version` field.

Example groups from a typical catalog:

| x86_64 | aarch64 |
|--------|---------|
| `baseos_rhel_10_0_x86_64` | `baseos_rhel_10_0_aarch64` |
| `slurm_node_rhel_10_0_x86_64` | `slurm_node_rhel_10_0_aarch64` |
| `slurm_control_node_rhel_10_0_x86_64` | `slurm_control_node_rhel_10_0_aarch64` |
| `login_node_rhel_10_0_x86_64` | `login_node_rhel_10_0_aarch64` |
| `login_compiler_node_rhel_10_0_x86_64` | `login_compiler_node_rhel_10_0_aarch64` |
| `service_kube_control_plane_first_rhel_10_0_x86_64` | |
| `service_kube_control_plane_rhel_10_0_x86_64` | |
| `service_kube_node_rhel_10_0_x86_64` | |

---

## Runtime Paths

### Data Path (`$OMNIA_DATA_PATH/image_build_manager/`)

```
/opt/omnia/image_build_manager/
+-- input/<project>/          Staged input files
+-- output/<project>/         build_status.yml
+-- log/<project>/            Domain runtime logs (validation, build)
+-- s3/                       MinIO data
+-- registry/                 OCI registry storage
+-- oci/                      OCI image data
+-- workdir/                  OpenCHAMI build workdir
```

### Ansible Log Path (`/var/log/omnia/image_build_manager/`)

All Ansible playbook execution logs are flat (no subfolders) under a single directory:

```
/var/log/omnia/image_build_manager/
+-- image_build_manager.log   Main playbook log
+-- build_image.log           Build sub-playbook log
+-- cleanup.log               Cleanup sub-playbook log
+-- credentials.log           Credentials sub-playbook log
+-- prepare.log               Prepare sub-playbook log
+-- rollback.log              Rollback sub-playbook log
+-- upgrade.log               Upgrade sub-playbook log
+-- validate.log              Validate sub-playbook log
```

> **Note**: This directory must exist before running playbooks (`ansible.cfg` cannot
> create parent directories). Use one of:
> - **Automatic**: `sudo ./domain-init.sh` (creates log dir + copies input files)
> - **Manual**: `sudo mkdir -p /var/log/omnia/image_build_manager`
> - **Override**: `export ANSIBLE_LOG_PATH=/path/to/custom.log`

---

## Documentation

| Document | Description |
|----------|-------------|
| `docs/architecture.md` | Execution flow, role dependency, data contracts |
| `docs/package-mapping-guide.md` | RPM package customization guide |
| `docs/troubleshooting.md` | Common issues and fixes |
| `docs/contracts/input-contract.md` | Input file specifications |
| `docs/contracts/output-contract.md` | Output file specifications |
| `docs/design/` | Design documents |
| `docs/design/catalog-migration-design.md` | Catalog migration design (dual-mode package resolution) |

---

## License

Apache License, Version 2.0