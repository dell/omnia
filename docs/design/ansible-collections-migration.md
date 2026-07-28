# Ansible Collections Migration — Design & Plan

**Version**: 1.0
**Status**: PROPOSAL
**Audience**: Omnia platform team, domain developers
**Purpose**: Evaluate and plan migration from flat playbook repositories to Ansible Collections.

---

## 1. What Is an Ansible Collection?

An Ansible Collection is the **standard distribution format** for Ansible content — modules,
plugins, roles, and playbooks bundled into a namespaced, versioned package installable via
`ansible-galaxy`.

```
<namespace>/<collection_name>/           # e.g. dell/omnia_image_build
├── galaxy.yml                           # Metadata + version + dependencies
├── plugins/
│   ├── modules/                         # Custom modules
│   ├── module_utils/                    # Shared Python utilities for modules
│   ├── callback/                        # Callback plugins
│   ├── filter/                          # Jinja2 filter plugins (optional)
│   └── inventory/                       # Inventory plugins (optional)
├── roles/
│   ├── setup/                           # Roles (referenced by FQCN)
│   ├── deploy_minio/
│   └── ...
├── playbooks/                           # Playbooks callable via FQCN
├── docs/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── sanity/
└── meta/
    └── runtime.yml                      # Ansible version compatibility + redirects
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Namespace** | Top-level vendor identifier (e.g., `dell`, `community`, `ansible`) |
| **Collection name** | The collection within the namespace (e.g., `omnia_common`, `omnia_image_build`) |
| **FQCN** | Fully Qualified Collection Name — `dell.omnia_image_build.validate_yaml_schema` |
| **galaxy.yml** | Metadata file defining name, version, dependencies, and authors |
| **meta/runtime.yml** | Ansible version compatibility and module redirects |

---

## 2. Current State — Omnia Mono-Repo

### Asset Inventory

| Asset Type | `common/` (shared) | `image_build_manager` | Other domains |
|---|---|---|---|
| **Custom modules** | 49 (`common/library/modules/`) | 6 (`library/modules/`) | Varies |
| **Module utils** | 68 items (`common/library/module_utils/`) | 2 packages | Varies |
| **Callback plugins** | 1 (`omnia_default.py`) | 1 (copy of same) | Copies |
| **Roles** | N/A (tasks only) | 11 | 50+ across domains |
| **Playbooks** | N/A | 9 sub-playbooks + 1 entry point | Hundreds |

### Current Pain Points

1. **`common/` coupling** — Every domain has `ansible.cfg` pointing to `../common/library/`. Any change in `common/` can break any domain.
2. **Module duplication** — Domains copy modules from `common/` to work standalone. No single source of truth.
3. **No versioning** — Modules are at "whatever commit you have". No way to pin versions.
4. **Bare module names** — `validate_yaml_schema:` could collide with another domain's module.
5. **`ansible.cfg` path hacks** — Every `ansible.cfg` has relative paths to `library/`, `module_utils/`, `callback_plugins/`.

---

## 3. Advantages of Collections

| # | Advantage | Detail |
|---|-----------|--------|
| 1 | **Namespaced FQCN** | `dell.omnia_image_build.validate_yaml_schema` instead of bare `validate_yaml_schema`. Eliminates name collisions across domains. |
| 2 | **Versioned distribution** | `ansible-galaxy collection install dell.omnia_image_build:1.2.0` — exact version pinning. |
| 3 | **Independent release cycles** | Each domain collection is versioned separately. `image_build` v1.3 while `orchestrator` v1.1. |
| 4 | **Eliminates `common/` coupling** | Each collection ships its own modules/plugins. No cross-domain `../common/library/` imports. |
| 5 | **Standard installation** | `ansible-galaxy collection install -r requirements.yml` — same workflow as community collections. |
| 6 | **Air-gap friendly** | `ansible-galaxy collection build` → `.tar.gz` → copy to air-gapped host → `ansible-galaxy collection install ./dell-omnia_common-1.0.0.tar.gz` |
| 7 | **Automation Hub compatible** | Can be published to Private Automation Hub for enterprise distribution. |
| 8 | **Testing framework** | `ansible-test` provides sanity, unit, and integration test runners designed for collections. |
| 9 | **Galaxy dependency resolution** | Collections declare dependencies on other collections in `galaxy.yml`. |
| 10 | **LLM/AI advantage** | FQCN is self-documenting. AI agents generate `dell.omnia_image_build.validate_yaml_schema` without guessing paths. |

---

## 4. Disadvantages of Collections

| # | Disadvantage | Detail |
|---|-------------|--------|
| 1 | **Migration effort** | Restructuring roles + modules + module_utils + callback plugins. Every `ansible.cfg` path reference changes. |
| 2 | **Playbook FQCN rewrite** | Every task using a custom module needs updating: `validate_yaml_schema:` → `dell.omnia_image_build.validate_yaml_schema:` |
| 3 | **`module_utils` import path changes** | `from ansible.module_utils.build_image.common_functions import ...` → `from ansible_collections.dell.omnia_image_build.plugins.module_utils.build_image.common_functions import ...` |
| 4 | **Build & publish pipeline** | Need CI/CD to build collection tarball, test, and publish. Additional infrastructure. |
| 5 | **Role naming constraints** | Role names must be unique within the collection namespace. |
| 6 | **Callback plugin path change** | `stdout_callback = omnia_default` → `stdout_callback = dell.omnia_common.omnia_default` |
| 7 | **Dev workflow friction** | Need to install collection in editable mode, symlink, or use `COLLECTIONS_PATHS` override during development. |
| 8 | **Debugging complexity** | Stack traces show full collection paths instead of local relative paths. |
| 9 | **Mono-repo compatibility** | Need to decide: collections as separate repos OR collection build from mono-repo subdirectory. |
| 10 | **Ansible version requirement** | Full collection support requires ansible-core ≥ 2.10 (not an issue — we're on 2.20+). |

---

## 5. Decision Matrix

| Factor | Stay as Playbook Repo | Convert to Collection |
|--------|----------------------|----------------------|
| **Time to value** | Already working | 2-4 sprints migration |
| **Module reuse** | Copy modules between domains | `dell.omnia_common` shared properly |
| **Version pinning** | Git commit hash only | Semantic versioning |
| **Air-gap distribution** | Git clone or tarball | `collection build` → `.tar.gz` |
| **FQCN clarity** | Bare module names | Namespaced, unambiguous |
| **Dev workflow** | Simple `cd src && ansible-playbook` | Needs collection install step |
| **CI/CD complexity** | Simple | Build + publish pipeline |
| **Ansible ecosystem alignment** | Non-standard | Standard Galaxy/Hub format |
| **LLM/AI productivity** | Needs `ansible.cfg` context | FQCN is self-documenting |

### Recommendation

**Convert — but phased. Start with `dell.omnia_common` to prove the pattern before touching domain code.**

---

## 6. Proposed Collection Architecture

### Omnia Collection Namespace

```
dell.omnia_common          ← Shared modules, module_utils, callback plugins
dell.omnia_image_build     ← Image build domain (roles, playbooks, domain modules)
dell.omnia_repo_manager    ← Repo manager domain
dell.omnia_orchestrator    ← Orchestrator domain
dell.omnia_discovery       ← Discovery domain
dell.omnia_telemetry       ← Telemetry domain
```

### Dependency Graph

```
                    ┌─────────────────────┐
                    │ dell.omnia_common    │
                    │ (shared modules,    │
                    │  utils, callback)   │
                    └─────────┬───────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ dell.omnia_     │ │ dell.omnia_     │ │ dell.omnia_     │
