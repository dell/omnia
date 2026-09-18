# BuildStream Manager — Design & Architecture


---

## 1. Overview

The **build_stream** is a self-contained Ansible domain that orchestrates automated OS image building, validation, and deployment through GitLab CI/CD pipelines. It manages PostgreSQL database, GitLab CE server, BuildStream API service, playbook-watcher service, and credential lifecycle.

The domain is fully decoupled from `src/playbooks/utils/` for credential management and cleanup operations. It owns its own credential utility, validation framework, cleanup lifecycle, and GitLab integration.

**Key Outputs**: `build_stream_status.yml` consumed by deployment orchestration, GitLab CI/CD pipelines for automated builds.

---

## 2. Directory Structure

```
src/build_stream/
├── build_stream.yml                     # Top-level orchestrator
├── ansible.cfg                          # Domain config (fully local paths)
├── app/                                 # Python FastAPI application (deployed to NFS)
│   ├── api/                             # REST API endpoints
│   │   ├── routers/                     # FastAPI route modules
│   │   ├── dependencies.py              # Dependency injection
│   │   ├── logging_utils.py             # Secure logging with redaction
│   │   └── main.py                      # FastAPI application entry
│   ├── core/                            # Domain-driven design core
│   │   ├── buildimage/                  # Build image domain entities
│   │   ├── common/                      # Shared value objects
│   │   │   └── playbook_registry.py     # Playbook path mapping registry
│   │   ├── deploy/                      # Deployment domain
│   │   ├── localrepo/                   # Local repository domain
│   │   ├── restart/                     # Restart domain
│   │   ├── upload/                      # File upload domain
│   │   └── validate/                    # Validation domain
│   ├── infra/                           # Infrastructure layer
│   │   ├── database/                    # PostgreSQL connection + models
│   │   ├── nfs/                         # NFS file repositories
│   │   └── s3/                          # MinIO S3 client
│   ├── orchestrator/                    # Application orchestrators (use cases)
│   │   ├── build_image/                 # Build image orchestration
│   │   ├── cleanup/                     # Cleanup orchestration
│   │   ├── deploy/                      # Deploy orchestration
│   │   ├── local_repo/                  # Local repo orchestration
│   │   ├── restart/                     # Restart orchestration
│   │   ├── upload/                      # Upload orchestration
│   │   └── validate/                    # Validation orchestration
│   ├── playbook-watcher/                # Playbook queue watcher service
│   │   └── playbook_watcher_service.py  # Long-running systemd service
│   ├── playbook_paths.yml               # Playbook name → path mapping (SSOT)
│   ├── alembic/                         # Database migrations
│   ├── requirements.txt                 # Python dependencies
│   └── tests/                           # Unit + integration tests
├── playbooks/
│   ├── ansible.cfg                      # Standalone sub-playbook config
│   ├── prepare_build_stream.yml         # Deploy Postgres + GitLab + BSM
│   ├── setup_gitlab.yml                 # Configure GitLab CI/CD
│   ├── cleanup_build_stream.yml         # Full domain cleanup
│   ├── cleanup_gitlab.yml               # GitLab-specific cleanup
│   ├── upgrade_build_stream.yml         # Upgrade flow
│   └── rollback_build_stream.yml        # Rollback flow
├── roles/
│   ├── credential_utility/              # Domain-specific credential management
│   │   ├── tasks/
│   │   │   ├── main.yml                 # Orchestrator: validate → create → decrypt → prompt
│   │   │   ├── validate_cred_file.yml   # Check credential file existence
│   │   │   ├── create_credential_file.yml # Create from template if missing
│   │   │   ├── decrypt_include_encrypt.yml # Vault decrypt → include → re-encrypt
│   │   │   ├── fetch_bs_credentials.yml # Prompt for build_stream credentials
│   │   │   └── update_credentials.yml   # Update existing credential values
│   │   ├── vars/main.yml                # Credential paths, prompt definitions
│   │   └── templates/
│   │       └── build_stream_credential.j2 # Credential file template
│   ├── postgres/                        # PostgreSQL Quadlet container service
│   ├── deploy_bsm/                      # BuildStream Manager deployment
│   │   ├── tasks/
│   │   │   ├── main.yml                 # Orchestrator: sync app → sync playbooks → deploy
│   │   │   ├── enable_watcher_service.yml # Playbook watcher systemd service
│   │   │   └── deploy_container.yml     # BuildStream API container deployment
│   │   └── vars/main.yml                # Container config, paths, health checks
│   ├── hosted_gitlab/                   # GitLab CE hosted mode deployment
│   │   ├── tasks/
│   │   │   ├── main.yml                 # Orchestrator: validate → install → configure → runner
│   │   │   ├── prereq_checks.yml        # Credential + config validation
│   │   │   ├── validate_prerequisites.yml # Resource checks (CPU, RAM, disk)
│   │   │   ├── install_gitlab.yml       # GitLab CE package installation
│   │   │   ├── configure_gitlab.yml     # GitLab configuration + SSL
│   │   │   ├── create_project.yml       # Create omnia-catalog project
│   │   │   ├── push_ci_files.yml        # Push .gitlab-ci.yml + input files
│   │   │   ├── sync_input_file.yml      # Sync individual input file to GitLab
│   │   │   ├── deploy_runner.yml        # GitLab Runner Quadlet service
│   │   │   └── podman_login.yml         # Docker Hub login (optional)
│   │   ├── vars/main.yml                # GitLab config, runner settings, CI/CD vars
│   │   └── files/
│   │       ├── .gitlab-ci-build.yml     # CI/CD pipeline for build jobs
│   │       └── .gitlab-ci-deploy-child-template.yml # Child pipeline template
│   ├── gitlab_passwordless_ssh/         # SSH key setup for GitLab host
│   ├── cleanup_build_stream/            # Domain cleanup orchestrator
│   │   ├── tasks/
│   │   │   ├── main.yml                 # Orchestrator: container → postgres → credentials
│   │   │   ├── cleanup_build_stream_container.yml # Stop/remove BSM + watcher
│   │   │   ├── cleanup_postgres.yml     # Stop/remove postgres container
│   │   │   ├── cleanup_automation.yml   # Remove automation framework
│   │   │   └── cleanup_credentials.yml  # Delete credential files
│   │   └── vars/main.yml                # Cleanup paths, container names
│   └── cleanup_gitlab/                  # GitLab cleanup
│       ├── tasks/
│       │   ├── main.yml                 # Orchestrator: services → packages → dirs → certs
│       │   ├── cleanup_services.yml     # Stop GitLab services
│       │   ├── cleanup_packages.yml     # Remove GitLab packages
│       │   ├── cleanup_directories.yml  # Remove GitLab directories
│       │   ├── cleanup_runner.yml       # Remove GitLab Runner
│       │   └── cleanup_certificates.yml # Remove SSL certificates
│       └── vars/main.yml                # GitLab paths, service names
├── input/                               # Default input configurations
│   └── build_stream_config.yml          # BuildStream configuration template
├── containers/
│   └── build_images.sh                  # Self-contained build_stream container build
├── INPUT_CONTRACT.md
├── OUTPUT_CONTRACT.md
└── BUILD_STREAM_DESIGN.md              # This file
```

