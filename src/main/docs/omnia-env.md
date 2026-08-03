# omnia.env — Environment Configuration Documentation

The `omnia.env` file is the **single source of configuration** for Omnia deployments. All domains read their configuration from this file.

## Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SYSTEM_ADMIN_NIC_IPV4` | Admin NIC IPv4 address of the OIM host. Used for Pulp, S3, container registry, and provisioning. | `172.16.107.254` |

## Optional Variables (with Defaults)

| Variable | Description | Default |
|----------|-------------|---------|
| `OMNIA_DATA_PATH` | Root data directory for all Omnia persistent data | `/opt/omnia` |
| `OMNIA_PROJECT_NAME` | Project name — maps to input/output subdirectories | `project_default` |
| `SYSTEM_HOSTNAME` | Short hostname of the OIM host (NOT FQDN) | `oim` |
| `SYSTEM_DOMAIN_NAME` | Domain name of the OIM host | `omnia.cluster` |
| `OMNIA_VENV_PATH` | Path to the shared Python virtual environment | `/opt/omnia/venv` |
| `CATALOG_FILE_PATH` | Convention path for catalog JSON (reference only — actual path is set in `image_build_config.yml`) | `${OMNIA_DATA_PATH}/catalog/catalog_rhel.json` |

## Component Override Variables

Each component stores data under `$OMNIA_DATA_PATH/<component>/`. Override these only for non-standard layouts:

| Variable | Default |
|----------|---------|
| `IMAGE_BUILD_MANAGER_DATA_PATH` | `${OMNIA_DATA_PATH}/image_build_manager` |
| `REPO_MANAGER_DATA_PATH` | `${OMNIA_DATA_PATH}/repo_manager` |
| `DISCOVERY_DATA_PATH` | `${OMNIA_DATA_PATH}/discovery` |
| `ORCHESTRATOR_DATA_PATH` | `${OMNIA_DATA_PATH}/orchestrator` |
| `TELEMETRY_DATA_PATH` | `${OMNIA_DATA_PATH}/telemetry` |
| `BUILD_STREAM_DATA_PATH` | `${OMNIA_DATA_PATH}/build_stream` |

## Example omnia.env

```bash
# =============================================================================
# omnia.env — Omnia Environment Configuration
# =============================================================================
#
# FILL THIS FILE BEFORE RUNNING omnia.sh OR ANY ANSIBLE PLAYBOOK.
#
# This file is the SINGLE source of configuration for the Omnia deployment.
# Uncomment and set the required variables below. Optional variables have
# sensible defaults — change them only if your setup differs.
#
# Usage:
#   1. Edit this file:    vi src/main/omnia.env
#   2. Setup venv:        ./omnia.sh --setup-venv
#   -- OR --
#   Source manually:      set -a; source src/main/omnia.env; set +a
#   Run playbooks:        cd src/<domain> && ansible-playbook playbooks/<playbook>.yml
#
# =============================================================================

# ┌───────────────────────────────────────────────────────────────────────────┐
# │ REQUIRED — You MUST set these before running anything                    │
# └───────────────────────────────────────────────────────────────────────────┘

# Admin NIC IP address of the OIM host.
# This is the IP used for Pulp, S3, container registry, and provisioning.
SYSTEM_ADMIN_NIC_IPV4=172.16.107.254

# ┌───────────────────────────────────────────────────────────────────────────┐
# │ OPTIONAL — Defaults work for most deployments                            │
# └───────────────────────────────────────────────────────────────────────────┘

# Root data directory for all Omnia persistent data (NFS-mounted or local).
# All component data paths are derived from this root.
OMNIA_DATA_PATH=/opt/omnia

# Project name — maps to input/output subdirectories.
# Override for multi-project deployments.
OMNIA_PROJECT_NAME=project_default

# Short hostname of the OIM host (NOT FQDN).
SYSTEM_HOSTNAME=oim

# Domain name of the OIM host.
SYSTEM_DOMAIN_NAME=omnia.cluster

# Path to the shared Omnia Python virtual environment.
# Created by: ./omnia.sh --setup-venv
OMNIA_VENV_PATH=/opt/omnia/venv

# Omnia release version.
# OMNIA_VERSION=2.2

# ┌───────────────────────────────────────────────────────────────────────────┐
# │ CATALOG — Repo Manager catalog for image build package resolution        │
# └───────────────────────────────────────────────────────────────────────────┘

# Default catalog JSON location (convention path).
# The actual catalog_file path is set in image_build_config.yml (Section 5).
# This env var documents the convention; image_build_manager reads
# the catalog path from its domain config, not from this env var.
# CATALOG_FILE_PATH=${OMNIA_DATA_PATH}/catalog/catalog_rhel.json

# ┌───────────────────────────────────────────────────────────────────────────┐
# │ COMPONENT OVERRIDES — Change only for non-standard layouts               │
# └───────────────────────────────────────────────────────────────────────────┘
# Each component stores data under OMNIA_DATA_PATH/<component>/.
# Uncomment to override:

# IMAGE_BUILD_MANAGER_DATA_PATH=${OMNIA_DATA_PATH}/image_build_manager
# REPO_MANAGER_DATA_PATH=${OMNIA_DATA_PATH}/repo_manager
# DISCOVERY_DATA_PATH=${OMNIA_DATA_PATH}/discovery
# ORCHESTRATOR_DATA_PATH=${OMNIA_DATA_PATH}/orchestrator
# TELEMETRY_DATA_PATH=${OMNIA_DATA_PATH}/telemetry
# BUILD_STREAM_DATA_PATH=${OMNIA_DATA_PATH}/build_stream
```

## Environment Loading

When you run `omnia.sh --setup-venv`, the script:

1. **Copies** `src/main/omnia.env` → `/etc/omnia/omnia.env`
2. **Creates** `/etc/profile.d/omnia-env.sh` — a drop-in that auto-sources the env on every login
3. **Sources** the file immediately so the current session has the vars

After setup, all new login shells (and Ansible playbooks run from them) automatically
have the Omnia environment variables available. No manual sourcing needed.

### System-Wide Paths

| File | Purpose |
|------|---------|
| `/etc/omnia/omnia.env` | System-wide copy of the environment config |
| `/etc/profile.d/omnia-env.sh` | Auto-sources `/etc/omnia/omnia.env` on login |

### Manual Override

To override a variable for a single command without editing the file:

```bash
SYSTEM_ADMIN_NIC_IPV4=10.0.0.1 omnia-cli status
```

### Re-install After Editing

If you edit `src/main/omnia.env`, re-run setup to install the updated file:

```bash
./omnia.sh -s
```

## Validation

`omnia.sh --setup-venv` validates that required variables (e.g., `SYSTEM_ADMIN_NIC_IPV4`) are set in the environment after sourcing. If validation fails, the script exits with an error indicating which variables are missing.

## Multi-Project Deployments

To manage multiple projects, you can either:

1. **Set `OMNIA_PROJECT_NAME` in omnia.env** for the default project
2. **Override it on the command line**:
   ```bash
   OMNIA_PROJECT_NAME=prod ./omnia-cli status
   ```
3. **Use the --project flag with omnia-cli**:
   ```bash
   ./omnia-cli status --project prod
   ```

Each project will have its own input/output directories under each domain's data path.
