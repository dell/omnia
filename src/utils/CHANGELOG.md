# Changelog

All notable changes to the omnia.utils collection will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-09-05

### Added
- Top-level `utils.yml` entry point with precheck, setup, collect, install OS, cleanup, upgrade, and rollback tags.
- Project-scoped status output through the `utils_status_writer` role.
- Standalone OS installation through iDRAC virtual media with x86_64 and aarch64 target support.
- OIM domain log backup with local/NFS destinations, metadata, SHA256 checksums, and dedicated cleanup.
- Functional test scenarios for the current Utils flows.

### Changed
- Galaxy version set to 2.3.0.
- Log collection now uses `collect_pxe.yml` functional-group inventory and emits timestamped archives with metadata.
- Input and output paths follow `$OMNIA_DATA_PATH/utils/{input,output}/<project>/`.
- PXE boot management moved to the orchestrator domain; obsolete Utils PXE roles and playbooks were removed.
- Domain initialization now stages flat input templates and caches dependency installation by checksum.

## [2.2.0] - 2026-08-04

### Added
- Galaxy collection infrastructure (galaxy.yml, meta/runtime.yml)
- Python module documentation blocks (DOCUMENTATION, EXAMPLES, RETURN)
- Role metadata files (README.md, meta/main.yml) for all 12 roles
- Type hints and improved exception handling in Python modules
- Domain integration scripts (domain-init.sh)
- Requirements files (requirements.txt, requirements.yml)

### Changed
- Updated ansible.cfg log_path to use /var/log/omnia/utils/ standard
- Improved Python code quality with specific exception handling

### Fixed
- YAML syntax errors in module documentation blocks
- Removed unused imports from Python modules

## [2.1.0] - 2026-01-15

### Added
- Initial release of omnia.utils collection
- Core utility roles for OS installation and Slurm management
- Custom Ansible modules for credential validation and telemetry status
- Log collection and PXE boot management capabilities
