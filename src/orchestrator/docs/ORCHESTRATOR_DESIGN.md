# Orchestrator — Design & Architecture


---

## 1. Overview

The **orchestrator** is a self-contained Ansible domain that manages the full post-discovery
lifecycle: OpenCHAMI deployment, PXE boot orchestration, image resolution, node provisioning,
and service deployment (K8s, Slurm, telemetry, storage, LDAP).

The domain is fully decoupled from `src/playbooks/utils/` and `src/common/` shared utilities.
It owns its own library (modules + module_utils), validation framework, credential management,
and cleanup lifecycle.

**Key Inputs**: `build_status.yml` (from image_build_manager), `pxe_mapping_file.csv` (from discovery).
**Key Outputs**: BSS/cloud-init boot configurations, functional groups, deployed OpenCHAMI services.

---

## 2. Directory Structure

```
src/orchestrator/
├── orchestrator.yml                    # Top-level orchestrator
├── ansible.cfg                         # Domain config (fully local paths)
├── callback_plugins/
│   └── omnia_default.py                # Local copy — stdout callback
├── library/                            # Domain-specific Python modules
│   ├── modules/
│   │   ├── generate_functional_groups.py
│   │   ├── generate_xname_in_mapping_file.py
│   │   ├── slurm_conf.py
│   │   ├── fetch_credential_rule.py
│   │   ├── validate_credentials.py
│   │   ├── generate_argon2_password.py
│   │   ├── fetch_telemetry_status.py
│   │   └── validate_orchestrator_config.py   # Domain-specific validation
│   └── module_utils/
│       ├── orchestrator_validation/          # Domain-specific validation
│       │   ├── orchestrator_validation_flow.py
│       │   └── schema/
│       │       ├── orchestrator_config.json
│       │       ├── network_spec.json
│       │       └── credential_rules.json
│       └── slurm/
│           └── slurm_conf_utils.py
├── playbooks/
│   ├── ansible.cfg                     # Sub-playbook config
│   ├── prepare_orchestrator.yml        # Deploy OpenCHAMI + S3 setup
│   ├── validate_orchestrator.yml       # Standalone validation
│   ├── orchestrator_credentials.yml    # Credential management
│   ├── cleanup_orchestrator.yml        # Cleanup OpenCHAMI + artifacts
│   ├── upgrade_orchestrator.yml        # Upgrade flow
│   └── rollback_orchestrator.yml       # Rollback flow
├── roles/
│   ├── orchestrator_setup/             # Upgrade guard, input dir, OIM group, guard facts
│   ├── orchestrator_functional_groups/ # Generate functional_groups_config.yml
│   ├── validate_orchestrator_input/    # L1 schema + L2 logic validation
│   ├── orchestrator_credentials/       # Credential prompt, encrypt, vault
│   ├── deploy_openchami/              # OpenCHAMI container deployment
│   ├── configure_ochami/             # BSS, cloud-init, node orchestration
│   ├── orchestrator_validations/      # Runtime L2/L3 pre-checks
│   ├── passwordless_ssh/              # SSH key distribution
│   ├── k8s_config/                    # Kubernetes configuration
│   ├── slurm_config/                  # Slurm scheduler configuration
│   ├── mount_config/                  # Storage mount configuration
│   ├── openldap/                      # OpenLDAP configuration
│   └── telemetry/                     # Telemetry deployment
├── vars/
│   ├── common_vars.yml                # Shared constants (permissions, retries)
│   ├── openchami_vars.yml             # OpenCHAMI auth/cert constants
│   └── openchami_image_cmd.yml        # OpenCHAMI build commands
├── tasks/
│   ├── configure_s3_access.yml        # Bridge build_status.yml → s3_configurations
│   ├── openchami_auth.yml             # OpenCHAMI cluster authentication
│   └── decrypt_include_encrypt.yml    # Vault credential helper
├── input/                             # Default input templates
│   ├── orchestrator_config.yml
│   ├── network_spec.yml
│   ├── pxe_mapping_file.csv
│   ├── omnia_config.yml
│   ├── storage_config.yml
│   ├── security_config.yml
│   ├── additional_cloud_init.yml
│   └── high_availability_config.yml
├── INPUT_CONTRACT.md
├── OUTPUT_CONTRACT.md
└── ORCHESTRATOR_DESIGN.md             # This file
```

---

## 3. Domain Configuration

| Item | Value |
|------|-------|
| Main playbook | `orchestrator.yml` |
| Input config | `orchestrator_config.yml` |
| Credential file | `omnia_config_credentials.yml` |
| Credential key | `.omnia_config_credentials_key` |
| Input subdir | `input/project_default/orchestrator/` |
| Output subdir | `output/project_default/orchestrator/` |
| Log path | `/opt/omnia/log/core/orchestrator/orchestrator.log` |

