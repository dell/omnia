# Discovery Domain — Design Document

> **Last Updated**: Sep 16, 2026 | **Domain**: `discovery`

---

## 1. Purpose

The Discovery domain discovers hardware through Dell OpenManage Enterprise
(OME) and produces a PXE mapping file that serves as the primary data contract
between Discovery and the Orchestrator domain.

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

`DISCOVERY_DATA_PATH` is the component data root. When it is unset or empty,
Discovery derives it as `$OMNIA_DATA_PATH/discovery`.

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
│   │   └── precheck_discovery.yml   # Data-path and OME endpoint precheck
│   ├── validate/
│   │   └── validate_discovery.yml   # Standalone validation
│   ├── credentials/
│   │   └── discovery_credentials.yml  # Standalone credential management
│   ├── prepare/
│   │   └── prepare_discovery.yml    # Prepare flow (placeholder)
│   ├── execute/
│   │   └── execute_discovery.yml    # OME discovery execution
│   ├── cleanup/
│   │   └── cleanup_discovery.yml    # Output and credential cleanup flow
│   ├── upgrade/
│   │   └── upgrade_discovery.yml    # Upgrade flow (placeholder)
│   └── rollback/
│       └── rollback_discovery.yml   # Rollback flow (placeholder)
├── plugins/
│   ├── modules/                     # Python modules
│   │   ├── ome_server_inventory.py  # OME device inventory collector
│   │   ├── generate_pxe_mapping.py  # PXE mapping CSV generator
│   │   ├── generate_discovery_report.py  # Discovery report generator
│   │   ├── validate_discovery_config.py  # Domain-specific validation (L1+L2)
│   │   └── validate_system_environment.py # Selective OIM environment validation
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
│   ├── precheck_environment/        # Data-path and OME endpoint checks
│   ├── validate_discovery_input/    # L1/L2 input validation
│   ├── discovery_credentials/       # Credential management (decrypt/prompt/encrypt)
│   ├── discovery_cleanup/           # Output and credential cleanup
│   ├── discovery_common/            # Shared vault and OME endpoint task library
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
│   └── Mark setup as done (discovery_setup_done=true)
│
├─ [always] Step 1: validate_discovery_input role
│   └── Run validate_discovery_config module (L1 schema + L2 logic)
│
├─ [always] Step 2: discovery_credentials role
│   ├── Validate credential file existence
│   ├── Create credential files from templates if missing
│   ├── Prompt for missing OME credentials
│   └── Encrypt credential files
│
├─ [execute] Step 3: execute_discovery.yml
│   ├── Validate OME inputs (ome_ip)
│   └── Include ome_discovery role
│       ├── check_ome_connectivity.yml  — wait for OME TCP/443
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
├─ [always]  validate_discovery.yml   (skipped for precheck/cleanup*)
├─ [always]  discovery_credentials.yml (skipped for precheck/validate/cleanup*)
│
├─ [precheck]   precheck/precheck_discovery.yml
│   ├── Validate the resolved Discovery data path
│   └── Wait for OME TCP/443
├─ [prepare]    prepare/prepare_discovery.yml      (placeholder)
├─ [execute]    execute/execute_discovery.yml       (OME discovery)
├─ [cleanup]    cleanup/cleanup_discovery.yml
│   ├── Empty the project output directory but keep the directory
│   └── Remove credentials by default (optional preservation)
├─ [cleanup_credentials] cleanup/cleanup_discovery.yml
│   └── Remove only the credential file and vault key
├─ [upgrade]    upgrade/upgrade_discovery.yml       (placeholder)
└─ [rollback]   rollback/rollback_discovery.yml    (placeholder)
```

The validation, credential, execute, and cleanup sub-playbooks contain a setup
guard for direct invocation. The precheck flow consumes setup facts and is run
through the supported top-level `discovery.yml --tags precheck` entrypoint.

---

## 5. Roles

### 5.1 discovery_setup

**Absorbs**: Inline tasks from `discovery.yml` (path init, config load, tag validation)

| Task | Description |
|------|-------------|
| Tag validation | Reject unsupported tags, detect invalid combinations |
| Skip-credentials flag | Set `skip_discovery_credentials` for precheck/validate/cleanup/cleanup_credentials |
| Upgrade guard | Block if upgrade lock file exists |
| Set project name | `project_name` → `discovery_project_name` |
| Set input/output dirs | `discovery_input_dir`, `discovery_output_dir`, `input_project_dir` |
| Verify input dir | Auto-copy from source if runtime input dir missing |
| Create output dir | Ensure output directory exists |
| Load config | Include `discovery_config.yml` |
| Mark done | `discovery_setup_done=true` (prevents re-run in imported sub-playbooks) |

For `cleanup` and `cleanup_credentials`, setup resolves tag and environment
state but does not copy missing inputs, create the output directory, or load
Discovery configuration. Cleanup therefore remains independent of the files
it removes. In the flow above, `cleanup*` means either cleanup tag.

### 5.2 validate_discovery_input

**Absorbs**: `../playbooks/input_validation/validate_config.yml`

Runs the `validate_discovery_config` module (lean, domain-specific).

### 5.3 precheck_environment

Performs Discovery-specific prerequisite validation without reading OME
credentials or calling the OME API:

- reports whether `/etc/omnia/omnia.env` is installed;
- validates the resolved `DISCOVERY_DATA_PATH`;
- calls the shared OME endpoint task to verify TCP connectivity from the OIM
  host to `ome_ip` on port 443.

Port 443 is an internal constant rather than a new user input because the OME
inventory client uses `https://<ome_ip>` on the standard HTTPS port. Only the
connection-attempt and overall wait time have internal role defaults.

