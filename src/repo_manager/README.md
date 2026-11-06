# Repository Manager

Repository Manager is an Ansible Galaxy collection that deploys an HTTPS Pulp content server and synchronizes catalog content for offline Omnia clusters. It supports RPM repositories and packages, container images, Python packages, files, and source artifacts for both x86_64 and aarch64 architectures.

## Overview

Repository Manager enables air-gapped deployments by:

- Deploying an HTTPS Pulp content server for package distribution
- Synchronizing catalog-selected content from upstream repositories
- Supporting multiple artifact types: RPMs, container images, Python packages, files
- Providing version-qualified repository endpoints for downstream consumption
- Managing RHEL subscription repositories
- Supporting private registries with authentication

## Key Features

### Pulp Content Server
- HTTPS-only access with TLS certificates
- Configurable host port mapping
- Systemd-enabled service for automatic startup
- Managed Pulp CLI with generated CA

### Content Types
- **RPM repositories**: RHEL baseos, appstream, codeready-builder, EPEL
- **Container images**: Docker/OCI registry support
- **Python packages**: PyPI synchronization
- **Files and source artifacts**: Generic file hosting

### Repository Policies
Configurable synchronization policies:
- `always`: Immediate synchronization
- `partial`: Streamed synchronization (default)
- `never`: Validation-only handling

Caching can be enabled per repository for on-demand retrieval.

### Private Registry Support
- Basic authentication with Vault-encrypted credentials
- TLS certificate management
- Support for Harbor, Docker Hub, and other registries

## Prerequisites

| Requirement | Minimum | Validated |
|-------------|---------|-----------|
| OIM OS | RHEL 10.x | RHEL 10.0 |
| Python | 3.12+ | 3.12.8 |
| Ansible | ansible-core 2.20+ | 2.20.0 |
| Podman | 5.0+ | 5.3.1 |
| Privileges | Root or equivalent | Root |
| Storage | Sized for retained catalog content | Deployment-specific |

## Quick Start

```bash
# 1. Configure the common environment
vi src/main/omnia.env
./src/main/omnia.sh --setup-venv
source /opt/omnia/venv/bin/activate
set -a
source /etc/omnia/omnia.env
set +a

# Required values:
# SYSTEM_ADMIN_NIC_IPV4=<admin_ipv4>
# CATALOG_FILE_PATH=/absolute/path/to/catalog.json

# 2. Edit the flat source inputs
vi src/repo_manager/input/repo_manager_config.yml
vi src/repo_manager/input/repo_manager_endpoint_config.yml

# 3. Stage inputs into the selected runtime project
cd src/repo_manager
./domain-init.sh

# 4. Run the standard workflow
cd playbooks
ansible-playbook repo_manager.yml --tags "prepare,precheck,download,status"
```

## Tags

| Tag | Description | Credentials |
|-----|-------------|-------------|
| `prepare` / `deploy` | Collect/reuse credentials and deploy HTTPS Pulp | Yes |
| `precheck` | Validate environment, input, catalog and subscription sources | No new credentials |
| `download` / `execute` | Resolve and synchronize catalog content | Existing credentials |
| `status` | Generate current `repo_status.yml` | Existing Pulp credentials |
| `cleanup_repos` | Selectively remove Pulp RPM, container, File or Python content | Existing Pulp credentials |
| `cleanup_pulp` / `cleanup` | Remove the Pulp deployment, runtime data, and credentials by default | `cleanup_credentials=false` preserves credentials |
| `catalog_generate` | Create catalog JSON from text input | No |
| `catalog_add` | Add or update catalog packages | No |
| `catalog_delete` | Delete catalog packages | No |
| `catalog_validate` | Validate catalog JSON | No |

## Exact RPM Repository Reconciliation

For exact mirror synchronization after normal download:

```bash
cd src/repo_manager/playbooks
ansible-playbook repo_operations/repo_sync.yml
```

This maintenance operation processes RHEL minor-version contexts sequentially, validates HTTPS `repomd.xml`, switches the stable distribution, and prunes superseded publications atomically.

## Selective Cleanup

```bash
# Remove one RPM repository
ansible-playbook repo_manager.yml --tags cleanup_repos \
  -e "cleanup_repos=x86_64_rhel_10.0_epel"

# Remove only one image tag
ansible-playbook repo_manager.yml --tags cleanup_repos \
  -e "cleanup_containers=registry.example.com/team/image:v1"

# Remove all synchronized artifacts but keep Pulp deployment
ansible-playbook repo_manager.yml --tags cleanup_repos \
  -e "cleanup_repos=all" -e "cleanup_containers=all" \
  -e "cleanup_files=all" -e "force=true"
```

## Documentation

- [Repository Manager Documentation](https://omnia.readthedocs.io/en/latest/HowTo/repo_manager/index.html)
- [Architecture](docs/architecture.md)
- [Content Configuration](docs/content-configuration-guide.md)
- [Catalog Operations](docs/catalog_operations.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Security](docs/security.md)
- [Input Contract](docs/contracts/input-contract.md)
- [Output Contract](docs/contracts/output-contract.md)

## License

Apache License, Version 2.0
