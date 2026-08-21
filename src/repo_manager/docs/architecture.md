# Repo Manager — Architecture Overview

## System Context

```
                    ┌─────────────────────────────────────────────┐
                    │           Repo Manager                       │
                    │                                             │
  ┌──────────┐      │  ┌────────────┐  ┌────────────┐  ┌────────┐│      ┌──────────┐
  │ repo_    │─────▶│  │ Deploy     │─▶│ Download   │─▶│ Status ││─────▶│ repo_    │
  │ manager_ │      │  │  Pulp      │  │  Content   │  │  Gen   ││      │ status.  │
  │ config. │      │  │  (Podman)  │  │            │  │        ││      │ yml      │
  │ yml +    │      │  └────────────┘  └────────────┘  └────────┘│      └──────────┘
  │ software_│      │                                             │
  │ config. │      │  ┌────────────┐  ┌────────────┐             │
  │ json     │      │  │ Validate    │─▶│ Cleanup    │             │
  └──────────┘      │  │  Config    │  │  Pulp      │             │
                    │  └────────────┘  └────────────┘             │
                    └─────────────────────────────────────────────┘
```

## Execution Mode

**Bare-metal** — the only supported execution mode. The playbook runs
directly on the RHEL host via `ansible-playbook`. All tasks execute locally
(`hosts: localhost`) with no SSH dependencies.

## Execution Flow

### 1. Deploy Pulp (`--tags deploy`)

- Deploy Pulp content server using Podman containers
- Configure Pulp CLI with system-wide symlink to `/usr/local/bin/pulp`
- Set up SSL/TLS certificates for HTTPS access
- Create repositories for RPM, file, and Python distributions
- Pre-flight checks to detect existing healthy Pulp deployment

### 2. Precheck Config (`--tags precheck`)

- Schema validation of `repo_manager_config.yml` against JSON schema
- Logic validation (subscription URLs, user repositories, OS versions)
- Validate RHEL subscription and OS URLs
- No credentials required for basic precheck

### 3. Download Content (`--tags download`)

- Download RPM repositories based on `software_config.json`
- Download container images (tarball, git, manifest types)
- Download Python pip modules
- Download ISO images and shell scripts
- Download Ansible Galaxy collections
- Parallel download with configurable concurrency
- Generate download status reports

### 4. Generate Status (`--tags status`)

- Query Pulp for all available distributions
- Generate `repo_status.yml` with repository URLs
- Include RPM repos, file repos, user repos, and base URLs
- Map repository names to Pulp distribution URLs
- Support for x86_64 and aarch64 architectures

### 5. Cleanup (`--tags cleanup`)

- Stop and remove Pulp containers
- Remove Pulp data and configuration
- Clean up temporary files and logs
- Remove system-wide Pulp CLI symlink

## Role Dependency Graph

```
deploy_pulp ─────────────────────────────────────────────┐
       │                                                 │
       ▼                                                 │
validate_subscription ───────────────────────────────────┤
       │                                                 │
       ▼                                                 │
download ──────────────────────────────────▶ generate_repo_status
       │                                                 │
       ▼                                                 │
cleanup_pulp ───────────────────────────────────────────┘
```

## Data Contract

### Inputs

| File | Source | Purpose |
|------|--------|---------|
| `repo_manager_config.yml` | `input/project_default/` | Repository configuration, user repos, OS settings |
| `software_config.json` | `input/project_default/` | Software packages and download configuration |
| `repo_manager_endpoint_config.json` | `input/project_default/` | Endpoint configuration for services |

### Outputs

| File | Purpose |
|------|---------|
| `repo_status.yml` | Repository URLs, cert paths, OS metadata for cluster nodes |
| Download status CSV | `/opt/omnia/repo_manager/output/<project_name>/` |
| Validation logs | `/var/log/omnia/repo_manager/repo_manager.log` |

## Key Paths

| Path | Purpose |
|------|---------|
| `/opt/omnia/repo_manager/` | Base directory for all repo manager data |
| `/opt/omnia/repo_manager/input/<project_name>/` | Input configuration files |
| `/opt/omnia/repo_manager/output/<project_name>/` | Output directory for repo_status.yml and status files |
| `/opt/omnia/repo_manager/log/` | Log files for repo manager operations |
| `/opt/omnia/repo_manager/log/pulp/` | Pulp server logs |
| `/opt/omnia/repo_manager/pulp_config/` | Pulp configuration and data |
| `/opt/omnia/repo_manager/pulp_config/settings/certs/` | Pulp SSL/TLS certificates |
| `/opt/omnia/repo_manager/rhel_repo_certs/` | RHEL subscription certificates |
| `/opt/omnia/repo_manager/offline_repo/` | Offline repository storage |
| `/opt/omnia/catalog/` | Catalog JSON files (shared across modules) |
| `/usr/local/bin/pulp` | System-wide Pulp CLI symlink |

