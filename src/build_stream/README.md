# Omnia Build Stream

**Collection**: `omnia.build_stream` v2.3.0

Build Stream is a RESTful API service that orchestrates the creation and
management of build jobs for the Omnia infrastructure platform. It provides a
centralized interface for managing software catalog parsing, local repository
creation, image building, and validation workflows through GitLab CI/CD
integration.

**Runs on a RHEL host** with Ansible + Python. The FastAPI service runs inside a
Podman container; Ansible playbooks run directly on the host from the shared
Omnia venv.

## Overview

This README follows the common Omnia domain structure and retains the complete Build Stream reference below.

## Architecture and Dependencies

Build Stream runs the BSM API, PostgreSQL, playbook watcher, and GitLab CI/CD integration on the configured infrastructure.

## Prerequisites

Complete Main setup and provide reachable OIM and GitLab hosts.

## Installation and Initialization

```bash
cd <OMNIA_SOURCE_PATH>/src/main
./omnia.sh --setup-venv
source /etc/profile.d/omnia-env.sh
```

## Configuration and Credentials

Configure `build_stream_config.yml`; collect GitLab, BSM, and PostgreSQL credentials through the encrypted workflow.

## Run with omnia.sh

```bash
cd <OMNIA_SOURCE_PATH>/src/main
./omnia.sh --run build_stream
./omnia.sh --run build_stream --tags precheck
./omnia.sh --run build_stream --tags validate
./omnia.sh --run build_stream --tags credentials
./omnia.sh --run build_stream --tags prepare
./omnia.sh --run build_stream --tags execute
./omnia.sh --run build_stream --tags build
./omnia.sh --run build_stream --tags cleanup
```

## Run with ansible-playbook

```bash
source /etc/profile.d/omnia-env.sh
source "$OMNIA_VENV_PATH/bin/activate"
cd <OMNIA_SOURCE_PATH>/src/build_stream/playbooks
export ANSIBLE_CONFIG=../ansible.cfg
ansible-playbook build_stream.yml
ansible-playbook build_stream.yml --tags precheck
ansible-playbook build_stream.yml --tags validate
ansible-playbook build_stream.yml --tags credentials
ansible-playbook build_stream.yml --tags prepare
ansible-playbook build_stream.yml --tags execute
ansible-playbook build_stream.yml --tags build
ansible-playbook build_stream.yml --tags cleanup
```

## Tags and Workflows

The public tags are documented with their prerequisites and effects in the detailed reference.

## Roles, Modules, and Plugins

The collection includes API deployment, GitLab, PostgreSQL, watcher, validation, credential, and cleanup components.

## Inputs, Outputs, and Runtime Paths

Project inputs, API state, job logs, status, and generated artifacts are scoped below `OMNIA_DATA_PATH`.

## Cleanup

Use scoped cleanup tags before global cleanup and preserve required external data explicitly.

## Security

JWT, TLS, Vault encryption, request validation, path validation, and output redaction protect Build Stream operations.

## Troubleshooting and Verification

Verify API health, containers, systemd services, GitLab access, database connectivity, status, and job logs.

## Documentation and Support

See the linked architecture, workflow, and contract documents in this README.

## Detailed Domain Reference

### Overview

Build Stream automates the end-to-end software lifecycle for HPC and AI
clusters by:

- Parsing software catalogs to determine required packages and images
- Triggering repository synchronization via Repository Manager
- Orchestrating OS image builds via Image Build Manager
- Managing build job queues and execution status
- Integrating with GitLab for CI/CD pipeline automation
- Running periodic cadence-based catalog refresh and reconciliation
- Providing automatic image cleanup based on retention policies

### Prerequisites

| Requirement | Minimum | Validated |
|------------|---------|-----------|
| OS | RHEL 10.x, Rocky 10.x | RHEL 10.0 |
| Python | 3.12+ | 3.12.8 |
| Ansible | ansible-core 2.20+ | 2.20.0 |
| Container runtime | Podman 5.0+ | 5.3.1 |
| Database | PostgreSQL 17+ | 17.x (containerized) |

#### Ansible Installation (Common Omnia Venv)

**Recommended -- use the shared Omnia venv**:

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

### Quick Start

