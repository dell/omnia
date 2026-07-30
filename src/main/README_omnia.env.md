# omnia.env — Environment Configuration Documentation

The `omnia.env` file is the **single source of configuration** for Omnia deployments. All domains read their configuration from this file.

## Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OMNIA_ADMIN_NIC_IP` | Admin NIC IP address of the OIM host. Used for Pulp, S3, container registry, and provisioning. | `172.16.107.254` |

## Optional Variables (with Defaults)

| Variable | Description | Default |
|----------|-------------|---------|
| `OMNIA_DATA_PATH` | Root data directory for all Omnia persistent data | `/opt/omnia` |
| `OMNIA_PROJECT_NAME` | Project name — maps to input/output subdirectories | `project_default` |
| `OMNIA_HOSTNAME` | Short hostname of the OIM host (NOT FQDN) | `oim` |
| `OMNIA_DOMAIN_NAME` | Domain name of the OIM host | `omnia.cluster` |
| `OMNIA_VENV_PATH` | Path to the shared Python virtual environment | `/opt/omnia/venv` |

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
OMNIA_ADMIN_NIC_IP=172.16.107.254

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
OMNIA_HOSTNAME=oim

# Domain name of the OIM host.
OMNIA_DOMAIN_NAME=omnia.cluster

# Path to the shared Omnia Python virtual environment.
# Created by: ./omnia.sh --setup-venv
OMNIA_VENV_PATH=/opt/omnia/venv

# Omnia release version.
# OMNIA_VERSION=2.2

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

Both `omnia.sh` and `omnia-cli` source the `omnia.env` file using:

```bash
set -a
. "$ENV_FILE"
set +a
```

This ensures all variables are exported to the shell environment.

## Validation

The `omnia.sh --setup-venv` command validates that required variables are set before proceeding. If validation fails, the script will exit with an error message indicating which variables are missing.

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
