# Omnia Architecture Refactor: Domain-Based Component Analysis

## Phase 1 – Current-State Architecture Analysis

### 1. Discovery Flow

**Entry playbook:** `src/playbooks/discovery/discovery.yml`

**Execution flow:**
1. Import `utils/include_input_dir.yml` → resolves `input_project_dir` from `/opt/omnia/input/default.yml`
2. Set discovery validation tags (`omnia_run_tags`)
3. Load `discovery_config.yml` from `input_project_dir`
4. Import `input_validation/validate_config.yml` (L1/L2 validation)
5. Import `utils/credential_utility/get_config_credentials.yml`
6. Validate `discovery_mechanism` parameter (ome | magellan)
7. Include role `ome_discovery`

**Roles:**
- `ome_discovery` (single role):
  - `get_ome_credentials.yml` → loads vault-encrypted credentials
  - `collect_inventory.yml` → uses `ome_server_inventory` module (Python)
  - `generate_pxe_mapping.yml` → uses `generate_pxe_mapping` module (Python)
  - `generate_discovery_report.yml` → uses `generate_discovery_report` module (Python)

**Variables:**
- `input_project_dir` (from include_input_dir)
- `ome_ip`, `enable_bmc_discovery` (from discovery_config.yml)
- `ome_username`, `ome_password` (from encrypted credentials)
- Network spec data (admin_subnet, ib_subnet from network_spec.yml)

**Input files consumed:**
- `{input_project_dir}/discovery_config.yml`
- `{input_project_dir}/network_spec.yml`
- `{input_project_dir}/omnia_config_credentials.yml` (vault-encrypted)
- `{input_project_dir}/build_stream_config.yml` (for completion message)

**Output files generated:**
- `{input_project_dir}/bmc_pxe_mapping_file_{timestamp}.csv` — **PXE mapping file (primary output)**
- `/opt/omnia/discovery/bmc_discovery_report_{timestamp}.csv` — NIC link status report

**Dependencies on provision:** None (discovery is already fairly independent)

**Dependencies on common:**
- `src/common/library/modules/ome_server_inventory.py`
- `src/common/library/modules/generate_pxe_mapping.py`
- `src/common/library/modules/generate_discovery_report.py`
- `src/common/callback_plugins/` (stdout callback)
- `src/common/vars/common_vars.yml` (loaded by include_input_dir)

**Dependencies on utils:**
- `utils/include_input_dir.yml` (project dir resolution)
- `input_validation/validate_config.yml`
- `utils/credential_utility/get_config_credentials.yml`

### 2. Provision Flow

**Entry playbook:** `src/playbooks/provision/provision.yml`

**Execution flow:**
1. Import `utils/upgrade_checkup.yml`
2. Import `utils/include_input_dir.yml` (with openchami_vars + metadata support)
3. Set build_stream config, compute_image_suffix
4. Import `utils/create_container_group.yml` (oim group)
5. Import `utils/generate_functional_groups.yml` (from pxe_mapping_file.csv)
6. Set validation tags
7. Import `input_validation/validate_config.yml`
8. Import `utils/credential_utility/get_config_credentials.yml`
9. Role: `provision_validations` (validates mapping file, images in S3, etc.)
10. OIM timezone validation
11. Role: `passwordless_ssh` (builds host lists, configures OIM SSH)
12. Validate OpenLDAP container
13. Image validation per functional group (S3 lookup)
14. OpenCHAMI auth on OIM
15. DNS configuration (CoreDNS)
16. Provision nodes via `configure_ochami/provision_mapping_nodes.yml`
17. Roles: `mount_config`, `k8s_config`, `slurm_config`, `openldap`, `telemetry`, `configure_ochami`

**Roles executed:**
- `provision_validations` — input validation, mapping file parsing
- `passwordless_ssh` — SSH key distribution, host list construction
- `configure_ochami` — OpenCHAMI node registration, BSS/cloud-init config
- `mount_config` — storage mount configuration
- `k8s_config` — Kubernetes cluster configuration
- `slurm_config` — Slurm scheduler configuration
- `openldap` — LDAP authentication
- `telemetry` — telemetry service setup

**Input files consumed:**
- `provision_config.yml` (pxe_mapping_file_path, dns_enabled, kernel_version_override)
- `network_spec.yml`
- `pxe_mapping_file.csv` (specified by pxe_mapping_file_path)
- `omnia_config.yml`
- `software_config.json`
- `security_config.yml`
- `telemetry_config.yml`
- `storage_config.yml`
- `build_stream_config.yml`
- `discovery_config.yml`
- `/opt/omnia/.data/oim_metadata.yml`
- `/opt/omnia/.data/functional_groups_config.yml` (generated)

