# Discovery Domain — Design Document

> **Last Updated**: Sep 2, 2026 | **Domain**: `discovery`

---

## 1. Purpose

The Discovery domain discovers hardware (servers) via management platforms
(e.g., Dell OpenManage Enterprise) and produces a PXE mapping file that serves
as the primary data contract between Discovery and the Orchestrator domain.

---

## 2. Self-Containment Principles

The discovery domain follows the same self-containment pattern as
`image_build_manager` and `orchestrator`:

| Principle | Implementation |
|-----------|---------------|
| **Zero `../common/` references** | All modules, module_utils, vars, and callback plugins are local |
| **Zero `../playbooks/` imports** | Validation and credential logic is absorbed into local roles |
| **Local ansible.cfg** | Root-level (`src/discovery/`) and playbook-level (`playbooks/`) configs |
| **Standalone execution** | `cd src/discovery && ansible-playbook playbooks/discovery.yml --tags execute` |

---

## 3. Directory Structure

```
src/discovery/
├── ansible.cfg                      # Root-level config (run from src/discovery/)
├── docs/
│   ├── DISCOVERY_DESIGN.md          # This document
│   └── contracts/
│       ├── input-contract.md        # Input contract
│       └── output-contract.md       # Output contract
├── playbooks/
│   ├── ansible.cfg                  # Playbook-level config (run from playbooks/)
│   ├── discovery.yml                # Top-level entrypoint (tag-based routing)
│   ├── precheck/
│   │   └── precheck_discovery.yml   # Precheck flow (placeholder)
│   ├── validate/
│   │   └── validate_discovery.yml   # Standalone validation
│   ├── credentials/
│   │   └── discovery_credentials.yml  # Standalone credential management
│   ├── prepare/
│   │   └── prepare_discovery.yml    # Prepare flow (placeholder)
│   ├── execute/
│   │   └── execute_discovery.yml    # OME discovery execution
│   ├── cleanup/
│   │   └── cleanup_discovery.yml    # Cleanup flow (placeholder)
│   ├── upgrade/
│   │   └── upgrade_discovery.yml    # Upgrade flow (placeholder)
│   └── rollback/
│       └── rollback_discovery.yml   # Rollback flow (placeholder)
├── plugins/
│   ├── modules/                     # Python modules
│   │   ├── ome_server_inventory.py  # OME device inventory collector
│   │   ├── generate_pxe_mapping.py  # PXE mapping CSV generator
│   │   ├── generate_discovery_report.py  # Discovery report generator
│   │   └── validate_discovery_config.py  # Domain-specific validation (L1+L2)
│   ├── module_utils/
│   │   └── discovery_validation/    # Domain-specific validation
│   │       ├── discovery_validation_flow.py  # L2 cross-field logic
│   │       └── schema/
│   │           └── discovery_config.json        # L1 JSON schema
│   └── callback/
│       └── omnia_default.py         # Custom stdout callback
├── vars/
│   ├── common_vars.yml              # Shared constants (retry, delay, permissions)
│   └── encrypt_files_vars.yml       # Credential encrypt/decrypt error messages
├── input/
│   ├── discovery_config.yml         # Input template
│   └── network_spec.yml             # Network spec template
├── roles/
│   ├── discovery_setup/             # Path init, config loading, tag validation
│   ├── validate_discovery_input/    # L1/L2 input validation
│   ├── discovery_credentials/       # Credential management (decrypt/prompt/encrypt)
│   ├── discovery_common/            # Shared task library (decrypt_include_encrypt)
│   └── ome_discovery/               # OME-specific discovery logic
├── domain-init.sh
├── galaxy.yml
├── README.md
├── requirements.txt
└── requirements.yml
```

---

## 4. Execution Flow

### 4.1 Default Flow (no tags)

When run without `--tags`, the default flow executes: setup → validate → credentials → execute.

```
discovery.yml (no --tags)
│
├─ [always] Step 0: discovery_setup role
│   ├── Tag validation (reject unsupported/conflicting tags)
│   ├── Upgrade guard (check lock file)
│   ├── Set project name, input/output dirs
│   ├── Verify discovery input directory exists
│   ├── Create discovery output directory
│   ├── Load discovery_config.yml
│   ├── Set enable_bmc_discovery flag
│   └── Mark setup as done (discovery_setup_done=true)
│
├─ [always] Step 1: validate_discovery_input role
│   └── Run validate_input module (L1 schema + L2 logic)
│
├─ [always] Step 2: discovery_credentials role
│   ├── Validate credential file existence
│   ├── Create credential files from templates if missing
│   ├── Prompt for missing OME credentials
│   └── Encrypt credential files
│
├─ [execute/discovery] Step 3: execute_discovery.yml
│   ├── Validate OME inputs (ome_ip)
│   └── Include ome_discovery role
│       ├── get_ome_credentials.yml     — decrypt & load OME creds
│       ├── collect_inventory.yml       — query OME API
│       ├── generate_pxe_mapping.yml    — produce CSV
│       └── generate_discovery_report.yml — produce report
```