---

## 3. Domain Configuration

| Item | Value |
|------|-------|
| Main playbook | `build_stream.yml` |
| Input config | `build_stream_config.yml` |
| Credential file | `build_stream_credentials.yml` |
| Credential key | `.build_stream_credentials_key` |
| Input subdir | `input/project_default/` |
| Output subdir | `output/project_default/` |
| Log path | `./output/build_stream.log` (relative to playbook CWD) |
| API log path | `/opt/omnia/build_stream/log/` |
| Playbook queue | `/opt/omnia/build_stream/playbook_queue/` |

### Ansible Config (ansible.cfg)

```ini
roles_path = roles
callback_plugins = ../playbooks/utils/callback_plugins
library = ../common/library/modules
module_utils = ../common/library/module_utils
```

**Note**: Unlike image_build_manager, build_stream still references `../common/` for shared modules. Future refactoring may eliminate this dependency.

---

## 4. End-to-End Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         BUILD STREAM — EXECUTION FLOW                               │
└─────────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
  │          │      │          │      │          │      │          │      │          │
  │  User /  │      │  Setup   │      │ Prepare  │      │  GitLab  │      │  Deploy  │
  │ omnia.sh │      │  Guard   │      │  Infra   │      │  CI/CD   │      │  Status  │
  │          │      │          │      │          │      │          │      │          │
  └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
       │                 │                 │                 │                 │
       │  Step 0: Setup  │                 │                 │                 │
       │────────────────>│                 │                 │                 │
       │                 │ ┌─────────────────────────────┐   │                 │
       │                 │ │ 1. Upgrade guard check      │   │                 │
       │                 │ │ 2. Load project config      │   │                 │
       │                 │ │ 3. Domain credential util   │   │                 │
       │                 │ └─────────────────────────────┘   │                 │
       │                 │                 │                 │                 │
       │  Step 1: Prepare Infrastructure   │                 │                 │
       │──────────────────────────────────>│                 │                 │
       │                 │                 │ ┌─────────────────────────────┐   │
       │                 │                 │ │ 1. Deploy PostgreSQL        │   │
       │                 │                 │ │ 2. Deploy BuildStream API   │   │
       │                 │                 │ │ 3. Deploy playbook-watcher  │   │
       │                 │                 │ │ 4. Health checks            │   │
       │                 │                 │ └─────────────────────────────┘   │
       │                 │                 │                 │                 │
       │  Step 2: Configure GitLab CI/CD                     │                 │
       │────────────────────────────────────────────────────>│                 │
       │                 │                 │                 │ ┌─────────────────────────────┐
       │                 │                 │                 │ │ 1. Install GitLab CE        │
       │                 │                 │                 │ │ 2. Configure SSL + auth     │
       │                 │                 │                 │ │ 3. Create omnia-catalog     │
       │                 │                 │                 │ │ 4. Push CI/CD pipelines     │
       │                 │                 │                 │ │ 5. Deploy GitLab Runner     │
       │                 │                 │                 │ └─────────────────────────────┘
       │                 │                 │                 │                 │
       │  Step 3: Write status output                                          │
       │──────────────────────────────────────────────────────────────────────>│
       │                 │                 │                 │                 │
  ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐
  │  User /  │      │  Setup   │      │ Prepare  │      │  GitLab  │      │  Deploy  │
  │ omnia.sh │      │  Guard   │      │  Infra   │      │  CI/CD   │      │  Status  │
  └──────────┘      └──────────┘      └──────────┘      └──────────┘      └──────────┘

