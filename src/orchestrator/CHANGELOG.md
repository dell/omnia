# Changelog

All notable changes to the `omnia.orchestrator` collection will be documented in this file.

## [3.0.0] - 2026-07-31

### Added
- **Phase 1 — Foundation**: Functional group classification data file (`vars/functional_group_classification.yml`), refactored `generate_functional_groups.py` for data-driven classification.
- **Phase 2 — Playbook Decomposition**: Split `orchestrator.yml` into 9 focused sub-playbooks with `import_playbook`. Added support-flag persistence via `orchestrator_state.yml` and configurable bolt-ons via `omnia_config.yml`.
- **Phase 3 — Provisioning Refactor**: New `provision_common` role (11 task files) for SMD registration, BSS, cloud-init, DNS, SELinux. New `generate_inventories` role. Demoted `configure_ochami` to template/task library.
- **Phase 4 — Bolt-On Decoupling**: Replaced all hardcoded functional group names with pattern-based matching in `slurm_config`, `k8s_config`, `mount_config`, `passwordless_ssh`, and `orchestrator_validations`.
- **Phase 5 — Lifecycle Operations**: Implemented `upgrade_orchestrator.yml` (backup → pull → restart → verify), `rollback_orchestrator.yml` (find backup → restore → verify), and `cleanup_orchestrator.yml` (stop → remove → clean → revert DNS).
- New roles: `validate_openchami`, `validate_provisioning`.
- New playbooks: `deploy_openchami.yml`, `provision_preamble.yml`, `provision_kubernetes.yml`, `provision_slurm.yml`, `provision_os.yml`, `provision_custom.yml`, `validate_openchami.yml`, `validate_provisioning.yml`.

### Changed
- Bumped Galaxy collection version from 2.2.0 to 3.0.0.
- All roles now include `meta/main.yml` and `README.md` for Galaxy compliance.

## [2.2.0] - 2026-07-22

### Added
- Initial Galaxy collection structure for orchestrator domain.
- Self-contained roles and playbooks with zero `../common/` references.
- Local copies of all shared modules, vars, and tasks.
