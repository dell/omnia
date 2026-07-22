# Image Build Manager — Design & Architecture


---

## 1. Overview

The **image_build_manager** is a self-contained Ansible domain that builds OS boot images
(kernel, initramfs, rootfs) for x86_64 and aarch64 architectures. It manages S3 storage
(MinIO or PowerScale), container registry deployment, credential lifecycle, and input validation.

The domain is fully decoupled from `src/playbooks/utils/` and `src/common/` shared utilities.
It owns its own library (modules + module_utils), validation framework, credential management,
and cleanup lifecycle.

**Key Outputs**: `build_status.yml` consumed by the provision domain.

---

## 2. Directory Structure

```
src/image_build_manager/
├── image_build_manager.yml              # Top-level orchestrator
├── ansible.cfg                          # Domain config (fully local paths)
├── callback_plugins/
│   └── omnia_default.py                 # Local copy — stdout callback
├── library/                             # Domain-specific Python modules
│   ├── modules/
│   │   ├── base_image_package_collector.py
│   │   ├── image_package_collector.py
│   │   ├── functional_group_parser.py
│   │   ├── generate_functional_groups.py
│   │   └── validate_image_build_config.py
│   └── module_utils/
│       ├── build_image/
│       │   ├── __init__.py
│       │   ├── common_functions.py       # JSON/YAML loaders, package helpers
│       │   └── config.py                 # ROLE_SPECIFIC_KEYS, FUNCTIONAL_GROUP_LAYER_MAP
│       └── image_build_validation/
│           ├── __init__.py
│           ├── image_build_validation_flow.py
│           └── schema/
│               ├── image_build_config.json
│               ├── image_build_credentials.json
│               └── functional_groups_config.json
├── playbooks/
│   ├── ansible.cfg                      # Standalone sub-playbook config
│   ├── prepare_image_build_manager.yml  # Deploy MinIO + Registry + SELinux preflight
│   ├── build_image_x86_64.yml
│   ├── build_image_aarch64.yml
│   ├── cleanup_image_build_manager.yml
│   ├── get_build_credentials.yml
│   ├── validate_image_build_config.yml  # Standalone validation
│   ├── upgrade_image_build_manager.yml
│   └── rollback_image_build_manager.yml
├── roles/
│   ├── image_build_setup/               # Upgrade guard, input dir, OIM group, guard facts
│   ├── validate_image_build_input/      # L1 schema + L2 logic validation
│   ├── collect_build_credentials/        # Credential prompt, encrypt, vault
│   ├── generate_functional_groups/      # Generate functional_groups_config.yml
│   ├── validate_build_runtime/          # Runtime L2/L3 pre-checks
│   ├── deploy_minio/                    # MinIO Quadlet container service
│   ├── deploy_registry/                 # Container registry Quadlet service
│   ├── fetch_build_packages/            # Package collection + repo fetch
│   ├── build_os_images/                 # Build base + compute images
│   ├── prepare_aarch64_node/            # aarch64 build host setup
│   └── cleanup_build_artifacts/         # Full cleanup (MinIO, registry, creds, artifacts)
├── vars/
│   ├── image_vars.yml                   # S3 bucket constants
│   └── openchami_image_cmd.yml          # OpenCHAMI build commands
├── containers/
│   └── build_images.sh                  # Self-contained image-builder container build
├── INPUT_CONTRACT.md
├── OUTPUT_CONTRACT.md
├── IMAGE_BUILD_MIGRATION_PLAN.md
└── IMAGE_BUILDER_DESIGN.md             # This file
```

---

## 3. Domain Configuration