Figure: build_stream.yml orchestration flow
```

### Execution Steps

| Step | Play | Host | Description |
|------|------|------|-------------|
| 0 | Setup | localhost | Upgrade guard + input dir + credential utility |
| 1 | Prepare | oim (SSH) | Deploy PostgreSQL + BuildStream API + playbook-watcher |
| 2 | GitLab | gitlab_server | Install GitLab CE + configure CI/CD + deploy runner |
| 3 | Output | localhost | Write `build_stream_status.yml` |

### Tags

| Tag | What runs |
|-----|-----------|
| *(none)* | Full flow: setup → prepare → gitlab |
| `prepare` | Steps 0–1 only (deploy infra) |
| `gitlab` | Steps 0 + 2 (GitLab deployment) |
| `cleanup` | Cleanup BuildStream + GitLab + Postgres |
| `upgrade` | Upgrade flow (placeholder) |
| `rollback` | Rollback flow (placeholder) |

---

## 5. Credential Management Design (HLD)

### 5.1 Architecture

```
┌─────────────────────────────────────────────────────────┐
│           credential_utility role                        │
│   (roles/credential_utility/tasks/main.yml)             │
├─────────────────────────────────────────────────────────┤
│  Step 1: Load build_stream_config.yml                   │
│  Step 2: Validate credential file exists                │
│  Step 3: Create from template if missing                │
│  Step 4: Decrypt and include existing credentials       │
│  Step 5: Prompt for build_stream credentials            │
│    ├── gitlab_root_password (mandatory)                 │
│    ├── gitlab_ssh_password (mandatory)                  │
│    ├── build_stream_auth_username (conditional)         │
│    ├── build_stream_auth_password (conditional)         │
│    ├── postgres_user (conditional)                      │
│    └── postgres_password (conditional)                  │
│  Step 6: Re-encrypt with Ansible Vault                  │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Credential Fields