**Generated outputs:**
- `/opt/omnia/.data/functional_groups_config.yml`
- OpenCHAMI nodes.yaml, hostname.yaml, groups.yaml
- BSS boot parameter configurations
- Cloud-init group/default configs
- `/opt/omnia/hosts` (hosts file)
- Telemetry BMC group data CSV

**Image resolution flow:**
Node → Functional Group → S3 pattern `rhel-{functional_group}{naming_suffix}` → kernel/initrd/rootfs from `s3://boot-images`

### 3. Prepare OIM Flow

**Entry playbook:** `src/playbooks/prepare_oim/prepare_oim.yml`

**Purpose:** Deploy infrastructure containers on OIM node before provisioning.

**Execution flow:**
1. Upgrade check
2. Include input dir
3. Set tags (prepare_oim, discovery, provision)
4. Validate software_config.json, telemetry_config, discovery_config
5. Input validation
6. Credential utility
7. Create container group (oim)
8. Role: `prepare_oim_validation`
9. Add OIM to known hosts
10. OpenLDAP password hash generation
11. Load build_stream config
12. Deploy containers on OIM:
   - `deploy_containers/common`
   - `deploy_containers/pulp`
   - `deploy_containers/auth`
   - **`deploy_containers/openchami`** ← OpenCHAMI deployment
13. Configure Pulp (HTTP/HTTPS)
14. Deploy postgres, build_stream containers
15. Omnia service deployment
16. Completion

**OpenCHAMI roles in prepare_oim:**
- `deploy_containers/openchami/` — verify, deploy, refresh configs
  - Templates: systemd units, openchami configs
  - Deploys: smd, bss, cloud-init-server, coresmd, acme-deploy

### 4. Data Contracts Between Discovery and Provision

| Contract | Producer | Consumer | Format |
|----------|----------|----------|--------|
| PXE Mapping File | Discovery (`generate_pxe_mapping`) | Provision (`provision_validations`, `generate_functional_groups`, `configure_ochami`) | CSV: FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IP |
| Network Spec | User input | Both Discovery and Provision | YAML: Networks[].admin_network, ib_network |

---

## Dependency Graph

```
                     ┌──────────────────────┐
                     │    src/common/        │
                     │  library/modules/     │
                     │  callback_plugins/    │
                     │  vars/                │
                     │  tasks/               │
                     └──────────┬────────────┘
                                │
            ┌───────────────────┼────────────────────┐
            │                   │                    │
            ▼                   ▼                    ▼
┌──────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    discovery/    │  │   provision/    │  │  prepare_oim/   │
│                  │  │                 │  │                 │
│ ome_discovery    │  │ provision_vals  │  │ deploy_containers│
│                  │  │ passwordless_ssh│  │   /openchami    │
│ Modules used:    │  │ configure_ochami│  │   /pulp         │
│  ome_server_inv  │  │ k8s_config     │  │   /auth         │
│  gen_pxe_mapping │  │ slurm_config   │  │   /common       │
│  gen_disc_report │  │ mount_config   │  │   /postgres     │
│                  │  │ openldap       │  │   /build_stream │
│ Output:          │  │ telemetry      │  │                 │
│  pxe_mapping.csv─┼──▶ Input:         │  │ prepare_oim_val │
│                  │  │  pxe_mapping   │  │                 │
└──────────────────┘  └─────────────────┘  └─────────────────┘
                                │
                                │ OpenCHAMI runtime
                                │ (consumes deployed
                                │  OpenCHAMI services)
                                ▼
                     ┌──────────────────────┐
                     │  src/playbooks/utils/ │
                     │  include_input_dir   │
                     │  generate_func_groups│
                     │  create_container_grp│
                     │  credential_utility  │
                     │  input_validation    │
                     └──────────────────────┘
```

## Classification of Components

### A. Discovery-owned
- `roles/ome_discovery/` (all tasks, vars, defaults)
- `common/library/modules/ome_server_inventory.py`
- `common/library/modules/generate_pxe_mapping.py`
- `common/library/modules/generate_discovery_report.py`
- `input/discovery_config.yml` (template)