│ image_build     │ │ orchestrator    │ │ repo_manager    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │
          ▼                   ▼
    ┌──────────┐       ┌──────────┐
    │ ansible. │       │ ansible. │
    │ utils    │       │ netcommon│
    └──────────┘       └──────────┘
```

---

## 7. Collection Structure Details

### 7.1 `dell.omnia_common` — Shared Collection

```
dell/omnia_common/
├── galaxy.yml
├── plugins/
│   ├── modules/
│   │   ├── generate_xname_in_mapping_file.py
│   │   ├── update_node_object.py
│   │   ├── ... (49 modules from common/library/modules/)
│   ├── module_utils/
│   │   ├── omnia_logging.py
│   │   ├── config_manager.py
│   │   ├── ... (68 items from common/library/module_utils/)
│   ├── callback/
│   │   └── omnia_default.py
│   └── filter/                        # Optional: shared Jinja2 filters
│       └── omnia_filters.py
├── roles/                             # Shared roles (if any)
├── tests/
│   ├── unit/
│   │   └── plugins/
│   │       └── modules/
│   │           └── test_generate_xname.py
│   └── sanity/
├── docs/
├── meta/
│   └── runtime.yml
└── README.md
```

**galaxy.yml:**

```yaml
namespace: dell
name: omnia_common
version: 1.0.0
readme: README.md
authors:
  - Dell Technologies <omnia@dell.com>
description: >-
  Shared Ansible modules, module utilities, and callback plugins for
  the Omnia HPC cluster management platform.
license:
  - Apache-2.0
tags:
  - dell
  - omnia
  - hpc
  - infrastructure
repository: https://github.com/dell/omnia
dependencies:
  ansible.utils: ">=2.0.0"
  community.general: ">=7.0.0"
build_ignore:
  - "*.tar.gz"
  - ".git"
  - ".github"
```

### 7.2 `dell.omnia_image_build` — Domain Collection

```
dell/omnia_image_build/
├── galaxy.yml
├── plugins/
│   ├── modules/
│   │   ├── validate_yaml_schema.py
│   │   ├── validate_image_build_config.py
│   │   ├── image_package_collector.py
│   │   ├── base_image_package_collector.py
│   │   ├── functional_group_parser.py
│   │   └── generate_functional_groups.py
│   ├── module_utils/
│   │   ├── build_image/
│   │   │   ├── __init__.py
│   │   │   ├── common_functions.py
│   │   │   └── config.py
│   │   └── image_build_validation/
│   │       ├── __init__.py
│   │       ├── image_build_validation_flow.py
│   │       └── schema/
│   │           ├── config.schema.json
│   │           ├── image_build_config.json
│   │           ├── image_build_credentials.json
│   │           └── functional_groups_config.json
│   └── callback/                      # (empty — uses dell.omnia_common callback)
├── roles/
│   ├── setup/                         # image_build_setup
│   │   ├── tasks/
│   │   ├── vars/
│   │   └── defaults/
│   ├── deploy_minio/
│   ├── deploy_registry/
│   ├── build_os_images/
│   ├── fetch_build_packages/
│   ├── collect_credentials/
│   ├── validate_input/
│   ├── validate_runtime/
│   ├── cleanup/
│   ├── prepare_aarch64/
│   ├── generate_functional_groups/
│   └── upgrade/
├── playbooks/
│   ├── image_build_manager.yml        # Entry point
│   ├── prepare.yml
│   ├── build_x86_64.yml
│   ├── build_aarch64.yml
│   ├── cleanup.yml
│   ├── validate.yml
│   ├── get_credentials.yml
│   ├── upgrade.yml
│   └── rollback.yml
├── tests/
├── docs/
├── meta/
│   └── runtime.yml
└── README.md
```

**galaxy.yml:**

```yaml
namespace: dell
name: omnia_image_build
version: 1.0.0
readme: README.md
authors:
  - Dell Technologies <omnia@dell.com>
