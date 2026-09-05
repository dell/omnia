# Orchestrator Modernization — Architecture & Implementation Plan

**Author:** Dell Omnia Engineering  
**Date:** August 2026  
**Status:** Implemented — Phases 1-6 Complete  
**Scope:** `src/orchestrator/`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Target Architecture](#3-target-architecture)
4. [Implemented Directory Structure](#4-implemented-directory-structure)
5. [Component Disposition](#5-component-disposition)
6. [Workflow Definitions](#6-workflow-definitions)
7. [Functional-Group-Driven Provisioning](#7-functional-group-driven-provisioning)
8. [Workflow Diagram](#8-workflow-diagram)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Risks and Mitigations](#10-risks-and-mitigations)

---

## 1. Executive Summary

The orchestrator modernization replaces the original monolithic `orchestrator.yml`
(247 lines, 16 plays, mixed concerns) with a clean, composable, tag-driven
workflow aligned to OpenCHAMI-based provisioning.

**Key changes (implemented):**

- Split monolithic entrypoint into component-specific playbooks per lifecycle phase
- Separate OpenCHAMI and OpenLDAP lifecycle management into independent playbooks
- Introduce 9 supported tags: `precheck`, `prepare`, `deploy`, `provision`,
  `validate`, `pxeboot`, `cleanup`, `upgrade`, `rollback`
- `orchestrator.yml` is now a thin routing wrapper using `import_playbook`
- Each component (OpenCHAMI, OpenLDAP) has dedicated precheck, prepare, deploy,
  cleanup, upgrade, and rollback playbooks
- Eliminate all hardcoded functional-group names from provisioning logic
- Treat functional groups as data, not code-level selectors
- Introduce post-provisioning validation
- Make bolt-on services (k8s, slurm, openldap, telemetry, mounts) fully
  data-driven and optional

**Boundaries (out of scope):**

- Discovery workflow (hardware, BMC, PXE mapping generation)
- Image build workflow (OS install, package config, image creation)
- Both produce artifacts consumed by the orchestrator as inputs

---

## 2. Current State Analysis

### 2.1 Previous Entrypoint (`orchestrator.yml` — before modernization)

The previous entrypoint was a single 247-line playbook containing 16 plays that
executed sequentially. It mixed concerns across validation, deployment,
provisioning, DNS, bolt-on configuration, and telemetry:

```
Step 0:  orchestrator_setup          (localhost)
Step 1:  validate_orchestrator_input (localhost)
Step 2:  orchestrator_credentials    (localhost)
Step 3:  orchestrator_functional_groups (localhost)
Step 4:  orchestrator_validations    (localhost)
Step 5:  validate OIM timezone       (oim)
Step 6:  passwordless_ssh            (localhost)
Step 7:  passwordless_ssh            (oim)
Step 8:  configure_s3_access         (oim)
Step 9:  deploy_openchami            (oim)
Step 10: validate openldap/images    (oim)
Step 11: openchami_auth              (oim)
Step 12: DNS configuration           (localhost)
Step 13: DNS configuration           (oim)
Step 14: orchestration_mapping_nodes (oim) — SELinux, SMD discovery, BSS,
         cloud-init, inventory generation, hostnames
Step 15: mount_config + k8s_config + slurm_config + openldap +
         configure_ochami (oim)
```

### 2.2 Previous Monolithic Playbooks

The previous structure used single-file playbooks that combined both OpenCHAMI
and OpenLDAP operations:

| Old Playbook | Issues |
|-------------|--------|
| `prepare_orchestrator.yml` | Mixed OpenCHAMI credentials + OpenLDAP prep in one file |
| `validate_orchestrator.yml` | Combined OpenCHAMI + OpenLDAP validation |
| `cleanup_orchestrator.yml` | Combined OpenCHAMI + OpenLDAP teardown |
| `upgrade_orchestrator.yml` | Placeholder — no real implementation |
| `rollback_orchestrator.yml` | Placeholder — no real implementation |

### 2.3 Existing Roles (14)

| Role | Responsibility | Status |
|------|---------------|--------|
| `orchestrator_setup` | Upgrade guard, project dirs, vars loading, OIM group | Retained + enhanced |
| `validate_orchestrator_input` | L1 schema + L2 logic validation | Retained |
| `orchestrator_credentials` | Credential prompt, encrypt, vault | Retained |
| `orchestrator_functional_groups` | Generate FG YAML from PXE CSV | Refactored |
| `orchestrator_validations` | Software config, mapping file, image, telemetry | Patched (conditional creds) |
| `orchestrator_common` | openchami_auth, configure_s3_access, kube_vip check | Retained |
| `passwordless_ssh` | Build host lists, configure OIM SSH | Retained |
| `deploy_openchami` | Deploy OpenCHAMI containers | Retained |
| `configure_ochami` | SMD groups, BSS boot, cloud-init, inventories | Retained (to be split in Phase 3) |
| `k8s_config` | K8s NFS share, manifests, packages | Refactored |
| `slurm_config` | Slurm config files on NFS | Refactored |
| `mount_config` | Cloud-init mounts, swap, NFS bolt-ons | Refactored |
| `openldap` | LDAP domain, server-ip, connection type | Retained |
| `telemetry` | iDRAC, LDMS, PowerScale, UFM, VAST, OME | Retained |

### 2.4 Data Flow

```
orchestrator_config.yml ──┐
network_spec.yml ─────────┤
pxe_mapping_file.csv ─────┼──► orchestrator_setup ──► validate ──► functional_groups
omnia_config.yml ──────────┤
software_config.json ──────┘
                               │
                               ▼
                          deploy_openchami ──► configure_ochami
                               │                    │
                               │           ┌────────┴────────┐
                               ▼           ▼                 ▼
                          SMD discovery    BSS boot       cloud-init
                               │           params           config
                               ▼
                     ┌─────────┼─────────┐
                     ▼         ▼         ▼
                mount_config  k8s_config  slurm_config + openldap + telemetry
```

---

## 3. Target Architecture

### 3.1 Design Principles

1. **Component independence** — OpenCHAMI and OpenLDAP lifecycle management is
   handled by separate playbooks. Each can be managed independently.

2. **Tag-driven routing** — `orchestrator.yml` is a thin wrapper. Tags control
   which phase runs. Each tag maps to a pair of component playbooks.

3. **Single Responsibility** — Each playbook owns exactly one lifecycle stage
   for one component.

4. **Functional groups are data, not code** — Adding a new FG requires zero
   code changes. The orchestrator reads FGs from the PXE mapping CSV and
   processes them generically.

5. **Generic provisioning pipeline** — All nodes follow the same path:
   PXE Mapping → Functional Groups → Image Resolution → SMD Registration →
   BSS/Cloud-Init → Validation.

6. **Bolt-on services are optional and data-driven** — k8s, slurm, openldap,
   telemetry configuration is gated by support flags, not hardcoded FG checks.

7. **Idempotency** — Every playbook must be safe to run multiple times.

### 3.2 Implemented Playbooks (Component-Specific)

| Phase | OpenCHAMI Playbook | OpenLDAP Playbook | Purpose |
|-------|-------------------|-------------------|---------|
| precheck | `precheck_openchami.yml` | `precheck_openldap.yml` | Read-only input validation |
| prepare | `prepare_openchami.yml` | `prepare_openldap.yml` | Credentials + configuration prep |
| deploy | `deploy_openchami.yml` | `deploy_openldap.yml` | Deploy services on OIM |
| validate | `validate_openchami.yml` | `validate_openldap.yml` | Readiness gate checks |
| cleanup | `cleanup_openchami.yml` | `cleanup_openldap.yml` | Service teardown + artifact removal |
| upgrade | `upgrade_openchami.yml` | `upgrade_openldap.yml` | In-place version upgrade |
| rollback | `rollback_openchami.yml` | `rollback_openldap.yml` | Revert to previous state |

Additional playbooks (not component-split):

| Playbook | Purpose |
|----------|---------|
| `provision_preamble.yml` | SSH key distribution + OpenCHAMI auth (runs once) |
| `provision_kubernetes.yml` | Provision K8s FGs + bolt-ons |
| `provision_slurm.yml` | Provision Slurm+Login FGs + bolt-ons |
| `provision_os.yml` | Provision OS-only FGs (minimal) |
| `provision_custom.yml` | Provision user-defined FGs (catch-all) |
| `validate_provisioning.yml` | Post-provision inventory gen + verification |
| `pxeboot.yml` | PXE boot on iDRAC nodes |

### 3.3 Orchestrator Entrypoint (Implemented)

The `orchestrator.yml` is now a thin routing wrapper (~290 lines including
comments) that imports component playbooks based on tags:

```yaml
---
# orchestrator.yml — Thin routing wrapper

# SHARED: Always runs — setup + FG generation
- name: Setup orchestrator environment
  hosts: localhost
  tags: always
  roles:
    - role: orchestrator_setup

- name: Generate functional groups configuration
  hosts: localhost
  tags: always
  roles:
    - orchestrator_functional_groups

# PRECHECK: Read-only validation
- import_playbook: precheck/precheck_openchami.yml    # tags: [precheck]
- import_playbook: precheck/precheck_openldap.yml     # tags: [precheck]

# PREPARE: Credentials + configuration
- import_playbook: prepare/prepare_openchami.yml      # tags: [prepare]
- import_playbook: prepare/prepare_openldap.yml       # tags: [prepare]

# DEPLOY: Services + readiness gates
- import_playbook: deploy/deploy_openchami.yml        # tags: [deploy]
- import_playbook: deploy/deploy_openldap.yml         # tags: [deploy]
- import_playbook: validate/validate_openchami.yml    # tags: [deploy, validate]
- import_playbook: validate/validate_openldap.yml     # tags: [deploy, validate]

# PROVISION: SSH preamble + category provisioning + validation
- import_playbook: provision/provision_preamble.yml   # tags: [provision]
- import_playbook: provision/provision_kubernetes.yml  # tags: [provision]
- import_playbook: provision/provision_slurm.yml       # tags: [provision]
- import_playbook: provision/provision_os.yml          # tags: [provision]
- import_playbook: provision/provision_custom.yml      # tags: [provision]
- import_playbook: validate/validate_provisioning.yml  # tags: [provision, validate]

# OPT-IN: PXE boot, cleanup, upgrade, rollback (all use never + explicit tag)
- import_playbook: pxeboot/pxeboot.yml                # tags: [never, pxeboot]
- import_playbook: cleanup/cleanup_openchami.yml       # tags: [never, cleanup]
- import_playbook: cleanup/cleanup_openldap.yml        # tags: [never, cleanup]
- import_playbook: upgrade/upgrade_openchami.yml       # tags: [never, upgrade]
- import_playbook: upgrade/upgrade_openldap.yml        # tags: [never, upgrade]
- import_playbook: rollback/rollback_openchami.yml     # tags: [never, rollback]
- import_playbook: rollback/rollback_openldap.yml      # tags: [never, rollback]
```

---

## 4. Implemented Directory Structure

```
src/orchestrator/
├── ansible.cfg                          # Domain config (fully local paths)
├── playbooks/
│   ├── orchestrator.yml                 # Thin tag-routing wrapper
│   ├── ansible.cfg                      # Sub-playbook config
│   │
│   ├── precheck/                        # Read-only input validation
│   │   ├── ansible.cfg
│   │   ├── precheck_openchami.yml       # L1/L2 validation, params, images, config vars
│   │   └── precheck_openldap.yml        # LDAP prerequisites (when enabled)
│   │
│   ├── prepare/                         # Credentials + configuration prep
│   │   ├── ansible.cfg
│   │   ├── prepare_openchami.yml        # Credential management (prompt, encrypt, vault)
│   │   └── prepare_openldap.yml         # LDAP dirs, TLS certs, config templating
│   │
│   ├── deploy/                          # Service deployment
│   │   ├── ansible.cfg
│   │   ├── deploy_openchami.yml         # S3 access + OpenCHAMI containers on OIM
│   │   └── deploy_openldap.yml          # OpenLDAP container on OIM (when enabled)
│   │
│   ├── validate/                        # Readiness gates + post-provision checks
│   │   ├── ansible.cfg
│   │   ├── validate_openchami.yml       # Input validation + OpenCHAMI health checks
│   │   ├── validate_openldap.yml        # OpenLDAP container health (when enabled)
│   │   └── validate_provisioning.yml    # Post-provision inventory gen + verification
│   │
│   ├── provision/                       # Node provisioning (category-scoped)
│   │   ├── ansible.cfg
│   │   ├── provision_preamble.yml       # SSH + OpenCHAMI auth (runs once)
│   │   ├── provision_kubernetes.yml     # K8s FGs + bolt-ons
│   │   ├── provision_slurm.yml          # Slurm+Login FGs + bolt-ons
│   │   ├── provision_os.yml             # OS-only FGs (minimal)
│   │   └── provision_custom.yml         # User-defined FGs (catch-all)
│   │
│   ├── pxeboot/                         # PXE boot on iDRAC nodes
│   │   ├── ansible.cfg
│   │   ├── pxeboot.yml                  # BMC inventory, reboot, node-registration verify
│   │   └── README.md
│   │
│   ├── cleanup/                         # Component teardown
│   │   ├── ansible.cfg
│   │   ├── cleanup_openchami.yml        # Stop services, remove containers/config
│   │   └── cleanup_openldap.yml         # Stop container, remove Quadlet/data
│   │
│   ├── upgrade/                         # In-place upgrade
│   │   ├── ansible.cfg
│   │   ├── upgrade_openchami.yml        # Version detect, backup, migrate, verify
│   │   └── upgrade_openldap.yml         # Fedora→Wolfi container migration
│   │
│   ├── rollback/                        # Revert to previous state
│   │   ├── ansible.cfg
│   │   ├── rollback_openchami.yml       # Backup restore, restart, verify
│   │   └── rollback_openldap.yml        # Wolfi→Fedora container rollback
│   │
│   └── credentials/                     # Standalone credential management
│       ├── ansible.cfg
│       └── orchestrator_credentials.yml
│
├── roles/
│   │── # ── Core Lifecycle Roles ──────────────────────────────
│   ├── orchestrator_setup/              # Upgrade guard, dirs, vars, OIM group
│   ├── orchestrator_credentials/        # Credential management
│   ├── validate_orchestrator_input/     # L1/L2 input validation
│   ├── orchestrator_functional_groups/  # Generate FG YAML from CSV
│   ├── orchestrator_common/             # Auth, S3, shared utils
│   ├── orchestrator_validations/        # Runtime pre-checks (conditional creds)
│   │
│   │── # ── OpenCHAMI Lifecycle Roles ─────────────────────────
│   ├── deploy_openchami/                # Deploy containers
│   ├── validate_openchami/              # Health checks
│   │
│   │── # ── Provisioning Roles ────────────────────────────────
│   ├── configure_ochami/                # BSS, cloud-init, node orchestration
│   ├── generate_inventories/            # Query SMD, generate inventories
│   ├── validate_provisioning/           # Post-provision verification
│   ├── passwordless_ssh/                # SSH key distribution
│   │
│   │── # ── Bolt-On Service Roles (data-driven) ──────────────
│   ├── k8s_config/                      # Kubernetes configuration
│   ├── slurm_config/                    # Slurm scheduler configuration
│   ├── mount_config/                    # Storage mount configuration
│   ├── openldap/                        # OpenLDAP configuration
│   └── telemetry/                       # Telemetry deployment
│
├── plugins/
│   ├── modules/
│   │   ├── generate_functional_groups.py
│   │   ├── validate_orchestrator_config.py
│   │   ├── generate_xname_in_mapping_file.py
│   │   ├── slurm_conf.py
│   │   ├── fetch_credential_rule.py
│   │   ├── validate_credentials.py
│   │   ├── generate_argon2_password.py
│   │   └── fetch_telemetry_status.py
│   ├── module_utils/
│   │   ├── orchestrator_validation/
│   │   │   ├── orchestrator_validation_flow.py
│   │   │   └── schema/
│   │   │       ├── orchestrator_config.json
│   │   │       ├── network_spec.json
│   │   │       └── credential_rules.json
│   │   └── slurm/
│   │       └── slurm_conf_utils.py
│   └── callback/
│       └── omnia_default.py
│
├── vars/
│   ├── common_vars.yml
│   └── openchami_vars.yml
│
├── input/
│   ├── orchestrator_config.yml
│   ├── network_spec.yml
│   ├── pxe_mapping_file.csv
│   ├── omnia_config.yml
│   ├── storage_config.yml
│   └── ...
│
├── docs/
│   ├── ORCHESTRATOR_DESIGN.md
│   └── ORCHESTRATOR_MODERNIZATION.md    # This file
│
├── INPUT_CONTRACT.md
└── OUTPUT_CONTRACT.md
```

---

## 5. Component Disposition

### 5.1 Components Retained

| Component | Reason |
|-----------|--------|
| `orchestrator_setup` role | Enhanced with catalog-based feature detection, `pxe_mapping_file_path`, `enable_pxe_boot`, and `orchestrator_state.yml` persistence |
| `orchestrator_credentials` role | Complete credential lifecycle (prompt, validate, encrypt) |
| `validate_orchestrator_input` role | L1 schema + L2 logic validation |
| `orchestrator_common` role | Shared utilities: `openchami_auth.yml`, `configure_s3_access.yml` |
| `passwordless_ssh` role | SSH key distribution to OIM and cluster nodes |
| `deploy_openchami` role | OpenCHAMI container deployment |
| `openldap` role | Already gated by `openldap_support` flag |
| All Python modules in `plugins/modules/` | Functional, tested |

### 5.2 Components Refactored

| Component | Change | Status |
|-----------|--------|--------|
| **`orchestrator.yml`** | Rewritten from 247-line monolith → thin tag-routing wrapper (~290 lines with comments) | ✅ Done |
| **`orchestrator_setup` role** | Added upgrade lock bypass for `upgrade`/`rollback` tags, catalog-based feature flags, `enable_pxe_boot` config | ✅ Done |
| **`orchestrator_validations` role** | Made credential loading conditional to avoid failures during `precheck` when creds aren't yet available | ✅ Done |
| **`prepare_orchestrator.yml`** | Split into `prepare_openchami.yml` (credentials) + `prepare_openldap.yml` (dirs, TLS, configs) | ✅ Done |
| **`validate_orchestrator.yml`** | Distributed to `validate_openchami.yml` + `validate_openldap.yml` with standalone setup plays | ✅ Done |
| **`cleanup_orchestrator.yml`** | Split into `cleanup_openchami.yml` + `cleanup_openldap.yml` for independent teardown | ✅ Done |
| **`upgrade_orchestrator.yml`** | Replaced with `upgrade_openchami.yml` (version-specific 0.1.7→0.2.0 migration) + `upgrade_openldap.yml` (Fedora→Wolfi) | ✅ Done |
| **`rollback_orchestrator.yml`** | Replaced with `rollback_openchami.yml` (backup restore) + `rollback_openldap.yml` (Wolfi→Fedora) | ✅ Done |
| **`setpxe/` directory** | Renamed to `pxeboot/`, `set_pxe_boot.yml` → `pxeboot.yml`, tags: `setpxe` → `pxeboot` | ✅ Done |
| **Tag validation variables** | Updated `supported_tags`, `invalid_tag_combinations`, `skip_credential_tags` in `orchestrator_setup/vars/main.yml` | ✅ Done |

### 5.3 Components Created

| Component | Purpose | Status |
|-----------|---------|--------|
| **`precheck_openchami.yml`** | Validate input (L1+L2), parameters, boot images, OIM timezone, OpenCHAMI config vars | ✅ Done |
| **`precheck_openldap.yml`** | Validate LDAP credentials, domain, container prereqs (when enabled) | ✅ Done |
| **`prepare_openchami.yml`** | Credential management (prompt, encrypt, vault) — extracted from prepare_orchestrator | ✅ Done |
| **`prepare_openldap.yml`** | Load LDAP creds, create dirs, TLS certs, template configs — extracted from prepare_orchestrator | ✅ Done |
| **`cleanup_openchami.yml`** | Stop OpenCHAMI, remove containers/config/artifacts/creds — extracted from cleanup_orchestrator | ✅ Done |
| **`cleanup_openldap.yml`** | Stop OpenLDAP container, remove Quadlet unit/data (when enabled) | ✅ Done |
| **`upgrade_openchami.yml`** | Version detection (package_facts), backup, legacy→fabrica migration, restart, verify | ✅ Done |
| **`upgrade_openldap.yml`** | Fedora→Wolfi container image migration with data backup/restore | ✅ Done |
| **`rollback_openchami.yml`** | Version detection (package_facts), backup restore, restart, verify | ✅ Done |
| **`rollback_openldap.yml`** | Wolfi→Fedora container image rollback with data backup/restore | ✅ Done |

### 5.4 Components Removed

| Component | Reason |
|-----------|--------|
| **`prepare_orchestrator.yml`** | Split into `prepare_openchami.yml` + `prepare_openldap.yml` |
| **`validate_orchestrator.yml`** | Distributed to `validate_openchami.yml` + `validate_openldap.yml` |
| **`cleanup_orchestrator.yml`** | Split into `cleanup_openchami.yml` + `cleanup_openldap.yml` |
| **`upgrade_orchestrator.yml`** | Replaced by `upgrade_openchami.yml` + `upgrade_openldap.yml` |
| **`rollback_orchestrator.yml`** | Replaced by `rollback_openchami.yml` + `rollback_openldap.yml` |
| **`setpxe/` directory** | Renamed to `pxeboot/` |

---

## 6. Workflow Definitions

### 6.1 Tag: `precheck` — Read-Only Validation

```
precheck_openchami.yml:
  Hosts: localhost
  Roles:
    1. orchestrator_setup (upgrade guard, dirs, vars, OIM group)
    2. validate_orchestrator_input (L1 schema + L2 logic)
    3. orchestrator_validations (pre-flight: mapping, software, images)
  Hosts: oim
  Tasks:
    4. validate_oim_timezone
    5. validate_boot_images (S3 image per FG)
    6. assert OpenCHAMI config vars (domain_name, admin_nic_ip, etc.)

precheck_openldap.yml:
  Hosts: localhost
  Tasks:
    7. Assert OpenLDAP prerequisites (when openldap_support)
       - LDAP admin credentials exist
       - Domain configuration valid
       - Container prerequisites met

Output:
  - Validated configuration (read-only, no system changes)
  - Clear error messages on any failure
```

**No deployment. No credentials. Pre-flight only.**

### 6.2 Tag: `prepare` — Credentials + Configuration

```
prepare_openchami.yml:
  Hosts: localhost
  Roles:
    1. orchestrator_setup
    2. orchestrator_credentials (prompt, encrypt, vault)

prepare_openldap.yml:
  Hosts: oim
  Tasks:
    3. Load decrypted credentials
    4. Create OpenLDAP directories
    5. Generate TLS certificates
    6. Template OpenLDAP configuration files

Output:
  - Encrypted credential vault
  - OpenLDAP dirs, TLS certs, configs ready for deployment
```

### 6.3 Tag: `deploy` — Service Deployment + Readiness Gates

```
deploy_openchami.yml:
  Hosts: localhost → oim
  Tasks:
    1. orchestrator_setup
    2. configure_s3_access (load build_status.yml, set s3_configurations)
    3. deploy_openchami role (verify → prereq → deploy/refresh)

deploy_openldap.yml:
  Hosts: oim
  Tasks:
    4. deploy_openldap role (when openldap_support)

validate_openchami.yml:
  Hosts: oim
  Tasks:
    5. Validate OpenCHAMI readiness (SMD, BSS, cloud-init-server)

validate_openldap.yml:
  Hosts: oim
  Tasks:
    6. Validate OpenLDAP readiness (when openldap_support)

Gate: provisioning blocked until all readiness checks pass.
```

### 6.4 Tag: `provision` — Node Provisioning

```
provision_preamble.yml:
  Hosts: localhost → oim
  Tasks:
    1. passwordless_ssh (build host lists, distribute keys)
    2. openchami_auth (refresh token)

provision_kubernetes.yml:    # Skip when no K8s FGs
provision_slurm.yml:         # Skip when no Slurm FGs
provision_os.yml:            # Skip when no OS-only FGs
provision_custom.yml:        # Skip when no unmatched FGs

validate_provisioning.yml:
  Tasks:
    - Query SMD → generate ALL inventories (one pass)
    - Verify nodes registered, BSS params set, cloud-init loaded
```

### 6.5 Tag: `pxeboot` — PXE Boot (Opt-In)

```
pxeboot.yml:
  Prerequisites: deploy must have completed
  Skip condition: enable_pxe_boot == false (VM environments)
  Hosts: bmc
  Tasks:
    1. Build BMC inventory from pxe_mapping_file
    2. Set PXE one-time boot via iDRAC
    3. Graceful reboot
    4. Node-registration verification
```

### 6.6 Tag: `cleanup` — Component Teardown (Opt-In)

```
cleanup_openchami.yml:
  Hosts: oim
  Tasks:
    1. Stop OpenCHAMI services (systemctl stop openchami.target)
    2. Remove OpenCHAMI containers and config
    3. Remove generated artifacts (inventories, FG configs)
    4. Remove credentials (opt-in)
    5. Remove orchestrator output directory

cleanup_openldap.yml:
  Hosts: oim
  Tasks:
    1. Stop OpenLDAP container (when openldap_support)
    2. Remove Quadlet unit file
    3. Remove OpenLDAP data and configuration
```

### 6.7 Tag: `upgrade` — In-Place Upgrade (Opt-In)

```
upgrade_openchami.yml:
  Hosts: oim
  Plays:
    1. Version detection (package_facts → openchami version)
    2. Backup current state (config, SMD data, secrets)
    3. Legacy-to-fabrica migration (0.1.7 → 0.2.0):
       - Stop services
       - Pull new images
       - Migrate configuration format
       - Start new services
    4. Post-upgrade verification (health checks)
    5. Cleanup: remove upgrade lock on success

upgrade_openldap.yml:
  Hosts: oim
  Plays:
    1. Backup OpenLDAP data
    2. Stop Fedora-based container
    3. Pull Wolfi-based image
    4. Start Wolfi-based container with restored data
    5. Verify LDAP service health
```

### 6.8 Tag: `rollback` — Revert to Previous State (Opt-In)

```
rollback_openchami.yml:
  Hosts: oim
  Plays:
    1. Version detection (package_facts → openchami version)
    2. Find latest backup
    3. Stop current services
    4. Restore backed-up configuration + SMD state
    5. Start previous version (0.1.7)
    6. Post-rollback verification

rollback_openldap.yml:
  Hosts: oim
  Plays:
    1. Backup current Wolfi data
    2. Stop Wolfi-based container
    3. Pull Fedora-based image
    4. Start Fedora-based container with restored data
    5. Verify LDAP service health
```

### 6.9 Tag: `validate` — Validation Only

```
Runs validate_openchami.yml + validate_openldap.yml + validate_provisioning.yml
without deploying or provisioning anything.

Useful for checking system health after manual changes or disaster recovery.
```

### 6.10 Standalone Playbook Usage

Each playbook can be run independently. Prerequisites:

| To run standalone... | Prerequisites |
|---------------------|---------------|
| `precheck_openchami.yml` | None (read-only) |
| `prepare_openchami.yml` | `precheck` should have passed |
| `deploy_openchami.yml` | `precheck` + `prepare` |
| `provision_preamble.yml` | `precheck` + `prepare` + `deploy` |
| `provision_kubernetes.yml` | All above + `provision_preamble` |
| `cleanup_openchami.yml` | Services must be deployed |
| `upgrade_openchami.yml` | Services must be deployed, backup recommended |
| `rollback_openchami.yml` | Backup must exist from previous upgrade/snapshot |

---

## 7. Functional-Group-Driven Provisioning

### 7.1 Classification Data File

Replace the hardcoded Python dicts with a data file:

```yaml
# vars/functional_group_classification.yml
---
functional_group_categories:
  kubernetes:
    patterns:
      - "^service_kube_"
    layer: management
    description_template: "Kubernetes {role} Node"

  slurm:
    patterns:
      - "^slurm_"
    layer_map:
      control: management
      node: compute
    description_template: "Slurm {role} Node"

  login:
    patterns:
      - "^login_node_"
      - "^login_compiler_node_"
    layer: management
    description_template: "Login Node"

  os_only:
    patterns:
      - "^os_"
    layer: compute
    description_template: "OS-Only Node"

  custom:
    patterns:
      - ".*"  # catch-all
    layer: compute
    description_template: "Custom Functional Group"

default_layer: compute
default_description: "User-Defined Functional Group"
```

### 7.2 Bolt-On Services as Data

Bolt-on services (k8s, slurm, openldap, telemetry) are NOT triggered by
functional group names. They are triggered by configuration data:

```yaml
# Target (data-driven — already implemented for support flags):
- name: Check if slurm support is true
  set_fact:
    slurm_support: >-
      {{ _catalog_fl_names | select('match', '.*slurm.*') | list | length > 0 }}
```

---

## 8. Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL WORKFLOWS                           │
│                                                                 │
│  ┌─────────────────────┐    ┌──────────────────────┐            │
│  │  Discovery Workflow  │    │ Image Build Workflow  │            │
│  │  ─────────────────── │    │ ──────────────────── │            │
│  │  • BMC discovery     │    │ • OS installation    │            │
│  │  • MAC collection    │    │ • Package config     │            │
│  │  • PXE mapping gen   │    │ • K8s/Slurm bake-in │            │
│  │  • Inventory gen     │    │ • Image → S3         │            │
│  └────────┬─────────────┘    └────────┬─────────────┘            │
│           │                           │                          │
│           ▼                           ▼                          │
│   pxe_mapping_file.csv        S3: boot-images/                  │
│   network_spec.yml            build_status.yml                   │
└───────────┬───────────────────────────┬─────────────────────────┘
            │                           │
            ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR WORKFLOWS                        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SHARED: orchestrator_setup + functional_groups (always)  │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                        │
│           ┌─────────────┼─────────────────┐                     │
│           ▼             ▼                 ▼                      │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐              │
│  │  precheck   │ │  prepare    │ │   deploy     │              │
│  │ ─────────── │ │ ─────────── │ │ ──────────── │              │
│  │ OpenCHAMI:  │ │ OpenCHAMI:  │ │ OpenCHAMI:   │              │
│  │ • L1/L2     │ │ • Creds     │ │ • S3+deploy  │              │
│  │ • params    │ │             │ │ • validate   │              │
│  │ • images    │ │ OpenLDAP:   │ │              │              │
│  │ • config    │ │ • dirs      │ │ OpenLDAP:    │              │
│  │             │ │ • TLS       │ │ • container  │              │
│  │ OpenLDAP:   │ │ • configs   │ │ • validate   │              │
│  │ • prereqs   │ │             │ │              │              │
│  └─────────────┘ └─────────────┘ └──────┬───────┘              │
│                                          │                      │
│                                          ▼                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  provision                                                │  │
│  │  ──────────                                               │  │
│  │  preamble → kubernetes → slurm → os → custom → validate  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Opt-In Lifecycle Operations                              │  │
│  │  ────────────────────────────                             │  │
│  │                                                           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │  │
│  │  │ pxeboot  │ │ cleanup  │ │ upgrade  │ │ rollback │     │  │
│  │  │ ──────── │ │ ──────── │ │ ──────── │ │ ──────── │     │  │
│  │  │ BMC boot │ │ OCH+LDAP │ │ OCH+LDAP │ │ OCH+LDAP │     │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Week 1-2) ✅ COMPLETE

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Create `vars/functional_group_classification.yml` with pattern-based rules | ✅ Done |
| 1.2 | Refactor `generate_functional_groups.py` to read classification from YAML | ✅ Done |
| 1.3 | Create `validate_openchami` role with health checks | ✅ Done |
| 1.4 | Create `validate_provisioning` role (post-provision checks) | ✅ Done |
| 1.5 | Create `provision_common` role skeleton | ✅ Done |

### Phase 2: Playbook Decomposition (Week 3-4) ✅ COMPLETE

| Task | Description | Status |
|------|-------------|--------|
| 2.1 | Create `precheck_openchami.yml` + `precheck_openldap.yml` | ✅ Done |
| 2.2 | Split `prepare_orchestrator.yml` → `prepare_openchami.yml` + `prepare_openldap.yml` | ✅ Done |
| 2.3 | Wire `deploy` tag for `deploy_openchami.yml` + `deploy_openldap.yml` | ✅ Done |
| 2.4 | Distribute `validate_orchestrator.yml` → `validate_openchami.yml` + `validate_openldap.yml` | ✅ Done |
| 2.5 | Create `provision_preamble.yml` (SSH + auth, runs once) | ✅ Done |
| 2.6 | Split `cleanup_orchestrator.yml` → `cleanup_openchami.yml` + `cleanup_openldap.yml` | ✅ Done |
| 2.7 | Rewrite `orchestrator.yml` as thin tag-routing wrapper | ✅ Done |
| 2.8 | Update `supported_tags`, `invalid_tag_combinations`, `skip_credential_tags` | ✅ Done |
| 2.9 | Remove old `*_orchestrator.yml` files | ✅ Done |

### Phase 3: Provisioning Refactor (Week 5-7) — Planned

| Task | Description | Risk |
|------|-------------|------|
| 3.1 | Extract `orchestration_mapping_nodes.yml` into `provision_common` role | High |
| 3.2 | Implement per-category `nodes_<category>.yaml` generation (upsert semantics) | High |
| 3.3 | Create `generate_inventories` role (query SMD, single-pass inventory gen) | Medium |
| 3.4 | Remove inline DNS shell scripts, move to `provision_common/tasks/configure_dns.yml` | Low |
| 3.5 | Consolidate duplicate SELinux context tasks | Low |
| 3.6 | Delete `configure_ochami` role after task absorption | Medium |

### Phase 4: Bolt-On Decoupling (Week 8-9) ✅ COMPLETE

| Task | Description | Status |
|------|-------------|--------|
| 4.1 | Refactor `slurm_config`: replace literal FG checks with pattern match | ✅ Done |
| 4.2 | Refactor `mount_config`: replace literal FG checks with support flags | ✅ Done |
| 4.3 | Refactor `k8s_config`: replace hardcoded FG references with pattern match | ✅ Done |
| 4.4 | Refactor `read_slurm_hostnames.yml`: parameterize FG regex patterns | ✅ Done |
| 4.5 | Implement configurable bolt-on assignment from `omnia_config.yml` | ✅ Done |
| 4.6 | Refactor `passwordless_ssh/vars`: dynamic FG list derivation | ✅ Done |
| 4.7 | Refactor `orchestrator_validations/validate_mapping_file.yml`: arch-agnostic regex | ✅ Done |

### Phase 5: Lifecycle Operations (Week 10) ✅ COMPLETE

| Task | Description | Status |
|------|-------------|--------|
| 5.1 | Implement `upgrade_openchami.yml` (version detect via package_facts, backup, migrate, verify) | ✅ Done |
| 5.2 | Implement `upgrade_openldap.yml` (Fedora→Wolfi migration) | ✅ Done |
| 5.3 | Implement `rollback_openchami.yml` (version detect via package_facts, restore, verify) | ✅ Done |
| 5.4 | Implement `rollback_openldap.yml` (Wolfi→Fedora rollback) | ✅ Done |
| 5.5 | Implement `cleanup_openchami.yml` (stop, remove containers/config/artifacts) | ✅ Done |
| 5.6 | Implement `cleanup_openldap.yml` (stop, remove Quadlet/data) | ✅ Done |
| 5.7 | Rename `setpxe/` → `pxeboot/`, update tags and routing | ✅ Done |
| 5.8 | Fix `orchestrator_validations` conditional credential loading | ✅ Done |
| 5.9 | Fix `orchestrator_setup` upgrade lock bypass for upgrade/rollback tags | ✅ Done |

### Phase 6: Testing & Validation (Week 11-12) — Static ✅ / E2E Pending

| Task | Description | Status |
|------|-------------|--------|
| 6.1 | Ansible `--syntax-check`: all playbooks + `orchestrator.yml` | ✅ Pass |
| 6.2 | ansible-lint: all 181 files processed | ✅ Pass (0 violations) |
| 6.3 | `--list-tasks` for each tag: precheck, prepare, deploy, provision, validate, pxeboot, cleanup, upgrade, rollback | ✅ Pass |
| 6.4 | Tag validation: unsupported tags rejected, conflicting combos rejected | ✅ Pass |
| 6.5 | No stale references to removed `*_orchestrator.yml` files | ✅ Pass |
| 6.6 | End-to-end test: standard deployment (k8s + slurm + login + os) | ⏳ Requires live environment |
| 6.7 | End-to-end test: custom FG (`ai_inference_gpu`) — zero code changes | ⏳ Requires live environment |
| 6.8 | End-to-end test: k8s-only deployment standalone | ⏳ Requires live environment |
| 6.9 | End-to-end test: slurm-only deployment standalone | ⏳ Requires live environment |
| 6.10 | End-to-end test: upgrade → rollback cycle | ⏳ Requires live environment |
| 6.11 | End-to-end test: cleanup | ⏳ Requires live environment |

---

## 10. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Regression in existing provisioning | High | Medium | Phase 2.8 cutover tested with --syntax-check and --list-tasks. Full E2E pending. |
| `generate_functional_groups.py` refactor breaks FG generation | High | Low | Unit tests for module. Side-by-side output comparison with current version |
| SMD registration without `--overwrite` causes stale nodes | Medium | Medium | `validate_provisioning.yml` compares expected vs actual SMD state |
| Per-category nodes.yaml split breaks node registration | High | Low | Phase 3.2 integration test planned |
| Login nodes without Slurm FGs fall through to custom | Low | Low | Documented behavior (§6.5.3). Configurable via classification data. |
| Telemetry role complexity | Medium | Low | Defer telemetry refactoring. Already uses support flags correctly. |
| Standalone playbook missing prerequisites | Medium | Medium | §6.10 documents prerequisites. Clear error messages on missing state. |
| Component-split playbooks drift apart | Low | Low | Consistent naming convention (`<phase>_<component>.yml`) and shared `orchestrator_setup` role. |

---

## Appendix A: Tag Configuration (Implemented)

### Supported Tags

```yaml
supported_tags:
  - precheck
  - prepare
  - deploy
  - provision
  - pxeboot
  - cleanup
  - validate
  - upgrade
  - rollback
```

### Skip Credential Tags

```yaml
skip_credential_tags:
  - precheck
  - cleanup
  - validate
```

### Invalid Tag Combinations

```yaml
invalid_tag_combinations:
  - [precheck, cleanup]
  - [prepare, cleanup]
  - [deploy, cleanup]
  - [provision, cleanup]
  - [pxeboot, cleanup]
  - [precheck, upgrade]
  - [prepare, upgrade]
  - [deploy, upgrade]
  - [provision, upgrade]
  - [cleanup, upgrade]
  - [upgrade, rollback]
```

## Appendix B: Functional Group Categories (Current)

| Category | FG Names | Layer | Bolt-On |
|----------|----------|-------|---------|
| Kubernetes | `service_kube_control_plane_x86_64`, `service_kube_node_x86_64` | management | `k8s_config` |
| Slurm | `slurm_control_node_x86_64`, `slurm_node_x86_64`, `slurm_node_aarch64` | management/compute | `slurm_config` |
| Login | `login_node_x86_64`, `login_node_aarch64`, `login_compiler_node_x86_64`, `login_compiler_node_aarch64` | management | — |
| OS-only | `os_x86_64`, `os_aarch64` | compute | — |
| Custom | Any user-defined name | compute (default) | None (generic provisioning only) |

## Appendix C: Input/Output Contract Summary

**Inputs (consumed):**

| File | Source | Required |
|------|--------|----------|
| `pxe_mapping_file.csv` | Discovery workflow | Yes |
| `network_spec.yml` | User / discovery | Yes |
| `orchestrator_config.yml` | User | Yes |
| `omnia_config.yml` | User | Yes |
| `software_config.json` | Image build / user | Yes |
| `storage_config.yml` | User | When NFS mounts needed |
| `build_status.yml` | Image build workflow | Yes (S3 endpoint) |

**Outputs (produced):**

| File | Consumer |
|------|----------|
| `functional_groups_config.yml` | Internal (provisioning) |
| `orchestrator_state.yml` | Internal (support flags for standalone runs) |
| `orchestrator_inventory.yml` | External (Ansible inventory) |
| `bmc_group_data.yml` | External (BMC operations) |
| `provisioning_report.yml` | External (audit/review) |
| SMD state (in OpenCHAMI) | OpenCHAMI services |
| BSS boot params (in OpenCHAMI) | PXE boot |
| Cloud-init data (in OpenCHAMI) | Node first-boot |
