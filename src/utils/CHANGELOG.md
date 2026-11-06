# Changelog

All notable changes to the `omnia.utils` collection will be documented in this
file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-09-05

### Added
- Top-level `utils.yml` entry point with `precheck`, `setup`, `collect`,
  `install_os`, `backup_oim_logs`, `slurm_config_backup`,
  `slurm_config_cleanup`, `slurm_config_rollback`, `cleanup`,
  `cleanup_logs`, `cleanup_install_os`, `cleanup_backup_oim_logs`,
  `cleanup_slurm_config_backups`, `upgrade`, and `rollback` tags.
- Project-scoped status output through the `utils_status_writer` role.
- Standalone OS installation through iDRAC virtual media with x86_64 and
  aarch64 target support, custom ISO generation, Kickstart rendering, and
  NFS-backed delivery.
- OIM domain log backup (`backup_oim_logs`) with local/NFS destinations,
  per-domain selection, metadata JSON with SHA256 checksums, and dedicated
  `cleanup_backup_oim_logs` tag.
- Slurm configuration backup (`slurm_config_backup`) with checksummed metadata,
  configurable backup base name, and local/NFS destinations.
- Slurm configuration cleanup (`slurm_config_cleanup`) with optional
  pre-cleanup backup and confirmation token requirement.
- Slurm configuration rollback (`slurm_config_rollback`) with interactive
  backup selection (latest first), safety backup before restore, NFS remount
  handling, `slurmdbd.conf` and `munge.key` permission repair, Slurm service
  restart, and `scontrol reconfigure`.
- `validate_backup_oim_logs_config`, `validate_collect_config`,
  `validate_install_os_config`, and `validate_slurm_config_util_config`
  validation roles.
- `slurm_config_common` shared role for Slurm controller resolution, path
  derivation, and backup destination handling.
- PXE mapping auto-detection: YAML (`nodes_slurm.yaml`) and CSV
  (`pxe_mapping_file.csv`) format support.
- Backup-path precedence: extra-var -> config file -> `OMNIA_BACKUP_PATH` ->
  default output path.
- `precheck_environment` role with `validate_system_environment` module for
  hostname, domain, admin IP, data path, and setup state validation.
- `fetch_telemetry_status` module for reading enabled telemetry-source status.
- `fetch_credential_rule` module for credential validation rule lookup.
- Functional test scenarios for all Utils flows.
- `domain-init.sh` with idempotent input staging, dependency caching
  (`--force`, `--deps-only`, `--force-deps` modes), and `--cleanup` mode.
- Input/output contract documentation (`docs/contracts/`).
- Architecture documentation (`docs/architecture.md`).

### Changed
- Galaxy version set to 2.3.0.
- Log collection now uses `collect_pxe.yml` functional-group inventory and
  emits timestamped archives with metadata; unreachable nodes produce warnings
  instead of stopping collection.
- Input and output paths follow
  `$OMNIA_DATA_PATH/utils/{input,output}/<project>/`.
- PXE boot management moved to the orchestrator domain; obsolete Utils PXE
  roles and playbooks removed.
- Domain initialization now stages flat input templates and caches dependency
  installation by checksum.
- Cleanup behavior aligned with cross-domain conventions: credential deletion
  enabled by default with explicit cleanup tag; `cleanup_credentials=false`
  preserves OS-install credentials.
- LDMS RPM build scripts moved from utils to the telemetry domain.
- Replaced all hardcoded `/opt/omnia` paths with environment variable
  references.

### Fixed
- Catalog `base_os` group type renamed to `baseos` for consistency (#5585).

### Security
- Callback plugin redacts sensitive keys from result dictionaries (#5604).
- Vaulted input reading operates in memory and reports validator errors
  completely (#5602).

## [2.2.0] - 2026-08-04

### Added
- Galaxy collection infrastructure (`galaxy.yml`, `meta/runtime.yml`).
- Python module documentation blocks (DOCUMENTATION, EXAMPLES, RETURN).
- Role metadata files (`README.md`, `meta/main.yml`) for all 12 roles.
- Type hints and improved exception handling in Python modules.
- Domain integration scripts (`domain-init.sh`).
- Requirements files (`requirements.txt`, `requirements.yml`).

### Changed
- Updated `ansible.cfg` log_path to use `/var/log/omnia/utils/` standard.
- Improved Python code quality with specific exception handling.

### Fixed
- YAML syntax errors in module documentation blocks.
- Removed unused imports from Python modules.

## [2.1.0] - 2026-01-15

### Added
- Initial release of `omnia.utils` collection.
- Core utility roles for OS installation and Slurm management.
- Custom Ansible modules for credential validation and telemetry status.
- Log collection and PXE boot management capabilities.
