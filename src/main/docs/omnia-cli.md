# omnia-cli — Diagnostics CLI Documentation

The `omnia-cli` script provides status checking and diagnostics for all Omnia domains.

## Install to PATH

`omnia-cli` is installed automatically during `./omnia.sh -s` to `/usr/local/bin/omnia-cli`. The shared Bash completion installed at `/etc/bash_completion.d/omnia-bash-completion` supports `omnia-cli`, `omnia.sh`, and `./omnia.sh`.

To skip the install:
```bash
./omnia.sh -s --skip-omnia-cli
```

Manual install (if needed):
```bash
sudo cp omnia-cli /usr/local/bin/
sudo chmod +x /usr/local/bin/omnia-cli
sudo mkdir -p /etc/bash_completion.d
sudo cp omnia-bash-completion /etc/bash_completion.d/omnia-bash-completion
source /etc/bash_completion.d/omnia-bash-completion  # or re-login
```

The same completion definitions can therefore be used for diagnostics such as
`omnia-cli st<Tab>` and lifecycle commands such as
`./omnia.sh --run image_<Tab> --tags pre<Tab>`.
Completions are command-aware: `omnia-cli` uses the documented hyphenated names,
and `omnia.sh --tags` suggests only tags supported by the selected domain.

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
| `check [--project <name>]` | Validate input files and output existence for all domains |
| `edit <domain> [--project <name>]` | Select and edit a domain input file |
| `repo-manager [--project <name>]` | Detailed repo_manager diagnostics |
| `image-build [--project <name>]` | Detailed image_build_manager diagnostics |
| `orchestrator [--project <name>]` | Orchestrator status |
| `discovery [--project <name>]` | Discovery domain status |
| `telemetry [--project <name>]` | Telemetry stack status |
| `build-stream [--project <name>]` | Build stream (GitLab) status |
| `utils [--project <name>]` | Shared utilities status |
| `logs <domain> [--project <name>] [--limit <n>]` | Browse and tail domain log files |
| `version` | Show Omnia version info |
| `help [<domain>]` | Show help (or domain-specific help) |

## Options

- `--project <name>` or `-p <name>` — Project name (default: `$OMNIA_PROJECT_NAME` or `project_default`)
- `--limit <n>` or `-l <n>` — Maximum number of logs to display (default: 30, applies to `logs` command only)

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
  2/7 domains completed for project project_default
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
./omnia-cli logs image-build
./omnia-cli logs repo-manager --project prod
./omnia-cli logs orchestrator --limit 50
./omnia-cli logs discovery -l 100
```

### edit

List a domain's input files and select one to open in `$EDITOR` (defaults to
`vi`). Credential and Vault-encrypted files are opened with `ansible-vault edit`;
plain-text files use the configured editor.

```bash
./omnia-cli edit image-build
./omnia-cli edit repo-manager --project prod
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
