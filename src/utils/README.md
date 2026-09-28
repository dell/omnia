# Utils

**Collection**: `omnia.utils` v2.3.0

Provides OIM utilities for collecting cluster logs, installing an operating
system through iDRAC virtual media, and backing up logs from all Omnia domains.
The top-level playbook also provides targeted cleanup operations and writes a
project-scoped `utils_status.yml` status file.

---

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | RHEL 10.x or compatible | Utilities run from the OIM |
| Python | 3.12+ | Shared Omnia virtual environment |
| Ansible | ansible-core 2.20+ | Declared in `requirements.txt` |
| Disk | 50 GB free | Recommended for ISO and log operations |
| SSH | Passwordless access | Required from OIM to nodes selected for log collection |
| iDRAC | Reachable with virtual media support | Required only for OS deployment |
| NFS | Reachable export | Required for OS artifacts and optional for OIM log backups |

---

## Quick Start

```bash
# From the repository root
cd src/main

# Configure the OIM, create the shared virtual environment, install domain
# dependencies, and stage Utils inputs.
vi omnia.env
sudo ./omnia.sh -s
source /etc/profile.d/omnia-env.sh

# Edit the staged input files.
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/collect_pxe.yml"
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/install_os_config.yml"
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/backup_oim_logs_config.yml"
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/slurm_config_util_config.yml"

# Run one public utility tag at a time.
cd ../utils
ansible-playbook playbooks/utils.yml --tags precheck
ansible-playbook playbooks/utils.yml --tags collect
ansible-playbook playbooks/utils.yml --tags install_os
ansible-playbook playbooks/utils.yml --tags backup_oim_logs
ansible-playbook playbooks/utils.yml --tags slurm_config_backup
ansible-playbook playbooks/utils.yml --tags slurm_config_cleanup
ansible-playbook playbooks/utils.yml --tags slurm_config_rollback
```

For direct playbook execution, source `/etc/profile.d/omnia-env.sh`, activate
`$OMNIA_VENV_PATH/bin/activate`, and run commands from `src/utils` so the domain
`ansible.cfg` is loaded.

---

## Public Tags

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

### Direct Utility Tags

The imported playbooks expose additional stage tags when run directly:

| Playbook | Tags |
|----------|------|
| `playbooks/collect.yml` | `setup`, `prepare`, `k8s`, `slurm`, `bundle`; no tag runs the complete flow |
| `playbooks/install_os.yml` | `credentials`, `build_iso`, `deploy`, `generate_ks`; no tag runs end to end |
| `playbooks/backup_oim_logs/backup_oim_logs.yml` | `setup`, `bundle`; no tag runs both stages |
| `playbooks/slurm_config_util/slurm_config_util.yml` | `slurm_config_backup`, `slurm_config_cleanup`, `slurm_config_rollback` (each self-contained; run one at a time) |

### Cleanup and Reset

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

---

## Utilities

### Cluster Log Collection

`collect.yml` reads functional-group node addresses from `collect_pxe.yml`,
builds dynamic inventory groups, collects predefined logs over SSH, and writes
a timestamped archive plus metadata. Unreachable nodes and missing sources are
recorded as warnings instead of stopping collection for the remaining nodes.

```bash
ansible-playbook playbooks/utils.yml --tags collect

# Direct stage execution or curated support filtering
ansible-playbook playbooks/collect.yml --tags k8s
ansible-playbook playbooks/collect.yml --tags slurm
```

### OS Installation

`install_os.yml` creates or reuses an NFS-hosted custom ISO, renders a Kickstart
file, mounts the ISO through Dell iDRAC virtual media, and optionally verifies
SSH connectivity after installation. Both x86_64 and aarch64 targets are
accepted; cross-architecture image building is not performed.

```bash
ansible-playbook playbooks/utils.yml --tags install_os

# Direct modes
ansible-playbook playbooks/install_os.yml --tags credentials
ansible-playbook playbooks/install_os.yml --tags build_iso
ansible-playbook playbooks/install_os.yml --tags deploy
ansible-playbook playbooks/install_os.yml --tags generate_ks
```