```bash
# 1. Configure environment (REQUIRED -- do this first)
vi src/main/omnia.env                         # Set SYSTEM_ADMIN_NIC_IPV4 at minimum

# 2. Set up env + venv + input files (one-time)
#    Installs env system-wide to /etc/omnia/omnia.env
#    Installs pip deps + Galaxy collections for all domains
#    Copies app source + input files to /opt/omnia/build_stream/
./src/main/omnia.sh --setup-venv
source /opt/omnia/venv/bin/activate

# 3. Edit config in source tree, then re-stage to NFS
vi src/build_stream/input/build_stream_config.yml
./src/build_stream/copy-input.sh              # Re-copy to runtime path

# 4. Run playbooks from domain root
cd src/build_stream
ansible-playbook build_stream.yml             # Full flow (credentials + deploy)

# Or run sub-playbooks directly:
cd playbooks
ansible-playbook prepare_build_stream.yml     # Deploy Postgres + GitLab + BSM
```

### Input Files

Input files are **edited in the source tree** and **staged to the runtime data path** before
playbook execution. The staging happens automatically during `omnia.sh -s`, or you can
run `copy-input.sh` manually after editing.

```
Source (git repo)                           Runtime (data path)
-----------------                           -------------------
src/build_stream/input/                   --copy-->  /opt/omnia/build_stream/input/project_default/
src/build_stream/app/                     --copy-->  /opt/omnia/build_stream/
                                                        |
                                                        v
                                               Ansible playbooks + container read from here
```

| File | Source Location | Runtime Location | Required | Description |
|------|----------------|-----------------|----------|-------------|
| `omnia.env` | `src/main/` | `/etc/omnia/omnia.env` (installed by omnia.sh) | Yes | Common environment variables |
| `build_stream_config.yml` | `input/` | `<data_path>/build_stream/input/<project>/` | Yes | BSM + GitLab configuration |
| `app/` (source code) | `app/` | `<data_path>/build_stream/` | Yes | FastAPI application code |

### Architecture

Build Stream follows a clean architecture pattern with clear separation of concerns:

- **API Layer** (`app/api/`): FastAPI routes and HTTP handling
- **Core Layer** (`app/core/`): Business logic, entities, and domain services
- **Orchestrator Layer** (`app/orchestrator/`): Use cases that coordinate workflows
- **Infrastructure Layer** (`app/infra/`): External integrations and data persistence
- **Common Layer** (`app/common/`): Shared utilities and configuration

#### Runtime Components

| Component | Runs As | Description |
|-----------|---------|-------------|
| FastAPI service | Podman container (`omnia_build_stream`) | REST API for build job management |
| PostgreSQL | Podman container (`omnia_postgres`) | Persistent job and artifact metadata |
| GitLab | Podman container (on GitLab host) | CI/CD pipeline for catalog-driven builds |
| Playbook watcher | systemd service | Monitors queue and triggers Ansible playbooks |
| Ansible playbooks | Host (Omnia venv) | Infrastructure provisioning and deployment |

### Configuration Reference

#### Environment Variables

Host and project settings are configured via environment variables. Source `omnia.env`
or export them directly in your shell before running.

| Variable | Description | Default |
|----------|-------------|---------|
| `OMNIA_DATA_PATH` | Root data directory for all Omnia persistent data | `/opt/omnia` |
| `OMNIA_PROJECT_NAME` | Project name (maps to input/output dirs) | `project_default` |
| `SYSTEM_HOSTNAME` | OIM hostname (NOT FQDN) | `oim` |
| `SYSTEM_DOMAIN_NAME` | Domain name of the OIM host | `omnia.cluster` |
| `SYSTEM_ADMIN_NIC_IPV4` | Admin NIC IPv4 | **REQUIRED** |
| `OMNIA_VENV_PATH` | Path to the shared Omnia Python venv | `/opt/omnia/venv` |

#### `build_stream_config.yml`

Per-domain configuration. Key sections:
- **`enable_build_stream`** -- Enable/disable the domain (`true`/`false`)
- **`build_stream_host_ip`** -- API server host IP
- **`build_stream_port`** -- API server port (default: `8010`)
- **`gitlab_host`** -- Target host for GitLab deployment
- **`gitlab_project_name`** -- GitLab project name (default: `omnia-catalog`)
- **`cadence.enabled`** -- Enable periodic repository reconciliation and catalog-driven pipelines
- **`cadence.interval_days`** -- Poll interval for cadence cycles (default 7 days, minimum 1 day)
- **`cadence.sync_timeout_seconds`** -- Maximum wait for repository synchronization
- **`cadence.sync_poll_interval_seconds`** -- Poll interval while waiting for repository synchronization
- **`retention.auto_cleanup_enabled`** -- Enable automatic image cleanup (default `true`)
- **`retention.retention_age_days`** -- Age after which a never-deployed, unprotected image group is cleaned up (default 90, minimum 1)
- **`retention.min_keep_count`** -- Image groups always kept per functional group (default 5)
- **`retention.evaluation_interval_hours`** -- Interval between automatic cleanup cycles (default 24, minimum 1)

