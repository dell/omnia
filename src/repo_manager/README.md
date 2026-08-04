# Omnia Repo Manager

**Ansible Galaxy Collection: `omnia.repo_manager`**

Manage Pulp content server for offline HPC cluster provisioning. Downloads and manages
RPM repositories, container images, Python packages, and other content types. Supports
x86_64 and aarch64 architectures with tag-based execution for selective operations.

**Runs directly on a RHEL host** with Ansible + Python.
All tasks execute on localhost with no SSH dependencies.

## Prerequisites

| Requirement | Minimum | Validated |
|------------|---------|-----------|
| OS | RHEL 10.x, Rocky 10.x | RHEL 10.0 |
| Python | 3.11+ | 3.12.8 |
| Ansible | ansible-core 2.20+ | 2.20.0 |
| Container runtime | Podman 5.0+ | 5.3.1 |
| Disk space | 100 GB free | — |

### Ansible Installation

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
./src/main/omnia.sh --setup-venv
source /opt/omnia/venv/bin/activate

# 3. Edit repo_manager_config.yml in the SOURCE tree, then re-stage
vi src/repo_manager/input/project_default/repo_manager_config.yml
vi src/repo_manager/input/project_default/software_config.json
./src/repo_manager/domain-init.sh             # Re-copy to runtime path

# 4. Run playbooks (cd into the playbooks directory)
cd src/repo_manager/playbooks
ansible-playbook repo_manager.yml --tags validate   # Validate config
ansible-playbook repo_manager.yml --tags deploy    # Deploy Pulp
ansible-playbook repo_manager.yml --tags download   # Download content
ansible-playbook repo_manager.yml --tags status     # Generate repo_status.yml
ansible-playbook repo_manager.yml --tags cleanup    # Remove everything

# Or run sub-playbooks directly from their directory:
cd deploy    && ansible-playbook deploy_pulp.yml
cd validate  && ansible-playbook validate_config.yml
cd cleanup   && ansible-playbook cleanup_pulp.yml
```

## Input Files

Input files are **edited in the source tree** and **staged to the runtime data path** before
playbook execution. The staging happens automatically during `omnia.sh -s`, or you can
run `domain-init.sh` manually after editing.

```
Source (git repo)                          Runtime (data path)
─────────────────                          ───────────────────
src/repo_manager/input/<project>/  ──copy──>  /opt/omnia/repo_manager/input/<project>/
                                                │
                                                ▼
                                       Ansible playbooks read from here
```

| File | Source Location | Runtime Location | Required | Description |
|------|----------------|-----------------|----------|-------------|
| `omnia.env` | `src/main/` | N/A (user sources manually) | Yes | Common environment variables |
| `repo_manager_config.yml` | `input/project_default/` | `<data_path>/repo_manager/input/<project>/` | Yes | Pulp server configuration, user repos, OS settings |
| `software_config.json` | `input/project_default/` | `<data_path>/repo_manager/input/<project>/` | Yes | Software packages and download configuration |
| `repo_manager_endpoint_config.json` | `input/project_default/` | `<data_path>/repo_manager/input/<project>/` | Yes | Endpoint configuration for services |

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
| `SYSTEM_ADMIN_NIC_IPV4` | Admin NIC IPv4 (Pulp server endpoint) | **REQUIRED** |
| `REPO_MANAGER_DATA_PATH` | Override repo_manager data path | `${OMNIA_DATA_PATH}/repo_manager` |
| `OMNIA_VENV_PATH` | Path to the shared Omnia Python venv | `/opt/omnia/venv` |

### `repo_manager_config.yml`

Main configuration file for repository manager settings.

```yaml
# Pulp server configuration
pulp_server_ip: "192.168.1.100"
pulp_server_port: 24817
pulp_protocol: "https"

# Cluster OS configuration
cluster_os_type: "rhel"
cluster_os_version: "10.0"

# Output configuration
repo_manager_output_path: "/opt/omnia/repo_manager/output/project_default"

# User repositories (optional)
user_repo_url_x86_64:
  - name: "custom_repo"
    url: "http://custom-repo.example.com/rhel10/"

user_repo_url_aarch64:
  - name: "custom_repo"
    url: "http://custom-repo.example.com/rhel10-aarch64/"
