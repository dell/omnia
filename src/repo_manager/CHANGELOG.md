# Changelog

All notable changes to the `omnia.repo_manager` collection will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-07-31

### Added
- Galaxy collection structure with `plugins/` directory layout
- Tag-based entry point (`repo_manager.yml`) for selective execution
- Playbook subdirectory organization (prepare/, deploy/, validate/, repo_operations/, cleanup/)
- Role metadata (README.md, meta/main.yml) for all 9 roles
- Module documentation (DOCUMENTATION, EXAMPLES, RETURN) for all 15 modules
- Input validation framework with schema-based validation
- Domain integration scripts (copy-input.sh, domain-init.sh)
- Contract documentation for inter-domain communication
- FQCN usage throughout all playbooks and roles

### Changed
- Migrated from `library/` to `plugins/` directory structure
- Updated `ansible.cfg` to use `/var/log/omnia/repo_manager/` for logs
- Improved credential handling with vault encryption support
- Enhanced path resolution for portability across environments
- Refactored output directory structure to use `omnia_base_dir`

### Fixed
- hostvars access patterns with safe `.get()` defaults
- Path resolution issues in subdirectory playbooks
- SELinux policy handling for NFS shares
- Pulp CLI configuration for HTTP/HTTPS endpoints

### Security
- Vault key preservation warnings for credential files
- Encrypted file detection before vault operations

## [1.0.0] - 2026-01-15

### Added
- Initial release of repo_manager domain
- Pulp container deployment and configuration
- RPM repository synchronization
- Container image mirroring
- File repository management (tarballs, manifests, pip modules)
- RHEL subscription validation
- Multi-architecture support (x86_64, aarch64)