### B. Orchestrator-owned (replaces provision + OpenCHAMI from prepare_oim)
- `roles/configure_ochami/` (all tasks, templates, vars)
- `roles/provision_validations/`
- `roles/passwordless_ssh/`
- `roles/k8s_config/`
- `roles/slurm_config/`
- `roles/mount_config/`
- `roles/openldap/`
- `roles/telemetry/`
- `prepare_oim/roles/deploy_containers/openchami/`
- `common/library/modules/generate_functional_groups.py`
- `common/library/modules/generate_xname_in_mapping_file.py`
- `common/library/modules/functional_group_parser.py`
- `common/library/modules/fetch_mapping_details.py`
- `common/vars/openchami_vars.yml`
- `common/vars/openchami_image_cmd.yml`
- `common/tasks/common/openchami_auth.yml`
- `input/provision_config.yml` (template)
- `input/pxe_mapping_file.csv` (template)

### C. Truly Shared (future src/common/)
- `common/callback_plugins/` (omnia_default stdout callback)
- `common/vars/common_vars.yml` (permissions, retry counts)
- `common/vars/image_vars.yml` (container image tags)
- `common/library/module_utils/` (shared Python utils like input_validation)
- `utils/include_input_dir` role (project directory resolution)
- `utils/credential_utility/` (vault handling)
- `input_validation/` (L1/L2 config validation framework)

---

## Target Directory Structure

```
src/
├── discovery/
│   ├── ansible.cfg
│   ├── discovery.yml                        # Main entrypoint
│   ├── roles/
│   │   └── ome_discovery/
│   │       ├── defaults/main.yml
│   │       ├── tasks/
│   │       │   ├── main.yml
│   │       │   ├── get_ome_credentials.yml
│   │       │   ├── collect_inventory.yml
│   │       │   ├── generate_pxe_mapping.yml
│   │       │   └── generate_discovery_report.yml
│   │       └── vars/main.yml
│   ├── library/                             # Discovery-owned modules
│   │   └── modules/
│   │       ├── ome_server_inventory.py
│   │       ├── generate_pxe_mapping.py
│   │       └── generate_discovery_report.py
│   └── CONTRACTS.md                         # Input/output contracts
│
├── orchestrator/
│   ├── ansible.cfg
│   ├── orchestrator.yml                     # Main entrypoint (was provision.yml)
│   ├── roles/
│   │   ├── configure_ochami/               # OpenCHAMI config (from provision)
│   │   ├── deploy_openchami/               # OpenCHAMI deploy (from prepare_oim)
│   │   ├── orchestrator_validations/       # Was provision_validations
│   │   ├── passwordless_ssh/
│   │   ├── k8s_config/
│   │   ├── slurm_config/
│   │   ├── mount_config/
│   │   ├── openldap/
│   │   └── telemetry/
│   ├── library/                            # Orchestrator-owned modules
│   │   └── modules/
│   │       ├── generate_functional_groups.py
│   │       ├── generate_xname_in_mapping_file.py
│   │       ├── functional_group_parser.py
│   │       └── fetch_mapping_details.py
│   ├── vars/
│   │   ├── openchami_vars.yml
│   │   └── openchami_image_cmd.yml
│   ├── tasks/
│   │   └── openchami_auth.yml
│   └── CONTRACTS.md                         # Input/output contracts
│
├── common/                                  # Shared infrastructure
│   ├── callback_plugins/
│   ├── library/
│   │   ├── modules/ (shared modules only)
│   │   └── module_utils/
│   ├── vars/
│   │   └── common_vars.yml
│   └── tasks/
│
├── input/                                   # Default input templates
│   ├── discovery/
│   │   ├── discovery_config.yml
│   │   └── network_spec.yml
│   └── orchestrator/
│       ├── orchestrator_config.yml          # Was provision_config.yml
│       ├── network_spec.yml
│       └── pxe_mapping_file.csv
│
└── playbooks/                               # Remaining playbooks (unchanged)
    ├── prepare_oim/                         # Minus OpenCHAMI (stays for pulp, auth, etc.)
    ├── utils/
    └── input_validation/
```

## Input/Output Paths (Runtime)

### Discovery
- **Input:** `/opt/omnia/input/project_default/discovery/`
  - `discovery_config.yml`
  - `network_spec.yml`
- **Output:** `/opt/omnia/output/project_default/discovery/`
  - `bmc_pxe_mapping_file.csv`
  - `bmc_discovery_report.csv`

### Orchestrator
- **Input:** `/opt/omnia/input/project_default/orchestrator/`
  - `orchestrator_config.yml`
  - `network_spec.yml`
  - `pxe_mapping_file.csv` (external contract from discovery)