The cadence catalog (`cadence_catalog_rhel.json`) and reconciliation playbook
(`repo_sync.yml`) are fixed system contracts. Cadence settings are reloaded at
the start of each cycle. Disabling cadence suppresses work but keeps the timer
alive so it can be re-enabled without restarting `playbook-watcher.service`.

#### Automatic Image Cleanup

The `omnia_build_stream` API container runs automatic cleanup in the
background (`AutoCleanupScheduler`). Each cycle cleans up `FAILED` image
groups and then image groups older than `retention.retention_age_days` that
were never deployed, are not protected, and whose functional group keeps more
than `retention.min_keep_count` groups. The `retention` settings are re-read
every minute, so changes apply without restarting the container; an invalid
value keeps the last valid settings. The first cycle runs 5 minutes after
the container starts. A manual pass can be run inside the container with
`python3 /opt/omnia/build_stream/cleanup_cron.py`.

#### Cadence Pipeline

When cadence is enabled, the playbook-watcher runs the registered
`repo_sync.yml` playbook and validates `repo_resync_status.yml`. A failed sync,
a non-zero stale-package count, or incomplete cleanup stops the cycle before
the catalog is changed. After every successful reconciliation, the watcher
increments the catalog version and pushes exactly one GitLab commit. That
commit starts the unified pipeline:

`initialization` -> `parse-catalog` -> `configure-local-repository` ->
`build-images` -> `deploy` -> `restart` -> `validate` -> `summary`

Cadence never suppresses the pipeline based on `packages_added` or
`packages_removed`. Those counts cannot reveal a package-version replacement
that leaves the total package count unchanged. A successful exact-mirror sync
therefore always advances the full cadence pipeline.

### High-Level Workflow

1. **Authentication**: JWT-based authentication secures all API endpoints
2. **Job Creation**: Clients submit build requests through the jobs API
3. **Stage Processing**: Jobs are broken into stages (catalog parsing, local repo, build image, validation)
4. **Async Execution**: Stages execute asynchronously with result polling
5. **Artifact Management**: Build artifacts are stored and tracked throughout the process
6. **Audit Trail**: All operations are logged for traceability and compliance

### Output Paths

All runtime output goes to `<OMNIA_DATA_PATH>/build_stream/` (default: `/opt/omnia/build_stream/`):

| Path | Purpose |
|------|---------|
| `<data_path>/build_stream/log/` | BuildStream job logs: API event log, per-job API logs and copies of per-attempt stage playbook logs (`log/<job_id>/`), cadence sync log copies (`log/cadence-<timestamp>/`), and validation logs (`log/<project>/`). Watcher-run playbooks log to `/var/log/omnia/<domain>/` like a manual run; that log is copied here when the stage ends |
| `<data_path>/build_stream/input/<project>/` | Staged input files |
| `<data_path>/build_stream/output/<project>/` | Build status output |
| `<data_path>/build_stream/playbook_queue/` | Watcher job queue |
| `<data_path>/build_stream_root/` | API runtime data (JWT keys, artifacts) |
| `<data_path>/build_stream_ssl/` | TLS certificates for the API |

### Domain Structure

