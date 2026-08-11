# Catalog Migration Design: Replace functional_group_packages.yml with catalog JSON

## Status: IMPLEMENTED

---

## 1. Objective

Replace the current `functional_group_packages.yml` (flat YAML mapping functional groups
to RPM package names) with the new `catalog_rhel.json` catalog structure. Simultaneously
adapt to the updated `repo_status.yml` format which replaces the `repo_manager.*` and
`rpm_repos.*` sections with a nested `repositories` structure.

### 1.1 Phased Approach

| Phase | Scope | Deliverables |
|-------|-------|--------------|
| **Phase 1 (Current)** | RHEL only | Catalog migration, new repo_status format, dual-mode (config/catalog), RHEL minor version support (10.0, 10.1, 10.2), unified build flow |
| **Phase 2 (Future)** | Ubuntu support | Ubuntu build templates, `deb` package type filter, `apt` package manager, `catalog_ubuntu.json` |

**Phase 1 design principle**: All code is structured so that when Ubuntu support is added
in Phase 2, **no redesign is needed** — only new templates and a `deb` filter branch.
The catalog adapter, unified flow, template matrix, and OS-agnostic variable names are
all designed to accommodate Ubuntu without architectural changes.

---

## 2. Current Architecture

### 2.1 Data Files

| File | Producer | Location | Consumer |
|------|----------|----------|----------|
| `repo_status.yml` | repo_manager | `/opt/omnia/repo_manager/output/{project}/` | `load_repo_status.yml`, `fetch_repo_manager_repos.yml` |
| `functional_group_packages.yml` | User (manual) | `input/{project}/` | `fetch_build_packages/tasks/main.yml` (when source=`"config"`) |
| `catalog_{name}.json` | repo_manager | `/opt/omnia/catalog/` | `fetch_build_packages/tasks/main.yml` (when source=`"catalog"`) |

### 2.2 Current repo_status.yml Structure (OLD)

```yaml
overall_status: "success"
cluster_os_type: "rhel"
cluster_os_version: "10.0"
repo_manager:
  port: 2225
  package_list: "/path/to/functional_group_packages.yml"
  certificates:
    server_crt: "/etc/omnia/certs/pulp_webserver.crt"
rpm_repos:
  x86_64:
    baseos: "https://host:port/pulp/.../baseos/"
    appstream: "https://host:port/pulp/.../appstream/"
  aarch64:
    baseos: "https://host:port/pulp/.../baseos/"
user_repos:
  x86_64:
    custom_repo: "https://host:port/pulp/.../custom/"
```

### 2.3 Current functional_group_packages.yml Structure (OLD)

```yaml
base_packages:
  - systemd
  - kernel
  - dracut

functional_groups:
  slurm_node_x86_64:
    packages:
      - munge
      - slurm-slurmd
  slurm_control_node_x86_64:
    packages:
      - slurm-slurmctld
      - mariadb-server
```

### 2.4 Current Data Flow

```
image_build_config.yml
  |-- repo_manager_output_path --> repo_status.yml
  |-- functional_groups_source: "config" | "repo_status"
  |-- functional_groups: [{name: "slurm_node_x86_64"}, ...]

validate_prereqs.yml
  |-- loads image_build_config.yml
  |-- stat check: repo_status.yml

load_repo_status.yml
  |-- include_vars: repo_status.yml
  |-- assert: repo_manager.port exists
  |-- resolves: package_list_path from repo_manager.package_list
  |-- stat check: functional_group_packages.yml
  |-- assert: repo manager certificate exists (optional)
  |-- builds: repo_manager_repos_x86_64 from rpm_repos.x86_64 + user_repos.x86_64
  |-- builds: repo_manager_repos_aarch64 from rpm_repos.aarch64 + user_repos.aarch64
  |-- output shape: [{name: "baseos", base_url: "https://...", gpg: ""}]

build_image_x86_64.yml
  |-- writes: functional_groups_config.yml from image_build_config.functional_groups
  |-- calls: check_functional_group.yml (validates arch-specific groups exist)
  |-- calls: fetch_build_packages role

fetch_build_packages/tasks/main.yml
  |-- include_vars: functional_group_packages.yml --> _fg_pkg_mapping
  |-- sets: base_image_packages = _fg_pkg_mapping.base_packages
  |-- when source == "repo_status": auto-detect groups from _fg_pkg_mapping.functional_groups
  |-- builds: compute_images_dict = {fg_name: {functional_group, packages: [rpm_names]}}
  |-- calls: fetch_repo_manager_repos.yml

fetch_repo_manager_repos.yml
  |-- sets: rhel_arch_repos = repo_manager_repos_{build_arch}
  |-- fallback: pulp CLI query

build_os_images role
  |-- templates: rhel-base-config.yaml.j2 uses rhel_arch_repos + base_image_packages
  |-- templates: rhel-compute-config.yaml.j2 uses rhel_arch_repos + compute_packages
  |-- iterates: compute_images_dict | dict2items
```

**Problems with current flow:**
- `functional_group_packages.yml` is produced by repo_manager but consumed by image_build_manager
  — tight coupling, no clean separation of concerns
- `package_list_path` is resolved from `repo_manager.package_list` inside `repo_status.yml`
  — forces dependency on repo_status for package mapping path
- `functional_groups_source: "repo_status"` auto-detects from the same file
  — no way to use a catalog without repo_status pointing to it

### 2.5 Variable Shape Contract (templates expect these exact shapes)

```yaml
# rhel_arch_repos — list of dicts consumed by ALL 4 config templates
rhel_arch_repos:
  - name: "baseos"
    base_url: "https://host:port/pulp/.../baseos/"
    gpg: ""

# base_image_packages — flat list of RPM names consumed by base config templates
base_image_packages:
  - systemd
  - kernel

# compute_images_dict — dict keyed by functional group name
compute_images_dict:
  slurm_node_x86_64:
    functional_group: slurm_node_x86_64
    packages:
      - munge
      - slurm-slurmd
```

---

## 3. New Data Structures

### 3.1 New repo_status.yml Structure

```yaml
overall_status: "success"
cluster_os_type: "rhel"
repo_config: "partial"

repositories:
  "10.0":
    x86_64:
      baseos:
        url: "https://host:port/pulp/.../baseos/"
      appstream:
        url: "https://host:port/pulp/.../appstream/"
      ldms: {}                 # empty = not synced
    aarch64:
      baseos: {}               # empty = not synced

registries:
  user_registry1:
    port: 443
    tls:
      capath: "/path/to/ca.crt"

file_repos:
  x86_64:
    git:
      karavi_observability: "https://host:port/pulp/.../git/karavi-observability/"
    tarball:
      sionlib: "https://host:port/pulp/.../tarball/sionlib/"
    manifest:
      calico_v3_31_4: "https://host:port/pulp/.../manifest/calico-v3.31.4/"
    pip_module:
      kubernetes_33_1_0: "https://host:port/pypi/.../pip_module/kubernetes==33.1.0/"
  aarch64: {}

tarball_base_url: "https://..."
manifest_base_url: "https://..."
pip_base_url: "https://..."
git_base_url: "https://..."
offline_tarball_path: "https://..."
offline_manifest_path: "https://..."
offline_pip_module_path: "https://..."
offline_git_path: "https://..."
offline_shell_path: "https://..."
offline_iso_path: "https://..."
offline_ansible_galaxy_collection_path: "https://..."
```

**Key changes from old format:**
- **Removed**: `repo_manager`, `repo_manager.port`, `repo_manager.package_list`,
  `repo_manager.certificates`, `rpm_repos`, `user_repos`, `cluster_os_version`
- **Added**: `repositories.{version}.{arch}.{repo_name}.url` nested structure
- **Added**: `registries` section for container registry TLS configs
- **Added**: `file_repos.{arch}.{type}.{name}` for git/tarball/manifest/pip URLs
- **Added**: `offline_*_path` base URL variables
- Empty `{}` means "not synced" (skip this repo)

### 3.2 New catalog_rhel.json Structure

