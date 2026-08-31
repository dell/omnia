# Orchestrator — Design & Architecture


---

## 1. Overview

The **orchestrator** is a self-contained Ansible domain that manages the full post-discovery
lifecycle: OpenCHAMI deployment, OpenLDAP authentication, PXE boot orchestration, image
resolution, node provisioning, and service deployment (K8s, Slurm, telemetry, storage, LDAP).

The domain is fully decoupled from `src/playbooks/utils/` and `src/common/` shared utilities.
It owns its own library (modules + module_utils), validation framework, credential management,
and cleanup lifecycle.

OpenCHAMI and OpenLDAP have **independent lifecycle management** — each component has dedicated
precheck, prepare, deploy, cleanup, upgrade, and rollback playbooks that can be managed separately.

**Key Inputs**: `build_status.yml` (from image_build_manager), `pxe_mapping_file.csv` (from discovery).
**Key Outputs**: BSS/cloud-init boot configurations, functional groups, deployed OpenCHAMI services.

---

## 2. Directory Structure

```
src/orchestrator/
├── ansible.cfg                         # Domain config (fully local paths)
├── playbooks/
│   ├── orchestrator.yml                # Top-level thin routing wrapper
│   ├── ansible.cfg                     # Sub-playbook config
│   │
│   ├── precheck/                       # Read-only input validation
│   │   ├── ansible.cfg
│   │   ├── precheck_openchami.yml      # Validate inputs, params, boot images, config vars
│   │   └── precheck_openldap.yml       # Validate LDAP prerequisites (when enabled)
│   │
│   ├── prepare/                        # Credentials + configuration preparation
│   │   ├── ansible.cfg
│   │   ├── prepare_openchami.yml       # Credential management (prompt, encrypt, vault)
│   │   └── prepare_openldap.yml        # LDAP dirs, TLS certs, config templating
│   │
│   ├── deploy/                         # Service deployment
│   │   ├── ansible.cfg
│   │   ├── deploy_openchami.yml        # S3 access + OpenCHAMI containers on OIM
│   │   └── deploy_openldap.yml         # OpenLDAP container on OIM (when enabled)
│   │
│   ├── validate/                       # Readiness gates + post-provision checks
│   │   ├── ansible.cfg
│   │   ├── validate_openchami.yml      # Input validation + OpenCHAMI health checks
│   │   ├── validate_openldap.yml       # OpenLDAP container health (when enabled)
│   │   └── validate_provisioning.yml   # Post-provision inventory gen + verification
│   │
│   ├── provision/                      # Node provisioning (category-scoped)
│   │   ├── ansible.cfg
│   │   ├── provision_preamble.yml      # SSH key distribution + OpenCHAMI auth
│   │   ├── provision_kubernetes.yml    # K8s FGs + bolt-ons
│   │   ├── provision_slurm.yml         # Slurm+Login FGs + bolt-ons
│   │   ├── provision_os.yml            # OS-only FGs (minimal)
│   │   └── provision_custom.yml        # User-defined FGs (catch-all)
│   │
│   ├── pxeboot/                        # PXE boot on iDRAC nodes
│   │   ├── ansible.cfg
│   │   ├── pxeboot.yml                 # BMC inventory, reboot, phone-home verify
│   │   └── README.md
│   │
│   ├── cleanup/                        # Component teardown
│   │   ├── ansible.cfg
│   │   ├── cleanup_openchami.yml       # Stop services, remove containers/config/artifacts
│   │   └── cleanup_openldap.yml        # Stop container, remove Quadlet/data
│   │
│   ├── upgrade/                        # In-place upgrade
│   │   ├── ansible.cfg
│   │   ├── upgrade_openchami.yml       # Version detect, backup, migrate, verify
│   │   └── upgrade_openldap.yml        # Fedora→Wolfi container migration
│   │
│   ├── rollback/                       # Revert to previous state
│   │   ├── ansible.cfg
│   │   ├── rollback_openchami.yml      # Backup restore, restart, verify
│   │   └── rollback_openldap.yml       # Wolfi→Fedora container rollback
│   │
│   └── credentials/                    # Standalone credential management
│       ├── ansible.cfg
│       └── orchestrator_credentials.yml
│
├── roles/
│   ├── orchestrator_setup/             # Upgrade guard, input dir, OIM group, vars
│   ├── orchestrator_functional_groups/ # Generate functional_groups_config.yml
│   ├── validate_orchestrator_input/    # L1 schema + L2 logic validation
│   ├── orchestrator_credentials/       # Credential prompt, encrypt, vault
│   ├── orchestrator_common/            # Shared: openchami_auth, S3, decrypt helpers
│   ├── orchestrator_validations/       # Runtime L2/L3 pre-checks
│   ├── deploy_openchami/              # OpenCHAMI container deployment
│   ├── deploy_openldap/               # OpenLDAP container deployment
│   ├── validate_openchami/            # OpenCHAMI health checks
│   ├── configure_ochami/              # BSS, cloud-init, node orchestration
│   ├── generate_inventories/          # Query SMD, generate inventories
│   ├── validate_provisioning/         # Post-provision verification
│   ├── passwordless_ssh/              # SSH key distribution
│   ├── k8s_config/                    # Kubernetes configuration
│   ├── slurm_config/                  # Slurm scheduler configuration
│   ├── mount_config/                  # Storage mount configuration
│   └── telemetry/                     # Telemetry deployment
│
├── plugins/
│   ├── modules/                        # Domain-specific Python modules
│   ├── module_utils/                   # Validation schemas + utils
│   └── callback/                       # Stdout callback
│
├── vars/
│   ├── common_vars.yml                 # Shared constants (permissions, retries)
│   └── openchami_vars.yml              # OpenCHAMI auth/cert constants
│
├── input/                              # Default input templates
│   ├── orchestrator_config.yml
│   ├── network_spec.yml
│   ├── pxe_mapping_file.csv
│   └── ...
│
├── docs/
│   ├── ORCHESTRATOR_DESIGN.md          # This file
│   └── ORCHESTRATOR_MODERNIZATION.md   # Architecture & implementation plan
│
├── INPUT_CONTRACT.md
└── OUTPUT_CONTRACT.md
```

