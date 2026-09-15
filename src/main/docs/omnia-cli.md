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
Completions are command-aware: `omnia-cli` uses the canonical source domain names,
and `omnia.sh --tags` suggests only tags supported by the selected domain.

After installation, run `omnia-cli` directly without `./` or path prefix:

```bash
omnia-cli status
omnia-cli repo_manager
omnia-cli version
```

## Commands

| Command | Description |
|---------|-------------|
| `status [--project <name>]` | Show all domain statuses for a project |
| `check [--project <name>]` | Validate input files and output existence for all domains |
| `edit <domain> [file] [--project <name>]` | Show the domain input checklist and edit an input file |
| `repo_manager [--project <name>]` | Detailed repo_manager diagnostics |
| `image_build_manager [--project <name>]` | Detailed image_build_manager diagnostics |
| `orchestrator [--project <name>]` | Orchestrator status |
| `discovery [--project <name>]` | Discovery domain status |
| `telemetry [--project <name>]` | Telemetry stack status |
| `build_stream [--project <name>]` | Build stream (GitLab) status |
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
./omnia-cli repo_manager

# Image build status for production
./omnia-cli image_build_manager --project prod

# Show version information
./omnia-cli version

# Get help for a specific domain
./omnia-cli help repo_manager
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

  ✔ repo_manager  completed
    RPM repository synchronization (Pulp)
    Last: 2026-07-29 10:30:15 (repo_status.yml)

  ✔ image_build_manager  completed
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

### repo_manager

Detailed diagnostics for the repo_manager domain:

- Checks output directory exists
- Validates `repo_status.yml` and `overall_status`
- Checks the Pulp certificate path when `server_crt` is configured
- Counts execution contexts and repository URLs from the current output contract
- Lists every generated artifact recursively

```bash
./omnia-cli repo_manager
```

### image_build_manager

Detailed diagnostics for the image_build_manager domain:

- Checks output directory exists
- Validates `build_status.yml` and `overall_status`
- Validates complete kernel, initrd, and rootfs entries for every functional group
- Shows the build engine and S3 endpoint/bucket
- Shows latest build log location
- Displays last modified timestamp

```bash
./omnia-cli image_build_manager
```

### logs

Browse and tail domain log files interactively. Results from every location are
combined, de-duplicated, sorted newest first, and limited globally by `--limit`.
Each entry shows its source, relative path, size, timestamp, and full path.
The command searches:

1. Runtime logs: `$OMNIA_DATA_PATH/<domain>/log/`, including project and shared subdirectories
2. Domain Ansible logs: `/var/log/omnia/<domain>/`, including phase files such as `prepare.log`
3. Legacy domain-named logs directly below `/var/log/omnia/`
4. Log files anywhere below `$OMNIA_DATA_PATH/<domain>/output/<project>/`

Set `OMNIA_ANSIBLE_LOG_PATH` only when Ansible logs use a non-standard root;
the default is `/var/log/omnia`.

```bash
./omnia-cli logs image_build_manager
./omnia-cli logs repo_manager --project prod
./omnia-cli logs orchestrator --limit 50
./omnia-cli logs discovery -l 100
```

### edit

Show a customer input checklist, then list the files available to edit. The
checklist marks each known file as `required`, `conditional`, `optional`, or
`generated`, marks only absent required files as missing, and explains what the
customer must review. Select a number interactively or provide the filename directly. YAML,
JSON, CSV, INI-style, TOML, log, and text files are supported. Credential and
Vault-encrypted files are opened with `ansible-vault edit`; plain-text files use
the configured editor. When shell completion is installed, press Tab after the
domain to complete staged input filenames, including CSV files.

```bash
./omnia-cli edit image_build_manager
./omnia-cli edit repo_manager --project prod
EDITOR=vim ./omnia-cli edit orchestrator pxe_mapping_file.csv
```

Only a file shown in the editable-file list can be opened directly. This keeps
relative-path traversal and hidden Vault key files out of the editor workflow.
After customer inputs are filled, run the complete respective domain flow. That
flow creates or updates any required Vault-encrypted credential document; no
separate credentials-only step is needed. Generated credentials must never be
committed.

## Customer Input Summary

