# Changelog

All notable changes to the `omnia.repo_manager` collection will be documented
in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-09-05

### Added
- Catalog-driven execution engine with multi-architecture support (x86_64 and
  aarch64) and modular repository management.
- RHEL 10.2 support with minor-version-fixed subscription repositories and
  secure entitlement reconciliation alongside RHEL 10.0.
- Multi-version RHEL artifact reconciliation: sequential processing of multiple
  OS minor versions with atomic checkpoint and rollback per context.
- Exact RPM repository reconciliation (`repo_sync.yml`) with
  `mirror_content_only`, HTTPS `repomd.xml` validation, atomic distribution
  switching, and `repo_resync_status.yml` output.
- Selective cleanup for RPM repositories, container images (by tag or
  repository), File artifacts, and Python packages.
- Full Pulp cleanup with `cleanup_credentials=false` and `cleanup_logs=false`
  preservation options.
- Catalog operations: `catalog_generate`, `catalog_add`, `catalog_delete`,
  `catalog_validate`, `catalog_transform`, and `catalog_optimize` tags.
- Extended catalog schema supporting additional package types and metadata
  fields.
- `precheck_environment` role with `validate_system_environment` module
  integration for environment and data-path validation.
- Environment variable path portability (`OMNIA_DATA_PATH`,
  `REPO_MANAGER_DATA_PATH`, `OMNIA_PROJECT_NAME`).
- Private registry authentication with TLS, basic auth, and vault-backed
  credential storage.
- User-defined repositories (`user_repos`) with configurable priority and
  certificate support.
- Container platform validation with improved error logging and OCI attestation
  support.
- `domain-init.sh` with idempotent input staging and `--cleanup` mode for
  initializer-owned paths.
- Comprehensive role metadata for `collect_repo_credentials` role.
- Input/output contract documentation (`docs/contracts/`).
- Architecture, content configuration, catalog operations, troubleshooting,
  security, Pulp administration, and design documentation.

### Changed
- Galaxy version set to 2.3.0.
- Replaced all hardcoded `/opt/omnia` paths with environment variable
  references (49+ instances).
- Pulp deployment uses HTTPS only; HTTP protocol support removed.
- Credential handling exposes only file paths in debug output; passwords masked
  in deployment configuration.
- Enhanced Jinja2 template syntax with proper operator precedence.
- Updated ansible-lint configuration to enable security rules
  (`no-log-password`, `risky-file-permissions`).
- Subscription repository handling hardened with entitlement certificate
  validation and explicit user-field precedence.
- Repository metadata validation strengthened for baseos, appstream, and CRB
  repositories.
- Removed cross-domain coupling: all consumer contracts use file-based
  `repo_status.yml` output.
- Cleanup behavior aligned with cross-domain cleanup conventions (credential
  deletion enabled by default with explicit cleanup tag).

### Fixed
- CWE-214: Removed password from Pulp container remote command argv (#5582).
- Vaulted input reading now operates in memory and reports validator errors
  completely (#5602).
- Jinja2 template syntax errors in `process_registry_credential.yml`.
- ansible-lint configuration (removed unskippable `load-failure` rule).
- Repository metadata validation for baseos, appstream, and CRB repos.
- Catalog `base_os` group type renamed to `baseos` for consistency (#5585).
- `domain-init.sh` input file overwrite issue (#5494).
- Enabled `git`, `manifest`, `pip_module` in parser for `catalog_add`
  operation (#5264).

### Security
- Remediated shell injection and credential exposure vulnerabilities (#5482).
- Added `no_log: true` to all credential handling tasks.
- Credential validation framework with configurable security rules.
- Hardened Pulp HTTPS configuration and repository metadata validation.
- Pre-populated `user_repos` with security updates enabled by default.

## [1.0.0] - 2026-08-19

### Added
- Initial release of repo_manager domain.
- Pulp repository server deployment and management.
- RPM repository synchronization and management.
- Credential management with encryption support.
- Input validation framework with four-directory pattern.
- Galaxy collection structure compliance.
- `domain-init.sh` for runtime environment setup.
- Integration with `omnia.sh` and `omnia-cli`.

### Features
- Support for HTTP and HTTPS Pulp protocols.
- Container-based Pulp deployment.
- TLS certificate management.
- Registry credential handling.
- Repository status generation.
- Cleanup operations for Pulp and repositories.
- RHEL subscription management.
- Parallel download execution.

### Documentation
- Domain-level `README.md`.
- Input/output contract documentation.
- Role documentation for all roles.
- Module documentation with DOCUMENTATION/EXAMPLES/RETURN blocks.

## [0.1.0] - 2026-08-01

### Added
- Initial repository structure.
- Basic playbook framework.
- Core role templates.
