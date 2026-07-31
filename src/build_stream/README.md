# Omnia Build Stream

**Build Stream** is a **RESTful API** service that orchestrates the creation and management
of build jobs for the Omnia infrastructure platform. It provides a centralized interface
for managing software catalog parsing, local repository creation, image building, and
validation workflows.

**Runs on a RHEL host** with Ansible + Python. The FastAPI service runs inside a Podman
container; Ansible playbooks run directly on the host from the shared Omnia venv.

## Prerequisites

| Requirement | Minimum | Validated |
|------------|---------|-----------|
| OS | RHEL 10.x, Rocky 10.x | RHEL 10.0 |
| Python | 3.12+ | 3.12.8 |
| Ansible | ansible-core 2.20+ | 2.20.0 |
| Container runtime | Podman 5.0+ | 5.3.1 |
| Database | PostgreSQL 17+ | 17.x (containerized) |

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
# 1. Configure environment (REQUIRED — do this first)
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

## Input Files

Input files are **edited in the source tree** and **staged to the runtime data path** before
playbook execution. The staging happens automatically during `omnia.sh -s`, or you can
run `copy-input.sh` manually after editing.

```
Source (git repo)                           Runtime (data path)
─────────────────                           ───────────────────
src/build_stream/input/                   ──copy──>  /opt/omnia/build_stream/input/project_default/
src/build_stream/app/                     ──copy──>  /opt/omnia/build_stream/
                                                        │
                                                        ▼
                                               Ansible playbooks + container read from here
```

| File | Source Location | Runtime Location | Required | Description |
|------|----------------|-----------------|----------|-------------|
| `omnia.env` | `src/main/` | `/etc/omnia/omnia.env` (installed by omnia.sh) | Yes | Common environment variables |
| `build_stream_config.yml` | `input/` | `<data_path>/build_stream/input/<project>/` | Yes | BSM + GitLab configuration |
| `app/` (source code) | `app/` | `<data_path>/build_stream/` | Yes | FastAPI application code |

## Architecture Overview

Build Stream follows a clean architecture pattern with clear separation of concerns:

- **API Layer** (`app/api/`): FastAPI routes and HTTP handling
- **Core Layer** (`app/core/`): Business logic, entities, and domain services
- **Orchestrator Layer** (`app/orchestrator/`): Use cases that coordinate workflows
- **Infrastructure Layer** (`app/infra/`): External integrations and data persistence
- **Common Layer** (`app/common/`): Shared utilities and configuration

### Runtime Components

| Component | Runs As | Description |
|-----------|---------|-------------|
| FastAPI service | Podman container (`omnia_build_stream`) | REST API for build job management |
| PostgreSQL | Podman container (`omnia_postgres`) | Persistent job and artifact metadata |
| GitLab | Podman container (on GitLab host) | CI/CD pipeline for catalog-driven builds |
| Playbook watcher | systemd service | Monitors queue and triggers Ansible playbooks |
| Ansible playbooks | Host (Omnia venv) | Infrastructure provisioning and deployment |

## Configuration Reference

### Environment Variables

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

### `build_stream_config.yml`

Per-domain configuration. Key sections:
- **`enable_build_stream`** — Enable/disable the domain (`true`/`false`)
- **`build_stream_host_ip`** — API server host IP
- **`build_stream_port`** — API server port (default: `8010`)
- **`gitlab_host`** — Target host for GitLab deployment
- **`gitlab_project_name`** — GitLab project name (default: `omnia-catalog`)

## High-Level Workflow

1. **Authentication**: JWT-based authentication secures all API endpoints
2. **Job Creation**: Clients submit build requests through the jobs API
3. **Stage Processing**: Jobs are broken into stages (catalog parsing, local repo, build image, validation)
4. **Async Execution**: Stages execute asynchronously with result polling
5. **Artifact Management**: Build artifacts are stored and tracked throughout the process
6. **Audit Trail**: All operations are logged for traceability and compliance

## Output Paths

All runtime output goes to `<OMNIA_DATA_PATH>/build_stream/` (default: `/opt/omnia/build_stream/`):

| Path | Purpose |
|------|---------|
| `<data_path>/build_stream/log/playbooks/` | Ansible playbook logs |
| `<data_path>/build_stream/input/<project>/` | Staged input files |
| `<data_path>/build_stream/output/<project>/` | Build status output |
| `<data_path>/build_stream/playbook_queue/` | Watcher job queue |
| `<data_path>/build_stream_root/` | API runtime data (JWT keys, artifacts) |
| `<data_path>/build_stream_ssl/` | TLS certificates for the API |

## Domain Structure

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
├── input/                                 # User input (source — staged to runtime)
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

### Runtime Directory (auto-created at `/opt/omnia/build_stream/`)

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

## Development

### API Development

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

### Ansible Playbook Development

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

## License

Apache License, Version 2.0