| Item | Value |
|------|-------|
| Main playbook | `image_build_manager.yml` |
| Input config | `image_build_config.yml` |
| Credential file | `image_build_credentials.yml` |
| Credential key | `.image_build_credentials_key` |
| Input subdir | `input/project_default/image_build_manager/` |
| Output subdir | `output/project_default/image_build_manager/` |
| Log path | `/opt/omnia/log/core/playbooks/image_build_manager.log` |

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
│                         IMAGE BUILD MANAGER — EXECUTION FLOW                        │
└─────────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
  │          │      │          │      │          │      │          │      │          │
  │  User /  │      │  Setup   │      │ Validate │      │ Prepare  │      │  Build   │
  │ omnia.sh │      │  Role    │      │  Role    │      │  Infra   │      │  Images  │
  │          │      │          │      │          │      │          │      │          │
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
       │                 │                 │ │ L1: JSON schema check       │   │
       │                 │                 │ │ L2: Cross-field logic       │   │
       │                 │                 │ │ Vault detection (skip enc)  │   │
       │                 │                 │ └─────────────────────────────┘   │
       │                 │                 │                 │                 │
       │  Step 2: Credentials              │                 │                 │
       │────────────────────────────────────────────────────>│                 │
       │                 │                 │                 │                 │
       │  Step 3: Load config + repo_status                  │                 │
       │────────────────────────────────────────────────────>│                 │
       │                 │                 │                 │                 │
       │  Step 4: Prepare (MinIO + Registry + SELinux)       │                 │
       │────────────────────────────────────────────────────>│                 │
       │                 │                 │                 │                 │
       │  Step 5-7: Build x86_64 + aarch64 + write status    │                 │
       │──────────────────────────────────────────────────────────────────────>│
       │                 │                 │                 │                 │
  ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐
  │  User /  │      │  Setup   │      │ Validate │      │ Prepare  │      │  Build   │
  │ omnia.sh │      │  Role    │      │  Role    │      │  Infra   │      │  Images  │
  └──────────┘      └──────────┘      └──────────┘      └──────────┘      └──────────┘

Figure: image_build_manager.yml orchestration flow
```

### Execution Steps

| Step | Play | Host | Description |
|------|------|------|-------------|
| 0 | Setup | localhost | `image_build_setup` role — upgrade guard, dirs, metadata, OIM group |
| 1 | Validate | localhost | `validate_image_build_config.yml` — L1 schema + L2 logic |
| 2 | Credentials | localhost | `get_build_credentials.yml` — prompt, encrypt, vault |
| 3 | Config | localhost | Load `image_build_config.yml` + S3 endpoint resolution |
| 4 | Pre-check | localhost | Load `repo_status.yml` → Pulp repos + certs |
| 5 | Prepare | oim (SSH) | Deploy MinIO + Registry + SELinux policy |
| 6 | Build x86_64 | oim (SSH) | Validate → fetch packages → build images |
| 7 | Build aarch64 | admin_aarch64 | Prepare ARM node → build images |
| 8 | Output | localhost | Write `build_status.yml` |

### Tags

| Tag | What runs |
|-----|-----------|
| *(none)* | Full flow: setup → validate → prepare → build |
| `prepare` | Steps 0–5 only (deploy infra) |
| `build` | Steps 0–4 + 5–8 (prepare + build) |
| `validate` | Steps 0–1 only (validation) |
| `cleanup` | Cleanup MinIO, registry, artifacts |
| `upgrade` | Upgrade flow (placeholder) |
| `rollback` | Rollback flow (placeholder) |

---

## 5. Input Validation Design (HLD)

### 5.1 Architecture

The image_build_manager uses a **two-tier validation architecture**:

```
┌─────────────────────────────────────────────────────────┐
│               validate_image_build_input role           │
│   (roles/validate_image_build_input/tasks/main.yml)     │
└───────────────────────┬─────────────────────────────────┘
                        │ calls
                        ▼
