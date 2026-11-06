# Image Build Manager

Image Build Manager (`omnia.image_build`) builds stateless RHEL/Rocky OS images for x86_64 and aarch64 nodes with OpenCHAMI Image Thrillhouse. It deploys MinIO S3 and a local OCI registry, builds one image per functional group, and writes `build_status.yml` for Orchestrator.

## Overview

Image Build Manager automates OS image creation for HPC and AI clusters by:

- Deploying MinIO S3 object storage for image artifacts
- Deploying local OCI registry for container image storage
- Building stateless bootable OS images (RHEL/Rocky) for x86_64 and aarch64
- Supporting dual-mode functional groups: config-based and catalog-driven
- Integrating with OpenCHAMI Image Thrillhouse as the build engine
- Producing `build_status.yml` with kernel, initrd, and rootfs artifact locations

### Related modules

| Direction | Module | Contract |
|-----------|--------|----------|
| Upstream | Repository Manager | `repo_status.yml` (repository endpoints and certificates) |
| Downstream | Orchestrator | `build_status.yml` (kernel, initrd, rootfs S3 locations) |
| Automation | Build Stream | Its build pipeline invokes this module |

## Architecture

Image Build Manager uses OpenCHAMI Image Thrillhouse as the sole image build engine. The domain supports:

- **Dual functional group modes**: Config mode uses `package_groups.yml`, catalog mode uses JSON catalog
- **Multi-architecture**: x86_64 builds run on OIM, aarch64 builds run on dedicated ARM node
- **Storage backends**: MinIO S3 for image artifacts, local OCI registry for container images
- **Image reuse**: Global dictionary lookup for catalog mode, per-group cache for config mode

### Roles

Roles are invoked as `omnia.image_build.<role>`.

| Role | Description |
|------|-------------|
| [`build_os_images`](roles/build_os_images/README.md) | Build base and compute OS images for HPC cluster provisioning |
| [`cleanup_build_artifacts`](roles/cleanup_build_artifacts/README.md) | Clean up build artifacts and temporary files from the image build process |
| [`collect_build_credentials`](roles/collect_build_credentials/README.md) | Collect and prepare credentials for the image build process |
| [`deploy_minio`](roles/deploy_minio/README.md) | Deploy MinIO S3-compatible object storage for image build artifacts |
| [`deploy_registry`](roles/deploy_registry/README.md) | Deploy local OCI container registry for storing built OS images |
| [`fetch_build_packages`](roles/fetch_build_packages/README.md) | Collect and resolve RPM packages for OS image building |
| [`image_build_setup`](roles/image_build_setup/README.md) | Setup role for image build — loads config, validates environment, checks prerequisites |
| [`precheck_environment`](roles/precheck_environment/README.md) | Validate environment prerequisites (env vars, hostname, IP, domain, omnia.sh setup) before running any image_build_manager playbook |
| [`prepare_aarch64_node`](roles/prepare_aarch64_node/README.md) | Prepare ARM64 build hosts for cross-architecture image building |
| [`validate_build_runtime`](roles/validate_build_runtime/README.md) | Validate build environment runtime dependencies and versions |
| [`validate_image_build_input`](roles/validate_image_build_input/README.md) | Validate input configuration files for the image build process |

### Modules

Modules are invoked as `omnia.image_build.<module>`.

| Module | Description |
|--------|-------------|
| `base_image_package_collector` | Collect RPM packages for base image creation |
| `functional_group_parser` | Parse and normalize functional group input |
| `generate_functional_groups` | Generate functional_groups.yaml from a CSV mapping file |
| `image_build_orchestrator` | Orchestrate parallel OS image builds with concurrency control |
| `image_package_collector` | Collect RPM packages per functional group for image builds |
| `load_validated_yaml` | Load literal runtime YAML without Jinja evaluation |
| `manage_image_group_dictionary` | Query and update the catalog image-group dictionary |
| `parse_catalog` | Parse catalog JSON and resolve packages by architecture |
| `parse_repo_status` | Parse repo_status.yml and build per-architecture repo lists |
| `validate_image_build_config` | Validate image build configuration files |
| `validate_repo_status_contract` | Validate repo_status.yml for image build execution |
| `validate_system_environment` | Validate Omnia environment variables against system state |
| `validate_yaml_schema` | Validate YAML file against JSON Schema |