- **Output:** `/opt/omnia/output/project_default/orchestrator/`
  - `functional_groups_config.yml`
  - `nodes.yaml`, `hostname.yaml`
  - BSS/cloud-init configurations

## PXE Mapping Contract

```
Discovery                        Orchestrator
   │                                  │
   │  bmc_pxe_mapping_file.csv        │
   │  ──────────────────────────>     │
   │                                  │
   │  Columns:                        │  Consumed by:
   │  FUNCTIONAL_GROUP_NAME           │  generate_functional_groups
   │  GROUP_NAME                      │  provision_validations
   │  SERVICE_TAG                     │  configure_ochami (nodes.yaml)
   │  PARENT_SERVICE_TAG              │  bmc_group_data.csv template
   │  HOSTNAME                        │  hostname.yaml template
   │  ADMIN_MAC                       │  BSS boot params
   │  ADMIN_IP                        │  nodes.yaml (interfaces)
   │  BMC_MAC                         │  nodes.yaml
   │  BMC_IP                          │  telemetry, bmc inventory
   │  IB_NIC_NAME                     │  network config
   │  IB_IP                           │  network config
```

## Image Resolution Flow (Phase 5)

```
pxe_mapping_file.csv
    │
    ▼
FUNCTIONAL_GROUP_NAME (e.g., slurm_node_aarch64)
    │
    ▼
Image pattern: rhel-{FUNCTIONAL_GROUP_NAME}{naming_suffix}{compute_image_suffix}
    │
    ▼
S3 lookup: s3://boot-images/{FUNCTIONAL_GROUP_NAME}/rhel-{pattern}/
    │
    ├── vmlinuz-{version}      → kernel
    ├── initramfs-{version}    → initrd
    └── rhel{os_ver}-rhel-{pattern}-{os_ver}  → rootfs
    │
    ▼
BSS boot params configured per functional group
    │
    ▼
PXE Boot
```

---

## Phase 2 – Discovery Domain Refactor (COMPLETED)

**Created:** `src/discovery/`

### File Moves and Changes

| Original | New Location | Change |
|----------|-------------|--------|
| `src/playbooks/discovery/discovery.yml` | `src/discovery/discovery.yml` | Rewritten: domain-specific paths, `discovery_input_dir`/`discovery_output_dir` |
| `src/playbooks/discovery/roles/ome_discovery/` | `src/discovery/roles/ome_discovery/` | Recreated: updated var refs to use `discovery_input_dir`/`discovery_output_dir` |
| `src/playbooks/discovery/ansible.cfg` | `src/discovery/ansible.cfg` | Updated: library paths to `../common/`, new log path |
| `src/input/discovery_config.yml` | `src/input/discovery/discovery_config.yml` | Domain-specific input template |
| `src/input/network_spec.yml` | `src/input/discovery/network_spec.yml` | Independent copy for discovery |

### Key Architectural Changes
- Discovery outputs now go to `/opt/omnia/output/<project>/discovery/` instead of `input_project_dir`
- PXE mapping file gets a timestamped name plus a `latest` symlink
- Discovery report also written to output directory
- No dependency on provision/orchestrator internals
- Still depends on shared utilities: `include_input_dir`, `input_validation`, `credential_utility`

---

## Phase 3 – Orchestrator Domain Refactor (COMPLETED)

**Created:** `src/orchestrator/`

### File Moves and Changes

| Original | New Location | Change |
|----------|-------------|--------|
| `src/playbooks/provision/provision.yml` | `src/orchestrator/orchestrator.yml` | Rewritten: domain-specific paths, orchestrator naming |
| `src/playbooks/provision/ansible.cfg` | `src/orchestrator/ansible.cfg` | Updated: library paths, new log path |
| `src/playbooks/provision/roles/provision_validations/` | `src/orchestrator/roles/orchestrator_validations/` | Renamed role |
| `src/playbooks/provision/roles/configure_ochami/` | `src/orchestrator/roles/configure_ochami/` | Copied (same functionality) |
| `src/playbooks/provision/roles/passwordless_ssh/` | `src/orchestrator/roles/passwordless_ssh/` | Copied |
| `src/playbooks/provision/roles/k8s_config/` | `src/orchestrator/roles/k8s_config/` | Copied |
| `src/playbooks/provision/roles/slurm_config/` | `src/orchestrator/roles/slurm_config/` | Copied |
| `src/playbooks/provision/roles/mount_config/` | `src/orchestrator/roles/mount_config/` | Copied |
| `src/playbooks/provision/roles/openldap/` | `src/orchestrator/roles/openldap/` | Copied |
| `src/playbooks/provision/roles/telemetry/` | `src/orchestrator/roles/telemetry/` | Copied |
| `src/common/vars/openchami_vars.yml` | `src/orchestrator/vars/openchami_vars.yml` | Orchestrator-owned copy |
| `src/common/vars/openchami_image_cmd.yml` | `src/orchestrator/vars/openchami_image_cmd.yml` | Orchestrator-owned copy |
| `src/common/tasks/common/openchami_auth.yml` | `src/orchestrator/tasks/openchami_auth.yml` | Updated: `include_vars` path to `playbook_dir` |
| `src/input/provision_config.yml` | `src/input/orchestrator/orchestrator_config.yml` | Renamed, domain-specific |
| `src/input/network_spec.yml` | `src/input/orchestrator/network_spec.yml` | Independent copy |
| `src/input/pxe_mapping_file.csv` | `src/input/orchestrator/pxe_mapping_file.csv` | Template with instructions |