description: >-
  Ansible collection for building OS images (RHEL/Rocky) for Omnia HPC clusters.
  Deploys MinIO S3 + OCI Registry and builds bare-metal OS images via OpenCHAMI.
license:
  - Apache-2.0
tags:
  - dell
  - omnia
  - hpc
  - image-build
  - openchami
repository: https://github.com/dell/omnia
dependencies:
  dell.omnia_common: ">=1.0.0"
  ansible.utils: ">=2.0.0"
  community.general: ">=7.0.0"
  containers.podman: ">=1.10.0"
build_ignore:
  - "*.tar.gz"
  - ".git"
  - ".github"
  - "test/"
```

---

## 8. How to Use `dell.omnia_common` From Other Collections

This is the critical pattern — how domain collections consume shared modules.

### 8.1 Declare Dependency in `galaxy.yml`

Every domain collection that uses shared modules MUST declare the dependency:

```yaml
# dell/omnia_image_build/galaxy.yml
dependencies:
  dell.omnia_common: ">=1.0.0"
```

When users install `dell.omnia_image_build`, Galaxy automatically installs `dell.omnia_common` too.

### 8.2 Use Shared Modules in Playbooks/Tasks (FQCN)

```yaml
# BEFORE (bare module name — requires ansible.cfg path hack):
- name: Generate xnames
  generate_xname_in_mapping_file:
    mapping_file_path: "{{ mapping_file }}"

# AFTER (FQCN — works anywhere, no ansible.cfg needed):
- name: Generate xnames
  dell.omnia_common.generate_xname_in_mapping_file:
    mapping_file_path: "{{ mapping_file }}"
```

### 8.3 Use Shared Module Utils in Python Code

When writing a custom module in `dell.omnia_image_build` that needs utilities from `dell.omnia_common`:

```python
# BEFORE (flat import — requires ansible.cfg module_utils path):
from ansible.module_utils.omnia_logging import OmniaLogger

# AFTER (collection-aware import):
from ansible_collections.dell.omnia_common.plugins.module_utils.omnia_logging import OmniaLogger
```

### 8.4 Use Shared Callback Plugin

```ini
# BEFORE (ansible.cfg — requires callback_plugins path):
[defaults]
stdout_callback = omnia_default
callback_plugins = ../common/callback_plugins

# AFTER (FQCN — no path needed):
[defaults]
stdout_callback = dell.omnia_common.omnia_default
```

### 8.5 Use Shared Roles From Another Collection

```yaml
# If dell.omnia_common had shared roles:
- name: Run common setup
  ansible.builtin.include_role:
    name: dell.omnia_common.base_setup
```

### 8.6 Use Domain Collection Playbooks

```bash
# Run a collection playbook directly:
ansible-playbook dell.omnia_image_build.image_build_manager --tags prepare

# Or reference in another playbook:
- name: Build images
  ansible.builtin.import_playbook: dell.omnia_image_build.image_build_manager
```

### 8.7 Use Shared Filters (Optional)

If `dell.omnia_common` includes custom Jinja2 filters:

```yaml
# In any domain task:
- name: Format output
  ansible.builtin.debug:
    msg: "{{ my_var | dell.omnia_common.omnia_format }}"
```

---

## 9. Development Workflow

### 9.1 Local Development (Editable Mode)

During development, you don't want to rebuild and reinstall the collection after every change.
Use symlinks:

```bash
# Create the collection namespace directory structure
mkdir -p ~/.ansible/collections/ansible_collections/dell

# Symlink your local development directories
ln -s /path/to/omnia_common ~/.ansible/collections/ansible_collections/dell/omnia_common
ln -s /path/to/omnia_image_build ~/.ansible/collections/ansible_collections/dell/omnia_image_build

# Now ansible-playbook resolves FQCN from your local source
ansible-playbook dell.omnia_image_build.image_build_manager
```

### 9.2 Alternative: `COLLECTIONS_PATHS` Override

```bash
# Point Ansible to your dev collections
export ANSIBLE_COLLECTIONS_PATHS=/path/to/dev/collections:~/.ansible/collections

# Or in ansible.cfg:
[defaults]
collections_paths = /path/to/dev/collections:~/.ansible/collections
```

### 9.3 Building a Collection Tarball

```bash
cd /path/to/dell/omnia_common
ansible-galaxy collection build
# → dell-omnia_common-1.0.0.tar.gz
```

### 9.4 Installing From Tarball (Air-Gap)

```bash
# On the air-gapped host:
ansible-galaxy collection install ./dell-omnia_common-1.0.0.tar.gz
ansible-galaxy collection install ./dell-omnia_image_build-1.0.0.tar.gz
```

### 9.5 Installing From Galaxy or Automation Hub

```bash
# From requirements.yml:
ansible-galaxy collection install -r requirements.yml

# Or directly:
ansible-galaxy collection install dell.omnia_image_build:1.0.0
```

### 9.6 Verifying Installation

```bash
# List installed collections
ansible-galaxy collection list | grep dell

# Expected output:
# dell.omnia_common       1.0.0
# dell.omnia_image_build  1.0.0