```
build_stream/                              # Omnia Build Stream domain
├── ansible.cfg                            # Ansible config (domain root)
├── build_stream.yml                       # Entry-point playbook
├── requirements.txt                       # Python dependencies (pip)
├── requirements.yml                       # Ansible Galaxy collections
├── requirements-dev.txt                   # Dev/test dependencies
├── copy-input.sh                          # Copies app + input to runtime data path
├── app/                                   # FastAPI application source
│   ├── main.py                            # Application entry point
│   ├── api/                               # Routes, auth, middleware
│   ├── core/                              # Business logic and entities
│   ├── orchestrator/                      # Use case coordinators
│   ├── infra/                             # DB, S3, external integrations
│   └── common/                            # Shared utilities
├── containers/                            # Container build files
│   └── omnia_build_stream/
│       └── Containerfile                  # FastAPI container image
├── input/                                 # User input (source -- staged to runtime)
│   └── build_stream_config.yml            # Domain configuration
├── playbooks/                             # Ansible playbooks
│   ├── prepare_build_stream.yml           # Deploy Postgres + GitLab + BSM
│   ├── ansible.cfg                        # Playbook-level Ansible config
│   └── ...
├── roles/                                 # Ansible roles
│   ├── build_stream_setup/                # Environment setup
│   ├── credential_utility/                # Credential management
│   ├── deploy_bsm/                        # Container + watcher deployment
│   ├── postgres/                          # PostgreSQL container
│   ├── hosted_gitlab/                     # GitLab deployment
│   ├── cleanup_build_stream/              # Cleanup
│   └── ...
├── tests/                                 # Unit and integration tests
│   ├── unit/                              # pytest unit tests (@pytest.mark.unit)
│   └── integration/                       # Integration tests
├── doc/                                   # Workflow documentation
└── README.md                              # This file
```

#### Runtime Directory (auto-created at `/opt/omnia/build_stream/`)

```
/opt/omnia/build_stream/
├── api/                             # FastAPI app source (from copy-input.sh)
├── input/project_default/           # Staged input files (from copy-input.sh)
│   └── build_stream_config.yml
├── output/project_default/          # Build status output
├── log/playbooks/                   # Ansible playbook logs
├── playbook_queue/                  # Watcher job queue directory
├── infra/db/                        # Alembic migrations
└── scripts/                         # JWT key generation, etc.
```

### Cleanup and Reset

Run the public `cleanup` tag before requesting an Omnia-wide reset. It removes
the BuildStream and GitLab services, generated artifacts, and BuildStream-owned
credential files and vault keys:

```bash
cd src/main
sudo ./omnia.sh --run build_stream --tags cleanup
```

BuildStream cleanup removes its project output, validation and watcher logs,
active and archived playbook queues, API logs, TLS/runtime data, host playbook
logs under `/var/log/omnia/build_stream`, and generated Python bytecode caches.
The initializer-owned application source and non-credential input files remain
available for redeployment.
PostgreSQL data is preserved by default; pass `-e postgres_backup=false` when
the database data must also be deleted.

Because cleanup removes the initializer-managed runtime and host log
directories, reinitialize the BuildStream domain before redeploying. Use the
public `omnia.sh` commands; `--init build_stream` invokes `domain-init.sh` and
recreates the required directories:

```bash
cd src/main
sudo ./omnia.sh --init build_stream
sudo ./omnia.sh --run build_stream
```

`src/build_stream/domain-init.sh --cleanup` is a non-interactive initializer
helper. It removes only `$OMNIA_DATA_PATH/build_stream/input`, the domain runtime
log directory, and `/var/log/omnia/build_stream`; it does not clean deployed
services or output. After all domain cleanup tags have completed, use
`sudo ./omnia.sh --cleanup --all` for the guarded global reset. Both global
cleanup modes prompt for `yes`; trusted automation can add `--skip-approval`.

### Development

#### API Development

```bash
# Install app + test dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
cd src/build_stream
pytest tests/unit/ -v -m unit

# Run development server (local)
export HOST=<host_ip> PORT=8010
uvicorn app.main:app --reload
```

#### Ansible Playbook Development

```bash
# Activate the shared Omnia venv
source /opt/omnia/venv/bin/activate

# Run from domain root
cd src/build_stream
ansible-playbook build_stream.yml

# Or from playbooks subdir
cd playbooks
ansible-playbook prepare_build_stream.yml
```

**API Documentation:**
- See Omnia ReadTheDocs for complete API documentation
- Health check endpoint: `/health`

### Documentation

| Document | Description |
|----------|-------------|
| [Build Stream Documentation](https://omnia.readthedocs.io/en/latest/HowTo/build_stream/index.html) | Read the Docs user guide |
| [Architecture](docs/architecture.md) | Domain architecture documentation |
| [Build Image](docs/build_image.md) | Build image workflow |
| [Catalog](docs/catalog.md) | Catalog processing |
| [Jobs](docs/jobs.md) | Jobs management |
| [Local Repo](docs/local_repo.md) | Local repository operations |
| [Validation](docs/validation.md) | Validation workflow |
| [Input Contract](docs/contracts/INPUT_CONTRACT.md) | Input file specifications |
| [Output Contract](docs/contracts/OUTPUT_CONTRACT.md) | Output file specifications |

### License

Apache License, Version 2.0