---

## Phase 4 – OpenCHAMI Ownership Migration (COMPLETED)

**Moved:** `src/playbooks/prepare_oim/roles/deploy_containers/openchami/` → `src/orchestrator/roles/deploy_openchami/`

### Migration Summary

The OpenCHAMI deployment logic has been moved from `prepare_oim` into the orchestrator domain as `roles/deploy_openchami/`. This consolidates all OpenCHAMI lifecycle management under the orchestrator:

| Responsibility | Role | Location |
|---------------|------|----------|
| Deploy OpenCHAMI containers | `deploy_openchami` | `src/orchestrator/roles/deploy_openchami/` |
| Configure OpenCHAMI (nodes, BSS, cloud-init) | `configure_ochami` | `src/orchestrator/roles/configure_ochami/` |
| OpenCHAMI authentication | `openchami_auth.yml` | `src/orchestrator/tasks/openchami_auth.yml` |
| OpenCHAMI variables | `openchami_vars.yml` | `src/orchestrator/vars/openchami_vars.yml` |
| OpenCHAMI image commands | `openchami_image_cmd.yml` | `src/orchestrator/vars/openchami_image_cmd.yml` |

### Impact on prepare_oim

`prepare_oim.yml` retains ownership of non-OpenCHAMI container deployments:
- `deploy_containers/common` — common container setup
- `deploy_containers/pulp` — Pulp repository server
- `deploy_containers/auth` — authentication services
- `deploy_containers/postgres` — PostgreSQL
- `deploy_containers/build_stream` — CI/CD build stream

The OpenCHAMI include in `prepare_oim.yml` should be replaced with a delegation
to `orchestrator.yml` or a standalone `deploy_openchami.yml` playbook.

---

## Phase 5 – Functional Group Image Resolution (DESIGN)

### Current Implementation

Image resolution is performed in `orchestrator_validations/validate_image.yml`:

1. Each functional group name from `pxe_mapping_file.csv` is iterated
2. An S3 search pattern is built: `rhel-{functional_group_name}{naming_suffix}{compute_image_suffix}`
3. `s3cmd ls` queries `s3://boot-images` for matching kernel/initrd files
4. Validated images are stored in `validated_images` dict: `{fg_name: {kernel, initrd}}`
5. BSS boot params are configured per functional group using the validated images

### naming_suffix Construction

```
naming_suffix = "_omnia_" + omnia_version
              + ("_k8s_" + k8s_version  if service_kube_* group)
```

### Image Path in BSS Template

```
s3://boot-images/{fg_name}/rhel-{fg_name}{naming_suffix}{bs_suffix}/
    rhel{os_version}-rhel-{fg_name}{naming_suffix}{bs_suffix}-{os_version}
```

### Data Contract

The `validated_images` fact serves as the contract between validation and BSS configuration:

```yaml
validated_images:
  slurm_node_aarch64:
    kernel: "boot-images/slurm_node_aarch64/rhel-.../vmlinuz-5.14.0"
    initrd: "boot-images/slurm_node_aarch64/rhel-.../initramfs-5.14.0.img"
  service_kube_node_x86_64:
    kernel: "boot-images/service_kube_node_x86_64/rhel-.../vmlinuz-5.14.0"
    initrd: "boot-images/service_kube_node_x86_64/rhel-.../initramfs-5.14.0.img"
```

### No Changes Required

