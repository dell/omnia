# Changelog

All notable changes to the `omnia.discovery` collection will be documented in this file.

## [2.3.0] - 2026-09-05

### Added
- Implemented Discovery project-output cleanup with default credential cleanup
  and a `cleanup_credentials=false` preservation option.
- Added the `discovery_cleanup` role.

### Changed
- Galaxy version set to 2.3.0.
- Discovery cleanup now removes current-project runtime logs and
  `/var/log/omnia/discovery` by default, and supports `cleanup_logs=false`
  when log retention is required.

### Fixed
- Galaxy collection documentation URL now points to Read the Docs latest (https://omnia.readthedocs.io/en/latest/) instead of GitHub source tree
- Removed unreleased 3.0.0 changelog entry to avoid version history confusion (DOC-RC1-018)