```json
{
  "catalog": {
    "name": "omnia services catalog - rhel 10.0",
    "version": "1.0",
    "identifier": "omnia-services-rhel-10-0",
    "functionallayer": [
      {
        "name": "slurm_node_rhel_10_0_x86_64",
        "components": ["baseos_group_10.0", "slurm_custom_group", "slurm_node_group"]
      }
    ],
    "groups": {
      "baseos_group_10.0": {
        "name": "baseos_group_10.0",
        "type": "group",
        "components": ["systemd", "kernel", "dracut", ...]
      },
      "slurm_node_group": {
        "components": ["slurm_slurmd", "kernel_devel", "kernel_headers"]
      }
    },
    "packages": {
      "slurm_slurmd": {
        "name": "slurm-slurmd",
        "packagetype": "rpm",
        "sources": [
          {"architecture": "x86_64", "reponame": "slurm_custom", "name": "rhel", "version": ["10.0"]},
          {"architecture": "aarch64", "reponame": "slurm_custom", "name": "rhel", "version": ["10.0"]}
        ]
      },
      "kube_vip": {
        "name": "ghcr.io/kube-vip/kube-vip",
        "packagetype": "image",
        "tag": "v0.8.9",
        "sources": [
          {"architecture": "x86_64", "registry": "ghcr.io", "name": "rhel", "version": ["10.0"]}
        ]
      }
    }
  }
}
```

**Key concepts:**
- **functionallayer**: Declares which groups compose each image variant (replaces old functional_groups)
- **groups**: Defines component groups — each lists package keys (not RPM names)
- **packages**: Individual package metadata — `name` is the real installable name,
  `packagetype` is one of: `rpm`, `image`, `pip_module`, `tarball`, `manifest`, `git`, `rpm_repo`
- **sources**: Per-architecture availability with `reponame` (for RPMs) or `registry` (for images)

### 3.3 Functional Layer Naming Convention Change

| Old Name (functional_group_packages.yml) | New Name (catalog functionallayer) |
|------------------------------------------|-------------------------------------|
| `os_x86_64` | `baseos_rhel_10_0_x86_64` |
| `slurm_node_x86_64` | `slurm_node_rhel_10_0_x86_64` |
| `slurm_control_node_x86_64` | `slurm_control_node_rhel_10_0_x86_64` |
| `service_kube_control_plane_x86_64` | `service_kube_control_plane_rhel_10_0_x86_64` |
| `service_kube_control_plane_first_x86_64` | `service_kube_control_plane_first_rhel_10_0_x86_64` |
| `service_kube_node_x86_64` | `service_kube_node_rhel_10_0_x86_64` |
| `login_node_x86_64` | `login_node_rhel_10_0_x86_64` |
| `login_compiler_node_x86_64` | `login_compiler_node_rhel_10_0_x86_64` |
| `os_aarch64` | `baseos_rhel_10_0_aarch64` |
| `slurm_node_aarch64` | `slurm_node_rhel_10_0_aarch64` |
| `login_node_aarch64` | `login_node_rhel_10_0_aarch64` |
| `login_compiler_node_aarch64` | `login_compiler_node_rhel_10_0_aarch64` |

**Pattern**: `{role}_{os}_{os_version}_{arch}` (e.g., `slurm_node_rhel_10_0_x86_64`)

This pattern naturally supports RHEL minor versions: `slurm_node_rhel_10_2_x86_64`
for RHEL 10.2. In Phase 2, Ubuntu will follow the same pattern:
`slurm_node_ubuntu_24_04_x86_64`.

---

## 4. Phase 2: Future Ubuntu Support (NOT IN CURRENT SCOPE)

> **This section documents the future plan only.** No Ubuntu code, templates, or
> catalog samples are created in Phase 1. The Phase 1 architecture is designed so
> that Ubuntu can be added without redesign.

### 4.1 What Phase 2 Will Add

| Deliverable | Description |
|-------------|-------------|
| `catalog_ubuntu.json` | Ubuntu catalog with `deb` packagetype and Ubuntu package names |
| 4 Ubuntu templates | `ubuntu-base-config.yaml.j2`, `ubuntu-compute-config.yaml.j2`, thrillhouse variants |
| `deb` filter branch | Package type filter: `rpm` (RHEL) or `deb` (Ubuntu) based on `cluster_os_type` |
| Template matrix entries | Add `ubuntu` rows to `_template_matrix` in `build_os_images/vars/main.yml` |

### 4.2 Why No Redesign Will Be Needed

Phase 1 builds the following extension points for Ubuntu:

| Extension Point | Phase 1 State | Phase 2 Change |
|-----------------|---------------|----------------|
| `cluster_os_type` from `repo_status.yml` | Used for RHEL only (`rhel`) | Add `ubuntu` value |
| Package type filter in `parse_catalog.yml` | Hardcoded `rpm` | Add `deb` branch based on `cluster_os_type` |
| Template matrix in `build_os_images/vars/main.yml` | RHEL entries only | Add `ubuntu` entries |
| `CATALOG_FILE_PATH` env var | Points to RHEL catalog | Point to Ubuntu catalog |
| OS-agnostic variable names (`arch_repos`, etc.) | Aliases for `rhel_*` vars | Used directly by Ubuntu templates |
| Functional layer naming `{role}_{os}_{ver}_{arch}` | RHEL versions only | Add Ubuntu versions |

### 4.3 Ubuntu Template Differences (Reference)

When Ubuntu templates are created in Phase 2, key differences from RHEL:
- `pkg_manager: apt` instead of `dnf`
- APT source list syntax instead of YUM repo format
- Ubuntu meta-packages (`ubuntu-minimal`) instead of RHEL groups
- No GPG key handling (Ubuntu repos use signed Release files)

---

## 5. Catalog Adapter Design (Core Change)

### 5.1 Resolution Algorithm

The catalog adapter replaces `functional_group_packages.yml` loading with a three-step
resolution from catalog JSON:

```
Step 1: Load catalog JSON
  catalog = slurp + from_json(catalog_{os_type}.json)

Step 2: For each requested functionallayer matching build_arch:
  layer.components[] --> groups.{component}.components[] --> packages.{key}

Step 3: Partition resolved packages by packagetype:
  rpm           --> compute_packages (for image builder; Phase 2 adds deb)
  rpm_repo      --> repo enablement only (not installed as package)
  image         --> container_images (for future pre-pull)
  tarball       --> tarball_packages (for future download)
  pip_module    --> pip_packages (for future pip install)
  manifest      --> manifest_packages (for future kubectl apply)
  git           --> git_packages (for future git clone)
```

### 5.2 Base Image Package Resolution

Layer classification uses the **layer name prefix**, not component membership.
The `baseos_prefix` parameter (default: `baseos_group`) is split at `_group` to
derive the layer-level prefix `baseos`. This ensures:

- **Base OS layers** (name starts with `baseos`, e.g. `baseos_rhel_10_0_x86_64`):
  All component packages are collected into `base_image_packages`.
- **Compute layers** (any other name, e.g. `slurm_node_rhel_10_0_x86_64`):
  Only non-baseos component packages are collected. Baseos components within
  compute layers contribute their `os_version` but their packages are skipped
  (they are already in the base image).

> **Note**: The previous implementation classified layers based on whether they
> *contained* a baseos component, which incorrectly treated compute layers as
> baseos when they referenced `baseos_group_*`. This was fixed to use the layer
> name prefix instead.

### 5.3 Package Source Modes: "config" vs "catalog"

`functional_groups_source` determines both WHERE the list of groups comes from AND
HOW packages are resolved. Two clean modes, no fallback:

#### Mode 1: `"config"` (default) — Manual Package Mapping

```
Source file:  input/{project}/package_groups.yml
Location:     User-editable input file in project directory
Use case:     Manual control over exact packages per functional group
```

- Reads `package_groups.yml` from `{{ input_project_dir }}/`
- `os` / `os_version` fields → `cluster_os_type` / `cluster_os_version` / `rhel_tag`
- `base_packages` list → `base_image_packages`
- `functional_groups.{name}.packages` → `compute_images_dict`
- Functional groups to build: derived from `functional_groups` keys in `package_groups.yml`,
  filtered by architecture suffix (`_x86_64` / `_aarch64`)
- No separate `functional_groups` list needed in `image_build_config.yml`
- `service_k8s_version`: set to empty string (not available in this mode)
- **No catalog file required** — purely manual package control
- For multi-OS support, each OS project directory has its own `package_groups.yml`

#### Mode 2: `"catalog"` — Catalog-Driven Package Resolution

```
Source file:  Configurable via CATALOG_FILE_PATH environment variable (omnia.env)
Location:     $OMNIA_DATA_PATH/catalog/ (convention)
Use case:     Automated package resolution from repo_manager catalog
```

- Reads catalog JSON from `CATALOG_FILE_PATH` environment variable (set in `omnia.env`)
- Three-level resolution: `functionallayer` → `groups` → `packages`
- Filters by `packagetype` and `sources[].architecture`
- Extracts `cluster_os_type` from baseos group's `os` field (e.g. `rhel`)
- Extracts `cluster_os_version` from baseos group's `os_version` field (e.g. `10.0`)
- Extracts `service_k8s_version` from `kubeadm_*` package name
- Sets `catalog_identifier` fact for traceability
- Functional groups to build: auto-detected from `catalog.functionallayer[]` filtered by `build_arch`
- No separate `functional_groups` list needed in `image_build_config.yml`

