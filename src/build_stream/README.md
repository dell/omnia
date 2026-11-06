# Omnia Build Stream

Build Stream is a RESTful API service that orchestrates the creation and management of build jobs for the Omnia infrastructure platform. It provides a centralized interface for managing software catalog parsing, local repository creation, image building, and validation workflows through GitLab CI/CD integration.

## Overview

Build Stream automates the end-to-end software lifecycle for HPC and AI clusters by:

- Parsing software catalogs to determine required packages and images
- Triggering repository synchronization via Repository Manager
- Orchestrating OS image builds via Image Build Manager
- Managing build job queues and execution status
- Integrating with GitLab for CI/CD pipeline automation

## Architecture

Build Stream follows a clean architecture pattern with clear separation of concerns:

- **API Layer** (`app/api/`): FastAPI routes and HTTP handling
- **Core Layer** (`app/core/`): Business logic, entities, and domain services
- **Orchestrator Layer** (`app/orchestrator/`): Use cases that coordinate workflows
- **Infrastructure Layer** (`app/infra/`): External integrations and data persistence
- **Common Layer** (`app/common/`): Shared utilities and configuration

## Runtime Components

| Component | Runs As | Description |
|-----------|---------|-------------|
| FastAPI service | Podman container (`omnia_build_stream`) | REST API for build job management |
| PostgreSQL | Podman container (`omnia_postgres`) | Persistent job and artifact metadata |
| GitLab | Podman container (on GitLab host) | CI/CD pipeline for catalog-driven builds |
| Playbook watcher | systemd service | Monitors queue and triggers Ansible playbooks |
| Ansible playbooks | Host (Omnia venv) | Infrastructure provisioning and deployment |

## Prerequisites

| Requirement | Minimum | Validated |
|------------|---------|-----------|
| OS | RHEL 10.x, Rocky 10.x | RHEL 10.0 |
| Python | 3.12+ | 3.12.8 |
| Ansible | ansible-core 2.20+ | 2.20.0 |
| Container runtime | Podman 5.0+ | 5.3.1 |
| Database | PostgreSQL 17+ | 17.x (containerized) |

## Quick Start

```bash
# 1. Configure environment (REQUIRED — do this first)
vi src/main/omnia.env                         # Set SYSTEM_ADMIN_NIC_IPV4 at minimum

# 2. Set up env + venv + input files (one-time)
./src/main/omnia.sh --setup-venv
source /opt/omnia/venv/bin/activate

# 3. Edit config in source tree, then re-stage to NFS
vi src/build_stream/input/build_stream_config.yml
./src/build_stream/copy-input.sh              # Re-copy to runtime path

# 4. Run playbooks from domain root
cd src/build_stream
ansible-playbook build_stream.yml             # Full flow (credentials + deploy)
```

## Key Features

### Cadence Pipeline
When cadence is enabled, Build Stream automatically:
- Runs repository synchronization
- Validates catalog content
- Increments catalog version
- Triggers GitLab CI/CD pipeline
- Executes build and deploy stages

### Automatic Image Cleanup
The API container runs automatic cleanup in the background:
- Removes FAILED image groups
- Cleans up old image groups based on retention policy
- Configurable retention age and minimum keep count

### Job Queue Management
- Asynchronous job execution with result polling
- Job stages: catalog parsing, local repo, build image, validation
- Audit trail for all operations

## Documentation

- [BuildStreaM Documentation](https://omnia.readthedocs.io/en/latest/HowTo/build_stream/index.html)
- [Architecture](docs/architecture.md)
- [Developer Guide](docs/developer-guide.md)
- [Jobs Management](docs/jobs.md)
- [Catalog Processing](docs/catalog.md)

## License

Apache License, Version 2.0
