# Orchestrator — Design & Architecture


---

## 1. Overview

The **orchestrator** is a self-contained Ansible domain that manages the full post-discovery
lifecycle: OpenCHAMI deployment, OpenLDAP authentication, PXE boot orchestration, image
resolution, node provisioning, and service deployment (Kubernetes, Slurm,
storage, and LDAP). Telemetry is a separate domain and consumes published
Orchestrator inventory when configured.

The domain is fully decoupled from `src/playbooks/utils/` and `src/common/` shared utilities.
It owns its own library (modules + module_utils), validation framework, credential management,
and cleanup lifecycle.

OpenCHAMI and OpenLDAP have **independent lifecycle management** — each component has dedicated
precheck, prepare, deploy, cleanup, upgrade, and rollback playbooks that can be managed separately.

**Key Inputs**: `build_status.yml` (from image_build_manager), `pxe_mapping_file.csv` (from discovery).
**Key Outputs**: Boot Service configurations, Metadata Service data,
functional groups, and deployed OpenCHAMI services.

---

## 2. Directory Structure

```
src/orchestrator/
├── ansible.cfg                         # Domain config (fully local paths)
├── playbooks/
│   ├── orchestrator.yml                # Top-level thin routing wrapper
│   ├── ansible.cfg                     # Sub-playbook config
│   │
│   ├── precheck/                       # Functional-group and input validation
│   │   ├── ansible.cfg
│   │   ├── precheck_openchami.yml      # Validate inputs, params, boot images, config vars
│   │   └── precheck_openldap.yml       # Validate LDAP prerequisites (when enabled)
│   │
│   ├── prepare/                        # Credentials + configuration preparation
│   │   ├── ansible.cfg
│   │   ├── prepare_openchami.yml       # Credential management (prompt, encrypt, vault)
│   │   └── prepare_openldap.yml        # Optional component-level LDAP preparation
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
│   │   ├── pxeboot.yml                 # BMC inventory, reboot, node-registration verify
│   │   └── README.md
│   │
│   ├── cleanup/                        # Component teardown
│   │   ├── ansible.cfg
│   │   ├── cleanup_orchestrator.yml     # Canonical component selector
│   │   ├── cleanup_openchami.yml       # Compatibility wrapper: OpenCHAMI only
│   │   └── cleanup_openldap.yml        # Compatibility wrapper: OpenLDAP only
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
│   ├── configure_ochami/              # Boot/Metadata Service orchestration
│   ├── generate_inventories/          # Query SMD, generate inventories
│   ├── validate_provisioning/         # Post-provision verification
│   ├── passwordless_ssh/              # SSH key distribution
│   ├── k8s_config/                    # Kubernetes configuration
│   ├── slurm_config/                  # Slurm scheduler configuration
│   ├── mount_config/                  # Storage mount configuration
│   └── openldap/                      # OpenLDAP client configuration
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
│   ├── ORCHESTRATOR_MODERNIZATION.md   # Architecture & implementation plan
│   └── contracts/
│       ├── input-contract.md
│       └── output-contract.md
```

---

## 3. Domain Configuration

| Item | Value |
|------|-------|
| Main playbook | `playbooks/orchestrator.yml` |
| Input config | `orchestrator_config.yml` |
| Credential file | `$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME/orchestrator_credentials.yml` |
| Credential key | `$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME/.orchestrator_credentials_key` |
| Input directory | `$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME/` |
| Output directory | `$ORCHESTRATOR_DATA_PATH/output/$OMNIA_PROJECT_NAME/` |
| Ansible execution log | `/var/log/omnia/orchestrator/orchestrator.log` |
| Component lifecycle logs | `$ORCHESTRATOR_DATA_PATH/log/` |

`ORCHESTRATOR_DATA_PATH` defaults to `$OMNIA_DATA_PATH/orchestrator`.

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
  │conditional│   │ (opt-in) │   │ Rollback │
  │          │   │          │   │ (opt-in) │
  └──────────┘   └──────────┘   └──────────┘

