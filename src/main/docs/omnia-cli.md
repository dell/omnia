# omnia-cli — Diagnostics CLI Documentation

The `omnia-cli` script provides status checking and diagnostics for all Omnia domains.

## Install to PATH

To use `omnia-cli` from anywhere on the system:

```bash
sudo cp omnia-cli /usr/local/bin/
sudo chmod +x /usr/local/bin/omnia-cli
```

After installation, run `omnia-cli` directly without `./` or path prefix:

```bash
omnia-cli status
omnia-cli repo-manager
omnia-cli version
```

## Commands

| Command | Description |
|---------|-------------|
| `status [--project <name>]` | Show all domain statuses for a project |
| `repo-manager [--project <name>]` | Detailed repo_manager diagnostics |
| `image-build [--project <name>]` | Detailed image_build_manager diagnostics |
| `orchestrator [--project <name>]` | Orchestrator status |
| `discovery [--project <name>]` | Discovery domain status |
| `telemetry [--project <name>]` | Telemetry stack status |
| `build-stream [--project <name>]` | Build stream (GitLab) status |
| `utils [--project <name>]` | Shared utilities status |
| `logs <domain>` | Browse and tail domain log files |
| `vault edit <domain>` | Edit domain credentials file (Ansible Vault) |
| `version` | Show Omnia version info |
| `help [<domain>]` | Show help (or domain-specific help) |

## Options

- `--project <name>` or `-p <name>` — Project name (default: `$OMNIA_PROJECT_NAME` or `project_default`)

## Examples

```bash
# Check all domains for default project
./omnia-cli status

# Check all domains for a specific project
./omnia-cli status --project my_cluster

# Detailed repo_manager check
./omnia-cli repo-manager

# Image build status for production
./omnia-cli image-build --project prod

# Show version information
./omnia-cli version

# Get help for a specific domain
./omnia-cli help repo-manager
```

## Status Output Format

The CLI uses symbols to indicate status:

- `✔` — Success/completed
- `✗` — Failure/error
- `⚠` — Warning/incomplete
- `–` — Skipped/not run

## Example: `omnia-cli status`

```
Omnia Domain Status  (project: project_default)
------------------------------------------------------------

  ✔ repo manager  completed
    RPM repository synchronization (Pulp)
    Last: 2026-07-29 10:30:15 (repo_status.yml)

  ✔ image build manager  completed
    OS image building (MinIO + Registry + OpenCHAMI)
    Last: 2026-07-29 11:15:42 (build_status.yml)

  – orchestrator
    Cluster orchestration and provisioning
    No output directory

  – discovery
    Hardware discovery and inventory
    No output directory

------------------------------------------------------------
  2/6 domains completed for project project_default
```

## Domain-Specific Commands

### repo-manager

Detailed diagnostics for the repo_manager domain:

- Checks output directory exists
- Validates `repo_status.yml` and `overall_status`
- Verifies `functional_group_packages.yml` exists
- Checks Pulp certificate files
- Counts RPM repos by architecture

```bash
./omnia-cli repo-manager
```

### image-build

Detailed diagnostics for the image_build_manager domain:

- Checks output directory exists
- Validates `build_status.yml` and `overall_status`
- Counts built images by architecture
- Shows latest build log location
- Displays last modified timestamp

```bash
./omnia-cli image-build
```

### logs

Browse and tail domain log files interactively. Searches the following locations:

1. Domain log directory: `$OMNIA_DATA_PATH/<domain>/log/<project>/`
2. Domain log directory (flat): `$OMNIA_DATA_PATH/<domain>/log/` (logs directly in the log folder)
3. Ansible logs: `/var/log/omnia/`
4. Domain output directory: `$OMNIA_DATA_PATH/<domain>/output/<project>/*.log`

```bash
./omnia-cli logs image_build_manager
./omnia-cli logs repo_manager --project prod
```

### vault edit

Edit domain credentials files using Ansible Vault. Prompts for the vault
password and opens the credentials file in `$EDITOR` (defaults to `vi`).

```bash
./omnia-cli vault edit image_build_manager
./omnia-cli vault edit repo_manager
```

## Output Directory Resolution

The CLI resolves output directories based on domain type:

- **repo_manager**: `$OMNIA_DATA_PATH/repo_manager/output/<project>/`
- **Other domains**: `$OMNIA_DATA_PATH/<domain>/output/<project>/`

## Status File Detection

Each domain has a known status file pattern:

| Domain | Status File |
|--------|-------------|
| repo_manager | `repo_status.yml` |
| image_build_manager | `build_status.yml` |
| orchestrator | `orchestrator_status.yml` |
| discovery | `discovery_status.yml` |
| telemetry | `telemetry_status.yml` |
| build_stream | `build_stream_status.yml` |
| utils | `utils_status.yml` |

The CLI will also search for any `*status*.yml` or `*status*.yaml` files
if the expected file is not found. Additionally, domain-specific status
commands list all output files (`.yml`, `.yaml`, `.json`, `.log`, `.txt`)
found in the output directory.
