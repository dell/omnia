# Changelog

All notable changes to the `build_stream` domain will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Changed
- Playbook timeout now kills the whole process group and bounds the log reader join, so orphaned ansible/ssh children cannot stall the watcher queue.
- Stage logs are written at write time with Tier 1 redaction and published with mode 0644 (and the parent directory SELinux label) so the BSM container can read them. They are redacted of secrets but still contain operational data such as IPs and hostnames.
- Playbook output is captured through a pipe (stdout+stderr merged), not `ANSIBLE_LOG_PATH`. Redacted lines are echoed to the unit stdout so `journalctl -u playbook-watcher` continues to show playbook output.
- Stage log lines no longer carry Ansible's timestamp/pid prefix. Log consumers in the watcher (`extract_dictionary_hits`, validate report parsing) use line-anchored or key=value regexes and do not depend on the prefix.

## [2.3.0] - 2026-09-03

### Added
- Galaxy collection structure alignment with Omnia domain standards
- `vars/` directory with shared variables (`build_stream_vars.yml`)
- `docs/architecture.md` with comprehensive domain architecture documentation
- `docs/contracts/` directory with input and output contracts
- `samples/` directory with contract file templates (`build_stream_status.yml`)
- Input validation framework (4-directory pattern: core/messages/schema/validators)
- Standard tag support: precheck, validate, credentials, prepare, execute/build, cleanup
- `domain-init.sh` with idempotent input staging and dependency caching
- `validate_system_environment` Ansible module for environment validation

### Changed
- Moved `INPUT_CONTRACT.md` and `OUTPUT_CONTRACT.md` to `docs/contracts/` directory
- Updated galaxy version to 2.3.0 to align with Omnia domain versioning
- Replaced hardcoded `/opt/omnia` paths with `OMNIA_DATA_PATH` environment variable
- Removed cross-domain reference to `repo_manager` in playbook_registry.py
- Updated playbook_paths.conf to remove repo_manager references
- Updated upload_files.py to use image_build_manager instead of repo_manager
- Updated nfs_input_repository.py to use image_build_manager instead of repo_manager
- Updated create_local_repo.py to use image_build_manager instead of repo_manager

### Fixed
- Contract file template availability for downstream consumers
- Documentation organization to match reference domain pattern
- Shared variables structure for cross-role configuration
- Hardcoded path violations (49 instances replaced with OMNIA_DATA_PATH)
- Cross-domain coupling to repo_manager domain
- Galaxy collection documentation URL now points to Read the Docs latest (https://omnia.readthedocs.io/en/latest/index.html) instead of GitHub source tree
- Renamed `docs/contracts/INPUT_CONTRACT.md` and `OUTPUT_CONTRACT.md` to lowercase `input-contract.md` and `output-contract.md`; updated references.
- Moved `BUILD_STREAM_DESIGN.md` to `docs/design/build-stream-design.md`.
- Fixed the broken `developer-guide.md` links in `README.md` and `docs/README.md`; they now point to `docs/architecture.md`.
- README restructured to the common domain layout; Architecture lists every role, module, and plugin; documented how the `credentials` tag works.
- Corrected README quick start, entry playbook path (`playbooks/build_stream.yml`), and initializer references (`domain-init.sh`).