| Field | Type | When Required |
|-------|------|---------------|
| `gitlab_root_password` | Mandatory | Always (GitLab root user password) |
| `gitlab_ssh_password` | Mandatory | Always (SSH to GitLab host) |
| `build_stream_auth_username` | Conditional | When `enable_build_stream == true` |
| `build_stream_auth_password` | Conditional | When `enable_build_stream == true` |
| `postgres_user` | Conditional | When `enable_build_stream == true` |
| `postgres_password` | Conditional | When `enable_build_stream == true` |

### 5.3 Credential Lifecycle

```
1. Template creates: build_stream_credentials.yml (plaintext with defaults)
2. Prompt fills:     Interactive prompts for empty mandatory fields
3. Vault encrypts:   ansible-vault encrypt with .build_stream_credentials_key
4. Runtime reads:    Ansible decrypts at playbook execution time
5. Cleanup removes:  cleanup_build_stream role deletes cred + key files
```

### 5.4 Domain Segregation

| Credential | Before (utils) | After (build_stream) |
|------------|---------------|----------------------|
| `gitlab_root_password` | `omnia_config_credentials.yml` | `build_stream_credentials.yml` only |
| `gitlab_ssh_password` | `provision_password` (shared) | `gitlab_ssh_password` (domain-specific) |
| `postgres_user` | N/A | `build_stream_credentials.yml` |
| `postgres_password` | N/A | `build_stream_credentials.yml` |

**Key Change**: `gitlab_ssh_password` replaces the shared `provision_password` for GitLab host SSH access. This eliminates cross-domain credential dependencies.

### 5.5 File Locations

```
input/project_default/
├── build_stream_credentials.yml         ← Vault-encrypted credentials
├── .build_stream_credentials_key        ← Vault password file
└── build_stream/
    └── build_stream_config.yml          ← BuildStream configuration
```

---

## 6. Cleanup Design (HLD)

### 6.1 Architecture

The cleanup flow is orchestrated by `cleanup_build_stream.yml` which calls domain-specific cleanup roles in the correct order:

```
┌─────────────────────────────────────────────────────────┐
│           cleanup_build_stream.yml                       │
├─────────────────────────────────────────────────────────┤
│  Step 1: Cleanup GitLab (cleanup_gitlab.yml)            │
│    ├── Stop GitLab services                             │
│    ├── Remove GitLab packages                           │
│    ├── Remove GitLab directories                        │
│    ├── Remove GitLab Runner                             │
│    └── Remove SSL certificates                          │
│  Step 2: Cleanup BuildStream container + watcher        │
│    ├── Stop omnia_build_stream container                │
│    ├── Remove Quadlet service files                     │
│    ├── Stop playbook_watcher.service                    │
│    ├── Remove watcher systemd unit                      │
│    └── Remove automation framework                      │
│  Step 3: Cleanup PostgreSQL                             │
│    ├── Stop omnia_postgres container                    │
│    ├── Remove Quadlet service files                     │
│    └── Optionally remove data (postgres_backup flag)    │
│  Step 4: Cleanup NFS directories                        │
│    ├── Remove logs, queue, SSL, inventory               │
│    └── Preserve postgres data by default                │
│  Step 5: Cleanup credentials                            │
│    ├── Delete build_stream_credentials.yml              │
│    └── Delete .build_stream_credentials_key             │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Cleanup Scope

| Component | What Gets Cleaned | Preserved by Default |
|-----------|-------------------|---------------------|
| **GitLab** | Packages, services, directories, runner, certs | None |
| **BuildStream** | Container, Quadlet, systemd service | None |
| **Playbook Watcher** | Service, systemd unit | None |
| **PostgreSQL** | Container, Quadlet service | **Data directories** (use `-e postgres_backup=false` to delete) |
| **NFS** | Logs, queue, SSL, inventory | None |
| **Credentials** | Credential files, vault keys | None |

### 6.3 Usage

```bash
# Full cleanup (preserves postgres data)
cd /omnia/build_stream
ansible-playbook playbooks/cleanup_build_stream.yml

# Full cleanup including postgres data
ansible-playbook playbooks/cleanup_build_stream.yml -e postgres_backup=false