---

## 3. Domain Configuration

| Item | Value |
|------|-------|
| Main playbook | `playbooks/orchestrator.yml` |
| Input config | `orchestrator_config.yml` |
| Credential file | `omnia_config_credentials.yml` |
| Credential key | `.omnia_config_credentials_key` |
| Input subdir | `input/project_default/orchestrator/` |
| Output subdir | `output/project_default/orchestrator/` |
| Log path | `/opt/omnia/log/core/orchestrator/orchestrator.log` |

### Ansible Config (ansible.cfg)

```ini
roles_path = roles
library = plugins/modules
module_utils = plugins/module_utils
callback_plugins = plugins/callback
```

All paths are fully local — **zero references to `../common/`**.

---

## 4. End-to-End Execution Flow

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR — EXECUTION FLOW                            │
└──────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
  │  Setup   │   │ Precheck │   │ Prepare  │   │  Deploy  │   │ Provision│
  │ (always) │──>│ (read-   │──>│ (creds + │──>│ (services│──>│  (nodes) │
  │          │   │  only)   │   │  config) │   │  + gates)│   │          │
  └─────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
       │              │              │              │              │
       │ Upgrade      │              │              │              │
       │ guard,       │ L1 schema    │ Credential   │ S3 access    │ SSH keys
       │ project      │ L2 logic     │ prompt/      │ OpenCHAMI    │ OpenCHAMI auth
       │ dirs,        │ params       │ encrypt      │ containers   │ K8s/Slurm/
       │ vars,        │ boot images  │ OpenLDAP     │ OpenLDAP     │ OS/custom
       │ OIM group    │ OIM timezone │ dirs/TLS     │ container    │ provisioning
       │ FG gen       │ LDAP prereqs │              │ Validate     │ Inventories
       │              │              │              │ readiness    │ Validation
       └──────────────┴──────────────┴──────────────┴──────────────┘

  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ PXE Boot │   │ Cleanup  │   │ Upgrade/ │
  │ (opt-in) │   │ (opt-in) │   │ Rollback │
  │          │   │          │   │ (opt-in) │
  └──────────┘   └──────────┘   └──────────┘

