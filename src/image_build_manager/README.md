# Image Build Manager

**Collection**: `omnia.image_build` v2.3.0

Builds OS images (RHEL/Rocky x86_64 + aarch64) for HPC cluster provisioning
using OpenCHAMI. Deploys MinIO S3 + local OCI registry, builds per-functional-group
images, and writes `build_status.yml` for downstream consumption by the provisioning workflow.

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
mkdir -p $OMNIA_DATA_PATH/repo_manager/output/$OMNIA_PROJECT_NAME
cp samples/repo_manager_output/repo_status.yml \
   $OMNIA_DATA_PATH/repo_manager/output/$OMNIA_PROJECT_NAME/

# 2b. For catalog mode: copy catalog JSON
mkdir -p $OMNIA_DATA_PATH/catalog
cp samples/repo_manager_output/catalog_rhel.json \
   $OMNIA_DATA_PATH/catalog/

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
| `validate` | Schema + logic config validation | No |
| `prepare` | Deploy MinIO S3 + OCI container registry | Yes |
| `build` / `execute` | Build x86_64 + aarch64 OS images | Yes |
| `cleanup` | Remove services, artifacts, credentials | No |
| `cleanup_images` | Delete built images from S3 + registry (by pattern or all) | No |

Sub-tags: `x86_64`, `aarch64` (run specific architecture only).

### Image Cleanup (`cleanup_images`)

Delete built OS images from S3 buckets and OCI registry without tearing down
the MinIO/registry infrastructure itself. Supports pattern-based deletion.

```bash
# Delete ALL images (prompts for confirmation)
ansible-playbook image_build_manager.yml --tags cleanup_images

# Delete images matching a pattern
ansible-playbook image_build_manager.yml --tags cleanup_images \
  -e cleanup_image_pattern="rhel-slurm_*"

# Delete only a specific functional group
ansible-playbook image_build_manager.yml --tags cleanup_images \
  -e cleanup_image_pattern="rhel-os_x86_64*"

# Skip approval prompt (for automation)
ansible-playbook image_build_manager.yml --tags cleanup_images \
  -e skip_approval=true
```

| Extra Variable | Default | Description |
|---------------|---------|-------------|
| `cleanup_image_pattern` | `*` | Glob pattern for images to delete |
| `skip_approval` | `false` | Skip interactive approval prompt (for automation) |

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

| File | Location | Description |
|------|----------|-------------|
| `build_status.yml` | `output/<project>/` | Per-group S3 artifact paths for provisioning |

See `samples/` for example input and output files.

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

## AArch64 Build Host

### Prerequisites

| Requirement | Details |
|------------|---------|
| Architecture | ARM64 (`uname -m` = `aarch64`) |
| OS | RHEL 10.x / Rocky 10.x |
| Podman | 5.0+ (for builder container image) |
| SSH | Passwordless SSH from OIM (`ssh-copy-id` — automated by `setup_ssh.yml`) |
| Network | IP reachable from OIM admin NIC; port 22 open |
| Internet | Optional — required only if Pulp registry is unavailable (for direct image pull and regctl download) |
| Disk | 30 GB free in `/opt/omnia/image_build_manager/` |

### Constraints

- **Single node only**: The `admin_aarch64` inventory group must contain exactly one host.
- **Work directory is fixed**: `/opt/omnia/image_build_manager/` on the aarch64 node.
  The remote node does not run `omnia.sh` and does not use `OMNIA_DATA_PATH`.
- **regctl installation**: Binary is pre-downloaded on the OIM to
  `$OMNIA_DATA_PATH/image_build_manager/aarch64/regctl-linux-arm64`,
  then SCP'd to `/usr/local/bin/regctl` on the aarch64 node. If SCP
  fails, direct download from GitHub is attempted as a fallback.
- **Builder image pull**: Tries the OIM's Pulp-based repo manager registry
  first, then falls back to upstream DockerHub/GHCR.
- **No NFS**: Build artifacts use local directories on the aarch64 node
  (no shared filesystem required).

### Cross-Architecture Building

**Important**: Cross-architecture building is **NOT supported**.

- image-thrillhouse requires native architecture builds
- aarch64 builds require a separate aarch64 host
- x86_64 builds run on the OIM host
- The `--arch` flag in image-thrillhouse is for manifest expansion, not cross-compilation
- No QEMU/emulation support for cross-arch builds

**Current Implementation**:
- x86_64 builds: Run directly on OIM host
- aarch64 builds: Orchestrate via SSH to dedicated aarch64 node
- Both architectures use `ghcr.io/openchami/image-thrillhouse:v0.0.24`
- Separate hosts are required for each architecture

### Configuration

Set in `image_build_config.yml`:

```yaml
aarch64_inventory_host_ip: "10.20.0.2"   # ARM node IP
aarch64_ssh_user: "root"                  # SSH user (default: root)
```

Set in `image_build_credentials.yml` (auto-encrypted with Ansible Vault):

```yaml
aarch64_ssh_password: "<password>"        # Only for initial ssh-copy-id
```

Leave `aarch64_inventory_host_ip` empty to skip aarch64 builds entirely.

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
| `docs/architecture.md` | Execution flow, tag reference, role dependency |
| `docs/package-mapping-guide.md` | RPM package customization guide |
| `docs/troubleshooting.md` | Common issues and fixes |
| `docs/contracts/input-contract.md` | Input file specifications |
| `docs/contracts/output-contract.md` | Output file specifications |

---

## License

Apache License, Version 2.0
