# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-09-05

### Added
- Precheck environment role with validate_system_environment integration
- Environment variable path portability (OMNIA_DATA_PATH support)
- Security hardening with no_log for credential operations
- Comprehensive role metadata for collect_repo_credentials role

### Changed
- Galaxy version set to 2.3.0.
- Replaced hardcoded `/opt/omnia` paths with environment variable references
- Updated ansible-lint configuration to enable security rules
- Enhanced Jinja2 template syntax with proper operator precedence
- Improved credential handling to expose only file paths in debug output

### Fixed
- Jinja2 template syntax errors in process_registry_credential.yml
- ansible-lint configuration (removed unskippable load-failure rule)
- YAML lint configuration with reasonable line-length limits
- Security vulnerabilities in credential debug output

### Security
- Masked passwords in deployment configuration debug output
- Added no_log: true to credential handling tasks
- Enabled ansible-lint security rules (no-log-password, risky-file-permissions, etc.)

## [1.0.0] - 2026-08-19

### Added
- Initial release of repo_manager domain
- Pulp repository server deployment and management
- RPM repository synchronization and management
- Credential management with encryption support
- Input validation framework with four-directory pattern
- Galaxy collection structure compliance
- Domain-init.sh for runtime environment setup
- Integration with omnia.sh and omnia-cli

### Features
- Support for HTTP and HTTPS Pulp protocols
- Container-based Pulp deployment
- TLS certificate management
- Registry credential handling
- Repository status generation
- Cleanup operations for Pulp and repositories
- RHEL subscription management
- Parallel download execution

### Documentation
- Domain-level README.md
- Input/output contract documentation
- Role documentation for all roles
- Module documentation with DOCUMENTATION/EXAMPLES/RETURN blocks

## [0.1.0] - 2026-08-01

### Added
- Initial repository structure
- Basic playbook framework
- Core role templates