### Ansible Config (ansible.cfg)

```ini
library = library/modules
module_utils = library/module_utils
roles_path = roles
callback_plugins = callback_plugins
```

All paths are fully local — **zero references to `../common/`**.

---

## 4. End-to-End Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR — EXECUTION FLOW                             │
└─────────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
  │  User /  │      │  Setup   │      │ Validate │      │  Deploy  │      │ Provision│
  │ omnia.sh │      │  Role    │      │  Role    │      │ OpenCHAMI│      │  Nodes   │
  └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
       │                 │                 │                 │                 │
       │  Step 0: Setup  │                 │                 │                 │
       │────────────────>│                 │                 │                 │
       │                 │ ┌─────────────────────────────┐   │                 │
       │                 │ │ 1. Upgrade guard check      │   │                 │
       │                 │ │ 2. Load project config      │   │                 │
       │                 │ │ 3. Load OIM metadata        │   │                 │
       │                 │ │ 4. Create OIM host group    │   │                 │
       │                 │ │ 5. Set guard facts          │   │                 │
       │                 │ └─────────────────────────────┘   │                 │
       │                 │                 │                 │                 │
       │  Step 1: Validate                 │                 │                 │
       │──────────────────────────────────>│                 │                 │
       │                 │                 │ ┌─────────────────────────────┐   │
       │                 │                 │ │ L1: Schema validation       │   │
       │                 │                 │ │ L2: Cross-field logic       │   │
       │                 │                 │ └─────────────────────────────┘   │
       │                 │                 │                 │                 │
       │  Step 2: Credentials              │                 │                 │
       │────────────────────────────────────────────────────>│                 │
       │                 │                 │                 │                 │
       │  Step 3: Generate functional groups                 │                 │
       │────────────────────────────────────────────────────>│                 │
       │                 │                 │                 │                 │
       │  Step 4: Configure S3 + Deploy OpenCHAMI            │                 │
       │────────────────────────────────────────────────────>│                 │
       │                 │                 │                 │                 │
       │  Step 5: Provision nodes (BSS, cloud-init, services) │                │
       │──────────────────────────────────────────────────────────────────────>│
       │                 │                 │                 │                 │
  ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐
  │  User /  │      │  Setup   │      │ Validate │      │  Deploy  │      │ Provision│
  │ omnia.sh │      │  Role    │      │  Role    │      │ OpenCHAMI│      │  Nodes   │
  └──────────┘      └──────────┘      └──────────┘      └──────────┘      └──────────┘

