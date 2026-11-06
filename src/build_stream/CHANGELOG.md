# Changelog

All notable changes to the `omnia.build_stream` collection will be documented
in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-09-03

### Added
- Galaxy collection structure alignment with Omnia domain standards.
- FastAPI REST API with clean architecture (API/Core/Orchestrator/Infra
  layers) for build job management.
- JWT and password-based authentication securing all API endpoints.
- Catalog parsing, validation, adapter policies, generation, and JSON schema
  enforcement.
- Build-image domain entities, repositories, services, and value objects.
- Idempotent job creation with request fingerprinting and stage tracking.
- Asynchronous playbook watcher service (`playbook-watcher.service`) for
  Ansible/Molecule execution with queue management.
- Cadence polling and unified pipeline (ER-BSM-002): periodic repository
  reconciliation via `repo_sync.yml`, catalog version bumping, and GitLab
  commit-driven pipeline (#5345, #5349).
- Cadence pipeline stages: `initialization` -> `parse-catalog` ->
  `configure-local-repository` -> `build-images` -> `deploy` -> `restart` ->
  `validate` -> `summary`.
- Automatic image cleanup (`AutoCleanupScheduler`) with configurable
  `retention_age_days`, `min_keep_count`, and `evaluation_interval_hours`.
- PostgreSQL containerized deployment for persistent job and artifact metadata.
- Hosted GitLab CE integration with passwordless SSH setup.
- Secure request/path/playbook validation and command sanitization in the
  playbook watcher.
- Stage logs, result files, audit events, and rejected-result handling.
- Artifact storage and upload handling with S3-backed cleanup services.
- Image-group listing and S3 artifact discovery endpoints.
- Deployment and restart endpoints.
- Local repository management API.
- `vars/` directory with shared variables (`build_stream_vars.yml`).
- `docs/architecture.md` with comprehensive domain architecture documentation.
- `docs/contracts/` directory with input and output contracts.
- `samples/` directory with contract file templates (`build_stream_status.yml`).
- Input validation framework (4-directory pattern:
  core/messages/schema/validators).
- Standard tag support: `precheck`, `validate`, `credentials`, `prepare`,
  `execute`/`build`, `cleanup`.
- `domain-init.sh` with idempotent input staging and dependency caching.
- `validate_system_environment` Ansible module for environment validation.
- BuildStream pre- and post-PXE processing separation (#5567).

### Changed
- Galaxy version set to 2.3.0.
- Moved `INPUT_CONTRACT.md` and `OUTPUT_CONTRACT.md` to `docs/contracts/`
  directory.
- Replaced all hardcoded `/opt/omnia` paths with `OMNIA_DATA_PATH` environment
  variable (49+ instances).
- Removed cross-domain reference to `repo_manager` in `playbook_registry.py`.
- Updated `playbook_paths.conf` to remove `repo_manager` references.
- Updated `upload_files.py`, `nfs_input_repository.py`, and
  `create_local_repo.py` to use `image_build_manager` instead of
  `repo_manager`.
- OAuth cleanup for Build Stream credential handling.
- Build Stream directory layout reorganized for clean architecture.
- Deploy pipeline and infrastructure enhancements (#5487).

### Fixed
- Contract file template availability for downstream consumers.
- Documentation organization to match reference domain pattern.
- Shared variables structure for cross-role configuration.
- Hardcoded path violations replaced with `OMNIA_DATA_PATH`.
- Cross-domain coupling to `repo_manager` domain eliminated.
- Cleanup credential and pipeline behavior aligned (#5313).

### Security
- Remediated CWE-78 (shell injection), CWE-94 (code injection), and
  clone-cache poisoning (CWE-494/CWE-349) in playbook watcher.
- Validate tag/registry inputs in build scripts; credentials cleared from
  memory (#5600).
- Secure request validation and command sanitization in all API endpoints.
- JWT key generation and TLS certificate management for API service.