Figure: orchestrator.yml tag-based execution flow
```

### Component Mapping (tag → playbooks)

| Tag | OpenCHAMI Playbook | OpenLDAP Playbook |
|-----|-------------------|-------------------|
| `precheck` | `precheck/precheck_openchami.yml` | `precheck/precheck_openldap.yml` |
| `prepare` | `prepare/prepare_openchami.yml` | `prepare/prepare_openldap.yml` |
| `deploy` | `deploy/deploy_openchami.yml` + `validate/validate_openchami.yml` | `deploy/deploy_openldap.yml` + `validate/validate_openldap.yml` |
| `provision` | `provision/provision_preamble.yml` + `provision_*.yml` | — |
| `validate` | `validate/validate_openchami.yml` | `validate/validate_openldap.yml` + `validate/validate_provisioning.yml` |
| `pxeboot` | `pxeboot/pxeboot.yml` | — |
| `cleanup` | `cleanup/cleanup_openchami.yml` | `cleanup/cleanup_openldap.yml` |
| `upgrade` | `upgrade/upgrade_openchami.yml` | `upgrade/upgrade_openldap.yml` |
| `rollback` | `rollback/rollback_openchami.yml` | `rollback/rollback_openldap.yml` |

### Execution Steps by Tag

#### Default (no tag): precheck + prepare + deploy + provision

| Step | Phase | Play | Host | Description |
|------|-------|------|------|-------------|
| 0 | setup | Setup orchestrator environment | localhost | `orchestrator_setup` role — upgrade guard, dirs, metadata, OIM group |
| 0 | setup | Generate functional groups | localhost | `orchestrator_functional_groups` role — generate from pxe_mapping |
| 1 | precheck | Validate input configuration | localhost | `validate_orchestrator_input` role — L1 schema + L2 logic |
| 2 | precheck | Validate parameters | localhost | `orchestrator_validations` role — mapping, software, images |
| 3 | precheck | Validate OIM timezone | oim (SSH) | Timezone drift detection |
| 4 | precheck | Validate boot images | oim (SSH) | S3 image availability per FG |
| 5 | precheck | Validate OpenCHAMI config | localhost | Assert domain_name, admin_nic_ip, input files |
| 6 | precheck | Validate OpenLDAP prereqs | localhost | Assert LDAP credentials, domain (when enabled) |
| 7 | prepare | Credential management | localhost | `orchestrator_credentials` role — prompt, encrypt, vault |
| 8 | prepare | Prepare OpenLDAP | oim (SSH) | Load creds, create dirs, TLS certs, template configs |
| 9 | deploy | Configure S3 + Deploy OpenCHAMI | oim (SSH) | `deploy_openchami` role — OpenCHAMI containers |
| 10 | deploy | Deploy OpenLDAP | oim (SSH) | `deploy_openldap` role — OpenLDAP container (when enabled) |
| 11 | deploy | Validate OpenCHAMI readiness | oim (SSH) | Gate: SMD, BSS, cloud-init-server health |
| 12 | deploy | Validate OpenLDAP readiness | oim (SSH) | Gate: LDAP container health (when enabled) |
| 13 | provision | SSH preamble + auth | localhost + oim | `passwordless_ssh` + `openchami_auth` |
| 14 | provision | Provision Kubernetes | oim (SSH) | Register K8s FGs, BSS/cloud-init, k8s bolt-ons |
| 15 | provision | Provision Slurm | oim (SSH) | Register Slurm+Login FGs, BSS/cloud-init, slurm bolt-ons |
| 16 | provision | Provision OS-only | oim (SSH) | Register OS FGs, BSS/cloud-init, minimal config |
| 17 | provision | Provision custom | oim (SSH) | Register custom FGs, BSS/cloud-init, no bolt-ons |
| 18 | provision | Validate provisioning | oim (SSH) | Generate inventories, verify SMD state |

---

## 5. Self-Containment — Zero External Dependencies

The orchestrator domain has **zero references to `../common/`** in `ansible.cfg`.
All modules, module_utils, callback plugins, and roles are local.

### 5.1 What Was Copied Locally

| Source (common) | Local Copy | Why |
|-----------------|-----------|-----|
| `common/callback_plugins/omnia_default.py` | `plugins/callback/omnia_default.py` | Stdout callback — needed by ansible.cfg |
| `common/library/modules/generate_functional_groups.py` | `plugins/modules/generate_functional_groups.py` | Used by `orchestrator_functional_groups` role |
| `common/library/modules/generate_xname_in_mapping_file.py` | `plugins/modules/generate_xname_in_mapping_file.py` | Used by `orchestrator_validations` role |
| `common/library/modules/slurm_conf.py` | `plugins/modules/slurm_conf.py` | Used by `slurm_config` role |
| `common/library/modules/fetch_credential_rule.py` | `plugins/modules/fetch_credential_rule.py` | Used by credential prompting |
| `common/library/modules/validate_credentials.py` | `plugins/modules/validate_credentials.py` | Used by credential validation |
| `common/library/modules/generate_argon2_password.py` | `plugins/modules/generate_argon2_password.py` | Argon2 password hash generation |
| `common/library/modules/fetch_telemetry_status.py` | `plugins/modules/fetch_telemetry_status.py` | Telemetry status check |
| `common/library/module_utils/input_validation/schema/*.json` | `plugins/module_utils/orchestrator_validation/schema/*.json` | Orchestrator-specific schemas |
| `common/vars/common_vars.yml` | `vars/common_vars.yml` | Shared constants |
| `common/vars/openchami_vars.yml` | `vars/openchami_vars.yml` | OpenCHAMI auth constants |
| *(new)* | `plugins/modules/validate_orchestrator_config.py` | Domain-specific validation module (L1+L2) |
| *(new)* | `plugins/module_utils/orchestrator_validation/orchestrator_validation_flow.py` | Orchestrator L2 validation logic |

### 5.2 Verification

```bash
# Confirm zero external references
grep -c '\.\./common' src/orchestrator/ansible.cfg             # expect: 0
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
- `orchestrator_state.yml` — Support flags for standalone runs
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

### 9.1 Supported Tags

| Tag | Type | Description |
|-----|------|-------------|
| *(none)* | Default | Full flow: precheck + prepare + deploy + provision |
| `precheck` | Read-only | Validate inputs, parameters, boot images (no system changes) |
| `prepare` | Preparation | Credential management, FG generation, OpenLDAP config prep |
| `deploy` | Deployment | Deploy OpenCHAMI + OpenLDAP containers, validate readiness gates |
| `provision` | Provisioning | SSH preamble, provision K8s/Slurm/OS/custom, validate provisioning |
| `validate` | Validation | Validate OpenCHAMI + OpenLDAP readiness + provisioning state |
| `pxeboot` | Opt-in | PXE boot on iDRAC nodes (physical servers only) |
| `cleanup` | Opt-in | Remove OpenCHAMI + OpenLDAP services, containers, artifacts |
| `upgrade` | Opt-in | In-place upgrade of OpenCHAMI + OpenLDAP |
| `rollback` | Opt-in | Revert OpenCHAMI + OpenLDAP to previous state from backup |

### 9.2 Invalid Combinations

`precheck+cleanup`, `prepare+cleanup`, `deploy+cleanup`, `provision+cleanup`,
`pxeboot+cleanup`, `precheck+upgrade`, `prepare+upgrade`, `deploy+upgrade`,
`provision+upgrade`, `cleanup+upgrade`, `upgrade+rollback`.

### 9.3 Credential Skipping

Credential prompting is skipped for `precheck`, `cleanup`, and `validate` tags.

### 9.4 Opt-In Tags

`pxeboot`, `cleanup`, `upgrade`, and `rollback` use the `never` tag to prevent
accidental execution during the default flow. They must be explicitly requested.

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
| Phase directories | `<phase>/` | `precheck/`, `prepare/`, `deploy/`, `cleanup/` |
| Component playbooks | `<phase>_<component>.yml` | `precheck_openchami.yml`, `cleanup_openldap.yml` |
| Log path | `/opt/omnia/log/core/<domain>/` | `/opt/omnia/log/core/orchestrator/` |

---

## 11. Backward Compatibility

- No breaking changes for users who don't use the new domain structure.
- `orchestrator_config.yml` is **required** — no legacy fallback.
- Sub-playbooks work independently with standalone setup guards.
- All `../playbooks/utils/` references eliminated.
- Each validate playbook includes its own `orchestrator_setup` always-tagged play for standalone use.