# Skip GitLab cleanup
ansible-playbook playbooks/cleanup_build_stream.yml --skip-tags gitlab
```

### 6.4 Domain Segregation Achievement

**Before**: BuildStream cleanup was scattered across `playbooks/utils/roles/oim_cleanup/` with shared logic for multiple domains.

**After**: All BuildStream cleanup is self-contained in:
- `build_stream/playbooks/cleanup_build_stream.yml`
- `build_stream/playbooks/cleanup_gitlab.yml`
- `build_stream/roles/cleanup_build_stream/`
- `build_stream/roles/cleanup_gitlab/`

The generic `oim_cleanup` now only displays a warning message pointing users to the domain-specific cleanup playbook.

---

## 7. GitLab CI/CD Integration Design (HLD)

### 7.1 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitLab CI/CD Pipeline                           │
├─────────────────────────────────────────────────────────────────────────┤
│  Trigger: Manual or API call to BuildStream                             │
│  Pipeline: .gitlab-ci-build.yml (parent) + child templates              │
│  Runner: GitLab Runner (Quadlet systemd service)                        │
│  Executor: Shell (runs ansible-playbook directly)                       │
│  Input: Omnia config files from GitLab repository                       │
│  Output: Job status via BuildStream API                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Pipeline Stages

| Stage | Jobs | Description |
|-------|------|-------------|
| `build` | `build-x86_64`, `build-aarch64` | Build OS images for each architecture |
| `deploy` | `deploy-parent` | Trigger child pipelines for deployment |
| `deploy-child` | `deploy-{job_id}` | Deploy images to target nodes |
| `validate` | `validate-{job_id}` | Run Molecule validation tests |
| `local-repo` | `local-repo-{job_id}` | Create local repository |
| `restart` | `restart-{job_id}` | Restart failed nodes |

### 7.3 Input File Synchronization

The `hosted_gitlab` role syncs Omnia input files to the GitLab repository:

| File | Required | Purpose |
|------|----------|---------|
| `build_stream_config.yml` | Yes | BuildStream configuration |
| `local_repo_config.yml` | No | Local repository settings |
| `network_spec.yml` | No | Network configuration |
| `provision_config.yml` | No | Provisioning settings |
| `pxe_mapping_file.csv` | No | PXE boot mappings |
| `storage_config.yml` | No | Storage configuration |
| `telemetry_config.yml` | No | Telemetry settings |
| `security_config.yml` | No | Security settings |
| `high_availability_config.yml` | No | HA configuration |
| `omnia_config.yml` | No | General Omnia config |

**Fix Applied**: Added existence check before copying optional files (e.g., `high_availability_config.yml`) to prevent failures when files are missing.

### 7.4 Playbook Path Registry

The `playbook_paths.yml` file serves as the **single source of truth** for playbook name → absolute path mappings:

```yaml
playbook_paths:
  build_image_x86_64.yml: "/omnia/build_image_x86_64/build_image_x86_64.yml"
  build_image_aarch64.yml: "/omnia/build_image_aarch64/build_image_aarch64.yml"
  provision.yml: "/omnia/provision/provision.yml"
  local_repo.yml: "/omnia/local_repo/local_repo.yml"
  set_pxe_boot.yml: "/omnia/utils/set_pxe_boot.yml"
  discovery.yml: "/omnia/discovery/playbooks/discovery.yml"
  include_input_dir.yml: "/omnia/utils/include_input_dir.yml"
```

**Consumers**:
1. **`playbook_registry.py`** — Loaded by orchestrator use cases via `get_playbook_path()`
2. **`playbook_watcher_service.py`** — Loaded as whitelist for playbook name validation

This prevents path injection attacks and provides a centralized mapping that can be updated without code changes.

---

## 8. Playbook Watcher Service Design (HLD)

### 8.1 Architecture

```
┌─────────────────────────────────────────────────────────┐
│           playbook_watcher_service.py                    │
│   (Long-running systemd service on OIM host)            │
├─────────────────────────────────────────────────────────┤
│  1. Watch /nfs/omnia/playbook_queue/ for JSON files     │
│  2. Validate playbook name against whitelist            │
│  3. Map playbook name to full path via registry         │
│  4. Execute ansible-playbook with extra vars            │
│  5. Stream output to job-specific log file              │
│  6. Update job status in PostgreSQL                     │
│  7. Move completed request to archive                   │
└─────────────────────────────────────────────────────────┘
```

### 8.2 Request Format

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "playbook_name": "provision.yml",
  "playbook_path": "provision.yml",
  "extra_vars": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "attempt": 1
  },
  "timeout_minutes": 60
}
```