### 4.2 Tag-Based Routing

Each tag routes to a dedicated sub-playbook under `playbooks/<tag>/`:

```
discovery.yml --tags <tag>
│
├─ [always]  discovery_setup          (runs for ALL tags)
├─ [always]  validate_discovery.yml   (skipped for precheck)
├─ [always]  discovery_credentials.yml (skipped for precheck/validate/cleanup)
│
├─ [precheck]   precheck/precheck_discovery.yml    (placeholder)
├─ [prepare]    prepare/prepare_discovery.yml      (placeholder)
├─ [execute]    execute/execute_discovery.yml       (OME discovery)
├─ [discovery]  execute/execute_discovery.yml       (alias for execute)
├─ [cleanup]    cleanup/cleanup_discovery.yml       (placeholder)
├─ [upgrade]    upgrade/upgrade_discovery.yml       (placeholder)
└─ [rollback]   rollback/rollback_discovery.yml    (placeholder)
```

Sub-playbooks include a standalone setup guard — if `discovery_setup_done` is
not set, they run `discovery_setup` themselves. This lets each sub-playbook
work both as an import from `discovery.yml` and as a standalone entry point.

---

## 5. Roles

### 5.1 discovery_setup

**Absorbs**: Inline tasks from `discovery.yml` (path init, config load, tag validation)

| Task | Description |
|------|-------------|
| Tag validation | Reject unsupported tags, detect invalid combinations |
| Skip-credentials flag | Set `skip_discovery_credentials` for precheck/validate/cleanup |
| Upgrade guard | Block if upgrade lock file exists |
| Set project name | `project_name` → `discovery_project_name` |
| Set input/output dirs | `discovery_input_dir`, `discovery_output_dir`, `input_project_dir` |
| Verify input dir | Auto-copy from source if runtime input dir missing |
| Create output dir | Ensure output directory exists |
| Load config | Include `discovery_config.yml` |
| Set flags | `enable_bmc_discovery` based on mechanism |
| Mark done | `discovery_setup_done=true` (prevents re-run in imported sub-playbooks) |

### 5.2 validate_discovery_input

**Absorbs**: `../playbooks/input_validation/validate_config.yml`

Runs the `validate_discovery_config` module (lean, domain-specific).

### 5.3 discovery_credentials

**Absorbs**: `../playbooks/utils/credential_utility/get_config_credentials.yml`

Simplified credential flow for discovery — only needs OME credentials
from `discovery_credentials.yml`.

### 5.4 discovery_common

Task-library role providing shared utilities:
- `decrypt_include_encrypt.yml` — decrypt/include/re-encrypt credential files

### 5.5 ome_discovery (existing)

OME-specific discovery logic — unchanged except credential loading now
uses the local `discovery_common` role.

---

## 6. Eliminated Dependencies

| Former Dependency | Replacement |
|-------------------|-------------|
| `../common/callback_plugins` | `callback_plugins/omnia_default.py` |
| `../common/library/modules` | `library/modules/` |
| `../common/library/module_utils` | `library/module_utils/` |
| `../playbooks/input_validation/validate_config.yml` | `validate_discovery_input` role |
| `../playbooks/utils/credential_utility/get_config_credentials.yml` | `discovery_credentials` role |

---

## 7. Data Contracts

### Input Contract

| File | Owner | Location |
|------|-------|----------|
| `discovery_config.yml` | User | `/opt/omnia/input/<project>/discovery/` |
| `network_spec.yml` | User | `/opt/omnia/input/<project>/discovery/` |
| `discovery_credentials.yml` | Credential utility | `/opt/omnia/input/<project>/discovery/` |

### Output Contract

