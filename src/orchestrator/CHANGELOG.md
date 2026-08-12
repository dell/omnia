# Changelog

All notable changes to the `omnia.orchestrator` collection will be documented in this file.

## [3.0.0] - 2026-07-31

### Added
- Galaxy collection structure for orchestrator domain.
- Self-contained roles and playbooks with zero `../common/` cross-domain references.
- Decomposed `orchestrator.yml` into 9 focused sub-playbooks with `import_playbook`.
- New roles: `orchestrator_setup`, `orchestrator_functional_groups`, `orchestrator_credentials`, `validate_orchestrator_input`, `provision_common`, `generate_inventories`, `validate_openchami`, `validate_provisioning`.
- New playbooks: `prepare_orchestrator.yml`, `validate_orchestrator.yml`, `orchestrator_credentials.yml`, `deploy_openchami.yml`, `provision_preamble.yml`, `provision_kubernetes.yml`, `provision_slurm.yml`, `provision_os.yml`, `provision_custom.yml`, `upgrade_orchestrator.yml`, `rollback_orchestrator.yml`, `cleanup_orchestrator.yml`.
- Pattern-based functional group matching in `slurm_config`, `k8s_config`, `mount_config`, `passwordless_ssh`.
- Data-driven functional group classification via `vars/functional_group_classification.yml`.
- Centralized consumption of `repo_status.yml` from `repo_manager` domain.
- Input validation with JSON schemas and L2 semantic validators.
- Domain-level documentation: `ORCHESTRATOR_DESIGN.md`, `INPUT_CONTRACT.md`, `OUTPUT_CONTRACT.md`.
