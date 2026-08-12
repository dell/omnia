# Orchestrator Modernization — Architecture & Implementation Plan

**Author:** Dell Omnia Engineering  
**Date:** July 2026  
**Status:** Proposal — Architecture Review  
**Scope:** `src/orchestrator/`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Target Architecture](#3-target-architecture)
4. [Proposed Directory Structure](#4-proposed-directory-structure)
5. [Component Disposition](#5-component-disposition)
6. [Workflow Definitions](#6-workflow-definitions)
7. [Functional-Group-Driven Provisioning](#7-functional-group-driven-provisioning)
8. [Workflow Diagram](#8-workflow-diagram)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Risks and Mitigations](#10-risks-and-mitigations)

---

## 1. Executive Summary

The orchestrator modernization replaces the current monolithic `orchestrator.yml`
(247 lines, 16 plays, mixed concerns) with a clean, composable workflow aligned
to OpenCHAMI-based provisioning.

**Key changes:**

- Split monolithic entrypoint into 9 focused playbooks
- Eliminate all hardcoded functional-group names from provisioning logic
- Treat functional groups as data, not code-level selectors
- Separate OpenCHAMI lifecycle (deploy/validate/upgrade/rollback/cleanup) from
  node provisioning
- Introduce post-provisioning validation
- Make bolt-on services (k8s, slurm, openldap, telemetry, mounts) fully
  data-driven and optional

**Boundaries (out of scope):**

- Discovery workflow (hardware, BMC, PXE mapping generation)
- Image build workflow (OS install, package config, image creation)
- Both produce artifacts consumed by the orchestrator as inputs

---

## 2. Current State Analysis

### 2.1 Existing Entrypoint (`orchestrator.yml`)

The current entrypoint is a single 247-line playbook containing 16 plays that
execute sequentially. It mixes concerns across validation, deployment,
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

### 2.2 Existing Roles (14)

| Role | Responsibility | Issues |
|------|---------------|--------|
| `orchestrator_setup` | Upgrade guard, project dirs, vars loading, OIM group | Well-structured. Retain. |
| `validate_orchestrator_input` | L1 schema + L2 logic validation | Retain. |
| `orchestrator_credentials` | Credential prompt, encrypt, vault | Retain. |
| `orchestrator_functional_groups` | Generate FG YAML from PXE CSV | Module has hardcoded FG maps. Refactor. |
| `orchestrator_validations` | Software config, mapping file, image, telemetry | Mixed pre-flight and runtime validation. Split. |
| `orchestrator_common` | openchami_auth, configure_s3_access, kube_vip check | Retain as shared utilities. |
| `passwordless_ssh` | Build host lists, configure OIM SSH | Retain. |
| `deploy_openchami` | Deploy OpenCHAMI containers | Retain. Add health checks. |
| `configure_ochami` | SMD groups, BSS boot, cloud-init, inventories | Monolithic (291-line task file). Split. |
| `k8s_config` | K8s NFS share, manifests, packages | Hardcoded `service_k8s_cluster[0]`. Refactor. |
| `slurm_config` | Slurm config files on NFS | Checks `slurm_control_node_x86_64` by name. Refactor. |
| `mount_config` | Cloud-init mounts, swap, NFS bolt-ons | Checks FG names for slurm/k8s support. Refactor. |
| `openldap` | LDAP domain, server-ip, connection type | Gated by `openldap_support` flag. OK. |
| `telemetry` | iDRAC, LDMS, PowerScale, UFM, VAST, OME | Complex conditional tree. Leave for now. |

### 2.3 Hardcoded Functional Group References

The following files contain hardcoded functional group names that violate the
extensibility requirement:

**`plugins/modules/generate_functional_groups.py`** (lines 35-48):
```python
FUNCTIONAL_GROUP_LAYER_MAP = {
    "service_kube_control_plane_first_x86_64": "management",
    "service_kube_control_plane_x86_64": "management",
    "slurm_control_node_x86_64": "management",
    "slurm_node_x86_64": "compute",
    "os_x86_64": "compute",
    ...
}
```

**`roles/slurm_config/tasks/main.yml`** (line 29):
```yaml
- "'slurm_control_node_x86_64' in (functional_groups | map(attribute='name'))"
```

**`roles/mount_config/tasks/main.yml`** (line 40):
```yaml
- "'slurm_control_node_x86_64' in (functional_groups | map(attribute='name'))"
```

**`roles/configure_ochami/tasks/orchestration_mapping_nodes.yml`** (lines 111-136):
```yaml
k8s_functional_groups: >-
  {{ hostvars['localhost']['k8s_functional_groups'] |
  default(['service_kube_control_plane_first_x86_64', ...]) }}
slurm_functional_groups: >-
  {{ hostvars['localhost']['slurm_functional_groups'] |
  default(['slurm_control_node_x86_64', ...]) }}
```

**`roles/k8s_config/tasks/create_k8s_config_nfs.yml`** (line 81):
```yaml
| selectattr('FUNCTIONAL_GROUP_NAME', 'match', '^service_kube_control_plane')
```

**`roles/slurm_config/tasks/read_slurm_hostnames.yml`** (lines 69-83):
```yaml
ctld_list: "{{ ... | selectattr('key', 'match', '^slurm_control_node_') ... }}"
cmpt_list: "{{ ... | selectattr('key', 'match', '^slurm_node_') ... }}"
login_list: "{{ ... | selectattr('key', 'match', '^login_node_') ... }}"
```

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

1. **Functional groups are data, not code** — Adding a new FG requires zero
   code changes. The orchestrator reads FGs from the PXE mapping CSV and
   processes them generically.

2. **Single Responsibility** — Each playbook owns exactly one lifecycle stage.

3. **Generic provisioning pipeline** — All nodes follow the same path:
   PXE Mapping → Functional Groups → Image Resolution → SMD Registration →
   BSS/Cloud-Init → Validation.

4. **Bolt-on services are optional and data-driven** — k8s, slurm, openldap,
   telemetry configuration is gated by the presence of entries in
   `software_config.json` / `omnia_config.yml`, not by hardcoded FG checks.

5. **Separation of concerns** — OpenCHAMI lifecycle (deploy/validate/upgrade/
   rollback/cleanup) is separate from node provisioning.

6. **Idempotency** — Every playbook must be safe to run multiple times. Re-running
   `provision_kubernetes.yml` must not duplicate nodes in SMD, corrupt BSS entries,
   or break nodes registered by other provisioning playbooks. SMD group creation
   uses upsert semantics; BSS uses delete-then-set; cloud-init uses overwrite.

### 3.2 Target Playbooks

| Playbook | Purpose |
|----------|--------|
| `prepare_orchestrator.yml` | Pre-flight validation, credential management, deployment plan |
| `deploy_openchami.yml` | Deploy OpenCHAMI services on OIM |
| `validate_openchami.yml` | Verify OpenCHAMI readiness for provisioning |
| `provision_preamble.yml` | SSH key distribution + OpenCHAMI auth (runs once before provisioning) |
| `provision_kubernetes.yml` | Provision K8s cluster: register K8s FGs, BSS/cloud-init, k8s bolt-ons |
| `provision_slurm.yml` | Provision Slurm cluster: register Slurm+Login FGs, BSS/cloud-init, slurm bolt-ons |
| `provision_os.yml` | Provision OS-only nodes: register OS FGs, BSS/cloud-init, minimal config |
| `provision_custom.yml` | Provision user-defined FGs: register custom FGs, BSS/cloud-init, no bolt-ons |
| `validate_provisioning.yml` | Post-provisioning validation + inventory generation |
| `upgrade_openchami.yml` | In-place upgrade of OpenCHAMI services |
| `rollback_openchami.yml` | Restore previous OpenCHAMI state |
| `cleanup_openchami.yml` | Remove OpenCHAMI and generated artifacts |

Each `provision_*.yml` playbook is **independently runnable** — operators can
provision only the Kubernetes cluster, or only Slurm, without touching the
rest. They share a common provisioning role (`provision_common`) for the
generic pipeline (SMD registration, BSS, cloud-init) and add category-specific
bolt-on configuration.

The `provision_preamble.yml` playbook handles SSH key distribution and
OpenCHAMI authentication **once**, eliminating redundant setup across the 4
provisioning playbooks. When running standalone, operators must run
`provision_preamble.yml` before any `provision_*.yml` playbook (see §6.9).

Bolt-on service assignment is configurable via `omnia_config.yml` — see §7.5.

### 3.3 Orchestrator Entrypoint

The new `orchestrator.yml` becomes a thin orchestration wrapper that imports
the above playbooks in order:

```yaml
---
# orchestrator.yml — Thin entrypoint
- import_playbook: playbooks/prepare_orchestrator.yml
- import_playbook: playbooks/deploy_openchami.yml
- import_playbook: playbooks/validate_openchami.yml
- import_playbook: playbooks/provision_preamble.yml
- import_playbook: playbooks/provision_kubernetes.yml
- import_playbook: playbooks/provision_slurm.yml
- import_playbook: playbooks/provision_os.yml
- import_playbook: playbooks/provision_custom.yml
- import_playbook: playbooks/validate_provisioning.yml
```

Each `provision_*.yml` playbook skips gracefully when no matching FGs exist
in the PXE mapping (i.e., if the user has no Kubernetes nodes, the K8s
playbook is a no-op).

---

## 4. Proposed Directory Structure

```
src/orchestrator/
├── orchestrator.yml                     # Thin entrypoint (imports playbooks)
├── ansible.cfg
├── galaxy.yml
├── meta/runtime.yml
│
├── playbooks/
│   ├── prepare_orchestrator.yml         # Pre-flight: validate, credentials, plan
│   ├── deploy_openchami.yml             # Deploy OpenCHAMI on OIM
│   ├── validate_openchami.yml           # Verify OpenCHAMI readiness
│   ├── provision_preamble.yml           # SSH + auth (runs once before provisioning)
│   ├── provision_kubernetes.yml         # Provision K8s cluster FGs + bolt-ons
│   ├── provision_slurm.yml              # Provision Slurm cluster FGs + bolt-ons
│   ├── provision_os.yml                 # Provision OS-only FGs (minimal)
│   ├── provision_custom.yml             # Provision user-defined FGs
│   ├── validate_provisioning.yml        # Post-provisioning checks + inventory gen
│   ├── upgrade_openchami.yml            # Upgrade OpenCHAMI
│   ├── rollback_openchami.yml           # Rollback OpenCHAMI
│   └── cleanup_openchami.yml            # Cleanup OpenCHAMI + artifacts
│
├── roles/
│   │
│   │── # ── Core Lifecycle Roles ──────────────────────────────
│   ├── orchestrator_setup/              # RETAIN — upgrade guard, dirs, vars
│   ├── orchestrator_credentials/        # RETAIN — credential management
│   ├── validate_orchestrator_input/     # RETAIN — L1/L2 input validation
│   ├── orchestrator_functional_groups/  # REFACTOR — remove hardcoded FG maps
│   ├── orchestrator_common/             # RETAIN — auth, S3, shared utils
│   │
│   │── # ── OpenCHAMI Lifecycle Roles ─────────────────────────
│   ├── deploy_openchami/                # RETAIN — deploy containers
│   ├── validate_openchami/              # NEW — OpenCHAMI health checks
│   │
│   │── # ── Provisioning Roles ────────────────────────────────
│   ├── provision_common/                # NEW — shared generic pipeline
│   │   ├── tasks/
│   │   │   ├── main.yml                 # Entry: filter FGs → register → BSS → cloud-init
│   │   │   ├── register_nodes.yml       # SMD node registration (per-category, no --overwrite)
│   │   │   ├── configure_bss.yml        # BSS boot params per FG
│   │   │   ├── configure_cloud_init.yml # Cloud-init config per FG
│   │   │   └── configure_dns.yml        # DNS/CoreDNS (from orchestrator.yml)
│   │   └── templates/                   # Moved from configure_ochami/templates
│   │
│   ├── provision_kubernetes/            # NEW — K8s-specific orchestration
│   │   └── tasks/main.yml              # provision_common(k8s FGs) → k8s_config
│   ├── provision_slurm/                 # NEW — Slurm-specific orchestration
│   │   └── tasks/main.yml              # provision_common(slurm FGs) → slurm_config
│   ├── provision_os/                    # NEW — OS-only orchestration
│   │   └── tasks/main.yml              # provision_common(os FGs) — no bolt-ons
│   ├── provision_custom/                # NEW — user-defined FG orchestration
│   │   └── tasks/main.yml              # provision_common(custom FGs) — no bolt-ons
│   │
│   ├── validate_provisioning/           # NEW — post-provision checks
│   ├── passwordless_ssh/                # RETAIN — SSH key distribution
│   │
│   ├── generate_inventories/            # NEW — query SMD, generate all inventories
│   │   └── tasks/main.yml              # Called by validate_provisioning
│   │
│   │── # ── Bolt-On Service Roles (data-driven) ──────────────
│   ├── k8s_config/                      # REFACTOR — remove hardcoded FG checks
│   ├── slurm_config/                    # REFACTOR — remove hardcoded FG checks
│   ├── mount_config/                    # REFACTOR — remove hardcoded FG checks
│   ├── openldap/                        # RETAIN — already flag-gated
│   ├── telemetry/                       # RETAIN — complex, refactor later
│   │
│   │── # ── Validation Roles ──────────────────────────────────
│   └── orchestrator_validations/        # REFACTOR — split pre-flight/post-provision
│
├── plugins/
│   ├── modules/
│   │   ├── generate_functional_groups.py # REFACTOR — data-driven FG classification
│   │   ├── validate_orchestrator_config.py
│   │   ├── generate_xname_in_mapping_file.py
│   │   ├── slurm_conf.py
│   │   ├── fetch_credential_rule.py
│   │   ├── validate_credentials.py
│   │   ├── generate_argon2_password.py
│   │   └── fetch_telemetry_status.py
│   ├── module_utils/
│   └── callback/
│
├── vars/
│   ├── common_vars.yml
│   ├── openchami_vars.yml
│   └── functional_group_classification.yml  # NEW — data-driven FG→layer mapping
│
├── input/                               # Default input templates
│   ├── orchestrator_config.yml
│   ├── network_spec.yml
│   ├── pxe_mapping_file.csv
│   ├── omnia_config.yml
│   ├── storage_config.yml
│   └── ...
│
├── containers/
├── docs/
└── examples/
```

---

## 5. Component Disposition

### 5.1 Components to Retain (no changes)

| Component | Reason |
|-----------|--------|
| `orchestrator_setup` role | Well-structured. Handles upgrade guard, project dirs, vars loading, OIM host group. |
| `orchestrator_credentials` role | Complete credential lifecycle (prompt, validate, encrypt). |
| `validate_orchestrator_input` role | L1 schema + L2 logic validation. |
| `orchestrator_common` role | Shared utilities: `openchami_auth.yml`, `configure_s3_access.yml`, `check_kube_vip_reachability.yml`. |
| `passwordless_ssh` role | SSH key distribution to OIM and cluster nodes. |
| `deploy_openchami` role | OpenCHAMI container deployment. Well-isolated. |
| `openldap` role | Already gated by `openldap_support` flag. No FG coupling. |
| All Python modules in `plugins/modules/` (except `generate_functional_groups.py`) | Functional, tested. |

### 5.2 Components to Refactor

| Component | Current Issue | Target State |
|-----------|--------------|--------------|
| **`generate_functional_groups.py`** | `FUNCTIONAL_GROUP_LAYER_MAP` and `DESCRIPTION_MAP` hardcode all known FG names. Unknown FGs are silently dropped. | Read classification from `vars/functional_group_classification.yml`. Unknown FGs default to `"compute"` layer with auto-generated description. Zero code changes to add FGs. |
| **`configure_ochami` role** | 291-line `orchestration_mapping_nodes.yml` mixes SMD registration, inventory generation, BSS config, hostname config, cloud-init, SELinux context. Generates K8s/Slurm-specific inventories. | **Remove entirely.** All tasks absorbed by `provision_common` (register, BSS, cloud-init, DNS, SMD groups) and `generate_inventories` (inventory files). No residual purpose. |
| **`orchestrator_validations` role** | Mixes pre-flight validation (mapping file, software config, network) with runtime checks (image validation, telemetry config). | Split into: (a) pre-flight tasks called from `prepare_orchestrator`, (b) `validate_openchami` role for OpenCHAMI health, (c) `validate_provisioning` role for post-provision checks. |
| **`k8s_config` role** | References `service_k8s_cluster[0]` directly. Hardcodes `service_kube_control_plane_first` for CIDR detection. | Gate on `service_k8s_support` flag (already present). Read cluster config from `omnia_config.yml` K8s section. Replace hardcoded FG name with pattern match from classification data. |
| **`slurm_config` role** | Checks `'slurm_control_node_x86_64' in functional_groups` literally. `read_slurm_hostnames.yml` uses regex patterns `^slurm_control_node_`, `^slurm_node_`, `^login_node_`. | Gate on `slurm_support` flag. Read slurm FG patterns from classification data instead of hardcoding. |
| **`mount_config` role** | Checks `'slurm_control_node_x86_64' in functional_groups` for slurm_support. Filters NFS mounts by hardcoded software names. | Use `slurm_support` and `service_k8s_support` flags (already computed). Remove literal FG name checks. |
| **`orchestrator.yml` entrypoint** | 247-line monolith with 16 plays, inline DNS shell scripts, mixed localhost/oim plays. | Thin wrapper: 9 `import_playbook` lines (prepare → deploy → validate → preamble → 4×provision → validate_provisioning). All logic moves to sub-playbooks. |

### 5.3 Components to Create

| Component | Purpose |
|-----------|---------|
| **`validate_openchami` role** | Health checks: SMD API, BSS API, cloud-init-server, IMS availability, certificate validity. Called after `deploy_openchami` and before provisioning. |
| **`provision_preamble` playbook** | SSH key distribution + OpenCHAMI auth token. Runs once before provisioning playbooks, avoiding 4× redundant setup. |
| **`provision_common` role** | Generic FG-driven provisioning pipeline: accepts a filtered FG list, then runs SELinux context, per-category nodes.yaml generation, SMD discovery (no `--overwrite`), hostname config, BSS boot params (delete-then-set), cloud-init config, DNS config. Does NOT generate inventories. |
| **`provision_kubernetes` role** | Filters FGs to K8s category, calls `provision_common`, then runs K8s bolt-ons (configurable via `omnia_config.yml`). |
| **`provision_slurm` role** | Filters FGs to Slurm+Login category, calls `provision_common`, then runs Slurm bolt-ons (configurable via `omnia_config.yml`). |
| **`provision_os` role** | Filters FGs to OS-only category, calls `provision_common`. No bolt-on services by default. |
| **`provision_custom` role** | Filters FGs to unrecognized/user-defined category, calls `provision_common`. No bolt-on services by default. |
| **`generate_inventories` role** | Queries SMD for all registered nodes, generates ALL inventories in a single pass (orchestrator, BMC, kube, slurm). Called from `validate_provisioning.yml`. |
| **`validate_provisioning` role** | Post-provision checks: verify SMD node state, verify BSS boot params set, verify cloud-init data loaded, verify node reachability, generate provisioning summary report. |
| **`vars/functional_group_classification.yml`** | Data file mapping FG name patterns to layers, categories, and descriptions. Replaces hardcoded Python dicts. |

### 5.4 Components to Remove

| Component | Reason |
|-----------|--------|
| **`configure_ochami` role** | Fully absorbed by `provision_common` (SMD groups, BSS, cloud-init) and `generate_inventories` (inventory files). No residual purpose. |
| Inline DNS shell scripts in `orchestrator.yml` (lines 157-229) | Move to `provision_common/tasks/configure_dns.yml` as a proper task file. |
| Duplicate SELinux context tasks | Currently repeated in `orchestration_mapping_nodes.yml`, `deploy_openchami.yml`, and `configure_bss_cloud_init.yml`. Consolidate into a single shared task. |

---

## 6. Workflow Definitions

### 6.1 `prepare_orchestrator.yml`

```
Hosts: localhost
Roles:
  1. orchestrator_setup (upgrade guard, dirs, vars, OIM group)
  2. validate_orchestrator_input (L1 schema + L2 logic)
  3. orchestrator_credentials (prompt, encrypt, vault)
  4. orchestrator_functional_groups (generate FG YAML from CSV)
  5. orchestrator_validations (pre-flight subset):
     - validate_mapping_mechanism
     - validate_mapping_file
     - include_software_config → derive support flags
     - validate_image (per FG)

Hosts: oim
Tasks:
  6. validate_oim_timezone

Output:
  - Validated configuration
  - functional_groups_config.yml
  - Support flags (service_k8s_support, slurm_support, openldap_support)
  - Validated images per FG
  - Deployment plan (runtime facts)
```

**No provisioning. No deployment. Pre-flight only.**

### 6.2 `deploy_openchami.yml`

```
Hosts: localhost
Roles:
  1. orchestrator_setup

Hosts: oim
Tasks:
  2. configure_s3_access
  3. deploy_openchami (verify → prereq → deploy/refresh)
```

### 6.3 `validate_openchami.yml`

```
Hosts: oim
Roles:
  1. validate_openchami:
     - Verify openchami.target is active
     - Verify SMD API is reachable (/smd/v2/service/ready)
     - Verify BSS API is reachable
     - Verify cloud-init-server is reachable
     - Verify ACME certificates are valid
     - Verify S3 bucket access
     - Verify OpenLDAP container (when openldap_support)

Output:
  - openchami_ready: true/false
  - Fail if not ready (provisioning must not proceed)
```

### 6.4 `provision_preamble.yml`

Runs **once** before all provisioning playbooks. Handles SSH key distribution
and OpenCHAMI auth that would otherwise be duplicated 4×.

```
Hosts: localhost
Roles:
  1. orchestrator_setup (load vars, OIM group)
  2. passwordless_ssh (build host lists from PXE mapping)

Hosts: oim
Tasks:
  3. passwordless_ssh (configure OIM SSH access)
  4. openchami_auth (refresh token, store as fact)

Output:
  - SSH keys distributed
  - openchami_access_token fact available for subsequent plays
```

**Standalone usage:** When running a single `provision_*.yml` standalone,
operators must run `provision_preamble.yml` first (see §6.10).

### 6.5 Provisioning Playbooks

Provisioning is split into 4 independently-runnable playbooks, each scoped to
a cluster category. They all share a common provisioning role (`provision_common`)
for the generic pipeline. **None of them include SSH or auth setup** — that
is handled by `provision_preamble.yml`.

#### 6.5.1 `provision_common` role (shared)

This role accepts a filtered list of functional groups and runs the generic
provisioning pipeline for them:

```
Inputs:
  - target_functional_groups: list of FG dicts (filtered by caller)
  - target_category: string (kubernetes|slurm|os|custom)

Tasks:
  a. Set SELinux context (once, idempotent)
  b. Generate per-category nodes.yaml from PXE mapping (scoped to target FGs)
  c. SMD node registration:
     - ochami discover static (NO --overwrite flag)
     - Uses upsert semantics: existing nodes are updated, not replaced
     - Nodes from other categories are untouched
  d. Generate hostname.yaml + apply to cloud-init
  e. Create SMD groups (iterate target FGs, upsert)
  f. Configure BSS boot params (iterate target FGs, delete-then-set)
  g. Configure cloud-init defaults
  h. Configure cloud-init per-group (iterate target FGs, overwrite)
  i. Configure additional cloud-init (when enabled)
  j. Configure DNS (when dns_enabled)
```

**No `if functional_group == "X"` logic anywhere in this role.**

**No inventory generation** — inventories are generated in a single pass by
`validate_provisioning.yml` after all provisioning is complete (see §6.8).

**SMD registration safety:** Each provisioning playbook generates its own
`nodes_<category>.yaml` (e.g., `nodes_kubernetes.yaml`, `nodes_slurm.yaml`)
and registers only those nodes. The `ochami discover static` command runs
without `--overwrite`, so nodes registered by a previous playbook are never
deleted. Re-running the same playbook updates existing entries (upsert).

#### 6.5.2 `provision_kubernetes.yml`

```
Skip when: no FGs match kubernetes category patterns (^service_kube_)

Hosts: oim
Roles:
  1. provision_common:
     target_functional_groups: {{ k8s_functional_groups }}
     target_category: kubernetes

  2. Bolt-on services (configurable via omnia_config.yml):
     - mount_config (when storage configured)
     - k8s_config (NFS share, manifests, helm, calico, metallb)
     - telemetry (when telemetry_enabled)
     - openldap (when openldap_support — optional for k8s)
```

#### 6.5.3 `provision_slurm.yml`

**Login node ownership:** Login nodes (`^login_node_`, `^login_compiler_node_`)
are provisioned as part of the Slurm cluster. This matches the current Omnia
behavior where login nodes appear in the Slurm inventory and share Slurm's
NFS mounts. If login nodes are present in the PXE mapping but no Slurm FGs
exist, they will fall through to `provision_custom.yml` instead.

```
Skip when: no FGs match slurm category patterns (^slurm_|^login_)

Hosts: oim
Roles:
  1. provision_common:
     target_functional_groups: {{ slurm_functional_groups }}
     target_category: slurm

  2. Bolt-on services (configurable via omnia_config.yml):
     - mount_config (when storage configured)
     - slurm_config (slurm.conf, host dirs, munge)
     - openldap (when openldap_support)
     - telemetry (when telemetry_enabled — optional for slurm)
```

#### 6.5.4 `provision_os.yml`

```
Skip when: no FGs match os category patterns (^os_)

Hosts: oim
Roles:
  1. provision_common:
     target_functional_groups: {{ os_functional_groups }}
     target_category: os

  2. No bolt-on services by default — minimal OS provisioning only
```

#### 6.5.5 `provision_custom.yml`

```
Skip when: no FGs match custom category (unrecognized names)

Hosts: oim
Roles:
  1. provision_common:
     target_functional_groups: {{ custom_functional_groups }}
     target_category: custom

  2. No bolt-on services by default
     (Users can extend by adding roles to this playbook)
```

**Design rationale:**
- Each playbook is a self-contained unit that can be run independently
  (after `provision_preamble.yml`)
- The `provision_common` role handles ALL generic provisioning logic identically
- Category filtering is done once at the playbook level using classification patterns
- Bolt-on services are configurable via `omnia_config.yml` (see §7.5)
- Adding a new cluster category (e.g., `provision_ai.yml`) requires only a new
  playbook file — no changes to existing code
- SMD registration uses per-category nodes files without `--overwrite`,
  ensuring cross-category safety

### 6.6 `validate_provisioning.yml`

```
Hosts: oim
Roles:
  1. generate_inventories:
     - Query SMD for ALL registered nodes (single API call)
     - Query functional_groups_config.yml for FG→category mapping
     - Generate orchestrator_inventory.yml (all nodes)
     - Generate bmc_group_data.yml (all nodes)
     - Generate kube_inventory.yml (FGs matching kubernetes category)
     - Generate slurm_inventory.yml (FGs matching slurm category)
     - All inventories generated in ONE pass — no append, no deduplication

  2. validate_provisioning:
     - Verify SMD components exist for all expected nodes
     - Verify BSS boot params set for all FGs
     - Verify cloud-init data loaded for all FGs
     - Verify node hostname assignments
     - Verify DNS records (when dns_enabled)
     - Verify generated inventories are consistent with SMD state
     - Generate provisioning summary report:
       * Nodes provisioned per FG per category
       * Boot image per FG
       * BSS status
       * Cloud-init status
       * Inventory file paths

Output:
  - orchestrator_inventory.yml
  - kube_inventory.yml
  - slurm_inventory.yml
  - bmc_group_data.yml
  - provisioning_report.yml → orchestrator output directory
  - Console summary
```

**Why inventory generation lives here:** Generating inventories after all
provisioning is complete avoids append-mode fragility, deduplication bugs,
and ordering issues across the 4 provision playbooks. SMD is the single
source of truth — query it once, generate everything.

### 6.7 `upgrade_openchami.yml`

```
Hosts: oim
Tasks:
  1. Backup current OpenCHAMI configuration
  2. Backup SMD state
  3. Pull new OpenCHAMI images
  4. Rolling restart of services
  5. Verify service health post-upgrade
  6. Update metadata with new version
```

### 6.8 `rollback_openchami.yml`

```
Hosts: oim
Tasks:
  1. Stop current OpenCHAMI services
  2. Restore backed-up configuration
  3. Restore backed-up SMD state
  4. Start previous OpenCHAMI version
  5. Verify service health post-rollback
```

### 6.9 `cleanup_openchami.yml`

```
Hosts: oim
Tasks:
  1. Stop OpenCHAMI services
  2. Remove OpenCHAMI containers and data
  3. Remove generated inventories
  4. Remove functional_groups_config.yml
  5. Remove orchestrator output directory
  6. Remove credentials (opt-in, tag-gated)
```

### 6.10 Standalone Playbook Usage

Each provisioning playbook can be run independently, but requires prerequisite
state from earlier stages. The following table shows which playbooks must run
first:

| To run standalone... | Prerequisites |
|---------------------|---------------|
| `provision_preamble.yml` | `prepare_orchestrator.yml`, `deploy_openchami.yml`, `validate_openchami.yml` |
| `provision_kubernetes.yml` | All of the above + `provision_preamble.yml` |
| `provision_slurm.yml` | All of the above + `provision_preamble.yml` |
| `provision_os.yml` | All of the above + `provision_preamble.yml` |
| `provision_custom.yml` | All of the above + `provision_preamble.yml` |
| `validate_provisioning.yml` | At least one `provision_*.yml` must have run |

**Support flags bootstrap:** The `prepare_orchestrator.yml` playbook computes
`service_k8s_support`, `slurm_support`, and `openldap_support` from
`software_config.json` and persists them as facts in the orchestrator output
directory (`<output_dir>/orchestrator_state.yml`). Subsequent playbooks load
this state file to access support flags without recomputing.

**Example: provision only Kubernetes on an existing OpenCHAMI deployment:**

```bash
ansible-playbook playbooks/provision_preamble.yml
ansible-playbook playbooks/provision_kubernetes.yml
ansible-playbook playbooks/validate_provisioning.yml
```

---

## 7. Functional-Group-Driven Provisioning

### 7.1 Classification Data File

Replace the hardcoded Python dicts with a data file:

```yaml
# vars/functional_group_classification.yml
---
# Functional group classification rules.
# Patterns are matched against FG names from the PXE mapping CSV.
# Unknown FGs that match no pattern default to category=custom, layer=compute.

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

# Default layer for FGs that match no explicit pattern
default_layer: compute
default_description: "User-Defined Functional Group"
```

### 7.2 Refactored `generate_functional_groups.py`

```python
# Instead of:
FUNCTIONAL_GROUP_LAYER_MAP = {
    "service_kube_control_plane_first_x86_64": "management",
    ...
}

# The module will:
# 1. Read classification rules from functional_group_classification.yml
# 2. Match each FG name from CSV against patterns
# 3. Assign layer + description based on first matching category
# 4. Default unknown FGs to layer=compute, description=auto-generated
# 5. Zero code changes to support new FGs
```

### 7.3 Generic Provisioning Loop

The `provision_common` role receives a filtered list of FGs and processes them
identically:

```yaml
# provision_common/tasks/main.yml (conceptual)

# target_functional_groups is passed by the calling playbook
# e.g., provision_kubernetes.yml passes only k8s FGs

# Generate per-category nodes file (e.g., nodes_kubernetes.yaml)
- name: Generate nodes YAML for target category
  ansible.builtin.template:
    src: nodes.yaml.j2
    dest: "{{ output_dir }}/nodes_{{ target_category }}.yaml"

# Register target nodes — upsert, no --overwrite (safe across categories)
- name: Discover target nodes in SMD
  ansible.builtin.command: >
    /usr/bin/ochami discover static -f yaml
    -d @{{ output_dir }}/nodes_{{ target_category }}.yaml
  when: target_functional_groups | length > 0

# Create SMD groups — iterate target FGs generically
- name: Create SMD groups for each functional group
  ansible.builtin.include_tasks: create_group.yml
  loop: "{{ target_functional_groups | map(attribute='name') | list }}"

# Configure BSS — iterate target FGs generically
- name: Configure BSS boot params for each functional group
  ansible.builtin.include_tasks: configure_bss_group.yml
  loop: "{{ target_functional_groups | map(attribute='name') | list }}"

# Configure cloud-init — iterate target FGs generically
- name: Configure cloud-init for each functional group
  ansible.builtin.include_tasks: configure_cloud_init_group.yml
  loop: "{{ target_functional_groups | map(attribute='name') | list }}"
```

**FG filtering happens in each playbook before calling `provision_common`:**

```yaml
# provision_kubernetes.yml (conceptual)
- name: Filter FGs to kubernetes category
  ansible.builtin.set_fact:
    k8s_functional_groups: >-
      {{ functional_groups
         | selectattr('name', 'match', '^service_kube_')
         | list }}

- name: Provision kubernetes nodes
  ansible.builtin.include_role:
    name: provision_common
  vars:
    target_functional_groups: "{{ k8s_functional_groups }}"
    target_category: kubernetes
  when: k8s_functional_groups | length > 0
```

**Adding a new functional group (e.g., `ai_inference_gpu`) requires only:**

1. Add rows to `pxe_mapping_file.csv` with `FUNCTIONAL_GROUP_NAME=ai_inference_gpu`
2. Build an OS image for it (image-build workflow)
3. Run orchestrator — it provisions automatically via `provision_custom.yml`

**Adding a new cluster category (e.g., AI inference) requires only:**

1. Create `playbooks/provision_ai.yml` with FG pattern filter + bolt-ons
2. Add `import_playbook` line to `orchestrator.yml`
3. No changes to existing playbooks or the `provision_common` role

**No orchestrator code changes needed for new FGs.**

### 7.4 Bolt-On Services as Data

Bolt-on services (k8s, slurm, openldap, telemetry) are NOT triggered by
functional group names. They are triggered by configuration data:

```yaml
# Current (BAD — hardcoded FG check):
- name: Check if slurm support is true
  set_fact:
    slurm_support: true
  when:
    - "'slurm_control_node_x86_64' in (functional_groups | map(attribute='name'))"

# Target (GOOD — data-driven):
- name: Check if slurm support is true
  set_fact:
    slurm_support: >-
      {{ (software_config.softwares
          | selectattr('name', 'in', ['slurm_custom'])
          | list | length) > 0
         and (functional_groups
              | map(attribute='name')
              | select('match', slurm_fg_pattern)
              | list | length) > 0 }}
  vars:
    slurm_fg_pattern: "{{ fg_categories.slurm.patterns | join('|') }}"
```

### 7.5 Configurable Bolt-On Assignment

Bolt-on services are NOT hardcoded per provisioning playbook. Instead, each
provisioning category has a **default set** of bolt-ons that can be overridden
in `omnia_config.yml`:

```yaml
# omnia_config.yml (example)
orchestrator:
  bolt_ons:
    kubernetes:
      - mount_config
      - k8s_config
      - telemetry
      # Uncomment to add LDAP for K8s nodes:
      # - openldap

    slurm:
      - mount_config
      - slurm_config
      - openldap
      # Uncomment to add telemetry for Slurm nodes:
      # - telemetry

    os: []         # No bolt-ons by default
    custom: []     # No bolt-ons by default
```

Each `provision_*.yml` playbook reads its bolt-on list from this config:

```yaml
# provision_kubernetes.yml (conceptual)
- name: Load bolt-on configuration
  ansible.builtin.set_fact:
    category_bolt_ons: >-
      {{ omnia_config.orchestrator.bolt_ons.kubernetes
         | default(['mount_config', 'k8s_config', 'telemetry']) }}

- name: Run bolt-on roles
  ansible.builtin.include_role:
    name: "{{ bolt_on }}"
  loop: "{{ category_bolt_ons }}"
  loop_control:
    loop_var: bolt_on
  when: bolt_on_enabled[bolt_on] | default(true) | bool
```

**Benefits:**
- Operators can add `telemetry` to Slurm or `openldap` to K8s without code changes
- Operators can disable default bolt-ons for specific environments
- Custom categories can have bolt-ons added via config, not code

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
│  ┌─────────────────────────────────────────────────────┐        │
│  │  1. prepare_orchestrator                             │        │
│  │  ─────────────────────                               │        │
│  │  • Validate PXE mapping + network + credentials      │        │
│  │  • Generate functional_groups_config.yml              │        │
│  │  • Validate boot images in S3 per FG                  │        │
│  │  • Generate deployment plan                           │        │
│  └──────────────────────┬──────────────────────────────┘        │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  2. deploy_openchami                                 │        │
│  │  ─────────────────────                               │        │
│  │  • Configure S3 access on OIM                         │        │
│  │  • Deploy OpenCHAMI containers                        │        │
│  │  • Configure networking + ACME certs                  │        │
│  └──────────────────────┬──────────────────────────────┘        │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  3. validate_openchami                               │        │
│  │  ──────────────────────                              │        │
│  │  • Verify SMD API reachable                           │        │
│  │  • Verify BSS API reachable                           │        │
│  │  • Verify cloud-init-server reachable                 │        │
│  │  • Verify certificate validity                        │        │
│  │  • GATE: provisioning blocked until all pass          │        │
│  └──────────────────────┬──────────────────────────────┘        │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  4. provision_preamble                                │        │
│  │  ─────────────────────                                │        │
│  │  • SSH key distribution (localhost → OIM)              │        │
│  │  • OpenCHAMI auth token (runs once, shared by all)    │        │
│  └──────────────────────┬──────────────────────────────┘        │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  5. Provisioning (4 independent, category-scoped playbooks) ││
│  │  ──────────────────────────────────────────────────────────  ││
│  │                                                              ││
│  │  Each playbook:  filter FGs → provision_common → bolt-ons   ││
│  │                                                              ││
│  │  ┌───────────────────────────────────────────────────┐      ││
│  │  │  provision_common (shared role)                    │      ││
│  │  │  ─────────────────────────────                     │      ││
│  │  │  PXE Mapping → FG Filter → Resolve Image/Config   │      ││
│  │  │       ▼                                            │      ││
│  │  │  SMD Registration (ochami discover static)         │      ││
│  │  │       ▼                                            │      ││
│  │  │  BSS Boot Params (per FG)                          │      ││
│  │  │       ▼                                            │      ││
│  │  │  Cloud-Init Config (per FG)                        │      ││
│  │  │       ▼                                            │      ││
│  │  │  DNS Config (optional)                             │      ││
│  │  └───────────────────────────────────────────────────┘      ││
│  │                                                              ││
│  │  ┌────────────────┐ ┌────────────────┐ ┌──────────────┐     ││
│  │  │ 5a. provision   │ │ 5b. provision  │ │ 5c. provision│     ││
│  │  │   _kubernetes   │ │   _slurm       │ │   _os        │     ││
│  │  │ ──────────────  │ │ ────────────── │ │ ──────────── │     ││
│  │  │ ^service_kube_  │ │ ^slurm_|login_ │ │ ^os_         │     ││
│  │  │ + k8s_config    │ │ + slurm_config │ │ (no bolt-ons)│     ││
│  │  │ + mount_config  │ │ + mount_config │ │              │     ││
│  │  │ + telemetry     │ │ + openldap     │ │              │     ││
│  │  └────────────────┘ └────────────────┘ └──────────────┘     ││
│  │                                                              ││
│  │  ┌────────────────┐                                         ││
│  │  │ 5d. provision   │  ← user-defined FGs (catch-all)        ││
│  │  │   _custom       │  ← no built-in bolt-ons                ││
│  │  │ ──────────────  │  ← extensible: add your own roles      ││
│  │  └────────────────┘                                         ││
│  │                                                              ││
│  │  Bolt-on assignment configurable via omnia_config.yml (§7.5) ││
│  └──────────────────────┬──────────────────────────────────────┘│
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  6. validate_provisioning                            │        │
│  │  ─────────────────────────                           │        │
│  │  • Query SMD → generate ALL inventories (one pass)    │        │
│  │  • Verify all nodes registered in SMD                 │        │
│  │  • Verify BSS boot params per FG                      │        │
│  │  • Verify cloud-init data loaded                      │        │
│  │  • Verify node reachability                           │        │
│  │  • Generate provisioning_report.yml                   │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  Lifecycle Operations (standalone)                    │        │
│  │  ─────────────────────────────────                   │        │
│  │  • upgrade_openchami.yml                              │        │
│  │  • rollback_openchami.yml                             │        │
│  │  • cleanup_openchami.yml                              │        │
│  └─────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Goal:** Create the structural skeleton without breaking existing functionality.

| Task | Description | Risk |
|------|-------------|------|
| 1.1 | Create `vars/functional_group_classification.yml` with pattern-based rules | Low |
| 1.2 | Refactor `generate_functional_groups.py` to read classification from YAML instead of hardcoded dicts. Unknown FGs default to `compute` layer. | Medium — must pass existing tests |
| 1.3 | Create `validate_openchami` role with health checks extracted from `orchestrator_validations` | Low |
| 1.4 | Create `validate_provisioning` role (new — post-provision checks) | Low |
| 1.5 | Create `provision_common` role skeleton — initially delegates to existing `configure_ochami` tasks | Low |

**Backward compatibility:** `orchestrator.yml` continues to work unchanged.
New roles exist alongside old ones.

### Phase 2: Playbook Decomposition (Week 3-4)

**Goal:** Split `orchestrator.yml` into sub-playbooks.

| Task | Description | Risk |
|------|-------------|------|
| 2.1 | Rewrite `prepare_orchestrator.yml` to include full pre-flight validation (setup + validate + credentials + FG gen + image validation + OIM timezone) | Medium |
| 2.2 | Rewrite `deploy_openchami.yml` to include S3 access + deployment | Low |
| 2.3 | Create `validate_openchami.yml` playbook using new role | Low |
| 2.4 | Create `provision_preamble.yml` (SSH + auth, runs once before provisioning) | Low |
| 2.5 | Create `provision_kubernetes.yml`, `provision_slurm.yml`, `provision_os.yml`, `provision_custom.yml` — initially call existing roles in order | Medium |
| 2.6 | Create `validate_provisioning.yml` playbook using new role | Low |
| 2.7 | Add support-flag persistence to `prepare_orchestrator.yml` — write `orchestrator_state.yml` so standalone runs can load flags | Low |
| 2.8 | Rewrite `orchestrator.yml` as thin `import_playbook` wrapper | High — this is the cutover |

**Backward compatibility:** Test the thin wrapper produces identical results
to the monolithic version before merging.

### Phase 3: Provisioning Refactor (Week 5-7)

**Goal:** Extract generic provisioning logic from `configure_ochami` and remove it.

| Task | Description | Risk |
|------|-------------|------|
| 3.1 | Extract `orchestration_mapping_nodes.yml` into `provision_common` role: `register_nodes.yml`, `configure_bss.yml`, `configure_cloud_init.yml`, `configure_dns.yml` | High — largest refactor |
| 3.2 | Implement per-category `nodes_<category>.yaml` generation in `provision_common` — each playbook registers only its own nodes without `--overwrite` (upsert semantics) | High — SMD registration safety |
| 3.3 | Create `generate_inventories` role — queries SMD for all registered nodes, generates all inventories in one pass. Called from `validate_provisioning.yml` | Medium |
| 3.4 | Remove inline DNS shell scripts from `orchestrator.yml`, move to `provision_common/tasks/configure_dns.yml` | Low |
| 3.5 | Consolidate duplicate SELinux context tasks into a single shared task | Low |
| 3.6 | Delete `configure_ochami` role — all tasks absorbed by `provision_common` + `generate_inventories` | Medium — verify no residual references |

### Phase 4: Bolt-On Decoupling (Week 8-9) ✅ COMPLETE

**Goal:** Remove hardcoded FG names from bolt-on roles. Make bolt-on assignment configurable.

| Task | Description | Risk | Status |
|------|-------------|------|--------|
| 4.1 | Refactor `slurm_config`: replace literal `slurm_control_node_x86_64` check with pattern match from classification data | Medium | ✅ Done |
| 4.2 | Refactor `mount_config`: replace literal FG name checks with support flags | Low | ✅ Done |
| 4.3 | Refactor `k8s_config`: replace `service_kube_control_plane_first` references with pattern match | Medium | ✅ Done |
| 4.4 | Refactor `read_slurm_hostnames.yml`: parameterize FG regex patterns from classification data | Medium | ✅ Already uses patterns |
| 4.5 | Implement configurable bolt-on assignment from `omnia_config.yml` (§7.5) — each `provision_*.yml` reads bolt-on list from config with sensible defaults | Medium | ✅ Done (Phase 2) |
| 4.6 | Refactor `passwordless_ssh/vars`: replace hardcoded FG lists with dynamic derivation | Medium | ✅ Done |
| 4.7 | Refactor `orchestrator_validations/validate_mapping_file.yml`: arch-agnostic regex | Low | ✅ Done |

### Phase 5: Lifecycle Operations (Week 10) ✅ COMPLETE

**Goal:** Implement upgrade, rollback, cleanup with real logic.

| Task | Description | Risk | Status |
|------|-------------|------|--------|
| 5.1 | Implement `upgrade_orchestrator.yml` (lock → backup → pull → restart → verify → unlock) | Medium | ✅ Done (222 lines, 6 plays) |
| 5.2 | Implement `rollback_orchestrator.yml` (find backup → stop → restore → start → verify → unlock) | Medium | ✅ Done (207 lines, 5 plays) |
| 5.3 | Finalize `cleanup_orchestrator.yml` (stop → remove containers → clean dirs → revert DNS → opt-in credentials) | Low | ✅ Done (167 lines, 4 plays) |

### Phase 6: Testing & Validation (Week 11-12) — Static Checks ✅ / E2E Pending

| Task | Description | Status |
|------|-------------|--------|
| 6.1 | Ansible `--syntax-check`: all 14 playbooks + `orchestrator.yml` entrypoint | ✅ Pass |
| 6.2 | YAML parse: all 202 YAML files across orchestrator tree | ✅ Pass |
| 6.3 | Python `py_compile`: all 8 plugin modules | ✅ Pass |
| 6.4 | Cross-reference validation: 10 include_tasks + 18 cross-role refs + 9 import_playbook | ✅ All resolve |
| 6.5 | Duplicate task name check: new roles | ✅ None found |
| 6.6 | End-to-end test: standard deployment (k8s + slurm + login + os) | ⏳ Requires live environment |
| 6.7 | End-to-end test: custom FG (`ai_inference_gpu`) — zero code changes | ⏳ Requires live environment |
| 6.8 | End-to-end test: k8s-only deployment (`provision_kubernetes.yml` standalone) | ⏳ Requires live environment |
| 6.9 | End-to-end test: slurm-only deployment (`provision_slurm.yml` standalone) | ⏳ Requires live environment |
| 6.10 | End-to-end test: os-only / custom FG deployment | ⏳ Requires live environment |
| 6.11 | End-to-end test: idempotency — run provision twice, verify no SMD duplicates | ⏳ Requires live environment |
| 6.12 | End-to-end test: upgrade → rollback cycle | ⏳ Requires live environment |
| 6.13 | End-to-end test: cleanup | ⏳ Requires live environment |

---

## 10. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Regression in existing provisioning | High | Medium | Phase 2.8 cutover only after integration test confirms identical behavior |
| `generate_functional_groups.py` refactor breaks FG generation | High | Low | Unit tests for module. Side-by-side output comparison with current version |
| SMD registration without `--overwrite` causes stale nodes | Medium | Medium | `validate_provisioning.yml` compares expected vs actual SMD state. Provide `--clean` tag to wipe SMD before re-provisioning. |
| Per-category nodes.yaml split breaks node registration | High | Low | Phase 3.2 integration test: register k8s nodes, then slurm nodes, verify both exist in SMD. |
| Inventory generation from SMD misses nodes not yet registered | Medium | Low | `validate_provisioning.yml` runs AFTER all provisioning playbooks. Standalone users must run all desired `provision_*.yml` first. |
| Login nodes without Slurm FGs fall through to custom | Low | Low | Documented behavior (§6.5.3). If undesirable, user adds login FG pattern to their preferred category. |
| Telemetry role complexity | Medium | Low | Defer telemetry refactoring. It already uses support flags correctly. |
| Custom FGs missing boot images in S3 | Medium | Medium | `validate_image.yml` already fails clearly with image-not-found message. No change needed. |
| `software_config.json` removal (future catalog file) | Low | Low | Current data-driven approach works regardless of file name/format. |
| Bolt-on roles assume specific cluster config structure | Medium | Medium | Document expected config schema. Validate in `prepare_orchestrator`. |
| Standalone playbook missing prerequisites | Medium | Medium | §6.10 documents prerequisites. `provision_common` checks for `orchestrator_state.yml` and fails with clear error if missing. |

---

## Appendix A: Functional Group Categories (Current)

| Category | FG Names | Layer | Bolt-On |
|----------|----------|-------|---------|
| Kubernetes | `service_kube_control_plane_x86_64`, `service_kube_node_x86_64` | management | `k8s_config` |
| Slurm | `slurm_control_node_x86_64`, `slurm_node_x86_64`, `slurm_node_aarch64` | management/compute | `slurm_config` |
| Login | `login_node_x86_64`, `login_node_aarch64`, `login_compiler_node_x86_64`, `login_compiler_node_aarch64` | management | — |
| OS-only | `os_x86_64`, `os_aarch64` | compute | — |
| Custom | Any user-defined name | compute (default) | None (generic provisioning only) |

## Appendix B: Input/Output Contract Summary

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
| `kube_inventory.yml` | External (K8s operations) |
| `slurm_inventory.yml` | External (Slurm operations) |
| `bmc_group_data.yml` | External (BMC operations) |
| `provisioning_report.yml` | External (audit/review) |
| SMD state (in OpenCHAMI) | OpenCHAMI services |
| BSS boot params (in OpenCHAMI) | PXE boot |
| Cloud-init data (in OpenCHAMI) | Node first-boot |
