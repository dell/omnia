# Image Build Manager

Image Build Manager is an Ansible Galaxy collection that builds stateless OS images for HPC cluster provisioning using OpenCHAMI. It deploys MinIO S3 and local OCI registry storage, builds per-functional-group images for both x86_64 and aarch64 architectures, and writes `build_status.yml` for downstream consumption by the Orchestrator provisioning workflow.

## Overview

Image Build Manager automates OS image creation for HPC and AI clusters by:

- Deploying MinIO S3 object storage for image artifacts
- Deploying local OCI registry for container image storage
- Building stateless bootable OS images (RHEL/Rocky) for x86_64 and aarch64
- Supporting dual-mode functional groups: config-based and catalog-driven
- Integrating with OpenCHAMI Image Thrillhouse as the build engine
- Producing `build_status.yml` with kernel, initrd, and rootfs artifact locations

## Architecture

Image Build Manager uses OpenCHAMI Image Thrillhouse as the sole image build engine. The domain supports:

- **Dual functional group modes**: Config mode uses `package_groups.yml`, catalog mode uses JSON catalog
- **Multi-architecture**: x86_64 builds run on OIM, aarch64 builds run on dedicated ARM node
- **Storage backends**: MinIO S3 for image artifacts, local OCI registry for container images
- **Image reuse**: Global dictionary lookup for catalog mode, per-group cache for config mode

## Prerequisites

| Requirement | Minimum | Validated |
|------------|---------|-----------|
| OS | RHEL 10.x, Rocky 10.x | RHEL 10.0 |
| Python | 3.12+ | 3.12.8 |
| Ansible | ansible-core 2.20+ | 2.20.0 |
| Podman | 5.0+ | 5.3.1 |
| Disk | 50 GB free | -- |

## Quick Start

```bash
# From the repository root
cd src/main

# Configure the host, create the shared virtual environment, stage domain inputs
vi omnia.env
sudo ./omnia.sh -s
source /etc/profile.d/omnia-env.sh

# Edit the staged project input. Run repo_manager before the image build.
vi "$OMNIA_DATA_PATH/image_build_manager/input/$OMNIA_PROJECT_NAME/image_build_config.yml"
./omnia.sh --run repo_manager --tags execute

# Validate, prepare infrastructure, and build images
./omnia.sh --run image_build_manager --tags validate
./omnia.sh --run image_build_manager --tags prepare
./omnia.sh --run image_build_manager --tags build
```

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

## AArch64 Build Host

Cross-architecture building is **NOT supported**. AArch64 builds require:

- Separate aarch64 node with ARM64 architecture
- SSH password for initial key installation (passwordless SSH configured automatically)
- Network connectivity from OIM admin NIC
- Separate host for each architecture (x86_64 on OIM, aarch64 on dedicated node)

## Functional Groups

### Config Mode
Functional groups derived from `package_groups.yml` keys, filtered by architecture suffix. OS type and version from `os` / `os_version` fields.

### Catalog Mode
Full names auto-detected from `catalog.functionallayer[]`. OS type from baseos group's `os` field; version from `os_version` field.

## Documentation

- [Image Build Manager Documentation](https://omnia.readthedocs.io/en/latest/HowTo/image_build_manager/index.html)
- [Architecture](docs/architecture.md)
- [Package Mapping Guide](docs/package-mapping-guide.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Security](docs/security.md)
- [Input Contract](docs/contracts/input-contract.md)
- [Output Contract](docs/contracts/output-contract.md)

## License

Apache License, Version 2.0
