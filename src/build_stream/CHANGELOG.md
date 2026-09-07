# Changelog

All notable changes to the `build_stream` domain will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [2.3.0] - 2026-09-03

### Added
- Galaxy collection structure alignment with Omnia domain standards
- `playbooks/upgrade/` directory with upgrade playbook and ansible.cfg
- `playbooks/rollback/` directory with rollback playbook and ansible.cfg
- `vars/` directory with shared variables (`build_stream_vars.yml`)
- `docs/architecture.md` with comprehensive domain architecture documentation
- `docs/contracts/` directory with input and output contracts
- `samples/` directory with contract file templates (`build_stream_status.yml`)
- Input validation framework (4-directory pattern: core/messages/schema/validators)
- Standard tag support: precheck, validate, credentials, prepare, execute/build, cleanup, upgrade, rollback
- `domain-init.sh` with idempotent input staging and dependency caching
- `validate_system_environment` Ansible module for environment validation

### Changed
- Moved `upgrade_build_stream.yml` from root to `playbooks/upgrade/` directory
- Updated upgrade and rollback playbooks to follow image_build_manager pattern
- Moved `INPUT_CONTRACT.md` and `OUTPUT_CONTRACT.md` to `docs/contracts/` directory
- Standardized playbook placeholder messages across upgrade and rollback
- Updated galaxy version to 2.3.0 to align with Omnia domain versioning
- Replaced hardcoded `/opt/omnia` paths with `OMNIA_DATA_PATH` environment variable
- Removed cross-domain reference to `repo_manager` in playbook_registry.py
- Updated playbook_paths.conf to remove repo_manager references
- Updated upload_files.py to use image_build_manager instead of repo_manager
- Updated nfs_input_repository.py to use image_build_manager instead of repo_manager
- Updated create_local_repo.py to use image_build_manager instead of repo_manager

### Fixed
- Galaxy directory structure compliance (missing upgrade directory)
- Contract file template availability for downstream consumers
- Documentation organization to match reference domain pattern
- Shared variables structure for cross-role configuration
- Hardcoded path violations (49 instances replaced with OMNIA_DATA_PATH)
- Cross-domain coupling to repo_manager domain