Discovery does not depend on `SYSTEM_HOSTNAME`, `SYSTEM_DOMAIN_NAME`, or
`SYSTEM_ADMIN_NIC_IPV4`, so precheck deliberately does not compare those
generic OIM values. The top-level `discovery_setup` role still runs first and
may initialize missing runtime input/output directories.

### 5.4 discovery_credentials

**Absorbs**: `../playbooks/utils/credential_utility/get_config_credentials.yml`

Simplified credential flow for discovery — only needs OME credentials
from `discovery_credentials.yml`.

### 5.5 discovery_common

Task-library role providing shared utilities:
- `decrypt_include_encrypt.yml` — decrypt/include/re-encrypt credential files
- `check_ome_connectivity.yml` — require `ome_ip` and wait for its TCP/443
  endpoint without authenticating or making an HTTPS request

### 5.6 ome_discovery (existing)

OME-specific discovery logic. It invokes the shared endpoint check before
making the OME API inventory call, so the execute flow remains protected even
when the user does not run precheck separately.

### 5.7 discovery_cleanup

Owns the Discovery cleanup boundary:

- does not remove or create
  `$DISCOVERY_DATA_PATH/output/$OMNIA_PROJECT_NAME`; when the directory
  exists, it removes every entry, including hidden entries, and leaves the
  empty directory in place;
- removes `discovery_credentials.yml` and `.discovery_credentials_key` by
  default;
- preserves those two credential artifacts when
  `cleanup_credentials=false`;
- preserves every other Discovery input file;
- validates the resolved data root, project name, derived paths, and Boolean
  cleanup option before deleting anything.

---

## 6. Eliminated Dependencies

| Former Dependency | Replacement |
|-------------------|-------------|
| `../common/callback_plugins` | `plugins/callback/omnia_default.py` |
| `../common/library/modules` | `plugins/modules/` |
| `../common/library/module_utils` | `plugins/module_utils/` |
| `../playbooks/input_validation/validate_config.yml` | `validate_discovery_input` role |
| `../playbooks/utils/credential_utility/get_config_credentials.yml` | `discovery_credentials` role |

---

## 7. Data Contracts

### Input Contract

| File | Owner | Location |
|------|-------|----------|
| `discovery_config.yml` | User | `$DISCOVERY_DATA_PATH/input/<project>/` |
| `network_spec.yml` | User | `$DISCOVERY_DATA_PATH/input/<project>/` |
| `discovery_credentials.yml` | Credential utility | `$DISCOVERY_DATA_PATH/input/<project>/` |

### Output Contract

| File | Consumer | Location |
|------|----------|----------|
| `bmc_pxe_mapping_file_<timestamp>.csv` | Operator → Orchestrator | `$DISCOVERY_DATA_PATH/output/<project>/` |
| `bmc_pxe_mapping_file.csv` (symlink) | Operator → Orchestrator | `$DISCOVERY_DATA_PATH/output/<project>/` |
| `bmc_discovery_report_<timestamp>.csv` | Operator (informational) | `$DISCOVERY_DATA_PATH/output/<project>/` |
| `discovery_status.yml` | Operator | `$DISCOVERY_DATA_PATH/output/<project>/` |

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
    input_project_dir: "{{ input_project_dir }}"
    schema_dir: "{{ discovery_schema_dir }}"
    log_dir: "{{ log_dir }}"
  register: result