### 8.3 Security Features

| Feature | Implementation |
|---------|---------------|
| **Playbook name whitelist** | Only playbooks in `playbook_paths.yml` are allowed |
| **Path injection prevention** | Full path resolved from whitelist, not user input |
| **Taint breaking** | `str()` cast on whitelist lookup result breaks Checkmarx taint chain |
| **Input sanitization** | JSON decoder used instead of `json.loads()` |
| **Timeout enforcement** | Configurable per-playbook timeout with default 30 minutes |

### 8.4 Systemd Service

```ini
[Unit]
Description=Omnia BuildStream Playbook Watcher
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={{ oim_shared_path }}/build_stream
ExecStart=/usr/bin/python3 {{ oim_shared_path }}/build_stream/playbook-watcher/playbook_watcher_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Note**: The watcher runs as a systemd service, separate from the `omnia_build_stream` container. Restarting the container does NOT reload watcher code — you must restart the systemd service.

---

## 9. BuildStream API Design (HLD)

### 9.1 Architecture

The BuildStream API is a FastAPI application following **Domain-Driven Design (DDD)** and **Clean Architecture** principles:

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                   │
│   Routers: build_image, deploy, local_repo, restart,    │
│            upload, validate, cleanup                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 Orchestrator Layer                       │
│   Use Cases: CreateBuildImageUseCase,                   │
│              DeployUseCase, CreateLocalRepoUseCase, etc. │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Core Domain Layer                      │
│   Entities: Job, Stage, PlaybookRequest                 │
│   Value Objects: JobId, PlaybookPath, ExtraVars         │
│   Repositories: JobRepository, StageRepository           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│               Infrastructure Layer                       │
│   Database: PostgreSQL (SQLAlchemy ORM)                 │
│   NFS: File-based repositories                          │
│   S3: MinIO client                                       │
└─────────────────────────────────────────────────────────┘
```

### 9.2 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/build-image` | POST | Create build image job |
| `/deploy` | POST | Create deployment job |
| `/local-repo` | POST | Create local repository job |
| `/restart` | POST | Restart failed nodes |
| `/upload` | PUT | Upload configuration files |
| `/validate` | POST | Run Molecule validation |
| `/cleanup` | POST | Cleanup job artifacts |
| `/jobs/{job_id}` | GET | Get job status |
| `/jobs/{job_id}/stages` | GET | Get job stages |
| `/health` | GET | Health check |

### 9.3 Database Schema

```sql
-- Jobs table
CREATE TABLE jobs (
  id UUID PRIMARY KEY,
  client_id VARCHAR NOT NULL,
  correlation_id VARCHAR,
  job_type VARCHAR NOT NULL,
  status VARCHAR NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Stages table
CREATE TABLE stages (
  id UUID PRIMARY KEY,
  job_id UUID REFERENCES jobs(id),
  stage_name VARCHAR NOT NULL,
  stage_type VARCHAR NOT NULL,
  status VARCHAR NOT NULL,
  attempt INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Playbook requests table (queue)
CREATE TABLE playbook_requests (
  id UUID PRIMARY KEY,
  job_id UUID REFERENCES jobs(id),
  stage_id UUID REFERENCES stages(id),
  playbook_name VARCHAR NOT NULL,
  playbook_path VARCHAR NOT NULL,
  extra_vars JSONB,
  timeout_minutes INTEGER,
  status VARCHAR NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 9.4 Logging Standards

**All logging MUST use `log_secure_info()`** from `api.logging_utils`:

```python
from api.logging_utils import log_secure_info

log_secure_info("info", "Job created", job_id[:8])
log_secure_info("error", "Database error", exc_info=True)
```

**Automatic redaction** of:
- IP addresses
- JWT tokens
- Passwords
- API keys
- Email addresses

---

## 10. Deployment Sync Design

### 10.1 Self-Contained App Deployment (podman cp)

The `omnia_build_stream` container image embeds the application code at `/app-source/`.
At deployment time, `prepare_build_stream.yml` extracts this code to the host/NFS shared
path so the volume mount provides it at `/opt/omnia/build_stream` inside the container:

```yaml
# prepare_build_stream.yml — Deploy build_stream app code
- name: Create temporary container to extract app code
  ansible.builtin.command:
    cmd: "podman create --name bs_app_extract {{ bs_image }} /bin/true"