```

### `software_config.json`

Defines software content to download and manage in Pulp.

```json
{
  "software": [
    {
      "name": "slurm",
      "version": "24.05.4",
      "architectures": ["x86_64", "aarch64"],
      "type": "rpm",
      "enabled": true
    },
    {
      "name": "geopm",
      "version": "2.0.0",
      "architectures": ["x86_64"],
      "type": "tarball",
      "enabled": true,
      "source_url": "https://github.com/geopm/geopm"
    }
  ]
}
```

Supported content types: `rpm`, `tarball`, `manifest`, `git`, `pip_module`, `iso`, `shell`, `ansible_galaxy_collection`

## Tags

| Tag | Description |
|-----|-------------|
| `deploy` | Deploy Pulp content server using Podman |
| `validate` | Validate configuration only (no credentials required) |
| `download` | Download content (RPM repos, containers, Python packages, etc.) |
| `status` | Generate repo_status.yml with repository URLs |
| `cleanup` | Remove Pulp containers, data, and configuration |

## Output Paths

All runtime output goes to `<shared_path>/` (default: `/opt/omnia/repo_manager/`):

| Path | Purpose |
|------|---------|
| `<shared_path>/output/<project_name>/` | repo_status.yml, download status CSV |
| `<shared_path>/log/playbooks/` | Ansible playbook logs |
| `<shared_path>/pulp/settings/` | Pulp configuration files |
| `/usr/local/bin/pulp` | System-wide Pulp CLI symlink |

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

## CI/CD Pipeline

The `.github/workflows/ci.yml` runs on push/PR to `main`:

- **lint** — `ansible-lint` on all playbooks
- **bandit** — Security scanning on Python modules
- **pylint** — Code quality checks on Python modules
- **validate-standalone** — Sets env vars, creates input dirs, runs `--tags validate --check`

## Collection Structure

```
repo_manager/                       # omnia.repo_manager collection
├── galaxy.yml                       # Collection metadata (namespace: omnia, name: repo_manager)
├── meta/runtime.yml                 # Ansible version compatibility
├── requirements.txt                 # Python dependencies
├── requirements.yml                 # Ansible Galaxy collections
├── ansible.cfg                      # FQCN config (no path hacks)
├── plugins/                         # Galaxy-standard plugin layout
│   ├── callback/                    # Callback plugins (omnia.repo_manager.omnia_default)
│   ├── modules/                     # Custom Ansible modules (FQCN: omnia.repo_manager.*)
│   │   ├── generate_local_repo_access.py   # Generate repo_status.yml
│   │   ├── pulp_cleanup.py               # Cleanup Pulp repositories
│   │   ├── validate_input.py             # Input validation
│   │   └── process_rpm_config.py         # RPM configuration processing
│   └── module_utils/                # Shared Python utilities for modules
│       ├── input_validation/        # Input validation framework
│       └── local_repo/              # Local repository utilities
├── roles/                           # All Ansible roles
│   ├── deploy_pulp/                 # Pulp deployment
│   ├── validate_subscription/       # RHEL subscription validation
│   ├── download/                    # Content download
│   └── cleanup_pulp/                # Pulp cleanup
├── playbooks/                       # All playbooks (entry point + sub-playbooks)
│   ├── repo_manager.yml             # Entry point
│   ├── deploy/                      # Pulp deployment
│   ├── validate/                    # Input validation
│   ├── repo_operations/             # Download and status generation
│   └── cleanup/                     # Cleanup operations
├── vars/                            # Shared variables
├── domain-init.sh                    # Copies input/ to runtime data path
├── input/                           # User input (source — staged to runtime)
│   └── project_default/
│       ├── repo_manager_config.yml  # User configuration
│       ├── software_config.json     # Software configuration
│       └── repo_manager_endpoint_config.json
├── docs/                            # Domain-specific documentation
│   ├── architecture.md              # Architecture overview
│   ├── content-configuration-guide.md # Software configuration guide
│   ├── troubleshooting.md           # Common issues and fixes
│   ├── contracts/                   # Input/output YAML contracts
│   └── design/                      # Design documents
└── README.md                        # This file
```

### Runtime Directory (auto-created at `/opt/omnia/repo_manager/`)

```
/opt/omnia/repo_manager/
├── input/project_default/       # Staged input files (copied from src/)
│   ├── repo_manager_config.yml
│   ├── software_config.json
│   └── repo_manager_endpoint_config.json
├── output/project_default/      # repo_status.yml, status.csv
├── log/playbooks/              # Ansible playbook logs
└── pulp/settings/              # Pulp configuration files
```

## Custom Modules

Repo Manager includes custom Ansible modules for Pulp operations:

| Module | Purpose |
|--------|---------|
| `generate_local_repo_access` | Generate repo_status.yml from Pulp distributions |
| `pulp_cleanup` | Cleanup Pulp repositories and distributions |
| `pulp_repo_name_migration` | Migrate repository names between versions |
| `validate_input` | Validate input configuration files |
| `validate_credentials` | Validate credential storage and access |
| `process_rpm_config` | Process RPM configuration and download tasks |
| `parallel_tasks` | Execute tasks in parallel with concurrency control |

## Security

### SSL/TLS Configuration

Pulp is configured with HTTPS by default. Certificates are stored in:
```
/opt/omnia/pulp_config/pulp/settings/certs/
├── pulp_webserver.crt
└── pulp_webserver.key
```

### Credential Management

Credentials are managed using Ansible Vault for secure storage. Never commit credentials to version control.

## Troubleshooting

For common issues and solutions, see the [troubleshooting guide](docs/troubleshooting.md).

## License

Apache License, Version 2.0