Figure: orchestrator.yml tag-based execution flow
```

### Component Mapping (tag → playbooks)

| Tag | OpenCHAMI Playbook | OpenLDAP Playbook |
|-----|-------------------|-------------------|
| `precheck` | `precheck/precheck_openchami.yml` | `precheck/precheck_openldap.yml` |
| `validate` | Input validation role in `orchestrator.yml` | — |
| `credentials` | `credentials/orchestrator_credentials.yml` | — |
| `prepare` | `prepare/prepare_openchami.yml` + deploy/readiness playbooks | Deploy/readiness playbooks |
| `deploy` | `deploy/deploy_openchami.yml` + `validate/validate_openchami.yml` | `deploy/deploy_openldap.yml` + `validate/validate_openldap.yml` |
| `provision` | `provision/provision_preamble.yml` + `provision_*.yml` | — |
| `execute` | Provisioning playbooks + conditional PXE | — |
| `validate-deployment` | `validate/validate_preamble.yml` + `validate/validate_openchami.yml` | `validate/validate_openldap.yml` |
| `pxeboot` | `pxeboot/pxeboot.yml` | — |
| `cleanup` | `cleanup/cleanup_full.yml` | Canonical cleanup role with component selection and aggregate reporting |
| `cleanup_credentials` | `cleanup/cleanup_full.yml` with credentials-only selection | — |
| `upgrade` | `upgrade/upgrade_openchami.yml` | `upgrade/upgrade_openldap.yml` |
| `rollback` | `rollback/rollback_openchami.yml` | `rollback/rollback_openldap.yml` |

### Execution Steps by Tag

#### Default (no tag): full lifecycle

With no tag filter, Ansible selects every non-`never` route. Together these
form the full lifecycle: input validation, credentials, deployment and
readiness, provisioning, and conditional PXE boot when `enable_pxe_boot` is
`true`. Cleanup, credential cleanup, upgrade, and rollback remain excluded.

| Step | Phase | Play | Host | Description |
|------|-------|------|------|-------------|
| 0 | setup | Resolve orchestrator context | localhost | `orchestrator_setup` role — validate tags, resolve paths, load existing inputs and metadata, and create the OIM group |
| 0 | precheck/prepare/provision/execute | Generate functional groups | localhost | Persist functional groups from the current PXE mapping for validation and provisioning consumers |
| 1 | precheck | Validate input configuration | localhost | `validate_orchestrator_input` role — L1 schema + L2 logic |
| 2 | precheck | Validate parameters | localhost | `orchestrator_validations` role — mapping, software, images |
| 3 | precheck | Validate OIM timezone | oim (SSH) | Timezone drift detection |
| 4 | precheck | Validate boot images | oim (SSH) | Require kernel, initrd, and rootfs paths, then verify each Boot Service URL with HTTP `HEAD` |
| 5 | precheck | Validate OpenCHAMI config | localhost | Assert domain_name, admin_nic_ip, input files |
| 6 | precheck | Validate OpenLDAP prereqs | localhost | Validate the domain and warn if the credential file is absent (when enabled) |
| 7 | prepare | Credential management | localhost | `orchestrator_credentials` role — prompt, encrypt, vault; PowerScale CSI credentials are requested only when explicitly enabled |
| 8 | deploy | Prepare OpenLDAP | oim (SSH) | The deployment role loads credentials and creates directories, TLS certificates, and configuration before starting the container |
| 9 | deploy | Configure S3 + Deploy OpenCHAMI | oim (SSH) | `deploy_openchami` role — OpenCHAMI 0.2.0 Fabrica services |
| 10 | deploy | Deploy OpenLDAP | oim (SSH) | `deploy_openldap` role — OpenLDAP container (when enabled) |
| 11 | deploy | Validate OpenCHAMI readiness | oim (SSH) | Gate: aggregate target, SMD, Boot Service, Metadata Service, TokenSmith, and certificate health |
| 12 | deploy | Validate OpenLDAP readiness | oim (SSH) | Gate: LDAP container health (when enabled) |
| 13 | provision | SSH preamble + auth | localhost + oim | `passwordless_ssh` + `openchami_auth` |
| 14 | provision | Provision Kubernetes | oim (SSH) | Register K8s FGs, publish Boot/Metadata Service data, apply K8s bolt-ons |
| 15 | provision | Provision Slurm | oim (SSH) | Register Slurm and login FGs, publish Boot/Metadata Service data, apply Slurm bolt-ons |
| 16 | provision | Provision OS-only | oim (SSH) | Register OS FGs and publish Boot/Metadata Service data |
| 17 | provision | Provision custom | oim (SSH) | Register custom FGs and publish Boot/Metadata Service data |
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
| `common/library/module_utils/input_validation/schema/*.json` | `plugins/module_utils/orchestrator_validation/schema/*.json` | Orchestrator-specific schemas |
| `common/vars/common_vars.yml` | `vars/common_vars.yml` | Shared constants |
| `common/vars/openchami_vars.yml` | `vars/openchami_vars.yml` | OpenCHAMI auth constants |
| *(new)* | `plugins/modules/validate_orchestrator_config.py` | Domain-specific validation module (L1+L2) |
| *(new)* | `plugins/module_utils/orchestrator_validation/core/validation_engine.py` | L1/L2 validation dispatch |
| *(new)* | `plugins/module_utils/orchestrator_validation/validators/` | Per-input L2 validation logic |

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
image_build_type: "image-builder"
s3_configurations:
  endpoint_url: "https://10.20.0.1:9000"
  bucket: "boot-images"
functional_group_images:
  - x86_64:
      - functional_group: "slurm_control_node_rhel_10_0_x86_64"
        kernel: "boot-images/efi-images/slurm_control_node_rhel_10_0_x86_64/example-imgbld/vmlinuz-<kernel-version>"
        initrd: "boot-images/efi-images/slurm_control_node_rhel_10_0_x86_64/example-imgbld/initramfs-<kernel-version>.img"
        image: "boot-images/slurm_control_node_rhel_10_0_x86_64/example-imgbld/<rootfs-filename>"
```

The Orchestrator-owned reference copy is
`src/orchestrator/samples/image_build_manager_output/build_status.yml`.

### 6.2 pxe_mapping_file.csv (Input from discovery)

**Producer**: discovery domain
**Consumer**: orchestrator (orchestrator_functional_groups, orchestrator_validations)

### 6.3 Orchestrator Outputs

**Location**: `$ORCHESTRATOR_DATA_PATH/output/$OMNIA_PROJECT_NAME/`

- `.data/functional_groups_config.yml` — Generated functional groups
- `orchestrator_state.yml` — Support flags for standalone runs
- Boot Service configurations
- Metadata Service cluster, group, and node data used to render cloud-init
- `$OMNIA_DATA_PATH/hosts` — Ansible inventory

---

## 7. Credential Management

### 7.1 Architecture

The `orchestrator_credentials` role manages vault-encrypted credential files
for Orchestrator services such as provisioning, Slurm, OpenLDAP, and
PowerScale CSI.

### 7.2 Credential Files

| File | Vault Key | Description |
|------|-----------|-------------|
| `orchestrator_credentials.yml` | `.orchestrator_credentials_key` | Provision, BMC, Slurm, LDAP, and CSI credentials |

### 7.3 Credential Lifecycle

```
1. Template creates: orchestrator_credentials.yml (plaintext with defaults)
2. Prompt fills:     Interactive prompts for empty mandatory fields
3. Vault encrypts:   ansible-vault encrypt with .orchestrator_credentials_key
4. Runtime reads:    Ansible decrypts at playbook execution time
5. Cleanup removes:  cleanup role deletes cred + key files by default;
                     cleanup_credentials=false preserves them
```

### 7.4 PowerScale CSI Feature Gate

`service_k8s_cluster[].enable_powerscale_csi` is the only Orchestrator runtime
switch for PowerScale CSI. The deployed Kubernetes entry is the entry with
`deployment: true`; its CSI secret and values paths are used when the switch is
enabled. The default is `false`.

When enabled, credential collection requires `csi_username` and
`csi_password`, the Kubernetes configuration role stages the three CSI Git
artifacts published in `repo_status.yml`, and the first control-plane
cloud-init configuration installs the driver. When disabled, each of those
steps is skipped. Catalog group membership does not activate CSI.

---

## 8. Input Validation Design

### 8.1 Pattern

Follows the modular `image_build_manager` validation pattern:
- **Domain-specific module**: `validate_orchestrator_config.py` — single Ansible module
- **Validation engine**: `core/validation_engine.py` — L1 validation and L2 routing
- **Per-input validators**: `validators/` — domain-specific L2 and cross-file logic
- **Domain-specific schemas**: Orchestrator-owned input and credential schemas

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
| *(none)* | Default | Full lifecycle, including PXE when `enable_pxe_boot` is `true` |
| `precheck` | Validation | Generate functional groups, then validate inputs, parameters, and boot images |
| `validate` | Validation | Validate project input files only; do not contact deployed services |
| `credentials` | Credentials | Collect or reuse the encrypted Orchestrator credentials |
| `prepare` | Preparation | Generate functional groups, collect credentials, deploy services, and validate readiness |
| `deploy` | Deployment | Deploy OpenCHAMI + OpenLDAP containers, validate readiness gates |
| `provision` | Provisioning | SSH preamble, provision K8s/Slurm/OS/custom, validate provisioning |
| `execute` | Execution | Provision nodes, validate provisioning, and run PXE when enabled |
| `validate-deployment` | Validation | Load deployed-state prerequisites and validate OpenCHAMI/OpenLDAP readiness |
| `pxeboot` | PXE | Run the PXE and node-registration flow independently |
| `cleanup` | Opt-in | Run selected component cleanups, report every result, then fail if any component is incomplete |
| `cleanup_credentials` | Opt-in | Remove only the encrypted credential file and vault key |
| `upgrade` | Opt-in | In-place upgrade of OpenCHAMI + OpenLDAP |
| `rollback` | Opt-in | Revert OpenCHAMI + OpenLDAP to previous state from backup |

### 9.2 Invalid Combinations

The canonical list is `invalid_tag_combinations` in
`roles/orchestrator_setup/vars/main.yml`. It prevents:

- `cleanup` from being combined with normal lifecycle, upgrade, or rollback
  tags;
- `cleanup_credentials` from being combined with normal lifecycle, upgrade,
  or rollback tags; and
- `upgrade` from being combined with `precheck`, `validate`,
  `validate-deployment`, `credentials`, `prepare`, `deploy`, `provision`,
  `execute`, or `rollback`.

`cleanup,cleanup_credentials` is the intentional exception and requests full
component cleanup plus credential removal.

### 9.3 Credential Skipping

Credential prompting is skipped for `precheck`, `validate`,
`validate-deployment`, `cleanup`, and `cleanup_credentials` tags.

The always-run setup role resolves context for every flow. When the runtime
project input directory is absent, it initializes that project from the source
input templates, matching the other Omnia domain setup roles. It never
overwrites an existing project directory. Only `prepare`, `deploy`,
`provision`, `execute`, `pxeboot`, `upgrade`, and the default lifecycle refresh
`orchestrator_state.yml`. Precheck creates the output `.data` directory for
`functional_groups_config.yml` but does not create the state file. Validation,
credentials, cleanup, deployment-health checks, and credential-only cleanup do
not create or rewrite those runtime output artifacts.

### 9.4 Opt-In Tags

`cleanup`, `cleanup_credentials`, `upgrade`, and `rollback` use the `never` tag
to prevent accidental execution during the default flow. The `pxeboot` tag can
be selected independently and also runs during the default/`execute` flow when
`enable_pxe_boot` is `true`.

---

## 10. Naming Convention

| Item | Convention | Example |
|------|------------|--------|
| Roles | `<domain>_<function>` | `orchestrator_setup`, `orchestrator_credentials` |
| Validation role | `validate_<domain>_input` | `validate_orchestrator_input` |
| Validation module | `validate_<domain>_config` | `validate_orchestrator_config` |
| Validation engine | `validation_engine.py` | `orchestrator_validation/core/validation_engine.py` |
| L2 validator | `<input>_validator.py` | `orchestrator_config_validator.py` |
| Schema dir | `<domain>_validation/schema/` | `orchestrator_validation/schema/` |
| Credential file | `<domain>_credentials.yml` | `orchestrator_credentials.yml` |
| Phase directories | `<phase>/` | `precheck/`, `prepare/`, `deploy/`, `cleanup/` |
| Component playbooks | `<phase>_<component>.yml` | `precheck_openchami.yml`, `cleanup_openldap.yml` |
| Ansible log path | `/var/log/omnia/<domain>/<domain>.log` | `/var/log/omnia/orchestrator/orchestrator.log` |

---

## 11. Backward Compatibility

- No breaking changes for users who don't use the new domain structure.
- `orchestrator_config.yml` is **required** — no legacy fallback.
- The top-level `orchestrator.yml` is the canonical entry point. A phase
  sub-playbook may be run directly only after satisfying the prerequisites
  documented by that playbook.
- All `../playbooks/utils/` references eliminated.
- Each validate playbook includes its own `orchestrator_setup` always-tagged play for standalone use.
