# Changelog

All notable changes to the `omnia.discovery` collection will be documented in
this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-09-05

### Added
- Discovery project-output cleanup with default credential cleanup and a
  `cleanup_credentials=false` preservation option.
- `discovery_cleanup` role with project-scoped output, runtime-log, Ansible
  execution-log, and credential cleanup.
- `cleanup_credentials` standalone tag to remove only the encrypted credential
  file and vault key.
- `cleanup_logs=false` option to preserve runtime and Ansible execution logs
  during cleanup.
- OS version suffix enforcement in PXE functional group names
  (`<prefix>_rhel_<major>_<minor>_<arch>`) (#5484).
- `precheck_environment` role with `validate_system_environment` module for
  data-path and OME HTTPS endpoint readiness checks.
- `precheck` tag for standalone prerequisite validation without OME API calls.
- Environment variable path portability (`OMNIA_DATA_PATH`,
  `DISCOVERY_DATA_PATH`, `OMNIA_PROJECT_NAME`).
- Project-scoped `input/<project>/`, `output/<project>/`, and `log/<project>/`
  directory structure.
- `domain-init.sh` with idempotent input staging and `--cleanup` mode.
- Functional group assignment from OME static groups with validated naming
  pattern and configurable default.
- `omnia_default` callback plugin with clean error formatting.

### Changed
- Galaxy version set to 2.3.0.
- Discovery cleanup now removes current-project runtime logs and
  `/var/log/omnia/discovery` by default, and supports `cleanup_logs=false`
  when log retention is required.
- Cleanup behavior aligned with cross-domain conventions: credential deletion
  enabled by default, explicit `cleanup_credentials` tag also available.
- Replaced all hardcoded `/opt/omnia` paths with environment variable
  references.

### Fixed
- Catalog `base_os` group type renamed to `baseos` for consistency (#5585).

### Security
- Callback plugin redacts sensitive keys from result dictionaries (#5604).
- Vaulted input reading operates in memory and reports validator errors
  completely (#5602).