### Plugins

| Plugin | Type | Description |
|--------|------|-------------|
| `omnia_default` | Callback | Custom Ansible stdout callback plugin for Omnia |

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | RHEL 10.0, 10.2; Rocky 10.x | Runs on the OIM; see the [support matrix](https://omnia.readthedocs.io/en/latest/Reference/SupportMatrix/index.html) |
| Python | 3.12+ | Shared Omnia virtual environment |
| Ansible | ansible-core 2.20+ | Pinned in `requirements.txt` |
| Podman | 5.0+ | Container runtime |
| Disk | 50 GB free |  |

## Installation

Run the shared setup once from the repository root. It creates the Omnia virtual environment, runs every domain's `domain-init.sh` (dependencies, log directories, input staging) and installs the default catalog if none is active.

```bash
cd src/main
vi omnia.env                       # first run only; afterwards edit /etc/omnia/omnia.env
sudo ./omnia.sh --setup-venv
source /etc/profile.d/omnia-env.sh
```

To re-run only this module's initializer (for example after editing source inputs):

```bash
sudo ./omnia.sh --init image_build_manager
```

## Configuration

### `image_build_config.yml`

| Section | Key Fields |
|---------|-----------|
| **S3 storage** | `s3_configurations.provider` (minio / powerscale), `endpoint_url` |
| **Upstream** | `repo_manager_output_path` (optional override; empty uses the current Repo Manager project output) |
| **Build engine** | OpenCHAMI Image Thrillhouse (fixed) |
| **Groups** | `functional_groups_source` (`config` / `catalog`) |
| **Build controls** | `build_image.max_parallel`, `build_image.build_timeout`, `build_image.force_rebuild`, `build_image.backup_s3_images`, `build_image.repo_ssl_verify` |
| **ARM** | `aarch64_inventory_host_ip`, `aarch64_ssh_user` |

### Environment variables

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

### AArch64 build host

#### Requirements

| Requirement | Details |
|------------|---------|
| Architecture | ARM64 (`uname -m` = `aarch64`) |
| OS | RHEL 10.0, 10.2; Rocky 10.x |
| Podman | 5.0+ (for builder container image) |
| SSH | SSH password for initial key installation; passwordless SSH is then configured automatically |
| Network | IP reachable from OIM admin NIC; port 22 open |
| Internet | Optional only when the builder image is available through Pulp and the ARM `regctl` binary is already staged on OIM; otherwise upstream registry/GitHub access is needed |
| Disk | 30 GB free in the configured image-build data path |

#### Constraints

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

#### Cross-architecture building

**Important**: Cross-architecture building is **NOT supported**.

- image-thrillhouse requires native architecture builds
- aarch64 builds require a separate aarch64 host
- x86_64 builds run on the OIM host
- The `--arch` flag in image-thrillhouse is for manifest expansion, not cross-compilation
- No QEMU/emulation support for cross-arch builds

**Current Implementation**:
- x86_64 builds: Run directly on OIM host
- aarch64 builds: Orchestrate via SSH to dedicated aarch64 node
- `image-thrillhouse` uses `ghcr.io/openchami/image-thrillhouse:v0.0.26` on both
  architectures using the same pinned Image Thrillhouse container from GHCR.
- The default, cadence, RHEL 10.0, RHEL 10.2, and hybrid catalogs under
  `src/main/samples/` pin the same Image Thrillhouse `v0.0.26` tag. Unit tests
  recursively enforce this catalog/runtime alignment.
- Separate hosts are required for each architecture

#### Configuration

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

### Functional groups

#### Config mode (`functional_groups_source: "config"`)

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

#### Catalog mode (`functional_groups_source: "catalog"`)

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

#### Image reuse and S3 backup behavior

| Package source | `backup_s3_images` | Reuse behavior | `_prev` backup |
|----------------|--------------------|----------------|----------------|
| `catalog` | `false` | Global dictionary lookup | No |
| `catalog` | `true` | Global dictionary lookup | No |
| `config` | `false` | Per-group last-hash cache | No |
| `config` | `true` | Per-group last-hash cache | Rebuilt groups only |

Catalog-mode lookups are shared across BuildStream and direct catalog-driven
builds. A hit is reused only when its recorded kernel, initrd, and rootfs S3
objects still exist. Missing artifacts turn the hit into a rebuild. A successful
catalog build atomically updates `image_group_dictionary.json`; `force_rebuild`
bypasses lookup and replaces the matching dictionary entries after validation.
`build_image.force_rebuild` in `image_build_config.yml` is the single rebuild
control for both direct and BuildStream-triggered catalog builds.

## Usage

Run this module through `omnia.sh`; it activates the virtual environment and runs `src/image_build_manager/playbooks/image_build_manager.yml`. All `./omnia.sh` commands in this document are run from `src/main` on the OIM. See [Tags](#tags) for the supported tags and combinations.

```bash
cd src/main
./omnia.sh --run image_build_manager --tags <tag> [-e <extra_var>=<value>]
```

To run the playbook directly, activate `$OMNIA_VENV_PATH/bin/activate`, source `/etc/profile.d/omnia-env.sh`, and run from the module root so its `ansible.cfg` is loaded:

```bash
cd src/image_build_manager
ansible-playbook playbooks/image_build_manager.yml --tags <tag>
```

Typical flow (run Repository Manager first):

```bash
cd src/main
./omnia.sh --run repo_manager --tags execute
./omnia.sh --run image_build_manager --tags validate
./omnia.sh --run image_build_manager --tags prepare   # MinIO (when selected) and OCI registry
./omnia.sh --run image_build_manager --tags build     # build x86_64 and aarch64 images
```

Edit the staged `$OMNIA_DATA_PATH/image_build_manager/input/$OMNIA_PROJECT_NAME/image_build_config.yml` before `validate`.

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

Run exactly one supported tag at a time. Although internal imported plays carry
`x86_64` and `aarch64` tags, the top-level tag validator does not accept them as
public tags; a `build` or `execute` run builds every configured architecture.

## Inputs and Outputs

### Inputs

| File | Source | Required |
|------|--------|----------|
| `image_build_config.yml` | Runtime `input/<project>/` | Yes |
| `repo_status.yml` | `repo_manager_output_path` | Build/execute/default flow |
| `package_groups.yml` | Runtime `input/<project>/` | When `functional_groups_source: "config"` |
| `catalog_rhel.json` | `CATALOG_FILE_PATH` env var | When `functional_groups_source: "catalog"` |
| `image_build_credentials.yml` | Auto-generated and Vault-encrypted | Credentials/prepare/build/default flow |

### Outputs

| File | Location | Description |
|------|----------|-------------|
| `build_status.yml` | Catalog: `output/<project>/<catalog-id>-v<version>/`; config: `output/<project>/` | Producing image engine and per-group S3 artifact paths for provisioning. Catalog mode also writes a project-level latest compatibility copy during migration. |

See `samples/` for example input and output files.

## Runtime Paths

### Data path (`$IMAGE_BUILD_MANAGER_DATA_PATH`)

The domain path defaults to `$OMNIA_DATA_PATH/image_build_manager`:

```
/opt/omnia/image_build_manager/
+-- input/<project>/          Staged input files
+-- output/<project>/         latest build_status.yml compatibility copy,
|                            image_group_dictionary.json
|   +-- <catalog-id>-v<version>/
|       +-- build_status.yml catalog-version contract
+-- log/<project>/            Domain runtime logs (validation, build)
+-- s3/                       MinIO data
+-- registry/                 OCI registry storage
+-- oci/                      OCI image data
+-- workdir/                  OpenCHAMI build workdir
```

### Ansible log path (`/var/log/omnia/image_build_manager/`)

All Ansible playbook execution logs are flat (no subfolders) under a single directory:

```
/var/log/omnia/image_build_manager/
+-- image_build_manager.log   Main playbook log
+-- build_image.log           Build sub-playbook log
+-- cleanup.log               Cleanup sub-playbook log
+-- credentials.log           Credentials sub-playbook log
+-- precheck.log              Precheck sub-playbook log
+-- prepare.log               Prepare sub-playbook log
+-- validate.log              Validate sub-playbook log
```

> **Note**: This directory must exist before running playbooks (`ansible.cfg` cannot
> create parent directories). Use one of:
> - **Automatic**: `sudo ./domain-init.sh` (creates log dir + copies input files)
> - **Manual**: `sudo mkdir -p /var/log/omnia/image_build_manager`
> - **Override**: `export ANSIBLE_LOG_PATH=/path/to/custom.log`

## Cleanup

### Full cleanup (`cleanup`)

The public cleanup removes MinIO, the OCI registry, build outputs, runtime data,
logs, `image_build_credentials.yml`, and its vault key. The shared `output/` and
`log/` roots are preserved as empty directories. It does not prompt for a second
credential decision:

```bash
cd src/main
sudo ./omnia.sh --run image_build_manager --tags cleanup
```

To keep the credentials (so the next deployment does not prompt), add
`-e cleanup_credentials=false`, as for repo_manager and orchestrator:

```bash
sudo ./omnia.sh --run image_build_manager --tags cleanup -e cleanup_credentials=false
```

The standalone cleanup playbook also supports `--skip-tags cleanup_credentials`. `domain-init.sh --cleanup`
is a non-interactive initializer helper that removes only staged input and
domain log paths; it does not remove services or build outputs. After every
domain cleanup tag has completed, `sudo ./omnia.sh --cleanup --all` performs the
guarded global reset. Both global cleanup modes prompt for `yes`; trusted
automation can add `--skip-approval`.

### Image cleanup (`cleanup_images`)

Delete built OS images from S3 buckets and OCI registry without tearing down
the MinIO/registry infrastructure itself. Supports pattern-based deletion.

```bash
# Delete ALL images (prompts for confirmation)
./omnia.sh --run image_build_manager --tags cleanup_images

# Delete images matching a pattern
./omnia.sh --run image_build_manager --tags cleanup_images \
  -e cleanup_image_pattern="rhel-slurm_*"

# Delete only a specific functional group
./omnia.sh --run image_build_manager --tags cleanup_images \
  -e cleanup_image_pattern="rhel-os_x86_64*"

# Skip approval prompt (for automation)
./omnia.sh --run image_build_manager --tags cleanup_images \
  -e skip_approval=true
```

| Extra Variable | Default | Description |
|---------------|---------|-------------|
| `cleanup_image_pattern` | `*` | Text/glob matched as "contains" against the S3 path and registry repo (`*` = any characters, `?` = one character; other characters, including `.`, are literal). Example: `*slurm_node_*`. If nothing matches, a warning lists the available images. |
| `skip_approval` | `false` | Skip interactive approval prompt (for automation) |

S3 deletion requires `s3cmd` plus `/root/.s3cfg`; registry deletion requires
`regctl` plus an active service or managed registry storage. Missing tooling is
reported and that side of cleanup is skipped. Package hash cache files of the
cleaned images (`<IMAGE_BUILD_MANAGER_DATA_PATH>/log/<project>/.*_pkg_hash_*`)
are removed too, so the next build rebuilds them instead of skipping.

## Troubleshooting

- Ansible log: `/var/log/omnia/image_build_manager/image_build_manager.log` (top-level playbook execution).
- Per-playbook logs (build, cleanup, credentials, precheck, prepare, validate) are in the same directory; domain runtime logs are under `<IMAGE_BUILD_MANAGER_DATA_PATH>/log/<project>/`.
- Re-run `sudo ./omnia.sh --init image_build_manager` if inputs or dependencies were not staged.
- [docs/troubleshooting.md](docs/troubleshooting.md) lists common failures and fixes.

## Security

- S3 and aarch64 credentials are collected by the `credentials` tag and stored Vault-encrypted; `cleanup` removes them unless `-e cleanup_credentials=false` is passed.
- See [docs/security.md](docs/security.md) for security considerations.

## Documentation

- [Read the Docs: Image Build Manager guides](https://omnia.readthedocs.io/en/latest/HowTo/image_build_manager/index.html)
- [Architecture](docs/architecture.md)
- [Package mapping guide](docs/package-mapping-guide.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Security](docs/security.md)
- [Input contract](docs/contracts/input-contract.md)
- [Output contract](docs/contracts/output-contract.md)
- [Omnia on GitHub](https://github.com/dell/omnia)
- [Report an issue](https://github.com/dell/omnia/issues)

## License

Apache License, Version 2.0