#### Mode Comparison

| Concern | `"config"` | `"catalog"` |
|---------|-----------|------------|
| **Package source** | `input/{project}/package_groups.yml` | Path from `CATALOG_FILE_PATH` env var |
| **Package format** | Flat YAML (group → package list) | JSON (functionallayer → groups → packages) |
| **OS metadata source** | `os` / `os_version` fields in `package_groups.yml` | baseos group's `os` / `os_version` fields |
| **Group source** | Keys of `package_groups.yml` | `catalog.functionallayer[]` filtered by arch |
| **service_k8s_version** | Empty string | Extracted from catalog |
| **catalog_identifier** | Not set | Set from `catalog.identifier` |
| **User editable** | Yes (input file) | No (repo_manager produces it) |
| **When to use** | Custom/dev builds, override packages | Production builds, standard pipeline |

#### Removed: `"repo_status"` mode

The old `"repo_status"` mode is **removed** (not deprecated — deleted). It was a hybrid
that auto-detected groups from `functional_group_packages.yml` located via `repo_status.yml`.
The catalog mode fully replaces this with better structure and more metadata.

### 5.4 Output Variable Shapes (UNCHANGED)

The adapter outputs the exact same variable shapes that templates expect:

```yaml
# arch_repos — same shape as current rhel_arch_repos
arch_repos:
  - name: "baseos"
    base_url: "https://..."
    gpg: ""

# base_image_packages — flat list of installable package names
base_image_packages:
  - systemd
  - kernel

# compute_images_dict — dict keyed by functional group (layer) name
compute_images_dict:
  slurm_node_rhel_10_0_x86_64:
    functional_group: slurm_node_rhel_10_0_x86_64
    packages:
      - munge
      - slurm-slurmd
```

This preserves backward compatibility with ALL four build config templates.

### 5.5 Catalog Identifier as Universal Reference

The catalog JSON always contains a top-level `identifier` field:

```json
{
  "catalog": {
    "identifier": "omnia-services-rhel-10-0",
    ...
  }
}
```

**`catalog.identifier` is always present** — it is a mandatory field in every catalog file.
This means we can use it as the canonical key for:

- **Catalog validation**: Load the catalog and validate its `identifier` matches the expected
  OS type and version for the build.
- **Image naming**: Use `identifier` in image tags and S3 paths for traceability
  (e.g., `rhel-slurm_node_x86_64_omnia_2.2.0.0_k8s_1.35.1` includes catalog-derived version info).
- **Build metadata**: Store `catalog.identifier` in build output metadata for provenance tracking.
- **OS type and version derivation**: Parse `identifier` to extract OS type and version
  (e.g., `omnia-services-rhel-10-0` → `os_type=rhel`, `os_version=10.0`), providing a
  cross-check against `repo_status.yml` values.

```yaml
# Set catalog_identifier as a fact after loading
- name: Set catalog identifier
  ansible.builtin.set_fact:
    catalog_identifier: "{{ _catalog.identifier }}"
    cacheable: true
```

Since the identifier is always available, **both build-stream and standalone flows can
rely on it** as a stable reference — eliminating the need for separate catalog-discovery
logic between the two modes.

### 5.6 Unified Build Flow (Eliminate Build-Stream vs Standalone Split)

#### 5.6.1 Current Problem: Two Divergent Paths

The current playbooks have two separate code paths:

| Concern | Standalone Mode | Build-Stream Mode |
|---------|----------------|-------------------|
| **functional_groups source** | `image_build_config.yml` → writes `functional_groups_config.yml` | Extra-vars (`-e functional_groups=[...]`) |
| **Prerequisite validation** | `check_functional_group.yml` (loads `functional_groups_config.yml`) | `build_stream_prerequisite.yml` (validates `job_id`, `image_key`) |
| **functional_groups_config.yml** | Written from config, then read back | Skipped (not written) |
| **Package resolution** | `fetch_build_packages/tasks/main.yml` (same) | `fetch_build_packages/tasks/main.yml` (same) |
| **Build execution** | `build_os_images` role (same) | `build_os_images` role (same) |

The actual package resolution and build execution are **identical** in both modes.
The only differences are:
1. Where `functional_groups` comes from
2. Whether `job_id`/`image_key` are set (for build-stream status tracking)
3. Whether `functional_groups_config.yml` is written to disk

#### 5.6.2 New Design: Single Unified Flow

The unified flow handles BOTH config and catalog modes through a single code path.
The package source is determined by `functional_groups_source`, but the build execution
is identical regardless of mode.

```
┌──────────────────────────────────────────────────────────────┐
│                    UNIFIED BUILD FLOW                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Load package source (MODE-DEPENDENT)                     │
│     IF source == "catalog":                                  │
│       → slurp + from_json: catalog_file                      │
│       → set catalog_identifier                               │
│       → extract service_k8s_version (if k8s layers exist)    │
│     IF source == "config":                                   │
│       → include_vars: input/{project}/package_groups.yml     │
│       → service_k8s_version = "" (not available)             │
│                                                              │
│  2. Determine functional_groups (THREE sources, ONE var)     │
│     Priority order:                                          │
│     a) extra-vars (build-stream: -e functional_groups)       │
│     b) image_build_config.yml (standalone: explicit list)    │
│     c) catalog auto-detect (catalog mode only)               │
│                                                              │
│  3. Validate functional_groups (MODE-DEPENDENT)              │
│     IF source == "catalog":                                  │
│       → assert each group exists in catalog.functionallayer[]│
│     IF source == "config":                                   │
│       → assert each group exists in package_groups.yml       │
│     → fail fast if group not found                           │
│                                                              │
│  4. Set build-stream metadata (if applicable)                │
│     → job_id, image_key (empty string if standalone)         │
│                                                              │
│  5. Resolve packages (MODE-DEPENDENT, SAME OUTPUT SHAPE)     │
│     IF source == "catalog":                                  │
│       → functionallayer → groups → packages (3-level)        │
│       → filter by packagetype == 'rpm' + architecture        │
│     IF source == "config":                                   │
│       → base_packages + functional_groups.{name}.packages    │
│     → OUTPUT: base_image_packages, compute_images_dict       │
│                                                              │
│  6. Build images (COMMON for all — identical regardless)     │
│     → build_os_images role                                   │
└──────────────────────────────────────────────────────────────┘
```

#### 5.6.3 What Changes

**Eliminated:**
- `functional_groups_config.yml` intermediate file (no longer needed)
- `check_functional_group.yml` loading from disk (validate against catalog in-memory)
- Separate `when: enable_build_stream` / `when: not enable_build_stream` branches
  for functional group handling
- `functional_groups_source: "repo_status"` option (replaced by `"catalog"`)

**Simplified in playbooks (`build_image_x86_64.yml`, `build_image_aarch64.yml`):**

```yaml
# BEFORE (two separate plays):

# Play: Fetch build_stream prerequisites
- name: Fetch build_stream prerequisites
  ansible.builtin.include_role:
    name: fetch_build_packages
    tasks_from: build_stream_prerequisite.yml
  when: enable_build_stream | default(false) | bool

# Play: Generate and verify functional groups (standalone only)
- name: Write functional_groups_config.yml from image_build_config.yml (standalone)
  when:
    - standalone_mode | default(false) | bool
    - not (enable_build_stream | default(false) | bool)
  ...

# AFTER (single unified play):

# Play: Resolve functional groups
- name: Resolve functional groups
  block:
    - name: Set functional_groups from extra-vars (build-stream)
      ansible.builtin.set_fact:
        functional_groups: "{{ functional_groups }}"
        build_stream_job_id: "{{ job_id | default('') }}"
        image_key: "{{ image_key | default('') }}"
      when: functional_groups is defined and (enable_build_stream | default(false) | bool)

    - name: Set functional_groups from config (standalone)
      ansible.builtin.set_fact:
        functional_groups: "{{ functional_groups }}"
      when: not (enable_build_stream | default(false) | bool) and functional_groups is defined

    # Catalog mode: validate against catalog.functionallayer[]
    - name: Validate groups exist in catalog
      ansible.builtin.assert:
        that:
          - item.name in (_catalog.functionallayer | map(attribute='name') | list)
        fail_msg: "Functional group '{{ item.name }}' not found in catalog {{ catalog_identifier }}"
      loop: "{{ functional_groups }}"
      when: functional_groups_source == 'catalog'

    # Config mode: validate against package_groups.yml keys
    - name: Validate groups exist in package_groups
      ansible.builtin.assert:
        that:
          - item.name in (_fg_pkg_mapping.functional_groups | default({}) | list)
        fail_msg: "Functional group '{{ item.name }}' not found in package_groups.yml"
      loop: "{{ functional_groups }}"
      when: functional_groups_source == 'config'
```