Figure: orchestrator.yml execution flow
```

### Execution Steps

| Step | Play | Host | Description |
|------|------|------|-------------|
| 0 | Setup | localhost | `orchestrator_setup` role — upgrade guard, dirs, metadata, OIM group |
| 1 | Validate | localhost | `validate_orchestrator_input` role — L1 schema + L2 logic |
| 2 | Credentials | localhost | `orchestrator_credentials` role — prompt, encrypt, vault |
| 3 | Functional Groups | localhost | `orchestrator_functional_groups` role — generate from pxe_mapping |
| 4a | S3 Access | oim (SSH) | `configure_s3_access.yml` — load build_status.yml, set s3_configurations |
| 4b | Deploy OpenCHAMI | oim (SSH) | `deploy_openchami` role — OpenCHAMI containers |
| 5a | Orchestrate | oim (SSH) | `configure_ochami` — BSS, cloud-init, node mapping |
| 5b | Services | oim (SSH) | `mount_config`, `k8s_config`, `slurm_config`, `openldap`, `telemetry` |

### Tags

| Tag | What runs |
|-----|-----------|
| *(none)* | Full flow: setup → validate → credentials → deploy → provision |
| `openchami` | Steps 0–4b (deploy OpenCHAMI only) |
| `validate` | Steps 0–1 only (validation) |
| `cleanup` | Cleanup OpenCHAMI, artifacts |
| `upgrade` | Upgrade flow (placeholder) |
| `rollback` | Rollback flow (placeholder) |

---

## 5. Self-Containment — Zero External Dependencies

The orchestrator domain has **zero references to `../common/`** in `ansible.cfg`.
All modules, module_utils, callback plugins, and roles are local.

### 5.1 What Was Copied Locally

| Source (common) | Local Copy | Why |
|-----------------|-----------|-----|
| `common/callback_plugins/omnia_default.py` | `callback_plugins/omnia_default.py` | Stdout callback — needed by ansible.cfg |
| `common/library/modules/generate_functional_groups.py` | `library/modules/generate_functional_groups.py` | Used by `orchestrator_functional_groups` role |
| `common/library/modules/generate_xname_in_mapping_file.py` | `library/modules/generate_xname_in_mapping_file.py` | Used by `orchestrator_validations` role |
| `common/library/modules/slurm_conf.py` | `library/modules/slurm_conf.py` | Used by `slurm_config` role |
| `common/library/modules/fetch_credential_rule.py` | `library/modules/fetch_credential_rule.py` | Used by credential prompting (prompt_password/prompt_username) to validate input against `credential_rules.json` |
| `common/library/modules/validate_credentials.py` | `library/modules/validate_credentials.py` | Used by credential validation to check credential fields against `credential_rules.json` |
| `common/library/modules/generate_argon2_password.py` | `library/modules/generate_argon2_password.py` | Argon2 password hash generation for credential management |
| `common/library/modules/fetch_telemetry_status.py` | `library/modules/fetch_telemetry_status.py` | Used by `orchestrator_credentials` pre-requisite to check telemetry status |
| `common/library/module_utils/input_validation/schema/orchestrator_config.json` | `library/module_utils/orchestrator_validation/schema/orchestrator_config.json` | Orchestrator-specific schema |
| `common/library/module_utils/input_validation/schema/network_spec.json` | `library/module_utils/orchestrator_validation/schema/network_spec.json` | Network spec schema |
| `common/library/module_utils/input_validation/schema/credential_rules.json` | `library/module_utils/orchestrator_validation/schema/credential_rules.json` | Credential rules |
| `common/library/module_utils/input_validation/common_utils/slurm_conf_utils.py` | `library/module_utils/slurm/slurm_conf_utils.py` | Slurm configuration parser |
| *(new)* | `library/modules/validate_orchestrator_config.py` | Domain-specific validation module (L1+L2) |
| *(new)* | `library/module_utils/orchestrator_validation/orchestrator_validation_flow.py` | Orchestrator L2 validation logic |
| `common/vars/common_vars.yml` | `vars/common_vars.yml` | Shared constants (permissions, retries) |
| `common/vars/openchami_vars.yml` | `vars/openchami_vars.yml` | OpenCHAMI auth constants |
| `common/tasks/common/decrypt_include_encrypt.yml` | `tasks/decrypt_include_encrypt.yml` | Vault credential helper |
| `common/vars/encrypt_files_vars.yml` | `vars/encrypt_files_vars.yml` | Error messages for vault ops |

### 5.2 What Was Eliminated (Not Needed)

| Dependency | Reason Not Needed |
|------------|-------------------|
| `../playbooks/utils/upgrade_checkup.yml` | Absorbed into `orchestrator_setup` role |
| `../playbooks/utils/include_input_dir.yml` | Absorbed into `orchestrator_setup` role |
| `../playbooks/utils/create_container_group.yml` | Absorbed into `orchestrator_setup` role |
| `../playbooks/utils/generate_functional_groups.yml` | Replaced by `orchestrator_functional_groups` role |
| `../playbooks/input_validation/validate_config.yml` | Replaced by `validate_orchestrator_input` role |
| `../playbooks/utils/credential_utility/` | Replaced by `orchestrator_credentials` role |
| `tasks/clone_dependencies.yml` (rsync common/) | Eliminated — all deps local |

### 5.3 Verification

```bash
# Confirm zero external references in ansible.cfg
grep -c '\.\./common' src/orchestrator/ansible.cfg             # expect: 0
grep -c '\.\./common' src/orchestrator/playbooks/ansible.cfg   # expect: 0
grep -c 'playbooks/utils' src/orchestrator/**/*.yml            # expect: 0
```

---

## 6. Input/Output Contracts

### 6.1 build_status.yml (Input from image_build_manager)

**Producer**: image_build_manager domain
**Consumer**: orchestrator (configure_s3_access.yml)

```yaml
overall_status: "success"
s3_configurations:
  endpoint_url: "http://10.20.0.1:9000"
  bucket: "boot-images"
functional_group_images:
  x86_64:
    - functional_group: "slurm_control_node_x86_64"
      kernel: "boot-images/efi-images/.../vmlinuz"
      initrd: "boot-images/efi-images/.../initramfs.img"
      image: "boot-images/slurm_control_node_x86_64/..."
