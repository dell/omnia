# Changelog

All notable changes to the `image_build_manager` domain will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added
- Optional `external_oci_registry` (Harbor) in `image_build_config.yml`: after the build, the OCI image of every functional group is annotated with provenance, tagged (OS version, release, catalog digest) and pushed with `regctl`, with remote digest verification
- Registry precheck before any build work (credentials, Registry V2 authentication, Harbor project access)
- `oci_registry_username` / `oci_registry_password` in the Vault-encrypted `image_build_credentials.yml`, collected only when `external_oci_registry` is set
- Optional `oci` section per functional group in `build_status.yml`

## [2.3.0] - 2026-09-01

### Added
- Initial Galaxy collection structure (`omnia.image_build`)
- Image Thrillhouse as the sole image build engine
- Dual-mode functional groups: `config` (package_groups.yml) and `catalog` (JSON catalog)
- x86_64 and aarch64 image build support
- MinIO S3 and OCI Registry deployment
- Input validation framework (4-directory pattern: core/messages/schema/validators)
- `validate_system_environment` module for setup and precheck roles
- Standard tag support: precheck, validate, credentials, prepare, execute/build, cleanup
- `domain-init.sh` with idempotent input staging and dependency caching
- `docs/contracts/` with input and output contracts

### Fixed
- Galaxy collection documentation URL now points to Read the Docs latest (https://omnia.readthedocs.io/en/latest/index.html) instead of GitHub source tree
- README restructured to the common domain layout (same sections in the same order across all domains); Architecture lists every role, module, and plugin; commands and links validated.
