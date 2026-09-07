# Changelog

All notable changes to the `omnia.discovery` collection will be documented in this file.

## [2.3.0] - 2026-09-05

### Changed
- Galaxy version set to 2.3.0.

## [3.0.0] - 2026-07-30

### Added
- Galaxy collection structure for discovery domain.
- Self-contained roles: `ome_discovery`, `discovery_setup`, `discovery_common`, `discovery_credentials`, `validate_discovery_input`.
- Plugins: `generate_discovery_report`, `generate_pxe_mapping`, `ome_server_inventory`, `validate_credentials`, `validate_discovery_config`.
- Input validation with JSON schemas for `discovery_config.yml` and `credential_rules.json`.
- L2 semantic validation flow for OME IP reachability checks.
- Domain-level documentation: `DISCOVERY_DESIGN.md`, `INPUT_CONTRACT.md`, `OUTPUT_CONTRACT.md`.
- All module references use FQCN (`ansible.builtin.*`).
- Zero `../common/` cross-domain imports.
