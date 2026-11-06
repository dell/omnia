# Changelog

All notable changes to the `omnia.image_build` collection will be documented
in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-09-01

### Added
- Initial Galaxy collection structure (`omnia.image_build`).
- Image Thrillhouse as the sole image build engine (OpenCHAMI
  `image-thrillhouse:v0.0.26`).
- Dual-mode functional groups: `config` (`package_groups.yml`) and `catalog`
  (JSON catalog with `functionallayer` resolution).
- x86_64 and aarch64 image build support with dedicated build hosts per
  architecture.
- MinIO S3 and OCI Registry deployment with health checks and Quadlet
  management.
- PowerScale S3 as an alternate storage backend.
- Global image-group dictionary (`image_group_dictionary.json`) for
  catalog-mode image reuse across BuildStream and direct builds.
- Per-group package-hash cache for config-mode image reuse.
- Image cleanup (`cleanup_images` tag) with pattern-based S3 and registry
  deletion and hash-cache pruning.
- Multi-version RHEL support with per-version base packages and `repo_status`
  contract consumption.
- Version-qualified `repo_status.yml` contract integration with Repo Manager
  (#5448).
- RHEL 10.2 catalog and artifact support alongside RHEL 10.0 (#5179, #5353).
- `validate_system_environment` module for setup and precheck roles.
- Input validation framework (4-directory pattern:
  core/messages/schema/validators).
- Standard tag support: `precheck`, `validate`, `credentials`, `prepare`,
  `execute`/`build`, `cleanup`, `cleanup_images`.
- `domain-init.sh` with idempotent input staging and dependency caching
  (`--force`, `--deps-only`, `--force-deps` modes).
- aarch64 node preparation: host architecture verification, repository
  certificate transfer, CA trust update, builder image lookup with
  Pulp/upstream fallback, and `regctl` installation.
- `build_status.yml` output with per-group kernel, initrd, and rootfs S3
  artifact paths; catalog mode adds `<catalog-id>-v<version>/` scoping.
- Input/output contract documentation (`docs/contracts/`).
- Architecture, package-mapping, and troubleshooting documentation.

### Changed
- Galaxy version set to 2.3.0.
- Replaced all hardcoded `/opt/omnia` paths with `OMNIA_DATA_PATH` and
  `IMAGE_BUILD_MANAGER_DATA_PATH` environment variables.
- Role structure and dependency checks aligned with Omnia domain conventions
  (#5426).
- Cleanup credential handling aligned with cross-domain cleanup conventions;
  credential deletion enabled by default with explicit cleanup tag (#5313).
- Versioned artifact naming and registry alignment (#5411).
- Unsupported upgrade and rollback flows removed (#5446).
- Callback plugin redacts sensitive keys from result dictionaries (#5604).

### Fixed
- Cleanup and runtime input handling improvements (#5499).
- Image lifecycle and validation corrections (#5145).
- Cleanup and retry of repository key (#5133).
- Builder profiles and artifact checks aligned (#5121).
- `save_compute_image_hashes.yml` file restored after accidental removal.
- Repo status validation for internet mode.
- Catalog `base_os` group type renamed to `baseos` for consistency (#5585).

### Security
- Remediated shell injection and credential exposure vulnerabilities (#5482).
- Tag and registry inputs validated in build scripts; credentials cleared from
  memory (#5600).
- Hardened aarch64 SSH key installation (#5448).
- Hardened environment and repository integration (#5182).