# Verify module is accessible
ansible-doc dell.omnia_common.generate_xname_in_mapping_file
ansible-doc dell.omnia_image_build.validate_yaml_schema
```

---

## 10. Testing Collections

### 10.1 Sanity Tests (Built-in)

```bash
cd /path/to/dell/omnia_common
ansible-test sanity --docker default
```

Checks: Python syntax, import validation, documentation, GPL license, metaclass boilerplate, etc.

### 10.2 Unit Tests

```bash
# tests/unit/plugins/modules/test_generate_xname.py
ansible-test units --docker default
```

### 10.3 Integration Tests

```bash
# tests/integration/targets/validate_yaml_schema/tasks/main.yml
ansible-test integration --docker default validate_yaml_schema
```

---

## 11. Migration Plan

### Phase 0: Preparation (1 sprint)

| Step | Action |
|------|--------|
| 0.1 | **Audit module usage** — map which domain uses which `common/` modules. Build dependency matrix. |
| 0.2 | **Choose namespace** — `dell.omnia_common`, `dell.omnia_image_build`, etc. |
| 0.3 | **Register namespace** on Galaxy or Private Automation Hub. |
| 0.4 | **Set up collection CI** — `ansible-test sanity`, `ansible-test units`, build + publish pipeline. |

### Phase 1: `dell.omnia_common` (2 sprints)

| Step | Action |
|------|--------|
| 1.1 | Scaffold `dell.omnia_common` using `ansible-galaxy collection init dell.omnia_common` |
| 1.2 | Move 49 modules from `common/library/modules/` → `plugins/modules/` |
| 1.3 | Move 68 module_utils from `common/library/module_utils/` → `plugins/module_utils/` |
| 1.4 | Update all Python imports: `from ansible.module_utils.xyz` → `from ansible_collections.dell.omnia_common.plugins.module_utils.xyz` |
| 1.5 | Move callback plugin → `plugins/callback/omnia_default.py` |
| 1.6 | Run `ansible-test sanity` — fix all issues |
| 1.7 | Build tarball: `ansible-galaxy collection build` |
| 1.8 | Update mono-repo — add `dell.omnia_common` to `requirements.yml` |
| 1.9 | Update all domain playbooks — FQCN for every `common/` module call |
| 1.10 | Test — run all domain playbooks, verify FQCN resolution |

### Phase 2: `dell.omnia_image_build` — Pilot (1-2 sprints)

| Step | Action |
|------|--------|
| 2.1 | Scaffold `dell.omnia_image_build` |
| 2.2 | Move 6 domain modules → `plugins/modules/` |
| 2.3 | Move domain module_utils → `plugins/module_utils/` |
| 2.4 | Move 11 roles → `roles/` (rename to shorter names) |
| 2.5 | Move playbooks → collection `playbooks/` |
| 2.6 | Update all FQCN in tasks |
| 2.7 | Update `galaxy.yml` dependencies — `dell.omnia_common: ">=1.0.0"` |
| 2.8 | Remove all `ansible.cfg` path overrides |
| 2.9 | Run `ansible-test sanity` + existing tests |
| 2.10 | Full end-to-end test with collection-installed roles/modules |

### Phase 3: Other Domain Collections (parallel, 1-2 sprints each)

- `dell.omnia_orchestrator`
- `dell.omnia_discovery`
- `dell.omnia_telemetry`
- `dell.omnia_repo_manager`

### Phase 4: Integration Repo Update

```yaml
# dell/omnia/requirements.yml (updated)
collections:
  - name: dell.omnia_common
    version: ">=1.0.0"
  - name: dell.omnia_image_build
    version: ">=1.0.0"
  - name: dell.omnia_orchestrator
    version: ">=1.0.0"
  - name: dell.omnia_discovery
    version: ">=1.0.0"
  - name: dell.omnia_repo_manager
    version: ">=1.0.0"
  - name: ansible.utils
    version: ">=2.0.0"
  - name: community.general
    version: ">=7.0.0"
  - name: containers.podman
    version: ">=1.10.0"
```

```bash
# dell/omnia/omnia.sh (updated)
#!/bin/bash
python3 -m venv /opt/omnia/venv
source /opt/omnia/venv/bin/activate
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml      # installs all domain collections
ansible-playbook dell.omnia_image_build.image_build_manager --tags prepare
```

---

## 12. Before vs After — Concrete Example

### Before: Using `common/` module in a task

```yaml
# ansible.cfg (required path hack):
# library = ../common/library/modules
# module_utils = ../common/library/module_utils
# callback_plugins = ../common/callback_plugins

# In a role task:
- name: Generate xnames
  generate_xname_in_mapping_file:
    mapping_file_path: "{{ mapping_file }}"
```

```python
# In a custom module (flat import):
from ansible.module_utils.omnia_logging import OmniaLogger
```

### After: Using `dell.omnia_common` module

```yaml
# ansible.cfg — NO path hacks needed:
# [defaults]
# stdout_callback = dell.omnia_common.omnia_default

# In a role task (FQCN):
- name: Generate xnames
  dell.omnia_common.generate_xname_in_mapping_file:
    mapping_file_path: "{{ mapping_file }}"
```

```python
# In a custom module (collection-aware import):
from ansible_collections.dell.omnia_common.plugins.module_utils.omnia_logging import OmniaLogger
```

### Before: Using domain module

```yaml
# ansible.cfg:
# library = library/modules
# module_utils = library/module_utils

- name: Validate config
  validate_yaml_schema:
    yaml_file: "{{ config_path }}"
    schema_file: "{{ schema_path }}"
```

### After: Using domain collection module

```yaml
# No ansible.cfg path override needed

- name: Validate config
  dell.omnia_image_build.validate_yaml_schema:
    yaml_file: "{{ config_path }}"
    schema_file: "{{ schema_path }}"