The image resolution flow is already cleanly contained within the orchestrator domain
(`orchestrator_validations` + `configure_ochami`). No cross-domain dependencies exist.

---

## Phase 6 – Repository Readiness Assessment

### Classification for Independent Repositories

#### Discovery Repository (`omnia-discovery`)

**Self-contained:** Yes, with shared dependency on `src/common/`

| Component | Status | Notes |
|-----------|--------|-------|
| Entrypoint | ✅ `src/discovery/discovery.yml` | Independent |
| Roles | ✅ `src/discovery/roles/ome_discovery/` | Independent |
| Python modules | ⚠️ In `src/common/library/modules/` | Needs copy or submodule |
| Callback plugins | ⚠️ In `src/common/callback_plugins/` | Needs copy or submodule |
| Input validation | ⚠️ In `src/playbooks/input_validation/` | Shared utility |
| Credential utility | ⚠️ In `src/playbooks/utils/credential_utility/` | Shared utility |
| include_input_dir | ⚠️ In `src/playbooks/utils/roles/include_input_dir/` | Shared utility |

**Modules to include in discovery repo:**
- `ome_server_inventory.py`
- `generate_pxe_mapping.py`
- `generate_discovery_report.py`
- Related `module_utils/` (OME-specific utils)

#### Orchestrator Repository (`omnia-orchestrator`)

**Self-contained:** Yes, with shared dependency on `src/common/`

| Component | Status | Notes |
|-----------|--------|-------|
| Entrypoint | ✅ `src/orchestrator/orchestrator.yml` | Independent |
| Roles | ✅ 9 roles in `src/orchestrator/roles/` | Independent |
| OpenCHAMI vars | ✅ `src/orchestrator/vars/` | Owned |
| OpenCHAMI auth | ✅ `src/orchestrator/tasks/` | Owned |
| Python modules | ⚠️ In `src/common/library/modules/` | Needs copy or submodule |
| Callback plugins | ⚠️ In `src/common/callback_plugins/` | Shared |
| Utils playbooks | ⚠️ In `src/playbooks/utils/` | Shared |

**Modules to include in orchestrator repo:**
- `generate_functional_groups.py`
- `generate_xname_in_mapping_file.py`
- `functional_group_parser.py`
- `fetch_mapping_details.py`
- Related `module_utils/` (input_validation, common_utils)

#### Shared Library (`omnia-common`)

Would become a git submodule or vendored dependency:

| Component | Consumers |
|-----------|-----------|
| `callback_plugins/omnia_default` | Both |
| `library/module_utils/` | Both |
| `vars/common_vars.yml` | Both |
| `vars/image_vars.yml` | Orchestrator |

### Coupling Points Requiring Resolution

1. **`include_input_dir` role** — Both domains use this. Options:
   - Keep in `omnia-common` submodule
   - Inline simplified version in each domain
   - Each domain already sets its own paths; dependency is minimal

2. **`input_validation/validate_config.yml`** — Shared validation framework. Options:
   - Include as submodule
   - Each domain brings its own validation

3. **`credential_utility/`** — Vault decryption. Options:
   - Include as submodule
   - Duplicate (small codebase)

4. **`generate_functional_groups` utility** — Currently a `utils/` playbook.
   - Move into orchestrator domain entirely (it only serves orchestrator)

### Recommended Repository Split Strategy

```
omnia-discovery/
├── src/
│   ├── discovery/          (from src/discovery/)
│   ├── common/             (git submodule → omnia-common)
│   └── input/discovery/    (templates)

omnia-orchestrator/
├── src/
│   ├── orchestrator/       (from src/orchestrator/)
│   ├── common/             (git submodule → omnia-common)
│   └── input/orchestrator/ (templates)

omnia-common/               (shared git submodule)
├── callback_plugins/
├── library/
│   ├── modules/            (only truly shared modules)
│   └── module_utils/
├── vars/
└── tasks/

omnia/                      (meta-repo, optional)
├── src/
│   ├── discovery/          → submodule omnia-discovery
│   ├── orchestrator/       → submodule omnia-orchestrator
│   ├── common/             → submodule omnia-common
│   └── playbooks/          (prepare_oim, utils, etc.)
```

### Migration Path

1. ✅ Phase 1-4 complete: domains created, contracts defined
2. Next: Move domain-specific Python modules into domain `library/` directories
3. Next: Update `ansible.cfg` library paths to reference local `library/` first
4. Next: Extract `omnia-common` as separate repo
5. Next: Set up git submodule references
6. Next: CI/CD pipeline per domain