## Complete Directory Structure

```
/opt/omnia/
├── repo_manager/                          # All repo_manager data (domain-based organization)
│   ├── input/                             # Input configurations
│   │   └── project_default/
│   │       ├── repo_manager_config.yml
│   │       └── repo_manager_endpoint_config.yml
│   ├── output/                            # Generated outputs
│   │   └── project_default/
│   │       └── repo_status.yml
│   ├── log/                               # All logs
│   │   ├── pulp/                          # Pulp server logs
│   │   ├── rhel/10.0/x86_64/              # Download logs by OS/arch
│   │   │   ├── slurm_control_node_group/
│   │   │   └── mirror_status/
│   │   │       ├── pulp_mirror_index.json
│   │   │       └── global_package_index.json
│   │   └── validation_omnia_project_default.log
│   ├── pulp_config/                       # Pulp configuration and data
│   │   ├── settings/
│   │   │   ├── certs/                     # SSL/TLS certificates
│   │   │   │   ├── pulp_webserver.crt
│   │   │   │   └── pulp_webserver.key
│   │   │   ├── pulp_storage/              # Pulp content storage
│   │   │   ├── pgsql/                     # PostgreSQL database
│   │   │   ├── containers/                # Container storage
│   │   │   └── settings.py                # Pulp configuration
│   │   ├── pulp_ha/                       # Pulp CLI config
│   │   │   └── cli.toml
│   │   └── nginx/                         # Nginx configuration (HTTPS)
│   │       └── nginx.conf
│   ├── rhel_repo_certs/                   # RHEL subscription certificates
│   │   ├── redhat.repo
│   │   └── redhat-uep.pem
│   ├── offline_repo/                      # Offline repository storage
│   │   └── cluster/
│   │       └── x86_64/rhel/10.0/rpms/
│   └── .data/                             # Metadata files
│       └── oim_metadata.yml
└── catalog/                               # Catalog files (shared across modules)
    └── catalog_rhel.json
```

## Content Types

Repo Manager supports the following content types in Pulp:

| Type | Description | Examples |
|------|-------------|----------|
| RPM | RPM repositories | OS repositories, custom RPM repos |
| Tarball | Container image tarballs | Docker images, Singularity images |
| Manifest | Container manifests | Image manifests, signatures |
| Git | Git repositories | Source code repositories |
| Pip Module | Python packages | PyPI packages, custom Python modules |
| ISO | ISO images | OS installation media |
| Shell | Shell scripts | Installation scripts, utilities |
| Ansible Galaxy Collection | Ansible collections | Automation collections |

## Key Design Decisions

1. **Localhost-only execution** — No SSH dependencies, all tasks run on localhost
2. **Pulp as content server** — Uses Pulp for content management and distribution
3. **System-wide Pulp CLI** — Creates `/usr/local/bin/pulp` symlink for easy access
4. **Tag-based execution** — Supports selective execution via tags (deploy, precheck, download, status, cleanup)
5. **Parallel downloads** — Configurable concurrency for content downloads
6. **Architecture support** — Supports both x86_64 and aarch64 architectures
7. **Subscription validation** — Validates RHEL subscription before OS URL configuration
8. **User repository support** — Allows custom user repositories in addition to standard repos
9. **SSL/TLS support** — Configures HTTPS for Pulp server with certificate management
10. **Pre-flight checks** — Detects existing healthy Pulp deployment to avoid unnecessary redeployment

## Custom Modules

Repo Manager includes custom Ansible modules for Pulp operations:

| Module | Purpose |
|--------|---------|
| `generate_local_repo_access` | Generate repo_status.yml from Pulp distributions |
| `pulp_cleanup` | Cleanup Pulp repositories and distributions |
| `pulp_repo_name_migration` | Migrate repository names between versions |
| `validate_input` | Validate input configuration files |
| `validate_credentials` | Validate credential storage and access |
| `validate_user_repo` | Validate user repository configurations |
| `process_rpm_config` | Process RPM configuration and download tasks |
| `parallel_tasks` | Execute tasks in parallel with concurrency control |
| `prepare_tasklist` | Prepare and organize download task lists |
| `localrepo_metadata_manager` | Manage local repository metadata |
| `check_user_registry` | Check user registry access and authentication |
| `fetch_credential_rule` | Fetch credential rules for validation |
| `cert_vault_handler` | Handle certificate vault operations |
| `vault_handler` | General vault operations for secrets |

## Plugin Structure

Following Ansible standard structure:

```
plugins/
├── callback/          # Output callbacks (omnia_default)
├── modules/           # Custom Ansible modules
└── module_utils/      # Module utilities
    ├── input_validation/  # Input validation framework
    └── repo_manager/       # Repo manager utilities
```
