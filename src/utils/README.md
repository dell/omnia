# Utils

Utils (`omnia.utils`) provides on-demand OIM utilities: cluster log collection, OS installation through iDRAC virtual media, OIM domain log backup, and Slurm configuration backup, cleanup, and rollback. It writes a project-scoped `utils_status.yml`.

## Overview

Utils is independent of the main deployment order and is run only when an operational task requires it.

### Related modules

| Direction | Module | Interaction |
|-----------|--------|-------------|
| Reads | Orchestrator, other domains | Slurm configuration inputs, PXE mapping, and each domain's `log/` directory |

## Architecture

### Roles

Roles are invoked as `omnia.utils.<role>`.

| Role | Description |
|------|-------------|
| [`collect_install_os_credentials`](roles/collect_install_os_credentials/README.md) | Self-contained credential collection for OS installation operations |
| [`fetch_iso`](roles/fetch_iso/README.md) | Download and validate OS ISO images for bare-metal provisioning |
| [`iso_creation`](roles/iso_creation/README.md) | Create custom OS installation ISO images with Kickstart automation |
| [`iso_delivery`](roles/iso_delivery/README.md) | Deliver custom ISO images via iDRAC virtual media for OS installation |
| [`log_collector`](roles/log_collector/README.md) | Collect system logs from cluster nodes for troubleshooting |
| [`oim_log_backup`](roles/oim_log_backup/README.md) | Archive OIM domain log directories into a single backup bundle |
| [`precheck_environment`](roles/precheck_environment/README.md) | Validate environment prerequisites (env vars, hostname, IP, domain, omnia.sh setup) before running any utils playbook |
| [`slurm_cleanup`](roles/slurm_cleanup/README.md) | Clean up Slurm configuration files and cluster settings |
| [`slurm_config_backup`](roles/slurm_config_backup/README.md) | Create backups of Slurm configuration files for recovery operations |
| [`slurm_config_common`](roles/slurm_config_common/README.md) | Shared setup for Slurm config backup/cleanup/rollback utilities |
| [`slurm_config_rollback`](roles/slurm_config_rollback/README.md) | Rollback Slurm configuration files from previous backups |
| [`utils_setup`](roles/utils_setup/README.md) | Initialize and validate utils domain environment |
| [`utils_status_writer`](roles/utils_status_writer/README.md) | Write domain execution status to status file contract |
| [`validate_backup_oim_logs_config`](roles/validate_backup_oim_logs_config/README.md) | Validates backup_oim_logs_config.yml for OIM log backup playbook |
| [`validate_collect_config`](roles/validate_collect_config/README.md) | Validates collect_pxe.yml configuration for log collection |
| [`validate_install_os_config`](roles/validate_install_os_config/README.md) | Validates install_os_config.yml parameters for the OS installation utility |
| [`validate_slurm_config_util_config`](roles/validate_slurm_config_util_config/README.md) | Validates slurm_config_util_config.yml for Slurm configuration utility |

### Modules

Modules are invoked as `omnia.utils.<module>`.

| Module | Description |
|--------|-------------|
| `fetch_credential_rule` | Fetch validation rules for credential fields |
| `fetch_telemetry_status` | Fetch enabled telemetry sources from telemetry configuration |
| `validate_credentials` | Validate credential inputs against defined rules |
| `validate_system_environment` | Validate Omnia environment variables against system state |

### Plugins

