# Omnia Build Stream

Build Stream (`omnia.build_stream`) is a RESTful API service plus GitLab CI/CD integration that automates catalog-driven repository synchronization, image builds, and node deployment for Omnia clusters. The FastAPI service and PostgreSQL run as Podman containers on the OIM; Ansible playbooks run from the shared Omnia virtual environment.

## Overview

Build Stream automates the end-to-end software lifecycle by:

- Parsing software catalogs to determine required packages and images
- Triggering repository synchronization through Repository Manager
- Orchestrating OS image builds through Image Build Manager
- Managing build job queues and execution status
- Integrating with GitLab for CI/CD pipeline automation

### Related modules

| Direction | Module | Interaction |
|-----------|--------|-------------|
| Upstream | Repository Manager, Image Build Manager | Must be prepared first; the build pipeline invokes both |
| Downstream | Orchestrator | The deploy pipeline invokes Orchestrator for mapped nodes |

### High-level workflow

1. **Authentication**: JWT-based authentication secures all API endpoints
2. **Job Creation**: Clients submit build requests through the jobs API
3. **Stage Processing**: Jobs are broken into stages (catalog parsing, local repo, build image, validation)
4. **Async Execution**: Stages execute asynchronously with result polling
5. **Artifact Management**: Build artifacts are stored and tracked throughout the process
6. **Audit Trail**: All operations are logged for traceability and compliance

## Architecture

Build Stream follows a clean architecture pattern with clear separation of concerns:

- **API Layer** (`app/api/`): FastAPI routes and HTTP handling
- **Core Layer** (`app/core/`): Business logic, entities, and domain services
- **Orchestrator Layer** (`app/orchestrator/`): Use cases that coordinate workflows
- **Infrastructure Layer** (`app/infra/`): External integrations and data persistence
- **Common Layer** (`app/common/`): Shared utilities and configuration

### Runtime components

| Component | Runs As | Description |
|-----------|---------|-------------|
| FastAPI service | Podman container (`omnia_build_stream`) | REST API for build job management |
| PostgreSQL | Podman container (`omnia_postgres`) | Persistent job and artifact metadata |
| GitLab | Podman container (on GitLab host) | CI/CD pipeline for catalog-driven builds |
| Playbook watcher | systemd service | Monitors queue and triggers Ansible playbooks |
| Ansible playbooks | Host (Omnia venv) | Infrastructure provisioning and deployment |

### Domain structure

```
build_stream/                              # Omnia Build Stream domain
├── ansible.cfg                            # Ansible config (domain root)
├── requirements.txt                       # Python dependencies (pip)
├── requirements.yml                       # Ansible Galaxy collections
├── requirements-dev.txt                   # Dev/test dependencies
├── domain-init.sh                         # Installs deps, stages app + input to runtime data path
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
│   ├── build_stream.yml                   # Entry-point playbook (tags: precheck, validate, credentials, prepare, execute, build, cleanup)
│   ├── ansible.cfg                        # Playbook-level Ansible config
│   ├── precheck/ validate/ credentials/   # Stage playbooks
│   ├── prepare/ build/ restart/ cleanup/  # Stage playbooks
├── roles/                                 # Ansible roles
│   ├── build_stream_setup/                # Environment setup
│   ├── credential_utility/                # Credential management
│   ├── deploy_bsm/                        # Container + watcher deployment
│   ├── postgres/                          # PostgreSQL container
│   ├── hosted_gitlab/                     # GitLab deployment
│   ├── cleanup_build_stream/              # Cleanup
│   └── ...
├── docs/                                  # Architecture, contracts, workflow docs
└── README.md                              # This file
```

### Runtime directory (auto-created at `/opt/omnia/build_stream/`)

```
/opt/omnia/build_stream/
├── api/                             # FastAPI app source (from domain-init.sh)
├── input/project_default/           # Staged input files (from domain-init.sh)
│   └── build_stream_config.yml
├── output/project_default/          # Build status output
├── log/playbooks/                   # Ansible playbook logs
├── playbook_queue/                  # Watcher job queue directory
├── build_stream_root/               # API runtime data
│   ├── api/.auth/keys/              # JWT keys
│   ├── artifacts/                   # Job artifacts
│   └── restart_state/               # Restart state per job
├── ssl/                             # TLS certificates
├── postgres/                        # PostgreSQL data
│   └── data/
├── infra/db/                        # Alembic migrations
└── scripts/                         # JWT key generation, etc.
```

### Roles

Roles are invoked as `omnia.build_stream.<role>`.