┌─────────────────────────────────────────────────────────┐
│         validate_image_build_config module              │
│   (library/modules/validate_image_build_config.py)      │
├─────────────────────────────────────────────────────────┤
│  L1: JSON Schema Validation                             │
│    ├── image_build_config.json                          │
│    ├── image_build_credentials.json                     │
│    └── functional_groups_config.json                    │
│  L2: Cross-Field Logic Validation                       │
│    ├── S3 provider ↔ endpoint_url consistency           │
│    ├── aarch64 host IP ↔ ssh_user dependency            │
│    ├── job_async ≥ job_retry × job_delay                │
│    └── powerscale → s3_access_id required               │
│  Vault Detection                                        │
│    └── Skip encrypted files (detect $ANSIBLE_VAULT)     │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Validation Levels

| Level | What | Where | When |
|-------|------|-------|------|
| **L1 — Schema** | JSON Schema type/required/enum checks | `validate_image_build_config.py` + `schema/*.json` | Always (Step 1) |
| **L2 — Logic** | Cross-field business rules | `image_build_validation_flow.py` | Always (Step 1) |
| **L3 — Runtime** | File existence, S3 reachability, cert validity | `validate_build_runtime` role | Before build (in build playbooks) |

### 5.3 Validated Files

| File | Schema | Required | Notes |
|------|--------|----------|-------|
| `image_build_config.yml` | `image_build_config.json` | Yes | S3 config, aarch64 host, job settings |
| `image_build_credentials.yml` | `image_build_credentials.json` | No | Skipped if vault-encrypted |
| `functional_groups_config.yml` | `functional_groups_config.json` | No | Generated at runtime from mapping.csv |

### 5.4 L2 Validation Rules

| Rule | Condition | Error |
|------|-----------|-------|
| PowerScale endpoint | `provider == powerscale` → `endpoint_url` required | "endpoint_url is required when provider is powerscale" |
| aarch64 SSH user | `aarch64_inventory_host_ip` set → `aarch64_ssh_user` required | "aarch64_ssh_user is required when host_ip is set" |
| Async budget | `job_async < job_retry × job_delay` | "job_async must be >= job_retry × job_delay" |
| PowerScale access ID | `provider == powerscale` → `s3_access_id` required in credentials | "s3_access_id is required for powerscale" |

### 5.5 Vault-Encrypted File Handling

Credential files are typically Ansible Vault encrypted. The validation module detects
the `$ANSIBLE_VAULT` header and skips schema validation for encrypted files. This avoids
the bug where `yaml.safe_load()` returns a string instead of a dict for encrypted content.

### 5.6 Usage

```bash
# Standalone validation
cd src/image_build_manager
ansible-playbook playbooks/validate_image_build_config.yml

# As part of full flow (always runs)
ansible-playbook image_build_manager.yml

# Validate-only tag
ansible-playbook image_build_manager.yml --tags validate
```

### 5.7 Reusability for Other Domains

Other domains can adopt this pattern:

1. Create `library/modules/validate_<domain>_config.py` using the same skeleton
2. Create `library/module_utils/<domain>_validation/schema/` with JSON schemas
3. Create `library/module_utils/<domain>_validation/<domain>_validation_flow.py` for L2 rules
4. Create `roles/validate_<domain>_input/` role with tasks + vars
5. Add `validate_<domain>_config.yml` sub-playbook
6. Update `ansible.cfg` with `library = library/modules:../common/library/modules`

**Template files to copy**:
- `validate_image_build_config.py` → rename and adjust `VALIDATION_FILES` list
- `image_build_validation_flow.py` → replace L2 rules with domain-specific logic
- `roles/validate_image_build_input/` → rename role, update vars

---

## 6. Credential Management Design (HLD)

### 6.1 Architecture