### OIM Domain Log Backup

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
ansible-playbook playbooks/utils.yml --tags backup_oim_logs
ansible-playbook playbooks/utils.yml --tags backup_oim_logs \
  -e 'backup_path=172.96.20.223:/mnt/backup_dir'
ansible-playbook playbooks/utils.yml --tags cleanup_backup_oim_logs
```

### Slurm Configuration Utilities

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
ansible-playbook playbooks/utils.yml --tags slurm_config_backup

# Cleanup: prompts for a pre-cleanup backup, then requires the confirmation token
ansible-playbook playbooks/utils.yml --tags slurm_config_cleanup

# Rollback: lists available backups (latest first), validates, restores,
# fixes slurmdbd.conf/munge.key permissions, and runs `scontrol reconfigure`
ansible-playbook playbooks/utils.yml --tags slurm_config_rollback

# NFS backup destination override
ansible-playbook playbooks/utils.yml --tags slurm_config_backup \
  -e 'slurm_backup_path=172.96.20.223:/mnt/backup_dir'

ansible-playbook playbooks/utils.yml --tags cleanup_slurm_config_backups
```

---

## Input / Output

### Input

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

#### Input File Sourcing

Some input files used by the Slurm configuration utilities are typically generated by other Omnia domains:

- `omnia_config.yml` and `storage_config.yml` - Typically generated by the orchestrator domain
- `nodes_slurm.yaml` (YAML format) - Typically generated by the OpenChami discovery process (e.g., `OMNIA_DATA_PATH/openchami/workdir/nodes/nodes_slurm.yaml`)
- `pxe_mapping_file.csv` (CSV format) - Typically generated by the orchestrator domain (e.g., `OMNIA_DATA_PATH/orchestrator/input/<project>/pxe_mapping_file.csv`)

The PXE/node mapping file auto-detects format based on file extension (.csv = CSV, otherwise YAML). These files should be copied from their respective domain locations to the utils input directory (`OMNIA_DATA_PATH/utils/input/OMNIA_PROJECT_NAME/`), or the paths can be overridden via CLI extra-vars or the `slurm_config_util_config.yml` configuration file.

### Output

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

---

## Roles

### Active Playbook Roles

| Role | Purpose |
|------|---------|
| `utils_setup` | Optional prerequisite/config/disk checks and shared guard facts |
| `precheck_environment` | Validate the OIM environment against exported settings |
| `log_collector` | Prepare inventory, collect node logs, and create support bundles |
| `validate_install_os_config` | Load and mode-conditionally validate OS-install input |
| `collect_install_os_credentials` | Collect and Vault-encrypt BMC and OS credentials |
| `fetch_iso` | Validate the source ISO and install required tooling |
| `iso_creation` | Render Kickstart and build embedded or NFS-delivered custom ISOs |
| `iso_delivery` | Attach virtual media through iDRAC and verify installation |
| `oim_log_backup` | Archive Omnia domain log directories with metadata |
| `slurm_config_common` | Shared setup for the three Slurm config utility roles (resolves controller, paths, backup destination) |
| `slurm_config_backup` | Back up the active Slurm controller configuration with checksummed metadata |
| `slurm_cleanup` | Delete the active Slurm configuration (with optional pre-cleanup backup) |
| `slurm_config_rollback` | Restore a Slurm configuration backup and reconfigure `slurmctld` |
| `utils_status_writer` | Write and validate `utils_status.yml` |

---

## Modules and Plugins

| Component | Purpose |
|-----------|---------|
| `validate_system_environment` | Validate hostname, domain, admin IP, and data path |
| `fetch_credential_rule` | Read credential validation rules |
| `validate_credentials` | Validate credential values using shared security rules |
| `fetch_telemetry_status` | Read enabled telemetry-source status |
| `security_filters` | Credential and input security filters |
| `omnia_default` | Domain stdout callback |

---

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

---

## Documentation

| Document | Description |
|----------|-------------|
| `docs/architecture.md` | Execution flow, tags, role dependencies, and cleanup behavior |
| `docs/contracts/input-contract.md` | Input files and environment-variable contracts |
| `docs/contracts/output-contract.md` | Archives, metadata, status files, and runtime paths |
| `roles/*/README.md` | Individual role documentation |

---

## License

Apache License, Version 2.0