| Role | Description |
|------|-------------|
| [`build_stream_setup`](roles/build_stream_setup/README.md) | Domain setup role for Build Stream — resolves input/output directories and loads OIM metadata |
| [`cleanup_build_stream`](roles/cleanup_build_stream/README.md) | Cleans up Build Stream containers, services, credentials, and data directories |
| [`cleanup_gitlab`](roles/cleanup_gitlab/README.md) | Removes GitLab CE, runner, TLS certificates, CI/CD configuration, and credentials |
| [`credential_utility`](roles/credential_utility/README.md) | Manages Build Stream domain credentials — creates, validates, prompts, and encrypts credential files |
| [`deploy_bsm`](roles/deploy_bsm/README.md) | Deploys the Build Stream Manager container and playbook watcher service |
| [`gitlab_passwordless_ssh`](roles/gitlab_passwordless_ssh/README.md) | Configures passwordless SSH access from the control node to the GitLab server |
| [`hosted_gitlab`](roles/hosted_gitlab/README.md) | Deploys GitLab CE Omnibus with TLS, CI/CD pipelines, runner, and project configuration |
| [`postgres`](roles/postgres/README.md) | Deploys the PostgreSQL container for the Build Stream database |
| [`precheck_build_stream`](roles/precheck_build_stream/README.md) | Precheck for build_stream domain — verifies repo_manager and image_build_manager containers are running, credentials are present, and output files exist |
| [`pxe_buildstream_manager`](roles/pxe_buildstream_manager/README.md) | Manage PXE boot operations with BuildStream integration |
| [`validate_build_stream_input`](roles/validate_build_stream_input/README.md) | Validate BuildStream input configuration files |

### Modules

Modules are invoked as `omnia.build_stream.<module>`.

| Module | Description |
|--------|-------------|
| `validate_build_stream_config` | Validate build stream configuration files |
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
| Container runtime | Podman | Runs the Build Stream API and PostgreSQL containers |
| Database | PostgreSQL | Containerized; deployed by the `prepare` tag |

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
sudo ./omnia.sh --init build_stream
```

### Manual dependency install

The shared virtual environment above is the supported path. To install dependencies manually:

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

## Configuration

### Environment variables

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
- **`cadence.enabled`** — Enable periodic repository reconciliation and catalog-driven pipelines
- **`cadence.interval_days`** — Poll interval for cadence cycles (default 7 days, minimum 1 day)
- **`cadence.sync_timeout_seconds`** — Maximum wait for repository synchronization
- **`cadence.sync_poll_interval_seconds`** — Poll interval while waiting for repository synchronization
- **`retention.auto_cleanup_enabled`** — Enable automatic image cleanup (default `true`)
- **`retention.retention_age_days`** — Age after which a never-deployed, unprotected image group is cleaned up (default 90, minimum 1)
- **`retention.min_keep_count`** — Image groups always kept per functional group (default 5)
- **`retention.evaluation_interval_hours`** — Interval between automatic cleanup cycles (default 24, minimum 1)

The cadence catalog (`cadence_catalog_rhel.json`) and reconciliation playbook
(`repo_sync.yml`) are fixed system contracts. Cadence settings are reloaded at
the start of each cycle. Disabling cadence suppresses work but keeps the timer
alive so it can be re-enabled without restarting `playbook-watcher.service`.

### Automatic image cleanup

The `omnia_build_stream` API container runs automatic cleanup in the
background (`AutoCleanupScheduler`). Each cycle cleans up `FAILED` image
groups and then image groups older than `retention.retention_age_days` that
were never deployed, are not protected, and whose functional group keeps more
than `retention.min_keep_count` groups. The `retention` settings are re-read
every minute, so changes apply without restarting the container; an invalid
value keeps the last valid settings. The first cycle runs 5 minutes after
the container starts. A manual pass can be run inside the container with
`python3 /opt/omnia/build_stream/cleanup_cron.py`.

### Cadence pipeline

When cadence is enabled, the playbook-watcher runs the registered
`repo_sync.yml` playbook and validates `repo_resync_status.yml`. A failed sync,
a non-zero stale-package count, or incomplete cleanup stops the cycle before
the catalog is changed. After every successful reconciliation, the watcher
increments the catalog version and pushes exactly one GitLab commit. That
commit starts the unified pipeline:

`initialization` → `parse-catalog` → `configure-local-repository` →
`build-images` → `deploy` → `restart` → `validate` → `summary`

Cadence never suppresses the pipeline based on `packages_added` or
`packages_removed`. Those counts cannot reveal a package-version replacement
that leaves the total package count unchanged. A successful exact-mirror sync
therefore always advances the full cadence pipeline.

## Usage

Run this module through `omnia.sh`; it activates the virtual environment and runs `src/build_stream/playbooks/build_stream.yml`. All `./omnia.sh` commands in this document are run from `src/main` on the OIM. See [Tags](#tags) for the supported tags and combinations.

```bash
cd src/main
./omnia.sh --run build_stream --tags <tag> [-e <extra_var>=<value>]
```

To run the playbook directly, activate `$OMNIA_VENV_PATH/bin/activate`, source `/etc/profile.d/omnia-env.sh`, and run from the module root so its `ansible.cfg` is loaded:

```bash
cd src/build_stream
ansible-playbook playbooks/build_stream.yml --tags <tag>
```

Typical flow:

```bash
cd src/main
./omnia.sh --run build_stream --tags validate     # validate build_stream_config.yml
./omnia.sh --run build_stream --tags credentials  # collect or update credentials
./omnia.sh --run build_stream --tags prepare      # deploy PostgreSQL, BSM container and playbook watcher
./omnia.sh --run build_stream --tags execute      # deploy GitLab and CI/CD configuration
```

Running without a tag performs validate, credentials, prepare, and execute.

### API development

```bash
# Install app + dev dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Functional (FVT) and non-functional (NFT) tests live outside the domain:
# see test/build_stream/README.md