**`build_stream_prerequisite.yml` becomes a thin wrapper** that only validates
build-stream-specific inputs (`job_id`, `image_key`). It no longer handles
functional group normalization.

#### 5.6.4 functional_groups_source Modes (Final)

Two clean modes, no fallback, no `"repo_status"` mode:

| Mode | `functional_groups_source` | Package Source | Group Source |
|------|--------------------------|----------------|-------------|
| **Manual** | `"config"` (default) | `input/{project}/package_groups.yml` | `functional_groups` list in config or extra-vars |
| **Catalog** | `"catalog"` | `CATALOG_FILE_PATH` env var | `functional_groups` list in config, extra-vars, OR auto-detect from catalog |

Build-stream mode always uses explicit functional_groups from extra-vars, so
`functional_groups_source` only affects WHERE packages are resolved from.

### 5.7 Extracting service_k8s_version from Catalog

#### 5.7.1 Current Problem

`service_k8s_version` is currently set to empty string in `fetch_build_packages/tasks/main.yml`
(line 88) and must be resolved later by `image_package_collector.py` from `software_config.json`.
This creates an unnecessary dependency on `software_config.json` when the catalog already
contains the version information.

#### 5.7.2 Catalog Evidence

The catalog contains Kubernetes packages with embedded version numbers:

```json
"kubeadm_1_35_1": {
  "name": "kubeadm-1.35.1",
  "packagetype": "rpm",
  "sources": [{"architecture": "x86_64", "reponame": "kubernetes-v1-35", ...}]
},
"kube_apiserver": {
  "name": "registry.k8s.io/kube-apiserver",
  "packagetype": "image",
  "tag": "v1.35.1",
  ...
}
```

The `service_k8s_common_group` lists `kubeadm_1_35_1` and `kubelet_1_35_1` as components.

#### 5.7.3 Extraction Algorithm

Extract `service_k8s_version` from the catalog by finding the `kubeadm` package:

```yaml
# Step 1: Find kubeadm package in catalog.packages
# Pattern: key starts with "kubeadm_" and packagetype == "rpm"
- name: Extract service_k8s_version from catalog kubeadm package
  ansible.builtin.set_fact:
    service_k8s_version: >-
      {% set ns = namespace(version='') -%}
      {% for pkg_key, pkg_data in _catalog.packages.items() -%}
        {% if pkg_key.startswith('kubeadm_') and pkg_data.packagetype == 'rpm' -%}
          {% set ns.version = pkg_data.name | regex_replace('^kubeadm-', '') -%}
        {% endif -%}
      {% endfor -%}
      {{ ns.version }}
    cacheable: true

# Result: service_k8s_version = "1.35.1"
```

**Extraction order** (catalog mode only):
1. Extract from catalog `kubeadm_*` package name (primary)
2. Extract from catalog `kube_apiserver` image tag (secondary)
3. Empty string (no k8s layers in this catalog)

In config mode, `service_k8s_version` is always empty string.

#### 5.7.4 Where This Replaces Current Code

**Current** (`fetch_build_packages/tasks/main.yml` line 86-89):
```yaml
- name: Set service_k8s_version (empty unless overridden)
  ansible.builtin.set_fact:
    service_k8s_version: ""
    cacheable: true
```

**New** (in `parse_catalog.yml`):
```yaml
- name: Extract service_k8s_version from catalog
  ansible.builtin.set_fact:
    service_k8s_version: >-
      {% set ns = namespace(version='') -%}
      {% for pkg_key, pkg_data in _catalog.packages.items() -%}
        {% if pkg_key.startswith('kubeadm_') and pkg_data.packagetype == 'rpm' -%}
          {% set ns.version = pkg_data.name | regex_replace('^kubeadm-', '') -%}
        {% endif -%}
      {% endfor -%}
      {{ ns.version }}
    cacheable: true

- name: Debug - service_k8s_version from catalog
  ansible.builtin.debug:
    msg: "service_k8s_version resolved from catalog: '{{ service_k8s_version }}'"
  when: service_k8s_version | length > 0
```

#### 5.7.5 Impact on Downstream

`service_k8s_version` is consumed by:

| Consumer | Usage | Impact |
|----------|-------|--------|
| `build_image_common_x86_64.yml` | `k8s_suffix: "_k8s_{{ service_k8s_version }}"` | Now populated from catalog instead of empty |
| `build_image_common_aarch64.yml` | Same `k8s_suffix` | Same |
| `build_os_images/tasks/main.yml` | `_fg_k8s_sfx` for `service_kube_*` groups | Now has correct version from catalog |
| `image_package_collector.py` | Extracts from `software_config.json` if not provided | Receives pre-populated value, skips `software_config.json` lookup |

With `service_k8s_version` resolved from the catalog, the `image_package_collector.py`
fallback to `software_config.json` becomes a safety net rather than the primary source.

### 5.8 Catalog Path Resolution

#### 5.8.1 Design Decision: CATALOG_FILE_PATH Environment Variable

The catalog file path is set via the `CATALOG_FILE_PATH` environment variable
(defined in `omnia.env`), not in `image_build_config.yml`.

**Why env var (not config field):**
- **Consistent with omnia.env pattern** — Environment-level settings belong in `omnia.env`
- **Multiple catalogs supported** — Users can override per-run via env var
  (e.g., `CATALOG_FILE_PATH=/opt/omnia/catalog/catalog_rhel_10_2.json`)
- **Simpler config** — Fewer fields in `image_build_config.yml`
- **Default provided** — `omnia.env` ships with a sensible default

#### 5.8.2 Catalog Directory Convention

Catalog files live under `$OMNIA_DATA_PATH/catalog/`:

```
/opt/omnia/catalog/
├── catalog_rhel.json              # RHEL 10.0 default
├── catalog_rhel_10_2.json          # RHEL 10.2 variant
└── catalog_custom_dev.json         # Custom development catalog
```

This is a **convention** (not enforced) — the user can place the catalog file
anywhere and set `CATALOG_FILE_PATH` to point to it.

#### 5.8.3 Configuration in omnia.env

```bash
# Catalog JSON file path (used when functional_groups_source: "catalog")
# Contains functional layers, groups, and package definitions.
# Override per-run: CATALOG_FILE_PATH=/path/to/custom_catalog.json
CATALOG_FILE_PATH="${OMNIA_DATA_PATH}/catalog/catalog_rhel.json"
```

#### 5.8.4 Implementation in validate_prereqs.yml

```yaml
# catalog_file fact is set from CATALOG_FILE_PATH env var
catalog_file: "{{ lookup('ansible.builtin.env', 'CATALOG_FILE_PATH') | default('', true) }}"

# Validate catalog file exists (catalog mode)
- name: Fail if CATALOG_FILE_PATH env var is not set
  ansible.builtin.fail:
    msg: "CATALOG_FILE_PATH environment variable is not set."
  when:
    - functional_groups_source == 'catalog'
    - catalog_file | length == 0

- name: Stat catalog file
  ansible.builtin.stat:
    path: "{{ catalog_file }}"
  register: _catalog_check
  when: functional_groups_source == 'catalog'
```

#### 5.8.5 Implementation in fetch_build_packages/tasks/main.yml

```yaml
# When source is "catalog" — load catalog JSON
- name: Load catalog JSON
  when: functional_groups_source == 'catalog'
  block:
    - name: Slurp catalog JSON
      ansible.builtin.slurp:
        src: "{{ catalog_file }}"
      register: _catalog_raw

    - name: Parse catalog JSON
      ansible.builtin.set_fact:
        _catalog: "{{ (_catalog_raw.content | b64decode | from_json).catalog }}"
        catalog_identifier: "{{ (_catalog_raw.content | b64decode | from_json).catalog.identifier }}"
        cacheable: true

# When source is "config" — load package_groups.yml
- name: Load package_groups.yml
  when: functional_groups_source == 'config'
  block:
    - name: Load package_groups.yml from input dir
      ansible.builtin.include_vars:
        file: "{{ input_project_dir }}/package_groups.yml"
        name: _fg_pkg_mapping
```

#### 5.8.6 No Fallback, No Resolution Chain

This is a clean new design:
- If `functional_groups_source: "catalog"` and `CATALOG_FILE_PATH` is unset or file missing → **fail**
- If `functional_groups_source: "config"` and `package_groups.yml` doesn't exist → **fail**
- No auto-detection between modes
- No backward compatibility with old `functional_group_packages.yml` location