```
┌─────────────────────────────────────────────────────────┐
│           collect_build_credentials role                 │
│   (roles/collect_build_credentials/tasks/main.yml)      │
├─────────────────────────────────────────────────────────┤
│  Step 1: Resolve credential file path                   │
│  Step 2: Check if credential file exists                │
│  Step 3: Create from template if missing                │
│  Step 4: Decrypt vault (if encrypted)                   │
│  Step 5: Prompt mandatory fields (s3_secret_key, etc.)  │
│  Step 6: Prompt conditional fields (s3_access_id)       │
│  Step 7: Re-encrypt with Ansible Vault                  │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Credential Fields

| Field | Type | When Required |
|-------|------|---------------|
| `s3_secret_key` | Mandatory | Always (MinIO password or PowerScale S3 key) |
| `provision_password` | Mandatory | Always (SSH to ARM build host) |
| `s3_access_id` | Conditional | When `s3_configurations.provider == powerscale` |

### 6.3 Credential Lifecycle

```
1. Template creates: image_build_credentials.yml (plaintext with defaults)
2. Prompt fills:     Interactive prompts for empty mandatory fields
3. Vault encrypts:   ansible-vault encrypt with .image_build_credentials_key
4. Runtime reads:    Ansible decrypts at playbook execution time
5. Cleanup removes:  cleanup_build_artifacts role deletes cred + key files
```

### 6.4 Ownership Transfer

| Credential | Before (prepare_oim) | After (image_build_manager) |
|------------|---------------------|-----------------------------|
| `s3_secret_key` | `omnia_config_credentials.yml` | `image_build_credentials.yml` only |
| `s3_access_id` | `omnia_config_credentials.yml` | `image_build_credentials.yml` only |
| `provision_password` | `omnia_config_credentials.yml` | `image_build_credentials.yml` (mandatory) |

### 6.5 File Locations

```
input/project_default/
├── image_build_credentials.yml      ← Vault-encrypted credentials
├── .image_build_credentials_key     ← Vault password file
└── image_build_manager/
    └── image_build_config.yml       ← S3 provider determines which creds are needed
```

### 6.6 Reusability for Other Domains

To create credentials for another domain:

1. Create `roles/collect_<domain>_credentials/` with same task structure
2. Create a Jinja2 template `<domain>_credential.j2` listing fields
3. Define `<domain>_cred_config.mandatory` and `<domain>_cred_config.conditional_mandatory` in vars
4. Use `prompt_credential_field.yml` pattern (loop over fields, prompt empty, re-encrypt)
5. Register vault password mapping in `config.py` → `get_vault_password()`

---

## 7. Self-Containment — Zero External Dependencies

The image_build_manager domain has **zero references to `../common/`** in `ansible.cfg`.
All modules, module_utils, callback plugins, and roles are local.

### 7.1 What Was Copied Locally

| Source (common) | Local Copy | Why |
|-----------------|-----------|-----|
| `common/callback_plugins/omnia_default.py` | `callback_plugins/omnia_default.py` | Stdout callback — needed by ansible.cfg |
| `common/library/module_utils/build_image/` | `library/module_utils/build_image/` | Used by `base_image_package_collector.py`, `image_package_collector.py` |
| `common/library/modules/generate_functional_groups.py` | `library/modules/generate_functional_groups.py` | Used by `generate_functional_groups` role |
| `common/library/module_utils/input_validation/common_utils/config.py` → `FUNCTIONAL_GROUP_LAYER_MAP` | Inlined into `library/module_utils/build_image/config.py` | Used by `generate_functional_groups.py` |

### 7.2 What Was Eliminated (Not Needed)

| Dependency | Reason Not Needed |
|------------|-------------------|
| `common/library/module_utils/input_validation/` | Domain has own `image_build_validation/` with schemas + flow |
| `common/library/modules/validate_input.py` | Replaced by `validate_image_build_config.py` |
| `../playbooks/input_validation/roles` | Replaced by `validate_image_build_input` role |
| `../playbooks/utils/credential_utility` | Replaced by `image_build_credentials` role |
| `../playbooks/utils/upgrade_checkup.yml` | Replaced by `image_build_setup` role (Step 1) |
| `../playbooks/utils/include_input_dir.yml` | Replaced by `image_build_setup` role (Step 2) |
| `../playbooks/utils/create_container_group.yml` | Replaced by `image_build_setup` role (Step 4) |
| `../playbooks/utils/generate_functional_groups.yml` | Replaced by `generate_functional_groups` role |

### 7.3 Verification

```bash
# Confirm zero external references in ansible.cfg
grep -c '\.\./common' src/image_build_manager/ansible.cfg           # expect: 0
grep -c '\.\./common' src/image_build_manager/playbooks/ansible.cfg # expect: 0
grep -c 'playbooks/utils' src/image_build_manager/**/*.yml          # expect: 0
```

---

## 8. Input/Output Contracts

### 8.1 repo_status.yml (Input from repo_manager)

**Producer**: repo_manager domain
**Consumer**: image_build_manager (Step 4)

```yaml
overall_status: "success"
repo_manager:
  port: 2225
  certificates:
    server_crt: "/opt/omnia/pulp/settings/certs/pulp_webserver.crt"