| File | Consumer | Location |
|------|----------|----------|
| `bmc_pxe_mapping_file_<timestamp>.csv` | Operator → Orchestrator | `/opt/omnia/output/<project>/discovery/` |
| `bmc_pxe_mapping_file.csv` (symlink) | Operator → Orchestrator | `/opt/omnia/output/<project>/discovery/` |
| `bmc_discovery_report_<timestamp>.csv` | Operator (informational) | `/opt/omnia/output/<project>/discovery/` |

---

## 8. Input Validation Design

### 8.1 Pattern

Follows the `image_build_manager` lean validation pattern:
- **Domain-specific module**: `validate_discovery_config.py` — single Ansible module
- **Domain-specific flow**: `discovery_validation_flow.py` — L2 cross-field logic
- **Domain-specific schema**: Only `discovery_config.json`

No wholesale copy of the central `input_validation/` framework.

### 8.2 Validation Module Interface

```yaml
- name: Run discovery configuration validation
  validate_discovery_config:
    input_project_dir: "{{ input_dir }}"
    schema_dir: "{{ discovery_schema_dir }}"
  register: result
```

Return keys: `validation_failed`, `errors`, `valid_files`, `invalid_files`, `log_file`.

---

## 9. Tag Support

Tags are **mutually exclusive** — use ONE tag at a time (or none for the default
flow). Running without tags executes: setup → validate → credentials → execute.

| Tag | Status | Sub-Playbook | Description |
|-----|--------|--------------|-------------|
| *(none)* | ✅ Active | — | Default flow (validate + credentials + execute) |
| `precheck` | Placeholder | `precheck/precheck_discovery.yml` | Environment precheck |
| `validate` | ✅ Active | `validate/validate_discovery.yml` | Validate config only (skips credentials) |
| `credentials` | ✅ Active | `credentials/discovery_credentials.yml` | Collect/update OME credentials only |
| `prepare` | Placeholder | `prepare/prepare_discovery.yml` | Prepare discovery environment |
| `execute` | ✅ Active | `execute/execute_discovery.yml` | Run BMC discovery via OME |
| `discovery` | ✅ Active | `execute/execute_discovery.yml` | Alias for execute (backward compat) |
| `cleanup` | Placeholder | `cleanup/cleanup_discovery.yml` | Cleanup discovery artifacts |
| `upgrade` | Placeholder | `upgrade/upgrade_discovery.yml` | Upgrade flow |
| `rollback` | Placeholder | `rollback/rollback_discovery.yml` | Rollback flow |

### Usage Examples

```bash
cd src/discovery

# Default flow (validate + credentials + execute)
ansible-playbook playbooks/discovery.yml

# Individual tags
ansible-playbook playbooks/discovery.yml --tags precheck
ansible-playbook playbooks/discovery.yml --tags validate
ansible-playbook playbooks/discovery.yml --tags credentials
ansible-playbook playbooks/discovery.yml --tags execute
ansible-playbook playbooks/discovery.yml --tags cleanup
```

### Credential Skipping

Credential prompting is automatically skipped for these tags:
- `precheck` — no OME interaction needed
- `validate` — config validation only
- `cleanup` — teardown only

### Invalid Combinations

All tags are mutually exclusive. Any combination of two tags (e.g.,
`execute+cleanup`, `precheck+validate`) will fail with an error message
listing the conflict. The full list of invalid combinations is defined in
`discovery_setup/vars/main.yml`.

---

## 10. Naming Convention

| Item | Convention | Example |
|------|------------|--------|
| Roles | `<domain>_<function>` | `discovery_setup`, `discovery_credentials` |
| Validation role | `validate_<domain>_input` | `validate_discovery_input` |
| Validation module | `validate_<domain>_config` | `validate_discovery_config` |
| Validation flow | `<domain>_validation_flow.py` | `discovery_validation_flow.py` |
| Schema dir | `<domain>_validation/schema/` | `discovery_validation/schema/` |
| Credential file | `discovery_credentials.yml` | Domain-specific |
| Log path | `/opt/omnia/log/core/<domain>/` | `/opt/omnia/log/core/discovery/` |

---

## 11. Self-Containment Verification

```bash
# Confirm zero external references in ansible.cfg
grep -c '\.\./' src/discovery/playbooks/ansible.cfg           # expect: only ../ (parent-relative)
grep -c 'playbooks/utils' src/discovery/**/*.yml              # expect: 0
```

---

## 12. Backward Compatibility

- No breaking changes for users who don't use the new domain structure.
- `discovery_config.yml` is **required** — no legacy fallback.
- Sub-playbooks work independently with standalone setup guards.
- All `../playbooks/utils/` references eliminated.