#### 5.8.7 Runtime Path Examples

```bash
# RHEL 10.0 production build (default in omnia.env):
CATALOG_FILE_PATH="/opt/omnia/catalog/catalog_rhel.json"

# RHEL 10.2 upgrade test (override per-run):
CATALOG_FILE_PATH="/opt/omnia/catalog/catalog_rhel_10_2.json"

# Developer custom catalog:
CATALOG_FILE_PATH="/home/dev/my_test_catalog.json"
```

### 5.9 package_groups.yml — Renamed and Relocated Input File

#### 5.9.1 What Changed

| Aspect | Before | After |
|--------|--------|-------|
| **Name** | `functional_group_packages.yml` | `package_groups.yml` |
| **Location** | `samples/repo_manager_output/` (sample) + `/opt/omnia/repo_manager/output/{project}/` (runtime) | `input/{project}/` (user-editable input) |
| **Producer** | repo_manager (or manual copy) | User (manual creation/edit) |
| **Path resolution** | Via `repo_manager.package_list` in `repo_status.yml` | `{{ input_project_dir }}/package_groups.yml` (hardcoded relative path) |
| **When used** | Always (only package source) | Only when `functional_groups_source: "config"` |

#### 5.9.2 Why Rename

- **Shorter** — `package_groups.yml` is clearer and more concise
- **Input file** — Moving to `input/` makes it clear this is a user-editable config,
  not a repo_manager output artifact
- **Decoupled** — No longer dependent on `repo_status.yml` for path resolution
- **Clean separation** — repo_manager produces catalogs; users maintain package groups

#### 5.9.3 File Structure

The internal YAML structure remains identical — RPM package names for RHEL:

```yaml
base_packages:         # RPM names installed in ALL images
  - systemd
  - kernel
  - dracut

functional_groups:
  slurm_node_x86_64:
    packages:
      - munge
      - slurm-slurmd
  slurm_node_aarch64:
    packages:
      - munge
      - slurm-slurmd
```

#### 5.9.4 Migration

Copy `samples/repo_manager_output/functional_group_packages.yml` to
`input/project_default/package_groups.yml` with updated header comments.
The sample file is kept in `samples/` for reference with a deprecation note.

#### 5.9.5 Phase 2 Note: Multi-OS via Project Directories

In Phase 2 (Ubuntu), each project directory will target one OS type. A separate
`input/project_ubuntu/` directory with its own `package_groups.yml` (DEB names)
and `image_build_config.yml` will be added. The `OMNIA_PROJECT_NAME` environment
variable already selects the active project — no architectural change needed.

### 5.10 RHEL Minor Version Support

#### 5.10.1 How Minor Versions Are Handled

RHEL minor version support (10.0, 10.1, 10.2) is built into the architecture
naturally — **no code changes are needed for new minor versions**.

| Component | How It Handles Minor Versions |
|-----------|-------------------------------|
| `repo_status.yml` `repositories` | Keyed by version (e.g., `"10.0"`, `"10.2"`) — new versions just add new keys |
| `cluster_os_version` | Derived from `repositories` first key — works for any version |
| Catalog `identifier` | Encodes version (e.g., `omnia-services-rhel-10-0`) — each catalog targets one version |
| Catalog `functionallayer` names | Include version (e.g., `slurm_node_rhel_10_0_x86_64`) — version-specific |
| Catalog `baseos_group_{version}` | Version in group name (e.g., `baseos_group_10.0`) — auto-adapts |
| `CATALOG_FILE_PATH` env var | User points to version-specific catalog — full control |
| RPM repo URLs | Version-encoded in `repo_status.yml` URLs — no code impact |
| Build templates | Same `dnf` package manager across all RHEL minor versions — no change |

#### 5.10.2 Switching Between RHEL Minor Versions

To build for a different RHEL minor version:

1. repo_manager produces a version-specific `repo_status.yml` with
   `repositories.{new_version}` keys and a matching catalog JSON
2. User updates `image_build_config.yml`:
   - `repo_manager_output_path` → points to new `repo_status.yml`
   - `CATALOG_FILE_PATH` env var → points to version-specific catalog (e.g., `catalog_rhel_10_2.json`)
   - `functional_groups` → uses version-specific names (e.g., `slurm_node_rhel_10_2_x86_64`)
3. Run the build — no code changes needed

#### 5.10.3 Config Mode and Minor Versions

In config mode (`package_groups.yml`), minor version handling is simpler:
- RPM package names are generally the same across RHEL 10.x minor versions
- The user ensures `repo_manager_output_path` points to the correct `repo_status.yml`
  (which provides version-appropriate repo URLs)
- Functional group names in config mode do NOT include version (`slurm_node_x86_64`)
  — the version comes from `repo_status.yml` and the repo URLs

#### 5.10.4 Why This Works Without Code Changes

The key insight is that version information flows through **data**, not **code**:
- Catalog files are version-specific (produced by repo_manager per version)
- `repo_status.yml` encodes version in its `repositories` keys
- Functional layer names encode version in catalog mode
- Templates use version-agnostic variables (`arch_repos`, `base_image_packages`)
- `cluster_os_version` is derived at runtime, not hardcoded

---

## 6. File-by-File Change Plan

### 6.1 Tier 1: Data Loading (MUST change)

#### 6.1.1 `roles/image_build_setup/tasks/load_repo_status.yml`

**Current**: Asserts `repo_manager` section, reads `rpm_repos.*`/`user_repos.*`,
resolves `package_list_path` from `repo_manager.package_list`.

**Changes:**
- Remove `repo_manager` assertion (section no longer exists)
- Remove `repo_manager.port` assertion
- Remove `package_list_path` resolution from `repo_manager.package_list`
- Remove `functional_group_packages.yml` validation (moved to `validate_prereqs.yml` per source mode)
- Derive `cluster_os_version` from first key of `repositories` dict
- Build `repo_manager_repos_{arch}` from `repositories.{version}.{arch}`:
  - Iterate `repositories.{version}.{arch} | dict2items`
  - Skip entries with empty `{}` (value has no `url` key)
  - Append `{name: repo_name, base_url: entry.url, gpg: ""}` for each valid entry
- Remove `_cert_path` from `repo_manager.certificates` (no longer present)
- Remove `repo_port` fact (no longer present)
- Set `repo_cert_path` to empty string (cert handling moves to registries config or is external)
- Keep `s3_endpoint` logic unchanged (comes from `image_build_config.yml`, not `repo_status.yml`)

**Before (simplified):**
```yaml
- name: Validate repo_status.yml has required sections
  ansible.builtin.assert:
    that:
      - repo_manager is defined
      - repo_manager.port is defined

- name: Set package_list_path from repo_status.yml
  ansible.builtin.set_fact:
    package_list_path: "{{ repo_manager.package_list }}"

- name: Build x86_64 repo list from rpm_repos
  ansible.builtin.set_fact:
    repo_manager_repos_x86_64: "{{ repo_manager_repos_x86_64 + [{'name': item.key, 'base_url': item.value, 'gpg': ''}] }}"
  loop: "{{ (rpm_repos.x86_64 | default({})) | dict2items }}"
```

**After (simplified):**
```yaml
- name: Determine cluster_os_version from repositories keys
  ansible.builtin.set_fact:
    cluster_os_version: "{{ (repositories | dict2items | first).key }}"

- name: Build x86_64 repo list from repositories
  ansible.builtin.set_fact:
    repo_manager_repos_x86_64: >-
      {{ repo_manager_repos_x86_64 + [{'name': item.key, 'base_url': item.value.url, 'gpg': ''}] }}
  loop: "{{ (repositories[cluster_os_version].x86_64 | default({})) | dict2items }}"
  when: item.value.url is defined
```

#### 6.1.2 `roles/fetch_build_packages/tasks/main.yml`

**Current**: Loads `functional_group_packages.yml`, reads flat `base_packages` list and
`functional_groups.{name}.packages` dict.

**Changes — dual-mode loading based on `functional_groups_source`:**

**When `functional_groups_source: "config"`:**
- Load `package_groups.yml` from `{{ input_project_dir }}/`
- Read flat `base_packages` → `base_image_packages`
- Read `functional_groups.{name}.packages` → `compute_images_dict`
- Set `service_k8s_version: ""`

