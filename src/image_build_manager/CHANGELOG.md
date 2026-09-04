# Changelog

All notable changes to the `image_build_manager` domain will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [2.3.0] - 2026-09-01

### Added
- Initial Galaxy collection structure (`omnia.image_build`)
- Support for `image-builder` and `image-thrillhouse` build types
- Dual-mode functional groups: `config` (package_groups.yml) and `catalog` (JSON catalog)
- x86_64 and aarch64 image build support
- MinIO S3 and OCI Registry deployment
- Input validation framework (4-directory pattern: core/messages/schema/validators)
- `validate_system_environment` module for setup and precheck roles
- Standard tag support: precheck, validate, credentials, prepare, execute/build, cleanup, upgrade, rollback
- `domain-init.sh` with idempotent input staging and dependency caching
- `docs/contracts/` with input and output contracts