| Domain | Always review/provide | Conditional or optional | Generated and external dependencies |
|--------|-----------------------|-------------------------|-------------------------------------|
| repo_manager | `repo_manager_config.yml`, `repo_manager_endpoint_config.yml` | Registry TLS/auth sections when used | Full `repo_manager` run generates required credentials; `CATALOG_FILE_PATH` must reference the approved catalog JSON |
| image_build_manager | `image_build_config.yml` | `package_groups.yml` for config mode; ARM values when ARM builds are enabled | Full `image_build_manager` run generates required credentials; successful `repo_status.yml` is required; catalog mode uses `CATALOG_FILE_PATH` |
| orchestrator | `orchestrator_config.yml`, `network_spec.yml`, `omnia_config.yml`, reviewed `pxe_mapping_file.csv`, `storage_config.yml`, `security_config.yml` | Provide selected Slurm and Kubernetes storage inputs; HA is required when provisioning Kubernetes; cloud-init and PXE overrides are optional | Replace sample networks with customer values; `primary_oim_admin_ip` must equal `SYSTEM_ADMIN_NIC_IPV4`; the full run generates required credentials |
| discovery | `discovery_config.yml`, `network_spec.yml` | Values depend on the selected discovery mechanism | Replace samples with customer admin/IB networks; `primary_oim_admin_ip` must equal `SYSTEM_ADMIN_NIC_IPV4`; full `discovery` run generates required credentials |
| telemetry | `telemetry_config.yml`, `telemetry_storage_config.yml`, `telemetry_packages.yml` | Storage sections depend on enabled sinks/bridges; `bmc_group_data.csv` is required for iDRAC telemetry | Full `telemetry` run generates required credentials; cluster inventory normally comes from Orchestrator |
| build_stream | `build_stream_config.yml` with enable flag, BSM address, and GitLab host | GitLab sizing and project settings have defaults | Run `omnia.sh --prepare-base` first for repo_manager, MinIO, and Registry prerequisites; the full `build_stream` run generates its credentials |
| utils | No single domain-wide mandatory file; choose a workflow | `collect_pxe.yml` for collect, `install_os_config.yml` for install, optional `backup_oim_logs_config.yml` | The full selected flow generates required install_os credentials |

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

Only the domain's canonical status file determines its status. Other status
files are listed as flow artifacts and cannot replace the canonical file.
Domain-specific commands recursively list every output artifact regardless of format, including
CSV files, archives, and symlinks such as Discovery's latest CSV mapping. Build
Stream statuses `prepared` and `running` are treated as healthy in addition to
the standard `success` state used by other domains.

An empty output directory is normal after input staging and is reported as
`not run`, without a failure marker. If non-Orchestrator artifacts exist but the
canonical status is absent, the CLI warns that a run may be incomplete or may
predate the current contract. Orchestrator is handled separately because its
inventory and internal state artifacts can be generated before its provision or
PXE phase writes `orchestrator_status.yml`.

## Generated Output Summary

| Domain | Generated output |
|--------|------------------|
| repo_manager | `repo_status.yml` |
| image_build_manager | Latest `build_status.yml` and timestamped `build_status_<version>_<timestamp>.yml` snapshot |
| discovery | Timestamped `bmc_pxe_mapping_file_<timestamp>.csv`, latest `bmc_pxe_mapping_file.csv` symlink, timestamped `bmc_discovery_report_<timestamp>.csv`, and `discovery_status.yml` |
| orchestrator | `orchestrator_state.yml`, `.data/functional_groups_config.yml`, `orchestrator_inventory.yaml`, `bmc_group_data.csv`, provision/PXE reports, and aggregate `orchestrator_status.yml` |
| telemetry | `telemetry_status.yml`, containing the latest deploy or cleanup component results |
| build_stream | `build_stream_status.yml`, written by an enabled prepare/build flow |
| utils | `utils_status.yml`, optional `install_os_status.yml`, collected-log bundles, and OIM log-backup bundles |

For a successful Discovery status, the CLI also verifies that both timestamped
CSV outputs and the valid latest-mapping symlink exist. For Orchestrator, it
checks `provisioning_report.yml` after a completed provisioning phase and
`pxeboot_status.yml` plus `failed_nodes.json` after a completed PXE phase.
