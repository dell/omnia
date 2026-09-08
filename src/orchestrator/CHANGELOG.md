# Changelog

All notable changes to the `omnia.orchestrator` collection will be documented in this file.

## [2.3.0] - 2026-09-05

### Fixed
- Removed the invalid generic cloud-init phone-home fragment; Metadata Service
  reserves that route for optional WireGuard bootstrap peer removal.
- Changed Boot Service's NoCloud datasource name from deprecated `nocloud-net`
  to `nocloud`.
- Disabled root filesystem resize for the live overlay image and made Slurm
  tracking mounts and controller-marker waits explicit and bounded.
- Inventory generation fails with `Recursive loop detected in template` — renamed template var from `kube_vip` to `inventory_kube_vip` to avoid self-reference when fact is not set.
- validate_preamble OIM tasks fail with undefined `pxe_mapping_file_path` — resolve from localhost hostvars and add defensive `when` guards.
- validate_preamble playbook uses `roles:` which doesn't resolve OIM hostvars — changed to `tasks:` with `include_role:` for proper variable resolution.
- Metadata-service configuration fails with `File not found: nodes_slurm.yaml` during K8s provisioning — `nodes_yaml` from `slurm_config/vars/main.yml` defaulted to slurm category; force-set for current category (#473).
- `generate_xname_in_mapping_file` module fails with `No module named 'pandas'` on OIM — replaced pandas with Python stdlib `csv` module (#473).
- Orchestrator fails with `symmetric_difference` NoneType error on `--tags provision` — `provision_preamble.yml` was missing the first-control-plane rename step that `validate_mapping_file.yml` performs during precheck (#472).
- K8s nodes receive random DHCP IPs instead of ADMIN_IPs from PXE mapping file when both K8s and Slurm catalogs are provisioned — `delete_smd_endpoints.yml` used `--all` which wiped previously-registered categories (#463).
- Stale phone-home detection: verify node boot time is after PXE start epoch to reject nodes that have been up for days (#461).
- `failed_nodes.json` wrong count due to `set_fact` + `delegate_to` race condition when multiple BMC hosts fail PXE boot simultaneously (#460).
- Orchestrator inventory includes `kube_vip_group` even for slurm-only clusters (#459).
- Provision report shows wrong `missing_nodes` by comparing GROUP_NAMEs against xnames (#458).
- Missing `configs_vars.yaml` pre-check causes unclear error during provision (#450).
- OS-versioned FG names (e.g. `slurm_control_node_rhel_10_0_x86_64`) fail metadata-service template lookup — normalize template path.

### Added
- Custom inventory (`-i`) support for `pxeboot.yml` playbook for build_stream retry/resume (#432).
- Boot freshness check via `/proc/uptime` in phone-home verification.
- Race-free PXE failure collection using localhost loop over BMC hostvars.

### Changed
- Galaxy version set to 2.3.0.
- Renamed `phone_home` timing and verification controls to `node_registration` throughout PXE provisioning workflow to avoid confusion with Dell Phone Home functionality.
  - Role: `verify_phone_home` → `verify_node_registration`
  - Variables: `enable_phone_home` → `enable_node_registration`, `phone_home_pause_minutes` → `node_registration_pause_minutes`, etc.
  - Playbook references and documentation updated
  - Backward compatibility: legacy `phone_home_*` variables supported with deprecation warning
  - Node completion is verified directly through SSH, boot freshness, and cloud-init status

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