**When `functional_groups_source: "catalog"`:**
- Call `omnia.image_build.parse_catalog` Python module with catalog path (from `CATALOG_FILE_PATH`) and `build_arch`
- Module performs three-level resolution: `functionallayer` → `groups` → `packages`
- Module filters packages by `packagetype == 'rpm'` and `sources[].architecture == build_arch`
- Module extracts `service_k8s_version` from `kubeadm_*` RPM name or `kube_apiserver` image tag
- Module returns: `catalog_identifier`, `base_image_packages`, `compute_images_dict`, `service_k8s_version`, `layer_count`
- Set cacheable facts from module output

**Key logic (new parse_catalog.yml — module-based):**
```yaml
# Resolve packages via Python module (plugins/modules/parse_catalog.py)
- name: Resolve RPM packages from catalog JSON
  omnia.image_build.parse_catalog:
    catalog_file: "{{ hostvars['localhost']['catalog_file'] }}"
    build_arch: "{{ build_arch }}"
    package_type: "rpm"
  register: _catalog_result

- name: Set catalog facts from module output
  ansible.builtin.set_fact:
    catalog_identifier: "{{ _catalog_result.catalog_identifier }}"
    base_image_packages: "{{ _catalog_result.base_image_packages }}"
    compute_images_dict: "{{ _catalog_result.compute_images_dict }}"
    service_k8s_version: "{{ _catalog_result.service_k8s_version }}"
    cacheable: true
```

**Benefits over Jinja2 approach:**
- ~130 lines of Jinja2 replaced by 2 Ansible tasks + Python module
- Unit-testable with pytest (no full Ansible run needed)
- Native Python performance vs template rendering
- Standard error handling with tracebacks vs opaque Jinja2 errors

#### 6.1.3 `roles/image_build_setup/vars/main.yml`

**Changes:**
- Update `functional_group_packages_not_found_fail_msg` to reference catalog JSON
- Update `repo_status_missing_section_fail_msg` to remove `repo_manager` reference
- Add `catalog_not_found_fail_msg` for missing catalog file

### 6.2 Tier 2: Config and Naming (MUST change)

#### 6.2.1 `input/project_default/image_build_config.yml`

**Changes:**
- Update `functional_groups_source` comments: `"config"` or `"catalog"` (remove `"repo_status"`)
- `catalog_file` removed from config — now set via `CATALOG_FILE_PATH` env var in `omnia.env`
- Update functional group names in comments to new naming convention
- Update functional_groups list entries to new names:
  ```yaml
  functional_groups:
    - name: "slurm_node_rhel_10_0_x86_64"
    - name: "slurm_control_node_rhel_10_0_x86_64"
  ```
- Update comments: when source is `"config"`, packages come from `package_groups.yml`
  in the input directory; when `"catalog"`, from `CATALOG_FILE_PATH` env var

#### 6.2.2 `roles/fetch_build_packages/tasks/check_functional_group.yml`

**IMPLEMENTED**: Now reads functional groups from `package_groups.yml` keys (config mode).
Skipped entirely in catalog mode (groups come from catalog layers).
The architecture suffix check (`_x86_64` / `_aarch64`) still works with both naming styles.

#### 6.2.3 `roles/fetch_build_packages/vars/main.yml`

**IMPLEMENTED:**
- Removed `functional_groups_file_path` variable (no longer needed)
- Updated `functional_group_absent_msg` to reference both config and catalog modes

### 6.3 Tier 3: Validation (MUST change)

#### 6.3.1 `roles/image_build_setup/tasks/validate_prereqs.yml`

**Changes:**
- Add stat check for catalog JSON file alongside `repo_status.yml`
- Add fail task if catalog not found (similar to current `functional_group_packages.yml` check
  but this is now in `validate_prereqs.yml` instead of `load_repo_status.yml`)

#### 6.3.2 `roles/validate_build_runtime/tasks/main.yml`

**IMPLEMENTED:**
- Removed `functional_groups_file_path` variable from vars
- Updated `validate_fg_config_fail_msg` to reference both config and catalog modes
- No longer references `functional_groups_config.yml`

### 6.4 Tier 4: Build Templates (CONDITIONAL changes)

#### 6.4.1 RHEL Templates — NO change if adapter normalizes

These templates consume `rhel_arch_repos`, `base_image_packages`, and `compute_packages`.
If the catalog adapter outputs the same shapes, **no template changes are needed**:

- `templates/images/rhel-base-config.yaml.j2` — unchanged
- `templates/images/rhel-compute-config.yaml.j2` — unchanged
- `templates/images/thrillhouse-base-config.yaml.j2` — unchanged
- `templates/images/thrillhouse-compute-config.yaml.j2` — unchanged

**Variable aliasing** in `build_image_common_{arch}.yml`:
```yaml
# Backward compatibility alias
rhel_arch_repos: "{{ arch_repos }}"
```

#### 6.4.2 Ubuntu Templates — Phase 2 (NOT in current scope)

Four Ubuntu template files will be created in Phase 2. No template files are added
in Phase 1. See Section 4 for the Phase 2 plan.

#### 6.4.3 Template Selection Logic

In `roles/build_os_images/vars/main.yml`, add OS-type-based template selection.
Phase 1 only includes RHEL entries. The matrix structure supports adding Ubuntu
in Phase 2 without code changes — just add `ubuntu` entries:

```yaml
# Template matrix: build_type x os_type
# Phase 1: RHEL only. Phase 2 adds ubuntu entries.
_template_matrix:
  image-builder:
    rhel:
      base: "{{ role_path }}/templates/images/rhel-base-config.yaml.j2"
      compute: "{{ role_path }}/templates/images/rhel-compute-config.yaml.j2"
  image-thrillhouse:
    rhel:
      base: "{{ role_path }}/templates/images/thrillhouse-base-config.yaml.j2"
      compute: "{{ role_path }}/templates/images/thrillhouse-compute-config.yaml.j2"

_os_type: "{{ hostvars['localhost']['cluster_os_type'] | default('rhel') }}"
openchami_base_image_config_template: "{{ _template_matrix[_image_build_type][_os_type].base }}"
openchami_compute_image_config_template: "{{ _template_matrix[_image_build_type][_os_type].compute }}"
```

### 6.5 Tier 5: Documentation and Samples

| File | Action |
|------|--------|
| `samples/repo_manager_output/functional_group_packages.yml` | Add deprecation header; keep as reference only |
| `input/project_default/package_groups.yml` | **NEW** — Copy from `functional_group_packages.yml`, rename, update header |
| `samples/repo_manager_output/catalog_rhel.json` | Already exists — verify completeness |
| `docs/package-mapping-guide.md` | Rewrite to document dual-mode (config vs catalog) flow |
| `docs/design/catalog-migration-design.md` | This document |

---

## 7. Implementation Stories

### Story 1: Update load_repo_status.yml with Python module for new format (2 SP)

**Files:**
- `plugins/modules/parse_repo_status.py` (**new** — Python Ansible module)
- `roles/image_build_setup/tasks/load_repo_status.yml` (rewrite to use module)
- `roles/image_build_setup/vars/main.yml` (update error messages)

**Acceptance Criteria:**
- [ ] Create `plugins/modules/parse_repo_status.py` with Galaxy documentation
- [ ] Module reads repo_status.yml, validates required sections (`repositories`, `cluster_os_type`)
- [ ] Module derives `cluster_os_version` from `repositories` dict first key
- [ ] Module extracts `repo_port` from first non-empty repo URL (default: 2225)
- [ ] Module builds `repo_manager_repos_{arch}` from `repositories.{version}.{arch}` — skip entries with empty URL
- [ ] Module core functions are independently unit-testable
- [ ] Rewrite `load_repo_status.yml` to call module and set cacheable facts
- [ ] Remove complex Jinja2 `namespace()` port extraction logic
- [ ] Remove `include_vars` + `assert` pattern (module handles validation)
- [ ] Remove loop-based repo list building (module handles it)
- [ ] Update error messages to reference new structure
- [ ] Output shape unchanged: `repo_manager_repos_{arch}: [{name, base_url, gpg}]`

### Story 2: Create catalog parser Python module with unified flow (3 SP)

**Files:**
- `plugins/modules/parse_catalog.py` (**new** — Python Ansible module)
- `roles/fetch_build_packages/tasks/parse_catalog.yml` (rewrite to use module)
- `roles/fetch_build_packages/tasks/main.yml` (rewrite)
- `roles/fetch_build_packages/tasks/build_stream_prerequisite.yml` (simplify to thin wrapper)
- `roles/fetch_build_packages/vars/main.yml` (update variable)
- `playbooks/build/build_image_x86_64.yml` (unify build-stream/standalone flow)
- `playbooks/build/build_image_aarch64.yml` (unify build-stream/standalone flow)