rpm_repos:
  x86_64: { baseos: "https://...", appstream: "https://...", ... }
  aarch64: { baseos: "https://...", ... }
user_repos:
  x86_64: { slurm_custom: "https://..." }
```

### 8.2 build_status.yml (Output to provision)

**Producer**: image_build_manager (Step 8)
**Consumer**: provision domain

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
  aarch64:
    - functional_group: "slurm_node_aarch64"
      kernel: "boot-images/efi-images/.../vmlinuz"
```

---

## 9. Backward Compatibility

- No breaking changes for users who don't use image_build_manager.
- `image_build_config.yml` is **required** — no legacy fallback.
- Sub-playbooks work independently with standalone setup guards.
- Container build is self-contained in `src/image_build_manager/containers/`.


## 10. Naming Convention

### Rules

| Component | Convention | Example |
|-----------|-----------|---------|
| **Playbook** | `verb_noun.yml` (user action) | `get_build_credentials.yml`, `build_image_x86_64.yml` |
| **Role** | `verb_noun` (what the role does) | `collect_build_credentials`, `deploy_minio` |
| **Data file** | `noun.yml` (artifact) | `image_build_credentials.yml`, `build_status.yml` |
| **Task file** | `verb_noun.yml` (action) | `prompt_credential_field.yml`, `cleanup_minio.yml` |

### Applied Renames

| Old | New | Why |
|-----|-----|-----|
| `roles/image_build_credentials/` | `roles/collect_build_credentials/` | Role *collects* credentials — verb differentiates from data file |
| `playbooks/image_build_credentials.yml` | `playbooks/get_build_credentials.yml` | User *gets* credentials — matches `get_config_credentials.yml` pattern |
| `tasks/prompt_credentials.yml` | `tasks/prompt_credential_field.yml` | More specific — prompts one field per loop iteration |

### Completed Renames (Batch 2)

| Old | New | Rationale |
|-----|-----|-----------|
| `roles/validate_build_config/` | `roles/validate_build_runtime/` | Distinguishes from `validate_image_build_input` (schema) |
| `roles/image_build_functional_groups/` | `roles/generate_functional_groups/` | Verb-first — role *generates* FGs |
| `roles/image_creation/` | `roles/build_os_images/` | Verb-first + domain-specific |
| `roles/fetch_packages/` | `roles/fetch_build_packages/` | Add domain prefix |
| `roles/prepare_arm_node/` | `roles/prepare_aarch64_node/` | Consistent arch naming |
| `roles/cleanup_image_build_manager/` | `roles/cleanup_build_artifacts/` | Shorter, action-focused |

---


#### Testing

```bash
# Standalone validation
cd src/image_build_manager
ansible-playbook playbooks/validate_image_build_config.yml

# Full flow
ansible-playbook image_build_manager.yml

# Tag-specific runs
ansible-playbook image_build_manager.yml --tags validate
ansible-playbook image_build_manager.yml --tags prepare
ansible-playbook image_build_manager.yml --tags build
ansible-playbook image_build_manager.yml --tags cleanup
```
