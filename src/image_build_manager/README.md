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
# From the repository root
cd src/main

# Configure the host, create the shared virtual environment, stage domain
# inputs, and copy the sample catalog to $OMNIA_DATA_PATH/catalog/.
vi omnia.env
sudo ./omnia.sh -s
source /etc/profile.d/omnia-env.sh

# Edit the staged project input. Run repo_manager before the image build.
vi "$OMNIA_DATA_PATH/image_build_manager/input/$OMNIA_PROJECT_NAME/image_build_config.yml"
./omnia.sh --run repo_manager --tags execute

# Validate, prepare infrastructure, and build images.
./omnia.sh --run image_build_manager --tags validate
./omnia.sh --run image_build_manager --tags prepare
./omnia.sh --run image_build_manager --tags build
```

For direct playbook execution, source `/etc/profile.d/omnia-env.sh`, activate
`$OMNIA_VENV_PATH/bin/activate`, and run commands from
`src/image_build_manager/playbooks/`.

---

## Tags

| Tag | Description | Credentials |
|-----|-------------|-------------|
| `precheck` | Environment and connectivity check | No |
| `validate` | Schema + logic config validation | No |
| `credentials` | Collect or update S3 and aarch64 credentials | Yes |
| `prepare` | Deploy local MinIO when selected, plus the OCI registry | Yes |
| `build` / `execute` | Build x86_64 + aarch64 OS images | Yes |
| `cleanup` | Remove services, artifacts, credentials | No |
| `cleanup_images` | Delete built images from S3 + registry (by pattern or all) | No |
| `upgrade` / `rollback` | Reserved placeholders; no lifecycle action is implemented | Yes (current flow) |

Run exactly one supported tag at a time. Although internal imported plays carry
`x86_64` and `aarch64` tags, the top-level tag validator does not accept them as
public tags; a `build` or `execute` run builds every configured architecture.

### Full Domain Cleanup (`cleanup`)

The public cleanup removes MinIO, the OCI registry, build outputs, runtime data,
logs, `image_build_credentials.yml`, and its vault key. The shared `output/` and
`log/` roots are preserved as empty directories. It does not prompt for a second
credential decision:

```bash
cd src/main
sudo ./omnia.sh --run image_build_manager --tags cleanup
```

The standalone cleanup playbook supports `--skip-tags credentials` only when
credentials must intentionally be retained. `domain-init.sh --cleanup` is a
non-interactive initializer helper that removes only staged input and domain log
paths; it does not remove services or build outputs. After every domain cleanup
tag has completed, `sudo ./omnia.sh --cleanup --all` performs the guarded global
reset. Both global cleanup modes prompt for `yes`; trusted automation can add
`--skip-approval`.

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

S3 deletion requires `s3cmd` plus `/root/.s3cfg`; registry deletion requires
`regctl` plus an active service or managed registry storage. Missing tooling is
reported and that side of cleanup is skipped.

---

## Input / Output

### Input

| File | Source | Required |
|------|--------|----------|
| `image_build_config.yml` | Runtime `input/<project>/` | Yes |
| `repo_status.yml` | `repo_manager_output_path` | Build/execute/default flow |
| `package_groups.yml` | Runtime `input/<project>/` | When `functional_groups_source: "config"` |
| `catalog_rhel.json` | `CATALOG_FILE_PATH` env var | When `functional_groups_source: "catalog"` |
| `image_build_credentials.yml` | Auto-generated and Vault-encrypted | Credentials/prepare/build/default flow |

### Output

| File | Location | Description |
|------|----------|-------------|
| `build_status.yml` | `output/<project>/` | Producing image engine and per-group S3 artifact paths for provisioning |

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
| **Build controls** | `build_image.max_parallel`, `build_image.build_timeout`, `build_image.force_rebuild`, `build_image.backup_s3_images`, `build_image.repo_ssl_verify` |
| **ARM** | `aarch64_inventory_host_ip`, `aarch64_ssh_user` |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SYSTEM_ADMIN_NIC_IPV4` | **required** | Admin NIC IPv4 (S3 + registry endpoint) |
| `SYSTEM_HOSTNAME` | **required** | Short hostname of the OIM host |
| `SYSTEM_DOMAIN_NAME` | **required** | OIM domain name |
| `OMNIA_DATA_PATH` | `/opt/omnia` | Root data directory; must be exported for direct playbook runs |
| `OMNIA_VERSION` | **required** | Version embedded in generated image names |
| `OMNIA_PROJECT_NAME` | `project_default` | Project name |
| `IMAGE_BUILD_MANAGER_DATA_PATH` | `${OMNIA_DATA_PATH}/image_build_manager` | Optional controller-side domain data-path override |
| `CATALOG_FILE_PATH` | `${OMNIA_DATA_PATH}/catalog/catalog_rhel.json` | Catalog JSON path (when `functional_groups_source: "catalog"`) |

---

## AArch64 Build Host

### Prerequisites

| Requirement | Details |
|------------|---------|
| Architecture | ARM64 (`uname -m` = `aarch64`) |
| OS | RHEL 10.x / Rocky 10.x |
| Podman | 5.0+ (for builder container image) |
| SSH | SSH password for initial key installation; passwordless SSH is then configured automatically |
| Network | IP reachable from OIM admin NIC; port 22 open |
| Internet | Optional only when the builder image is available through Pulp and the ARM `regctl` binary is already staged on OIM; otherwise upstream registry/GitHub access is needed |
| Disk | 30 GB free in the configured image-build data path |

### Constraints

- **Single node only**: The `admin_aarch64` inventory group must contain exactly one host.
- **Work directory follows `OMNIA_DATA_PATH`**: the remote path is constructed
  as the controller's `OMNIA_DATA_PATH` plus `/image_build_manager`. It defaults
  to `/opt/omnia/image_build_manager/` and does not follow a separate
  `IMAGE_BUILD_MANAGER_DATA_PATH` override.
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
- `image-thrillhouse` uses `ghcr.io/openchami/image-thrillhouse:v0.0.24` on both
  architectures. `image-builder` uses the architecture-specific Omnia images
  `image-build-el10:1.3` and `image-build-aarch64:1.3` from Docker Hub.
- Separate hosts are required for each architecture

### Configuration

Set in `image_build_config.yml`:

```yaml
aarch64_inventory_host_ip: "10.20.0.2"   # ARM node IP
aarch64_ssh_user: "root"                  # SSH user (shipped value: root)
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

Groups defined in the shipped `package_groups.yml` are shown below. Config mode
builds only architecture-matching groups with a non-empty `packages` list;
the `os_*` and Kubernetes entries are currently skipped because they are empty.

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

### Data Path (`$IMAGE_BUILD_MANAGER_DATA_PATH`)

The domain path defaults to `$OMNIA_DATA_PATH/image_build_manager`:

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
+-- precheck.log              Precheck sub-playbook log
+-- prepare.log               Prepare sub-playbook log
+-- rollback.log              Rollback placeholder log
+-- upgrade.log               Upgrade placeholder log
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