**Acceptance Criteria:**
- [ ] Create `plugins/modules/parse_catalog.py` with Galaxy documentation (DOCUMENTATION, EXAMPLES, RETURN)
- [ ] Module reads catalog JSON, filters by architecture, resolves three-level hierarchy
- [ ] Module filters packages by `packagetype` and `sources[].architecture`
- [ ] Module separates baseos packages (`base_image_packages`) from compute groups (`compute_images_dict`)
- [ ] Module extracts `service_k8s_version` from `kubeadm_*` RPM or `kube_apiserver` image tag
- [ ] Module returns: `catalog_identifier`, `base_image_packages`, `compute_images_dict`, `service_k8s_version`, `layer_count`
- [ ] Module core functions are independently unit-testable (no Ansible dependency)
- [ ] Rewrite `parse_catalog.yml` to call module and set cacheable facts from output
- [ ] Implement dual-mode loading based on `functional_groups_source`
- [ ] Config mode: load `package_groups.yml` from `{{ input_project_dir }}/`, set `service_k8s_version: ""`
- [ ] Handle `functional_groups_source: "catalog"` auto-detection from `catalog.functionallayer[]`
- [ ] Validate requested functional_groups against `catalog.functionallayer[].name` (catalog mode)
- [ ] Unify build-stream and standalone functional group resolution into single code path
- [ ] Simplify `build_stream_prerequisite.yml` to validate only `job_id` and `image_key`
- [ ] Remove `functional_groups_config.yml` write/read cycle from playbooks
- [ ] Output shapes identical: `base_image_packages`, `compute_images_dict`, `service_k8s_version`
- [ ] Handle `rpm_repo` packagetype (e.g., `doca-ofed`) — skip from package list (repo enablement only)
- [ ] No fallback between modes — fail fast if required file is missing

### Story 3: Update image_build_config.yml, package_groups.yml, and naming (2 SP)

**Files:**
- `input/project_default/image_build_config.yml` (update names, comments, add `catalog_file`)
- `input/project_default/package_groups.yml` (**new** — copy from `functional_group_packages.yml`, rename)
- `plugins/module_utils/input_validation/schema/image_build_config.json` (update enum if present)

**Acceptance Criteria:**
- [ ] Update functional group names to `{role}_{os}_{version}_{arch}` pattern
- [ ] Add `"catalog"` as valid option for `functional_groups_source` (remove `"repo_status"`)
- [ ] Add section 6 with `catalog_file` configuration (default: `/opt/omnia/catalog/catalog_rhel.json`)
- [ ] Update comments: config mode uses `package_groups.yml` in input dir, catalog mode uses `catalog_file`
- [ ] Create `input/project_default/package_groups.yml` from existing `functional_group_packages.yml`
- [ ] Update file header to reflect it is a user-editable input file (not repo_manager output)

### Story 4: Add template selection matrix and OS-agnostic variables (1 SP)

**Files:**
- `roles/build_os_images/vars/main.yml` (add template matrix with RHEL entries)
- `roles/build_os_images/tasks/build_image_common_x86_64.yml` (add variable aliases)
- `roles/build_os_images/tasks/build_image_common_aarch64.yml` (add variable aliases)

**Acceptance Criteria:**
- [ ] Add `_template_matrix` with RHEL entries only (Phase 1)
- [ ] Template selection driven by `cluster_os_type` (defaults to `rhel`)
- [ ] Add OS-agnostic variable aliases (`arch_repos`, `base_image_name`, `os_version_tag`)
- [ ] Keep backward-compatible `rhel_*` variable names as aliases
- [ ] Existing RHEL templates remain unchanged
- [ ] Matrix structure supports adding Ubuntu entries in Phase 2 without code changes

### Story 5: Update validation and documentation (1 SP)

**Files:**
- `roles/image_build_setup/tasks/validate_prereqs.yml` (add dual-mode stat checks)
- `docs/package-mapping-guide.md` (rewrite for dual-mode flow)
- `samples/repo_manager_output/functional_group_packages.yml` (add deprecation header)

**Acceptance Criteria:**
- [ ] Add catalog_file stat check in `validate_prereqs.yml` (when `functional_groups_source: "catalog"`)
- [ ] Add `package_groups.yml` stat check in `validate_prereqs.yml` (when `functional_groups_source: "config"`)
- [ ] Rewrite `package-mapping-guide.md` for dual-mode package resolution (config vs catalog)
- [ ] Add deprecation header to `functional_group_packages.yml` sample

---

## 8. No Backward Compatibility (Clean Break)

This is a **new design** — no fallback, no transition period, no format auto-detection.

### 8.1 What Is Removed

| Removed | Replacement |
|---------|-------------|
| `functional_groups_source: "repo_status"` | Use `"config"` or `"catalog"` |
| `package_list_path` from `repo_manager.package_list` | `input/{project}/package_groups.yml` (config mode) or `catalog_file` (catalog mode) |
| `functional_group_packages.yml` at runtime `/opt/omnia/repo_manager/output/` | `package_groups.yml` in `input/{project}/` |
| `repo_manager` section in `repo_status.yml` | `repositories` nested structure |
| `rpm_repos` / `user_repos` flat sections | `repositories.{version}.{arch}` nested structure |
| Catalog path derived from `repo_status.yml` directory | `catalog_file` in `image_build_config.yml` |
| Format auto-detection (old vs new) | Single format only |
| `functional_group_packages.yml` fallback | Fail if required file is missing |

### 8.2 Variable Aliases (Kept)

Keep `rhel_*` variable names as aliases to avoid breaking existing templates:

```yaml
rhel_tag: "{{ os_version_tag }}"
rhel_arch_repos: "{{ arch_repos }}"
rhel_arch_base_image_name: "{{ base_image_name }}"
```

These aliases will be removed in a future release when templates are updated.

---

## 9. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Catalog JSON missing in production | Build fails | Fail fast with clear error message; catalog_file path is explicit in config |
| Functional group name change breaks downstream | Provision/discovery uses old names | Coordinate naming change with discovery/provision teams |
| RHEL minor version mismatch | Catalog version ≠ repo_status version | Validate `catalog.identifier` against `cluster_os_version` |
| `rpm_repo` type (doca-ofed) counted as installable package | Build fails | Filter out `rpm_repo` packagetype in resolver |
| Jinja2 complex resolution in Ansible | Performance/maintainability | **MITIGATED**: Converted to Python module (`parse_catalog.py`, `parse_repo_status.py`) |
| `baseos_group_10.0` has dot in name | YAML/JSON parsing issues | Already works in catalog JSON — validate in Ansible |

---

## 10. New Data Flow (Post-Migration — Unified)

```
image_build_config.yml
  |-- repo_manager_output_path --> repo_status.yml
  |-- functional_groups_source: "config" | "catalog"
  |-- catalog_file: "/opt/omnia/catalog/catalog_rhel.json"  (when source=catalog)
  |-- functional_groups: [{name: "slurm_node_rhel_10_0_x86_64"}, ...]

validate_prereqs.yml
  |-- stat check: repo_status.yml (always)
  |-- stat check: catalog_file (when source=catalog)
  |-- stat check: package_groups.yml in input dir (when source=config)

load_repo_status.yml
  |-- omnia.image_build.parse_repo_status module:
  |      |-- reads: repo_status.yml
  |      |-- derives: cluster_os_version, cluster_os_type
  |      |-- extracts: repo_port from first URL
  |      |-- builds: repo_manager_repos_{arch} from repositories.{version}.{arch}
  |-- set_fact: cacheable facts from module output
  |-- output: [{name, base_url, gpg}] (SAME SHAPE)
  |-- NOTE: No package_list_path, no catalog_path — decoupled from package resolution

build_image_{arch}.yml  (UNIFIED — same flow for both modes)
  |-- 1. image_build_setup (always)
  |-- 2. Load image_build_config.yml
  |-- 3. Set build-stream metadata (job_id, image_key — empty if standalone)
  |-- 4. Validate build-stream inputs (only when enable_build_stream=true)
  |-- 5. validate_build_runtime
  |-- 6. Resolve functional_groups:
  |      |-- source: extra-vars (build-stream) OR config OR catalog auto-detect
  |      |-- validate (catalog mode): all groups exist in catalog.functionallayer[]
  |      |-- validate (config mode): all groups exist in package_groups.yml keys
  |-- 7. fetch_build_packages (DUAL-MODE — config or catalog)
  |-- 8. build_os_images
  |-- 9. build_image_completion

fetch_build_packages/tasks/main.yml  (DUAL-MODE)
  |-- WHEN source="config":
  |      |-- include_vars: input/{project}/package_groups.yml --> _fg_pkg_mapping
  |      |-- sets: base_image_packages from _fg_pkg_mapping.base_packages
  |      |-- sets: compute_images_dict from _fg_pkg_mapping.functional_groups
  |      |-- sets: service_k8s_version = "" (not available)
  |-- WHEN source="catalog":
  |      |-- omnia.image_build.parse_catalog module:
  |      |      |-- reads: catalog_file JSON
  |      |      |-- resolves: functionallayer -> groups -> packages (Python)
  |      |      |-- filters: packagetype == 'rpm', architecture == build_arch
  |      |      |-- extracts: service_k8s_version from kubeadm/kube_apiserver
  |      |      |-- returns: catalog_identifier, base_image_packages,
  |      |      |            compute_images_dict, service_k8s_version
  |      |-- set_fact: cacheable facts from module output
  |-- calls: fetch_repo_manager_repos.yml (UNCHANGED)

build_os_images role
  |-- selects template: {build_type} x {os_type} matrix
  |-- templates: *-base-config.yaml.j2 uses arch_repos + base_image_packages
  |-- templates: *-compute-config.yaml.j2 uses arch_repos + compute_packages
  |-- k8s_suffix: "_k8s_1.35.1" (catalog mode) or "" (config mode)
  |-- iterates: compute_images_dict | dict2items (UNCHANGED)
```