```

### 6.2 pxe_mapping_file.csv (Input from discovery)

**Producer**: discovery domain
**Consumer**: orchestrator (orchestrator_functional_groups, orchestrator_validations)

### 6.3 Orchestrator Outputs

**Location**: `output/project_default/orchestrator/`

- `functional_groups_config.yml` — Generated functional groups
- BSS boot parameter configurations
- Cloud-init default/group/node configurations
- `/opt/omnia/hosts` — Ansible inventory

---

## 7. Credential Management

### 7.1 Architecture

The `orchestrator_credentials` role manages vault-encrypted credential files
for all orchestrator services (provision, slurm, openldap, telemetry, etc.).

### 7.2 Credential Files

| File | Vault Key | Description |
|------|-----------|-------------|
| `omnia_config_credentials.yml` | `.omnia_config_credentials_key` | Provision, BMC, Slurm, LDAP, telemetry credentials |

### 7.3 Credential Lifecycle

```
1. Template creates: omnia_config_credentials.yml (plaintext with defaults)
2. Prompt fills:     Interactive prompts for empty mandatory fields
3. Vault encrypts:   ansible-vault encrypt with .omnia_config_credentials_key
4. Runtime reads:    Ansible decrypts at playbook execution time
5. Cleanup removes:  cleanup role deletes cred + key files (opt-in)
```

---

## 8. Input Validation Design

### 8.1 Pattern

Follows the `image_build_manager` lean validation pattern:
- **Domain-specific module**: `validate_orchestrator_config.py` — single Ansible module
- **Domain-specific flow**: `orchestrator_validation_flow.py` — L2 cross-field logic
- **Domain-specific schemas**: Only `orchestrator_config.json`, `network_spec.json`, `credential_rules.json`

No wholesale copy of the central `input_validation/` framework.

### 8.2 L1 — Schema Validation

JSON schemas define required properties, types, enums, and patterns.
The module loads each config file + its schema and validates structurally.

### 8.3 L2 — Cross-Field Logic Validation

| Rule | File | Description |
|------|------|-------------|
| Language check | orchestrator_config.yml | Must contain `en_US.UTF-8` |
| Lease time | orchestrator_config.yml | Must be a positive integer |
| Kernel version | orchestrator_config.yml | Must match `X.Y.Z-suffix` format |
| S3 config | orchestrator_config.yml | Endpoint required for powerscale/external providers |
| Mapping file | orchestrator_config.yml | Required columns, no duplicates, valid IPs |
| Network spec | network_spec.yml | Admin network with valid IP and netmask |
| Cross-file | mapping + network_spec | ADMIN_IPs must be in admin subnet |

### 8.4 Validation Module Interface

```yaml
- name: Run orchestrator configuration validation
  validate_orchestrator_config:
    input_project_dir: "{{ input_dir }}"
    schema_dir: "{{ orchestrator_schema_dir }}"
  register: result
```

Return keys: `validation_failed`, `errors`, `valid_files`, `invalid_files`, `log_file`.

---

## 9. Tag Support

| Tag | Supported | Description |
|-----|-----------|-------------|
| `prepare` | ✅ | Deploy OpenCHAMI + S3 setup |
| `provision` | ✅ | Provision nodes |
| `pxe` | ✅ | PXE boot only |
| `cleanup` | ✅ | Cleanup OpenCHAMI + artifacts |
| `validate` | ✅ | Validate config only |
| `upgrade` | ✅ | Upgrade flow |
| `rollback` | ✅ | Rollback flow |

### Invalid Combinations

`prepare+cleanup`, `provision+cleanup`, `pxe+cleanup`, `prepare+upgrade`,
`provision+upgrade`, `cleanup+upgrade`, `upgrade+rollback`.

Credential prompting is skipped for `cleanup` and `validate` tags.

---

## 10. Naming Convention

| Item | Convention | Example |
|------|------------|--------|
| Roles | `<domain>_<function>` | `orchestrator_setup`, `orchestrator_credentials` |
| Validation role | `validate_<domain>_input` | `validate_orchestrator_input` |
| Validation module | `validate_<domain>_config` | `validate_orchestrator_config` |
| Validation flow | `<domain>_validation_flow.py` | `orchestrator_validation_flow.py` |
| Schema dir | `<domain>_validation/schema/` | `orchestrator_validation/schema/` |
| Credential file | `omnia_config_credentials.yml` | Shared naming |
| Sub-playbooks | `<verb>_<domain>.yml` | `prepare_orchestrator.yml` |
| Log path | `/opt/omnia/log/core/<domain>/` | `/opt/omnia/log/core/orchestrator/` |

---

## 11. Backward Compatibility

- No breaking changes for users who don't use the new domain structure.
- `orchestrator_config.yml` is **required** — no legacy fallback.
- Sub-playbooks work independently with standalone setup guards.
- All `../playbooks/utils/` references eliminated.