# Run the API server locally (from the app directory)
cd src/build_stream/app
export HOST=<host_ip> PORT=8010
uvicorn main:app --host "$HOST" --port "$PORT"
```

### API documentation

- See [BuildStreaM documentation](https://omnia.readthedocs.io/en/latest/HowTo/build_stream/index.html) for complete API documentation
- Health check endpoint: `/health`

## Tags

Run one tag at a time (from the `build_stream.yml` header).

| Tag | Description | Credentials |
|-----|-------------|-------------|
| _(none)_ | Default flow: setup, validate, credentials, prepare, execute | Yes |
| `precheck` | Environment precheck: containers and credentials present | No |
| `validate` | Validate `build_stream_config.yml` only | No |
| `credentials` | Collect or update Build Stream, PostgreSQL, and GitLab credentials | Yes |
| `prepare` | Deploy PostgreSQL, BSM container, and playbook watcher | Yes |
| `execute` | Deploy GitLab CE and CI/CD configuration | Yes |
| `build` | Alias for `prepare` plus `execute` | Yes |
| `cleanup` | Remove GitLab, BSM, PostgreSQL, and credentials (`-e cleanup_credentials=false` keeps credentials) | No |

`credentials` has no dedicated play. Setup, input validation, and the credential step run under the `always` tag, and the setup role skips the credential step only for `precheck`, `validate`, and `cleanup`. Running `--tags credentials` therefore performs setup, validation, and the credential prompt, and stops there.

## Inputs and Outputs

Input files are **edited in the source tree** and **staged to the runtime data path** before
playbook execution. The staging happens automatically during `omnia.sh -s`, or you can
run `domain-init.sh --force` manually after editing.

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

### Outputs

Build status is written to `<data_path>/build_stream/output/<project>/`. See the [output contract](docs/contracts/output-contract.md) for the field-level specification.

## Runtime Paths

All runtime output goes to `<OMNIA_DATA_PATH>/build_stream/` (default: `/opt/omnia/build_stream/`):

| Path | Purpose |
|------|---------|
| `<data_path>/build_stream/log/` | BuildStream job logs: API event log, per-job API logs and copies of per-attempt stage playbook logs (`log/<job_id>/`), cadence sync log copies (`log/cadence-<timestamp>/`), and validation logs (`log/<project>/`). Watcher-run playbooks log to `/var/log/omnia/<domain>/` like a manual run; that log is copied here when the stage ends |
| `<data_path>/build_stream/input/<project>/` | Staged input files |
| `<data_path>/build_stream/output/<project>/` | Build status output |
| `<data_path>/build_stream/playbook_queue/` | Watcher job queue |
| `<data_path>/build_stream/build_stream_root/` | API runtime data (JWT keys, artifacts) |
| `<data_path>/build_stream/ssl/` | TLS certificates for the API |
| `<data_path>/build_stream/postgres/` | PostgreSQL data directory |

## Cleanup

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

## Troubleshooting

- Ansible log: `/var/log/omnia/build_stream/build_stream.log` (top-level playbook execution).
- Re-run `sudo ./omnia.sh --init build_stream` if inputs or dependencies were not staged.
- Job, stage, cadence, and validation logs are under `<data_path>/build_stream/log/` (see [Runtime Paths](#runtime-paths)).
- Workflow-specific guidance: [docs/README.md](docs/README.md).
- See [docs/troubleshooting.md](docs/troubleshooting.md) for common failures and fixes.

## Security

- API endpoints are secured with JWT-based authentication; TLS certificates for the API are stored under `<data_path>/build_stream/ssl/`.
- Credentials are collected by the `credentials` tag and stored in Vault-protected files owned by Build Stream; `cleanup` removes them unless `-e cleanup_credentials=false` is passed.
- See [docs/security.md](docs/security.md) for the full security notes.

## Documentation

- [Read the Docs: Build Stream guides](https://omnia.readthedocs.io/en/latest/HowTo/build_stream/index.html)
- [Architecture](docs/architecture.md)
- [Design](docs/design/build-stream-design.md)
- [Documentation index](docs/README.md)
- [Input contract](docs/contracts/input-contract.md)
- [Output contract](docs/contracts/output-contract.md)
- [Jobs](docs/jobs.md)
- [Catalog](docs/catalog.md)
- [Local repository](docs/local_repo.md)
- [Image build](docs/build_image.md)
- [Validation](docs/validation.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Security](docs/security.md)
- [Omnia on GitHub](https://github.com/dell/omnia)
- [Report an issue](https://github.com/dell/omnia/issues)

## License

Apache License, Version 2.0