**Key differences from current flow:**
- No `functional_groups_config.yml` intermediate file
- No separate `build_stream_prerequisite.yml` for functional group normalization
- `package_groups.yml` is a user-editable input file (not a repo_manager output)
- Catalog file path is explicit in `image_build_config.yml` (not derived from repo_status)
- `service_k8s_version` resolved from catalog (catalog mode) or empty (config mode)
- `catalog_identifier` set as a fact for traceability (catalog mode only)
- Single code path regardless of build-stream or standalone mode
- No fallback between modes — explicit choice via `functional_groups_source`

---

## 11. Testing Strategy

### 11.1 Unit Tests

- Test catalog JSON parsing with sample `catalog_rhel.json`
- Test package resolution for each functional layer
- Test architecture filtering (x86_64 vs aarch64)
- Test packagetype filtering (`rpm` only — skip `image`/`tarball`/`pip_module`/`git`/`manifest`/`rpm_repo`)
- Test empty group handling
- Test `baseos_group_{version}` extraction into `base_image_packages`
- Test config mode: load `package_groups.yml` from input dir
- Test `service_k8s_version` extraction from `kubeadm_*` package name
- Test `service_k8s_version` fallback to `kube_apiserver` image tag
- Test `service_k8s_version` empty when no k8s packages in catalog
- Test `catalog_identifier` fact is set from catalog
- Test unified flow: build-stream and standalone produce same package resolution
- Test functional_group validation against `catalog.functionallayer[]`
- Test RHEL minor version: catalog with `10.2` version produces correct `cluster_os_version`
- Test RHEL minor version: functional layer names with different versions resolve correctly

### 11.2 Integration Tests

- End-to-end build with new `repo_status.yml` format (RHEL 10.0)
- End-to-end build with `catalog_rhel.json`
- Verify output images are identical to old format builds (same packages installed)
- Test `functional_groups_source: "catalog"` auto-detection from catalog
- Test `functional_groups_source: "config"` reads from `input/{project}/package_groups.yml`
- Test with RHEL 10.2 catalog and repo_status (minor version verification)

### 11.3 Manual Verification

- Compare rendered config YAML (from templates) before and after migration
- Verify no missing packages in computed lists vs old `functional_group_packages.yml`

---

## 12. Files Inventory — Complete List

### Files to MODIFY

| # | File | Change Type | Story |
|---|------|------------|-------|
| 1 | `roles/image_build_setup/tasks/load_repo_status.yml` | Rewrite repo parsing | 1 |
| 2 | `roles/image_build_setup/vars/main.yml` | Update error messages | 1 |
| 3 | `roles/fetch_build_packages/tasks/main.yml` | Rewrite package loading | 2 |
| 4 | `roles/fetch_build_packages/vars/main.yml` | Update variable names | 2 |
| 5 | `roles/build_os_images/vars/main.yml` | Add template matrix (RHEL only), OS-agnostic vars | 4 |
| 6 | `roles/build_os_images/tasks/build_image_common_x86_64.yml` | Add variable aliases | 4 |
| 7 | `roles/build_os_images/tasks/build_image_common_aarch64.yml` | Add variable aliases | 4 |
| 8 | `input/project_default/image_build_config.yml` | Add `catalog_file`, update `functional_groups_source` options, update names | 3 |
| 9 | `roles/image_build_setup/tasks/validate_prereqs.yml` | Add dual-mode stat checks (catalog_file or package_groups.yml) | 5 |
| 10 | `docs/package-mapping-guide.md` | Rewrite for dual-mode (config vs catalog) flow | 5 |
| 14 | `samples/repo_manager_output/functional_group_packages.yml` | Add deprecation header | 5 |
| 11 | `playbooks/build/build_image_x86_64.yml` | Unify build-stream/standalone flow | 2 |
| 12 | `playbooks/build/build_image_aarch64.yml` | Unify build-stream/standalone flow | 2 |
| 13 | `roles/fetch_build_packages/tasks/build_stream_prerequisite.yml` | Simplify to thin wrapper (job_id/image_key only) | 2 |

### Files to CREATE

| # | File | Purpose | Story |
|---|------|---------|-------|
| 15 | `roles/fetch_build_packages/tasks/parse_catalog.yml` | Module wrapper — calls `parse_catalog` module | 2 |
| 18 | `plugins/modules/parse_catalog.py` | Python module — catalog resolution logic | 2 |
| 19 | `plugins/modules/parse_repo_status.py` | Python module — repo_status parsing + repo list building | 1 |
| 16 | `input/project_default/package_groups.yml` | User-editable package mapping (config mode) | 3 |
| 17 | `docs/design/catalog-migration-design.md` | This design document | — |

### Files to CREATE — Phase 2 (Ubuntu)

| # | File | Purpose |
|---|------|---------|
| P2-1 | `roles/build_os_images/templates/images/ubuntu-base-config.yaml.j2` | Ubuntu base template |
| P2-2 | `roles/build_os_images/templates/images/ubuntu-compute-config.yaml.j2` | Ubuntu compute template |
| P2-3 | `roles/build_os_images/templates/images/thrillhouse-ubuntu-base-config.yaml.j2` | Thrillhouse Ubuntu base |
| P2-4 | `roles/build_os_images/templates/images/thrillhouse-ubuntu-compute-config.yaml.j2` | Thrillhouse Ubuntu compute |
| P2-5 | `samples/repo_manager_output/catalog_ubuntu.json` | Ubuntu catalog sample |

### Files UNCHANGED (verified)

| # | File | Reason |
|---|------|--------|
| 23 | `templates/images/rhel-base-config.yaml.j2` | Adapter normalizes output shape |
| 24 | `templates/images/rhel-compute-config.yaml.j2` | Adapter normalizes output shape |
| 25 | `templates/images/thrillhouse-base-config.yaml.j2` | Adapter normalizes output shape |
| 26 | `templates/images/thrillhouse-compute-config.yaml.j2` | Adapter normalizes output shape |
| 27 | `roles/fetch_build_packages/tasks/fetch_repo_manager_repos.yml` | Consumes same `repo_manager_repos_{arch}` shape |
| 28 | `roles/fetch_build_packages/tasks/check_functional_group.yml` | **DEPRECATED** — validation moves to catalog in-memory check (catalog mode) |
| 29 | `roles/build_os_images/tasks/main.yml` | Uses `compute_images_dict` — shape unchanged |
| 30 | `roles/build_os_images/tasks/build_compute_image_x86_64.yml` | Uses `compute_images_dict` — shape unchanged |
| 31 | `roles/build_os_images/tasks/build_base_image_x86_64.yml` | Uses `base_image_packages` — shape unchanged |
| 32 | `roles/validate_build_runtime/tasks/main.yml` | Validates orthogonal concerns |

---

## 13. Implementation Order

```
Phase 1 (RHEL only):

Story 1 (load_repo_status.yml)     -- No dependency, can start immediately
    |
    v
Story 2 (parse_catalog.yml)        -- Depends on Story 1 (OS type/version needed)
    |
    v
Story 3 (image_build_config.yml)   -- Can run parallel with Story 2
    |
    v
Story 4 (template matrix + aliases) -- Depends on Stories 1+2 (OS type needed)
    |
    v
Story 5 (validation + docs)        -- Final, after all implementation stories

Phase 2 (Ubuntu — future):
  Ubuntu templates + deb filter + catalog_ubuntu.json
```

**Phase 1 Total: 9 Story Points across 5 stories** (2+3+2+1+1)