- name: Extract app code from image to NFS
  ansible.builtin.command:
    cmd: "podman cp bs_app_extract:/app-source/. {{ bs_nfs_dest }}/"

- name: Remove temporary extraction container
  ansible.builtin.command:
    cmd: "podman rm bs_app_extract"
```

This approach eliminates the dependency on `omnia_core` for delivering app code.
The build_stream domain is fully self-contained — its container image carries
both the runtime environment and the application source.

### 10.2 Development Deployment Sync

**After ANY file is modified under `/root/Documents/omnia/src/build_stream/app/`**, you MUST:

1. **Rsync** the changed file(s) to the shared path:
   ```bash
   rsync -av /root/Documents/omnia/src/build_stream/app/<path> /opt/omnia/build_stream/<path>
   ```

2. **Restart** the appropriate service(s):
   - For **API / orchestrator / core / infra** code changes:
     ```bash
     podman restart omnia_build_stream
     ```
   - For **playbook-watcher** code changes:
     ```bash
     systemctl restart playbook_watcher.service
     ```

**Why**: The volume mount (`/opt/omnia:/opt/omnia`) is what the running container and watcher use. Changes are not picked up until synced and restarted.

---

## 11. Input/Output Contracts

### 11.1 build_stream_config.yml (Input)

**Location**: `input/project_default/build_stream_config.yml`

```yaml
enable_build_stream: true
build_stream_host_ip: "100.10.0.28"
build_stream_port: 8010
gitlab_host: "100.10.0.112"
gitlab_https_port: 443
gitlab_project_name: "omnia-catalog"
gitlab_project_visibility: "private"
gitlab_default_branch: "main"
gitlab_puma_workers: 2
gitlab_sidekiq_concurrency: 10
gitlab_min_cpu_cores: 2
gitlab_min_memory_gb: 4
gitlab_min_storage_gb: 20
```

### 11.2 build_stream_status.yml (Output)

**Location**: `output/project_default/build_stream/build_stream_status.yml`

```yaml
overall_status: "success"
build_stream:
  api_url: "http://100.10.0.28:8010"
  gitlab_url: "https://100.10.0.112"
  project_url: "https://100.10.0.112/root/omnia-catalog"
  runner_status: "online"
  postgres_status: "healthy"
```

---

## 12. Backward Compatibility

- No breaking changes for users who don't use build_stream.
- `build_stream_config.yml` is **required** — no legacy fallback.
- Sub-playbooks work independently with setup guards.
- Container build is self-contained in `src/build_stream/containers/`.
- Cleanup is fully domain-segregated — no impact on other domains.

---

## 13. Testing

```bash
# Standalone credential utility
cd /omnia/build_stream
ansible-playbook -i localhost, roles/credential_utility/tasks/main.yml

# Full deployment flow
ansible-playbook build_stream.yml

# Tag-specific runs
ansible-playbook build_stream.yml --tags prepare
ansible-playbook build_stream.yml --tags gitlab

# Cleanup
ansible-playbook playbooks/cleanup_build_stream.yml

# Cleanup without postgres data
ansible-playbook playbooks/cleanup_build_stream.yml -e postgres_backup=false

# Skip GitLab cleanup
ansible-playbook playbooks/cleanup_build_stream.yml --skip-tags gitlab
```

---

## 14. Future Enhancements

1. **Eliminate `../common/` dependency** — Copy shared modules locally like image_build_manager
2. **Add L1/L2 validation** — JSON schema + cross-field logic validation for `build_stream_config.yml`
3. **OAuth2 integration** — Replace basic auth with OAuth2 for API security
4. **Multi-tenant support** — Isolate jobs by client_id with RBAC
5. **Horizontal scaling** — Multiple API instances behind load balancer
6. **Observability** — Prometheus metrics + Grafana dashboards
7. **Automated rollback** — Detect failures and auto-rollback to previous version