```

Return keys: `validation_failed`, `errors`, `valid_files`, `invalid_files`, `log_file`.

`discovery_setup` derives `log_dir` as
`$DISCOVERY_DATA_PATH/log/$OMNIA_PROJECT_NAME`. This project-scoped
directory contains Discovery validation/runtime logs. Ansible execution logs
remain separate under `/var/log/omnia/discovery/` as configured by each
entrypoint's `ansible.cfg`; the main entrypoint uses `discovery.log`.

---

## 9. Tag Support

Run one functional tag at a time. The setup role rejects conflicting tag
combinations; `cleanup` and `cleanup_credentials` may be combined to make
credential deletion explicit. Running without tags executes: setup → validate
→ credentials → execute.

| Tag | Status | Sub-Playbook | Description |
|-----|--------|--------------|-------------|
| *(none)* | ✅ Active | — | Default flow (validate + credentials + execute) |
| `precheck` | ✅ Active | `precheck/precheck_discovery.yml` | Validate data path and OME TCP/443 connectivity |
| `validate` | ✅ Active | `validate/validate_discovery.yml` | Validate config only (skips credentials) |
| `credentials` | ✅ Active | `credentials/discovery_credentials.yml` | Validate config, then load stored or collect missing OME credentials |
| `prepare` | Placeholder | `prepare/prepare_discovery.yml` | Prepare discovery environment |
| `execute` | ✅ Active | `execute/execute_discovery.yml` | Run BMC discovery via OME |
| `cleanup` | ✅ Active | `cleanup/cleanup_discovery.yml` | Cleanup project outputs and credentials |
| `cleanup_credentials` | ✅ Active | `cleanup/cleanup_discovery.yml` | Cleanup credentials only |
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
ansible-playbook playbooks/discovery.yml --tags cleanup \
  -e cleanup_credentials=false
ansible-playbook playbooks/discovery.yml --tags cleanup_credentials
```

### Credential Skipping

Credential prompting is automatically skipped for these tags:
- `precheck` — endpoint connectivity only; no credentials or OME API calls
- `validate` — config validation only
- `cleanup` — teardown only
- `cleanup_credentials` — credential teardown only

The cleanup tag removes credentials by default. The
`cleanup_credentials=false` extra variable preserves the encrypted Discovery
credential file and its vault key without preserving generated outputs.

### Invalid Combinations

Unsupported tag combinations (for example, `execute+cleanup`) fail with an
error listing the conflict. `cleanup+cleanup_credentials` is intentionally
allowed; the explicit credential tag takes precedence even if
`cleanup_credentials=false` is supplied. The full list is defined in
`discovery_setup/vars/main.yml`.

---

## 10. Naming Convention

| Item | Convention | Example |
|------|------------|--------|
| Roles | `<domain>_<function>` | `discovery_setup`, `discovery_cleanup` |
| Validation role | `validate_<domain>_input` | `validate_discovery_input` |
| Validation module | `validate_<domain>_config` | `validate_discovery_config` |
| Validation flow | `<domain>_validation_flow.py` | `discovery_validation_flow.py` |
| Schema dir | `<domain>_validation/schema/` | `discovery_validation/schema/` |
| Credential file | `discovery_credentials.yml` | Domain-specific |
| Project log path | `$DISCOVERY_DATA_PATH/log/$OMNIA_PROJECT_NAME/` | `/opt/omnia/discovery/log/project_default/` |
| Ansible log path | `/var/log/omnia/<domain>/<domain>.log` | `/var/log/omnia/discovery/discovery.log` |

---

## 11. Self-Containment Verification

```bash
# Confirm zero external references in ansible.cfg
grep -c '\.\./' src/discovery/playbooks/ansible.cfg           # expect: only ../ (parent-relative)
grep -c 'playbooks/utils' src/discovery/**/*.yml              # expect: 0
```

---

## 12. Compatibility and Migration

- `discovery_config.yml` is **required** and `ome_ip` must contain a valid,
  non-loopback IPv4 address.
- The legacy `enable_bmc_discovery` switch is no longer part of the input
  contract because the Discovery domain is OME-only and execution was never
  gated by that switch. Existing files containing the old key remain readable,
  but the key has no effect.
- OME is the only Discovery backend. Users do not set a
  `discovery_mechanism` extra variable; use the `execute` tag to run discovery.
- Use the top-level `discovery.yml` entrypoint for tag-based workflows.
- All `../playbooks/utils/` references are eliminated.