```

---

## 13. `ansible.cfg` Simplification

### Before (path hacks everywhere)

```ini
[defaults]
library = library/modules:../common/library/modules
module_utils = library/module_utils:../common/library/module_utils
callback_plugins = callback_plugins:../common/callback_plugins
roles_path = roles
stdout_callback = omnia_default
```

### After (collections handle everything)

```ini
[defaults]
stdout_callback = dell.omnia_common.omnia_default
roles_path = roles

# No library, module_utils, or callback_plugins paths needed.
# Collections are resolved via COLLECTIONS_PATHS or default ~/.ansible/collections/
```

---

## 14. Quick Reference — Common Operations

| Operation | Command |
|-----------|---------|
| **Init new collection** | `ansible-galaxy collection init dell.omnia_<name>` |
| **Build tarball** | `ansible-galaxy collection build` |
| **Install from tarball** | `ansible-galaxy collection install ./dell-omnia_common-1.0.0.tar.gz` |
| **Install from Galaxy** | `ansible-galaxy collection install dell.omnia_common` |
| **Install from requirements** | `ansible-galaxy collection install -r requirements.yml` |
| **List installed** | `ansible-galaxy collection list \| grep dell` |
| **View module docs** | `ansible-doc dell.omnia_common.generate_xname_in_mapping_file` |
| **Run sanity tests** | `ansible-test sanity --docker default` |
| **Run unit tests** | `ansible-test units --docker default` |
| **Dev symlink** | `ln -s /path/to/src ~/.ansible/collections/ansible_collections/dell/omnia_common` |

---

## 15. Input Handling in Collections

### The Problem

In the current flat repo, input files live relative to the playbook:

```
image-build-manager/
├── config.yml                    ← User edits this (repo root)
└── src/
    ├── image_build_manager.yml   ← playbook_dir
    └── input/
        └── project_default/      ← {{ playbook_dir }}/input/{{ project_name }}
            ├── image_build_config.yml
            ├── image_build_credentials.yml
            └── repo_manager_output/
                ├── repo_status.yml
                └── functional_group_packages.yml
```

Tasks reference files via `{{ playbook_dir }}/../config.yml` and `{{ playbook_dir }}/input/...`.

**In a collection**, playbooks are installed into a **read-only** location
(`~/.ansible/collections/ansible_collections/dell/omnia_image_build/playbooks/`).
User config files **cannot** live inside the collection directory.

### The Solution: Workspace-Based Input

Collections separate **code** (read-only, versioned) from **user data** (writable, per-project).

The user works from a **workspace directory** — a local directory where they keep their config
and input files. A thin wrapper playbook or the collection playbook reads user data from the
workspace via variables.

```
# User's workspace (NOT inside the collection):
~/my-omnia-project/                       ← User's working directory
├── config.yml                            ← Project config (user-editable)
├── requirements.yml                      ← Collection dependencies
├── site.yml                              ← Thin wrapper playbook (optional)
└── input/
    └── project_default/
        ├── image_build_config.yml        ← Domain config
        ├── image_build_credentials.yml   ← Vault-encrypted credentials
        └── repo_manager_output/
            ├── repo_status.yml           ← From repo_manager
            └── functional_group_packages.yml

# Collection (read-only, installed via ansible-galaxy):
~/.ansible/collections/ansible_collections/dell/omnia_image_build/
├── playbooks/
│   └── image_build_manager.yml           ← Collection playbook
├── roles/
│   └── setup/                            ← Reads config from workspace
└── plugins/
    └── modules/                          ← Domain modules
```

### Three Input Patterns for Collections

#### Pattern A: `--extra-vars` (Simplest)

Pass the workspace path as an extra variable:

```bash
# User runs from their workspace:
cd ~/my-omnia-project

ansible-playbook dell.omnia_image_build.image_build_manager \
  -e "workspace_dir=$(pwd)" \
  --tags prepare
```

Inside the collection roles, all paths are derived from `workspace_dir`:

```yaml
# roles/setup/tasks/load_config.yml (inside collection)
- name: Load config.yml from workspace
  ansible.builtin.include_vars:
    file: "{{ workspace_dir }}/config.yml"
    name: standalone_config

- name: Set input directory from workspace
  ansible.builtin.set_fact:
    input_project_dir: "{{ workspace_dir }}/input/{{ standalone_config.project_name }}"
    cacheable: true
```

#### Pattern B: Thin Wrapper Playbook (Recommended)

User creates a minimal `site.yml` in their workspace that calls the collection playbook:

```yaml
# ~/my-omnia-project/site.yml — User's wrapper playbook
---
- name: Load workspace config
  hosts: localhost
  connection: local
  gather_facts: false
  tags: always
  tasks:
    - name: Set workspace directory
      ansible.builtin.set_fact:
        workspace_dir: "{{ playbook_dir }}"
        cacheable: true

- name: Run image build manager
  ansible.builtin.import_playbook: dell.omnia_image_build.image_build_manager
```

```bash
cd ~/my-omnia-project
ansible-playbook site.yml --tags prepare
```

Now `playbook_dir` resolves to the user's workspace, and the collection roles pick up
`workspace_dir` to find config files.

#### Pattern C: Environment Variable

```bash
export OMNIA_WORKSPACE=~/my-omnia-project
ansible-playbook dell.omnia_image_build.image_build_manager --tags prepare
```

```yaml
# Inside collection role:
- name: Set workspace from environment
  ansible.builtin.set_fact:
    workspace_dir: "{{ lookup('env', 'OMNIA_WORKSPACE') | default(playbook_dir + '/..') }}"