| Plugin | Type | Description |
|--------|------|-------------|
| `security_filters` | Filter | Ansible filter plugins for security operations |
| `omnia_default` | Callback | Custom Ansible stdout callback plugin for Omnia |

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | RHEL 10.0, 10.2 or compatible | Runs on the OIM; see the [support matrix](https://omnia.readthedocs.io/en/latest/Reference/SupportMatrix/index.html) |
| Python | 3.12+ | Shared Omnia virtual environment |
| Ansible | ansible-core 2.20+ | Declared in `requirements.txt` |
| Disk | 50 GB free | Recommended for ISO and log operations |
| SSH | Passwordless access | Required from the OIM to nodes selected for log collection |
| iDRAC | Reachable, virtual media support | Required only for OS deployment |
| NFS | Reachable export | Required for OS artifacts; optional for OIM log backups |

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
sudo ./omnia.sh --init utils
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OMNIA_DATA_PATH` | `/opt/omnia` | Root Omnia data directory; Utils uses `$OMNIA_DATA_PATH/utils` |
| `OMNIA_PROJECT_NAME` | `project_default` | Active input/output project |
| `OMNIA_BACKUP_PATH` | unset | Optional default destination for OIM log and Slurm configuration backups |

Edit the staged input files for the utility you intend to run:

```bash
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/collect_pxe.yml"
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/install_os_config.yml"
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/backup_oim_logs_config.yml"
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/slurm_config_util_config.yml"
```

## Usage

Run this module through `omnia.sh`; it activates the virtual environment and runs `src/utils/playbooks/utils.yml`. All `./omnia.sh` commands in this document are run from `src/main` on the OIM. See [Tags](#tags) for the supported tags and combinations.

```bash
cd src/main
./omnia.sh --run utils --tags <tag> [-e <extra_var>=<value>]
```

To run the playbook directly, activate `$OMNIA_VENV_PATH/bin/activate`, source `/etc/profile.d/omnia-env.sh`, and run from the module root so its `ansible.cfg` is loaded:

```bash
cd src/utils
ansible-playbook playbooks/utils.yml --tags <tag>
```

Examples:

```bash
cd src/main
./omnia.sh --run utils --tags precheck
./omnia.sh --run utils --tags collect
./omnia.sh --run utils --tags install_os
./omnia.sh --run utils --tags backup_oim_logs
./omnia.sh --run utils --tags slurm_config_backup
```

With no tag, `utils.yml` runs the common setup and status writer only; every utility is opt-in.

### Cluster log collection

`collect.yml` reads functional-group node addresses from `collect_pxe.yml`,
builds dynamic inventory groups, collects predefined logs over SSH, and writes
a timestamped archive plus metadata. Unreachable nodes and missing sources are
recorded as warnings instead of stopping collection for the remaining nodes.

```bash
./omnia.sh --run utils --tags collect

# Direct stage execution or curated support filtering
ansible-playbook playbooks/collect.yml --tags k8s
ansible-playbook playbooks/collect.yml --tags slurm
```

### OS installation

`install_os.yml` creates or reuses an NFS-hosted custom ISO, renders a Kickstart
file, mounts the ISO through Dell iDRAC virtual media, and optionally verifies
SSH connectivity after installation. Both x86_64 and aarch64 targets are
accepted; cross-architecture image building is not performed.

```bash
./omnia.sh --run utils --tags install_os

# Direct modes
ansible-playbook playbooks/install_os.yml --tags credentials
ansible-playbook playbooks/install_os.yml --tags build_iso
ansible-playbook playbooks/install_os.yml --tags deploy
ansible-playbook playbooks/install_os.yml --tags generate_ks
```

### OIM domain log backup

`backup_oim_logs` archives the `log/` directory of each selected Omnia domain
directly into a compressed bundle. It writes `metadata.json` beside the archive
with included/skipped domains, warnings, exclusions, host context, and SHA256.
The destination may be a local absolute path or a raw NFS export.

Backup-path precedence, highest to lowest:

1. `-e backup_path=<path>`
2. `backup_path` in `backup_oim_logs_config.yml`
3. `OMNIA_BACKUP_PATH`
4. `$OMNIA_DATA_PATH/utils/output/$OMNIA_PROJECT_NAME/backup_oim_logs`

```bash
./omnia.sh --run utils --tags backup_oim_logs
./omnia.sh --run utils --tags backup_oim_logs \
  -e 'backup_path=172.96.20.223:/mnt/backup_dir'
./omnia.sh --run utils --tags cleanup_backup_oim_logs
```

### Slurm configuration utilities

`slurm_config_backup`, `slurm_config_cleanup`, and `slurm_config_rollback` manage the active
Slurm controller configuration (`etc/slurm`, `etc/munge`, `etc/my.cnf.d`)
stored on the Slurm NFS share (`storage_config.yml` → `slurm_cluster[].nfs_storage_name`).
Each tag resolves the controller from the PXE mapping (YAML `nodes_slurm.yaml`
or CSV `pxe_mapping_file.csv`, auto-detected) and is self-contained, so any
one can be run standalone without the others.

Backup-destination precedence, highest to lowest (same as `backup_oim_logs`):

1. `-e slurm_backup_path=<path>`
2. `slurm_backup_path` in `slurm_config_util_config.yml`
3. `OMNIA_BACKUP_PATH`
4. `$OMNIA_DATA_PATH/utils/output/$OMNIA_PROJECT_NAME/slurm_config_util`

```bash
# Backup: uses configurable backup_base_name (default: "slurm_config")
./omnia.sh --run utils --tags slurm_config_backup

# Cleanup: prompts for a pre-cleanup backup, then requires the confirmation token
./omnia.sh --run utils --tags slurm_config_cleanup

# Rollback: lists available backups (latest first), validates, restores,
# fixes slurmdbd.conf/munge.key permissions, and runs `scontrol reconfigure`
./omnia.sh --run utils --tags slurm_config_rollback

# NFS backup destination override
./omnia.sh --run utils --tags slurm_config_backup \
  -e 'slurm_backup_path=172.96.20.223:/mnt/backup_dir'

./omnia.sh --run utils --tags cleanup_slurm_config_backups
```

## Tags

| Tag | Description | Input required |
|-----|-------------|----------------|
| `precheck` | Validate the OIM hostname, domain, admin IP, data path, and setup state | Environment variables |
| `setup` | Run the common Utils setup only | None |
| `collect` | Collect configured Kubernetes, Slurm, and login-node logs | `collect_pxe.yml` |
| `install_os` | Run the OS installation playbook | `install_os_config.yml`; credentials are collected as needed |
| `backup_oim_logs` | Archive OIM log directories for selected Omnia domains | Optional `backup_oim_logs_config.yml` |
| `slurm_config_backup` | Back up the active Slurm controller configuration from the NFS share | `omnia_config.yml`, `storage_config.yml`, PXE mapping |
| `slurm_config_cleanup` | Delete the active Slurm configuration from the NFS share (with optional pre-backup) | Same as `slurm_config_backup` |
| `slurm_config_rollback` | Restore a Slurm configuration backup and run `scontrol reconfigure` | Same as `slurm_config_backup`; requires an existing backup |
| `cleanup` | Clean all utility artifacts and remove OS-install credentials by default | None |
| `cleanup_logs` | Apply retention cleanup to collected log bundles | None |
| `cleanup_install_os` | Remove temporary OS-installation artifacts and credentials by default | None |
| `cleanup_backup_oim_logs` | Remove all OIM log-backup run directories | Optional backup-path override |
| `cleanup_slurm_config_backups` | Remove all Slurm config-backup run directories | Optional backup-path override |
| `upgrade` / `rollback` | Reserved placeholders; no lifecycle action is implemented | None |

Run exactly one public tag at a time. With no tag, `utils.yml` runs the common
setup and status writer only; utility flows are opt-in.

### Direct utility tags

The imported playbooks expose additional stage tags when run directly:

| Playbook | Tags |
|----------|------|
| `playbooks/collect.yml` | `setup`, `prepare`, `k8s`, `slurm`, `bundle`; no tag runs the complete flow |
| `playbooks/install_os.yml` | `credentials`, `build_iso`, `deploy`, `generate_ks`; no tag runs end to end |
| `playbooks/backup_oim_logs/backup_oim_logs.yml` | `setup`, `bundle`; no tag runs both stages |
| `playbooks/slurm_config_util/slurm_config_util.yml` | `slurm_config_backup`, `slurm_config_cleanup`, `slurm_config_rollback` (each self-contained; run one at a time) |

## Inputs and Outputs

### Inputs

| File | Runtime location | Required |
|------|------------------|----------|
| `collect_pxe.yml` | `utils/input/<project>/` | Log collection |
| `install_os_config.yml` | `utils/input/<project>/` | OS installation except credentials-only mode |
| `install_os_credentials.yml` | `utils/input/<project>/` | Generated and Vault-encrypted when credentials are collected |
| `.install_os_credentials_key` | `utils/input/<project>/` | Generated with restrictive permissions |
| `backup_oim_logs_config.yml` | `utils/input/<project>/` | No; selects domains and optionally the destination |
| `slurm_config_util_config.yml` | `utils/input/<project>/` | No; overrides input paths and optionally the backup destination |
| `omnia_config.yml` | `utils/input/<project>/` | Slurm config utilities (default: from orchestrator domain) |
| `storage_config.yml` | `utils/input/<project>/` | Slurm config utilities (default: from orchestrator domain) |
| `nodes_slurm.yaml` or `pxe_mapping_file.csv` | `utils/input/<project>/` | Slurm config utilities (YAML from OpenChami, CSV from orchestrator) |

#### Input file sourcing

Some input files used by the Slurm configuration utilities are typically generated by other Omnia domains:

- `omnia_config.yml` and `storage_config.yml` - Typically generated by the orchestrator domain
- `nodes_slurm.yaml` (YAML format) - Typically generated by the OpenChami discovery process (e.g., `OMNIA_DATA_PATH/openchami/workdir/nodes/nodes_slurm.yaml`)
- `pxe_mapping_file.csv` (CSV format) - Typically generated by the orchestrator domain (e.g., `OMNIA_DATA_PATH/orchestrator/input/<project>/pxe_mapping_file.csv`)

The PXE/node mapping file auto-detects format based on file extension (.csv = CSV, otherwise YAML). These files should be copied from their respective domain locations to the utils input directory (`OMNIA_DATA_PATH/utils/input/OMNIA_PROJECT_NAME/`), or the paths can be overridden via CLI extra-vars or the `slurm_config_util_config.yml` configuration file.

### Outputs

| Output | Default location | Description |
|--------|------------------|-------------|
| Collected log run | `utils/output/<project>/collect/omnia_logs_<timestamp>/` | `omnia_logs_<timestamp>.tar.gz` and `metadata.json` |
| Install status | `utils/output/<project>/install_os_status.yml` | Target, ISO, architecture, and verification result |
| OIM log backup | `utils/output/<project>/backup_oim_logs/omnia_oim_logs_<timestamp>/` | Archive and `metadata.json` |
| Slurm config backup | `utils/output/<project>/slurm_config_util/<name>_<timestamp>/` | Config directories per controller and `metadata.json` |
| Domain status | `utils/output/<project>/utils_status.yml` | Latest Utils execution status |
| Runtime logs | `utils/log/<project>/` | Project-scoped domain logs |
| Ansible log | `/var/log/omnia/utils/utils.log` | Top-level playbook execution log |

See `docs/contracts/` for field-level contracts.

## Runtime Paths

The domain root defaults to `$OMNIA_DATA_PATH/utils`:

```text
$OMNIA_DATA_PATH/utils/
+-- input/<project>/
|   +-- collect_pxe.yml
|   +-- install_os_config.yml
|   +-- install_os_credentials.yml
|   +-- backup_oim_logs_config.yml
|   +-- slurm_config_util_config.yml
|   +-- omnia_config.yml (from orchestrator domain)
|   +-- storage_config.yml (from orchestrator domain)
|   +-- nodes_slurm.yaml (from OpenChami: OMNIA_DATA_PATH/openchami/workdir/nodes/nodes_slurm.yaml) OR
|   +-- pxe_mapping_file.csv (from orchestrator: OMNIA_DATA_PATH/orchestrator/input/<project>/pxe_mapping_file.csv)
+-- output/<project>/
|   +-- collect/
|   +-- backup_oim_logs/
|   +-- slurm_config_util/
|   +-- install_os_status.yml
|   +-- utils_status.yml
+-- log/<project>/
```

`domain-init.sh` installs dependencies with checksum caching, creates runtime
and Ansible log directories, and stages the flat `input/` templates into the
active project directory. Use `--force` to overwrite staged inputs,
`--deps-only` to skip input staging, or `--force-deps` to bypass dependency
caches.

## Cleanup

The public `cleanup` tag removes log-collection artifacts, OS-installation
temporary files, OIM log backups, and stored OS-install credentials and their
vault key by default. Use `-e cleanup_credentials=false` only when the
OS-install credentials must be retained:

```bash
cd src/main
sudo ./omnia.sh --run utils --tags cleanup
sudo ./omnia.sh --run utils --tags cleanup \
  -e cleanup_credentials=false
```

`src/utils/domain-init.sh --cleanup` is non-interactive and removes only
initializer-owned staged input and domain log paths; it does not replace the
Ansible cleanup tag. After domain cleanup, use
`sudo ./omnia.sh --cleanup --all` for the guarded global reset. Both global
cleanup modes prompt for `yes`; trusted automation can add `--skip-approval`.

## Troubleshooting

- Ansible log: `/var/log/omnia/utils/utils.log` (top-level playbook execution).
- Runtime logs: `$OMNIA_DATA_PATH/utils/log/<project>/`; the latest run status is in `utils/output/<project>/utils_status.yml`.
- Re-run `sudo ./omnia.sh --init utils` if inputs or dependencies were not staged.
- Role documentation: `roles/*/README.md`.
- See [docs/troubleshooting.md](docs/troubleshooting.md) for common failures and fixes.

## Security

- OS-install credentials are collected by the `install_os` flow and stored Vault-encrypted with a vault key created with restrictive permissions; `cleanup` removes them unless `-e cleanup_credentials=false` is passed.
- Credential values are validated with the shared security rules (`validate_credentials`, `security_filters`).

## Documentation

- [Read the Docs: Utils guides](https://omnia.readthedocs.io/en/latest/HowTo/utils/index.html)
- [Architecture](docs/architecture.md)
- [Input contract](docs/contracts/input-contract.md)
- [Output contract](docs/contracts/output-contract.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Omnia on GitHub](https://github.com/dell/omnia)
- [Report an issue](https://github.com/dell/omnia/issues)

## License

Apache License, Version 2.0