```

### Input Resolution Priority

The setup role resolves input paths in this priority order:

```yaml
# 1. Explicit extra-var (highest priority)
workspace_dir: "{{ workspace_dir }}"

# 2. Environment variable
workspace_dir: "{{ lookup('env', 'OMNIA_WORKSPACE') | default('') }}"

# 3. Wrapper playbook (playbook_dir = user's workspace)
workspace_dir: "{{ playbook_dir }}"

# 4. Fallback — collection playbook_dir + parent (development/flat-repo mode)
workspace_dir: "{{ playbook_dir + '/..' }}"
```

Collection setup role implementation:

```yaml
# dell/omnia_image_build/roles/setup/tasks/resolve_workspace.yml
- name: Resolve workspace directory
  ansible.builtin.set_fact:
    workspace_dir: >-
      {{ workspace_dir | default(
           lookup('env', 'OMNIA_WORKSPACE') | default(
             playbook_dir + '/..', true
           ), true
         ) }}
    cacheable: true

- name: Validate workspace directory exists
  ansible.builtin.stat:
    path: "{{ workspace_dir }}/config.yml"
  register: _ws_config

- name: Fail if workspace config not found
  ansible.builtin.fail:
    msg: >-
      config.yml not found in workspace '{{ workspace_dir }}'.
      Either:
        1. Run from your project directory: cd ~/my-project && ansible-playbook site.yml
        2. Pass workspace: ansible-playbook dell.omnia_image_build.image_build_manager -e workspace_dir=/path/to/project
        3. Set environment: export OMNIA_WORKSPACE=/path/to/project
  when: not _ws_config.stat.exists
```

### Input File Mapping (Flat Repo → Collection)

| Input File | Flat Repo Path | Collection Path |
|-----------|---------------|-----------------|
| `config.yml` | `{{ playbook_dir }}/../config.yml` | `{{ workspace_dir }}/config.yml` |
| `image_build_config.yml` | `{{ playbook_dir }}/input/<project>/image_build_manager/image_build_config.yml` | `{{ workspace_dir }}/input/<project>/image_build_manager/image_build_config.yml` |
| `image_build_credentials.yml` | `{{ playbook_dir }}/input/<project>/image_build_credentials.yml` | `{{ workspace_dir }}/input/<project>/image_build_credentials.yml` |
| `repo_status.yml` | `/opt/omnia/repo_manager/output/<project>/repo_status.yml` | Same (absolute path — unchanged) |
| `functional_group_packages.yml` | `{{ playbook_dir }}/input/<project>/repo_manager_output/functional_group_packages.yml` | `{{ workspace_dir }}/input/<project>/repo_manager_output/functional_group_packages.yml` |
| JSON schemas | `{{ playbook_dir }}/library/module_utils/.../schema/*.json` | `{{ ansible_collections_path }}/.../plugins/module_utils/.../schema/*.json` (inside collection) |

**Key insight**: User-editable files come from `workspace_dir`. Read-only assets (schemas,
templates) ship inside the collection. Upstream contract files (repo_status.yml) use absolute
paths configured in `config.yml`.

---

## 16. Inter-Domain Output Handling (Stage Chaining)

### The Problem

Omnia domains run in sequence. Each domain produces output that the next domain consumes:

```
repo_manager → repo_status.yml → image_build_manager → build_status.yml → orchestrator
```

In the current flat repo, output paths are hardcoded or derived from `shared_path`:

```yaml
# repo_manager writes to:
/opt/omnia/repo_manager/output/project_default/repo_status.yml

# image_build_manager reads from:
repo_manager_output_dir: "/opt/omnia/repo_manager/output/project_default/"

# image_build_manager writes to:
{{ shared_path }}/output/{{ project_name }}/build_status.yml

# orchestrator reads from:
{{ shared_path }}/output/{{ project_name }}/build_status.yml
```

### How Collections Handle Inter-Domain Contracts

Collections don't change the contract mechanism — **file-based YAML contracts stay the same**.
The output files live on the filesystem (under `<state_path>/`), not inside any collection.

```
┌───────────────────────────────────┐
│          File System              │
│  (state_path = /opt/omnia/...)    │
│                                   │
│  repo_manager/                    │
│    └── output/project_default/    │
│        └── repo_status.yml ──────────────┐
│                                   │      │
│  image_build_manager/             │      │
│    └── output/project_default/    │      │
│        └── build_status.yml ─────────────────┐
│                                   │      │   │
└───────────────────────────────────┘      │   │
                                           │   │
┌──────────────────────────────┐           │   │
│ dell.omnia_image_build       │           │   │
│ (collection — read-only)     │◄──────────┘   │
│                              │               │
│ roles/setup reads            │               │
│   repo_status.yml            │               │
│   from configured path       │               │
└──────────────────────────────┘               │
                                               │
┌──────────────────────────────┐               │
│ dell.omnia_orchestrator      │               │
│ (collection — read-only)     │◄──────────────┘
│                              │
│ roles/setup reads            │
│   build_status.yml           │
│   from configured path       │
└──────────────────────────────┘
```

### Contract Path Configuration

Each domain's `config.yml` declares where to find upstream contracts:

```yaml
# ~/my-omnia-project/config.yml
project_name: "project_default"

host:
  hostname: "myhost"
  shared_path: "/opt/omnia/image_build_manager"
  domain_name: "local"
  admin_nic_ip: "10.20.0.1"

# Upstream contract paths (where to find other domains' output)
upstream:
  repo_manager_output_dir: "/opt/omnia/repo_manager/output/project_default"
  pulp_cert_path: "/opt/omnia/pulp/settings/certs/pulp_webserver.crt"
```

### Output Location

Output is written to the filesystem (never inside the collection):

```yaml
# Collection role writes output to state_path (from config.yml):
- name: Write build_status.yml
  ansible.builtin.template:
    src: build_status.yml.j2
    dest: "{{ output_project_dir }}/build_status.yml"
    # output_project_dir = {{ shared_path }}/output/{{ project_name }}
    # e.g., /opt/omnia/image_build_manager/output/project_default/build_status.yml
```

### Integration Repo Orchestration

In the `dell/omnia` integration repo, `omnia.sh` chains domain collections:

```bash
#!/bin/bash
# dell/omnia/omnia.sh — Orchestrator

source /opt/omnia/venv/bin/activate

# Each domain reads upstream contracts from well-known state_path locations.
# repo_manager writes to /opt/omnia/repo_manager/output/
# image_build_manager reads from there, writes to /opt/omnia/image_build_manager/output/
# orchestrator reads from image_build_manager output

ansible-playbook dell.omnia_repo_manager.repo_manager \
  -e workspace_dir=/opt/omnia/workspace

ansible-playbook dell.omnia_image_build.image_build_manager \
  -e workspace_dir=/opt/omnia/workspace \
  --tags prepare

ansible-playbook dell.omnia_image_build.image_build_manager \
  -e workspace_dir=/opt/omnia/workspace \
  --tags build

ansible-playbook dell.omnia_orchestrator.orchestrator \
  -e workspace_dir=/opt/omnia/workspace
```

### Contract Validation in Collections

Each collection's setup role validates upstream contracts on startup:

```yaml
# dell/omnia_image_build/roles/setup/tasks/validate_upstream.yml
- name: Check repo_status.yml exists
  ansible.builtin.stat:
    path: "{{ upstream_repo_manager_output_dir }}/repo_status.yml"
  register: _repo_status_file

- name: Fail if repo_status.yml not found
  ansible.builtin.fail:
    msg: >-
      Upstream contract file not found: {{ upstream_repo_manager_output_dir }}/repo_status.yml.
      Run repo_manager first:
        ansible-playbook dell.omnia_repo_manager.repo_manager -e workspace_dir={{ workspace_dir }}
  when: not _repo_status_file.stat.exists

- name: Load repo_status.yml
  ansible.builtin.include_vars:
    file: "{{ upstream_repo_manager_output_dir }}/repo_status.yml"
    name: repo_status

- name: Validate repo_manager completed successfully
  ansible.builtin.assert:
    that:
      - repo_status.overall_status == 'success'
    fail_msg: "repo_manager did not complete successfully. Re-run repo_manager."
```

---

## 17. Tag Handling in Collections

### How Tags Work With Collection Playbooks

Ansible tags work **identically** in collection playbooks as in flat-repo playbooks.
The `--tags` flag is passed at the CLI and applies to all plays/tasks regardless of where
the playbook lives.

```bash
# Flat repo (current):
ansible-playbook image_build_manager.yml --tags prepare

# Collection (same tags, same behavior):
ansible-playbook dell.omnia_image_build.image_build_manager --tags prepare

# Via wrapper playbook:
ansible-playbook site.yml --tags prepare
```

### Tag Architecture in Collection

The entry point playbook inside the collection uses the same tag structure:

```yaml
# dell/omnia_image_build/playbooks/image_build_manager.yml

# Step 0: Setup (always runs — loads config, validates tags)
- name: Image build manager setup
  hosts: localhost
  connection: local
  gather_facts: false
  tags: always
  roles:
    - dell.omnia_image_build.setup         # FQCN for collection role

# Step 1: Validate
- name: Validate configuration
  ansible.builtin.import_playbook: dell.omnia_image_build.validate
  tags:
    - always
    - validate

# Step 2: Credentials (skipped for cleanup/validate)
- name: Get build credentials
  ansible.builtin.import_playbook: dell.omnia_image_build.get_credentials
  when: not (skip_build_credentials | default(false) | bool)
  tags: always

# FLOW: prepare
- name: Prepare infrastructure
  ansible.builtin.import_playbook: dell.omnia_image_build.prepare
  tags:
    - prepare

# FLOW: build
- name: Build x86_64 images
  ansible.builtin.import_playbook: dell.omnia_image_build.build_x86_64
  tags:
    - x86_64
    - build

- name: Build aarch64 images
  ansible.builtin.import_playbook: dell.omnia_image_build.build_aarch64
  when: hostvars['localhost']['aarch64_inventory_host_ip'] | default('') | length > 0
  tags:
    - aarch64
    - build

# FLOW: cleanup (opt-in)
- name: Cleanup
  ansible.builtin.import_playbook: dell.omnia_image_build.cleanup
  tags:
    - never
    - cleanup

# FLOW: upgrade (opt-in)
- name: Upgrade
  ansible.builtin.import_playbook: dell.omnia_image_build.upgrade
  tags:
    - never
    - upgrade

# FLOW: rollback (opt-in)
- name: Rollback
  ansible.builtin.import_playbook: dell.omnia_image_build.rollback
  tags:
    - never
    - rollback
```

### Tag Validation Inside Collection Roles

The setup role validates tags using `ansible_run_tags` — this works the same in collections:

```yaml
# dell/omnia_image_build/roles/setup/vars/main.yml
supported_tags:
  - prepare
  - build
  - cleanup
  - validate
  - upgrade
  - rollback

skip_credential_tags:
  - cleanup
  - validate

invalid_tag_combinations:
  - [prepare, cleanup]
  - [build, cleanup]
  - [prepare, validate]
  - [build, validate]
  - [prepare, upgrade]
  - [build, upgrade]
  - [cleanup, upgrade]
  - [prepare, rollback]
  - [build, rollback]
  - [cleanup, rollback]
  - [upgrade, rollback]
```

```yaml
# dell/omnia_image_build/roles/setup/tasks/validate_tags.yml
- name: Get provided tags
  ansible.builtin.set_fact:
    provided_tags: "{{ ansible_run_tags | difference(['always', 'all']) }}"

- name: Fail if invalid tags
  ansible.builtin.fail:
    msg: "{{ tag_validation_fail_msg }}"
  when:
    - provided_tags | length > 0
    - (provided_tags | difference(supported_tags)) | length > 0

- name: Check invalid combinations
  ansible.builtin.set_fact:
    has_invalid_combination: true
  when:
    - provided_tags | length > 1
    - item | difference(provided_tags) | length == 0
  loop: "{{ invalid_tag_combinations }}"

- name: Fail if invalid combination
  ansible.builtin.fail:
    msg: "{{ tag_combination_fail_msg }}"
  when: has_invalid_combination | default(false) | bool

- name: Set skip_credentials for cleanup/validate
  ansible.builtin.set_fact:
    skip_build_credentials: true
    cacheable: true
  when:
    - provided_tags | length > 0
    - (provided_tags | intersect(skip_credential_tags)) | length > 0
```

### Tag Behavior Summary

| Tag | What Runs | Credentials | Notes |
|-----|-----------|-------------|-------|
| *(none)* | setup → validate → credentials → prepare → build | Yes | Default full flow |
| `prepare` | setup → validate → credentials → prepare | Yes | Deploy MinIO + Registry |
| `build` | setup → validate → credentials → build | Yes | Build images only |
| `validate` | setup → validate | No | Config validation only |
| `cleanup` | setup → cleanup | No | Remove all artifacts |
| `upgrade` | setup → upgrade | No | Version migration |
| `rollback` | setup → rollback | No | Revert to previous version |

### Key Nuances for Collection Tags

1. **`tags: always`** works the same — setup role always runs regardless of which tag is passed.
2. **`tags: [never, cleanup]`** works the same — cleanup only runs when explicitly requested.
3. **`ansible_run_tags`** variable is available inside collection roles — tag validation code is unchanged.
4. **`import_playbook` with FQCN** — `dell.omnia_image_build.prepare` resolves to the collection's `playbooks/prepare.yml`. Tags on `import_playbook` work identically.
5. **Wrapper playbook tags pass through** — when `site.yml` imports a collection playbook, `--tags prepare` applies to both the wrapper and the imported collection playbook.

### Tag Flow Diagram (Collection)

```
User: ansible-playbook dell.omnia_image_build.image_build_manager --tags prepare

  ┌──────────────────────────────────────────────────────────────────────┐
  │ Collection: dell.omnia_image_build                                   │
  │                                                                      │
  │  image_build_manager.yml                                             │
  │  │                                                                   │
  │  ├── [tags: always]  setup role                                      │
  │  │   ├── resolve_workspace.yml    ← find config.yml                 │
  │  │   ├── validate_tags.yml        ← validate 'prepare' is valid     │
  │  │   ├── load_config.yml          ← load workspace/config.yml       │
  │  │   └── validate_prereqs.yml     ← check upstream contracts        │
  │  │                                                                   │
  │  ├── [tags: always]  validate playbook                               │
  │  │   └── schema + logic checks                                      │
  │  │                                                                   │
  │  ├── [tags: always]  credentials playbook                            │
  │  │   └── prompts user for S3 + provision credentials                │
  │  │                                                                   │
  │  ├── [tags: prepare] ← MATCHES → prepare playbook RUNS              │
  │  │   ├── deploy_minio role                                           │
  │  │   └── deploy_registry role                                        │
  │  │                                                                   │
  │  ├── [tags: build]   ← NO MATCH → SKIPPED                           │
  │  ├── [tags: never, cleanup] ← NO MATCH → SKIPPED                    │
  │  ├── [tags: never, upgrade] ← NO MATCH → SKIPPED                    │
  │  └── [tags: never, rollback] ← NO MATCH → SKIPPED                   │
  │                                                                      │
  └──────────────────────────────────────────────────────────────────────┘
```

---

## 18. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Migration breaks existing playbooks | All domains fail | Phase 1 only touches `common/` — domains migrate one at a time |
| `module_utils` import path change | Python ImportError in modules | Automated find-replace + `ansible-test sanity` catches all |
| Dev workflow friction | Slower development cycle | Symlink pattern for local development |
| Collection version conflicts | Incompatible versions installed | Pin versions in `requirements.yml` + CI validation |
| Air-gap distribution | Can't reach Galaxy | Build tarballs and distribute via Pulp or file copy |
| Galaxy namespace reservation | Someone else takes `dell` | Register namespace early on Galaxy |
| Large `common/` collection | Slow install, bloated deps | Split further if needed (e.g., `dell.omnia_network`, `dell.omnia_storage`) |

---

## 16. References

- [Ansible Collection Developer Guide](https://docs.ansible.com/ansible/latest/dev_guide/developing_collections.html)
- [ansible-galaxy CLI](https://docs.ansible.com/ansible/latest/cli/ansible-galaxy.html)
- [Collection Structure](https://docs.ansible.com/ansible/latest/dev_guide/developing_collections_structure.html)
- [Using Collections in Playbooks](https://docs.ansible.com/ansible/latest/collections_guide/collections_using_playbooks.html)
- [ansible-test](https://docs.ansible.com/ansible/latest/dev_guide/testing.html)
- [Private Automation Hub](https://access.redhat.com/documentation/en-us/red_hat_ansible_automation_platform/)
