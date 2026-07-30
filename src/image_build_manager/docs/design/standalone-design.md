# Image Build Manager — Standalone Repository Design

## Status: ACTIVE v3.1

This document describes how `image_build_manager` operates as a **fully independent domain**
running directly on a RHEL bare-metal host using Ansible + Python.
The core container is **not required**. Bare-metal is the only supported execution mode.

---

## 1. Current Independence Audit

### 1.1 Dependency Inventory

| # | Dependency | Files Affected | Type | Status |
|---|-----------|---------------|------|--------|
| 1 | **OIM metadata** (`/opt/omnia/.data/oim_metadata.yml`) | `image_build_setup/vars/main.yml` | Config | ✅ Replaced by `config.yml` |
| 2 | **Project config** (`/opt/omnia/input/default.yml`) | `image_build_setup` role | Config | ✅ Replaced by `config.yml` |
| 3 | **Upgrade lock** (`/opt/omnia/.data/upgrade_in_progress.lock`) | `image_build_setup` role | Guard | ✅ Commented out |
| 4 | **repo_status.yml** (from `repo_manager`) | `image_build_manager.yml` Step 4 | Contract | ✅ User-provided in `repo_manager_output/` |
| 5 | **software_config.json** | `fetch_build_packages`, `image_package_collector.py` | Config | ✅ Replaced by `functional_group_packages.yml` |
| 6 | **Core container** (`omnia_core`) | Runtime assumption | Runtime | ✅ Not required — Mode A/B only |
| 7 | **OIM host group** (SSH to OIM) | All `hosts: oim` plays | Inventory | ✅ Auto-detected (local/SSH) |
| 8 | **omnia.target** (systemd) | `prepare_image_build_manager.yml`, `cleanup` | Service | ✅ Skipped in standalone |
| 9 | **`/opt/omnia/` hardcoded paths** | All role vars files | Paths | ✅ All defaults removed — use `config.yml` paths |
| 10 | **Credential utility** | Replaced by `collect_build_credentials` role | Eliminated | ✅ Done |
| 11 | **common/callback_plugins/** | Local copy at `callback_plugins/omnia_default.py` | Eliminated | ✅ Done |
| 12 | **common/library/modules/** | All 5 modules local at `library/modules/` | Eliminated | ✅ Done |
| 13 | **common/library/module_utils/** | `build_image/` + `image_build_validation/` local | Eliminated | ✅ Done |
| 14 | **common/vars/** | `common_vars` inlined into `image_build_setup/vars/main.yml` | Eliminated | ✅ Done |
| 15 | **playbooks/utils/** | All absorbed into domain roles | Eliminated | ✅ Done |

### 1.2 Self-Containment Summary

```
✅ ansible.cfg           — fully local paths (library, module_utils, callback_plugins, roles)
✅ callback_plugins/     — local copy of omnia_default.py
✅ library/modules/      — all 5 modules (base_image_package_collector, image_package_collector,
                           functional_group_parser, generate_functional_groups, validate_image_build_config)
✅ library/module_utils/ — build_image/ + image_build_validation/ fully local
✅ credential flow       — collect_build_credentials role
✅ validation flow       — validate_image_build_input role + validate_image_build_config module
✅ functional groups     — defined in image_build_config.yml (standalone); generate_functional_groups commented out
✅ tag validation        — image_build_setup role (supported_tags, skip_credential_tags, invalid_tag_combinations)
✅ zero ../common/       — no ansible.cfg references to ../common/ or ../playbooks/utils/
```

### 1.3 Omnia Coupling — FULLY RESOLVED

All 9 Omnia coupling points have been resolved:

| # | Coupling | Resolution |
|---|---------|------------|
| 1 | OIM metadata | Replaced by `config.yml → build_host` section |
| 2 | Project config | Replaced by `config.yml → project_name` |
| 3 | Upgrade lock | Commented out in `image_build_setup/vars/main.yml` |
| 4 | `repo_status.yml` | User-provided in `repo_manager_output/` |
| 5 | `software_config.json` | **Replaced by `functional_group_packages.yml`** — direct RPM mapping, no software_config.json needed |
| 6 | Core container | Mode A (bare-metal) + Mode B (domain container) — no `omnia_core` needed |
| 7 | `omnia.target` | Skipped in standalone mode |
| 8 | `/opt/omnia/` in `ansible.cfg` | Uses `./log/` and `/tmp/.ansible/` |
| 9 | `/opt/omnia/` defaults in vars | All `/opt/omnia` fallback defaults removed from role vars |

---

## 2. Input Files — Package Resolution (Standalone)

### 2.1 Design Decision: Replace `software_config.json` With Direct Mapping

**Problem** (Mode C): `software_config.json` is a project-level file shared across ALL domains.
It defines which software modules are enabled, then per-arch JSON files in `config/<arch>/<os>/<ver>/`
contain the actual RPM packages. `image_package_collector.py` and `base_image_package_collector.py`
read both to resolve the final package list. This chain has 4 files and 2 Python modules.

**Solution** (Standalone): A single `functional_group_packages.yml` file in `repo_manager_output/`
maps functional groups directly to RPM packages. No `software_config.json`, no per-arch JSON files,
no collector modules needed.

```
MODE C (NOT SUPPORTED):                 STANDALONE (Mode A/B):
software_config.json                    functional_group_packages.yml
  → config/<arch>/<os>/<ver>/*.json       ├── base_packages: [systemd, kernel, ...]
  → image_package_collector.py            └── functional_groups:
  → base_image_package_collector.py             slurm_node_x86_64:
  → compute_images_dict                           packages: [munge, slurm-slurmd, ...]
                                                → compute_images_dict (directly)
```

### 2.2 Design Decision: Keep `repo_status.yml` Separate, Extend With OS Metadata

`repo_status.yml` remains a **separate input file** — NOT merged into `config.yml`.

**Rationale**:
- `repo_status.yml` is the **output contract of repo_manager** — it's infrastructure data, not user config
- In Omnia mode, repo_manager produces it automatically after syncing repos
- In standalone mode, user provides it manually (copy from `samples/repo_status.yml`)
- Merging it into config.yml would force users to duplicate repo URLs into a config format
- The RPM repo URLs already embed OS version in their paths (e.g. `rhel/10.0/rpms/`)

**Extension**: Add `cluster_os_type` and `cluster_os_version` to `repo_status.yml`:

```yaml
# repo_status.yml — UPDATED contract (v2)
---
overall_status: "success"

# OS metadata (NEW — tells consumers what OS the repos were synced for)
cluster_os_type: "rhel"
cluster_os_version: "10.0"

# RPM Repository Base URLs
rpm_repos:
  x86_64:
    baseos: "https://10.20.0.1:2225/pulp/content/.../x86_64_rhel_10.0_baseos/"
    appstream: "https://10.20.0.1:2225/pulp/content/.../x86_64_rhel_10.0_appstream/"
    # ... other repos
  aarch64:
    baseos: "https://10.20.0.1:2225/pulp/content/.../aarch64_rhel_10.0_baseos/"
    appstream: "https://10.20.0.1:2225/pulp/content/.../aarch64_rhel_10.0_appstream/"

# Repo manager metadata (Omnia mode — optional in standalone)
repo_manager:
  port: 2225
  certificates:
    server_crt: "/opt/omnia/pulp/settings/certs/pulp_webserver.crt"

# User-defined repos (optional)
user_repos:
  x86_64: {}
  aarch64: {}
```

### 2.3 Where OS Version and OS Name Come From

**Current flow** (Omnia mode):
```
software_config.json → fetch_build_packages/tasks/main.yml
                        → include_vars software_config.json
                        → set_fact rhel_tag: software_config.cluster_os_version
                        → set_fact default_json_path using cluster_os_type/cluster_os_version
                     → validate_build_runtime/tasks/main.yml
                        → validates software_config.json exists and has valid JSON
                     → library/modules/image_package_collector.py
                        → reads cluster_os_version from software_config.json
                     → library/modules/base_image_package_collector.py
                        → reads software_config.json for OS info
```

**Updated flow** (all modes):
```
repo_status.yml → cluster_os_type, cluster_os_version    (OS metadata — NEW)
               → rpm_repos                               (repo URLs — existing)
               → repo_manager.certificates               (Omnia only — existing)

software_config.json → softwares[] array                  (package catalog — KEEP)
                     → service_k8s version                (KEEP)
                     → additional_packages, admin_debug   (KEEP)
                     → cluster_os_type, cluster_os_version (DEPRECATED — use repo_status.yml)
```

### 2.4 Code Changes Required for OS Version Source

**File: `roles/fetch_build_packages/tasks/main.yml`** — Change OS fact source:

```yaml
# BEFORE (reads OS info from software_config.json):
- name: Include software config
  ansible.builtin.include_vars:
    file: "{{ software_config_file_path }}"
    name: software_config

- name: Set cluster OS facts
  ansible.builtin.set_fact:
    rhel_tag: "{{ software_config.cluster_os_version }}"
    default_json_path: "{{ input_project_dir }}/config/{{ build_arch }}/{{ software_config.cluster_os_type }}/{{ software_config.cluster_os_version }}/..."

# AFTER (reads OS info from repo_status.yml facts, with software_config.json fallback):
- name: Include software config
  ansible.builtin.include_vars:
    file: "{{ software_config_file_path }}"
    name: software_config

- name: Set cluster OS facts
  ansible.builtin.set_fact:
    rhel_tag: "{{ cluster_os_version | default(software_config.cluster_os_version) }}"
    default_json_path: >-
      {{ input_project_dir }}/config/{{ build_arch }}/
      {{ cluster_os_type | default(software_config.cluster_os_type) }}/
      {{ cluster_os_version | default(software_config.cluster_os_version) }}/default_packages.json
    additional_json_path: >-
      {{ input_project_dir }}/config/{{ build_arch }}/
      {{ cluster_os_type | default(software_config.cluster_os_type) }}/
      {{ cluster_os_version | default(software_config.cluster_os_version) }}/additional_packages.json
    admin_debug_json_path: >-
      {{ input_project_dir }}/config/{{ build_arch }}/
      {{ cluster_os_type | default(software_config.cluster_os_type) }}/
      {{ cluster_os_version | default(software_config.cluster_os_version) }}/admin_debug_packages.json
```

The `cluster_os_type` and `cluster_os_version` facts are set by `image_build_setup`
(from `repo_status.yml` in all modes). The `| default(software_config.*)` fallback
preserves backward compatibility when repo_status.yml doesn't have OS fields yet.

### 2.5 `software_config.json` — NOT USED in Standalone Mode

In standalone mode, `software_config.json` is **completely replaced** by
`functional_group_packages.yml`. The entire Mode C package resolution chain
(`software_config.json` → per-arch JSONs → `image_package_collector.py` →
`base_image_package_collector.py`) is commented out in `fetch_build_packages/tasks/main.yml`.

**Standalone user provides these input files**:
1. `config.yml` — project settings + build host (replaces OIM metadata + default.yml)
2. `repo_status.yml` — RPM repo URLs + OS type/version (in `repo_manager_output/`)
3. `functional_group_packages.yml` — functional group → RPM package mapping (in `repo_manager_output/`)
4. `image_build_config.yml` — S3 provider, functional groups list, aarch64 host, build settings

---

## 3. Execution Modes

### 3.1 Three Supported Modes

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    IMAGE BUILD MANAGER — THREE EXECUTION MODES                           │
└─────────────────────────────────────────────────────────────────────────────────────────┘

  MODE A: BARE-METAL              MODE B: DOMAIN CONTAINER           MODE C: OMNIA MONO-REPO
  ──────────────────              ──────────────────────              ───────────────────────
  ┌──────────────────┐            ┌──────────────────┐               ┌──────────────────┐
  │  Build Host      │            │  image_build     │               │  omnia_core      │
  │  (RHEL/Rocky)    │            │  _runner         │               │  container       │
  │                  │            │  container       │               │  (wolfi-base)    │
  │  Ansible 2.16+   │            │  (wolfi-base)    │               │  Ansible bundled │
  │  Python 3.12+    │            │  Ansible pinned  │               │  All domains     │
  │  Podman/Docker   │            │  Long-running    │               │  OIM metadata    │
  └────────┬─────────┘            │  (sshd + shell)  │               └────────┬─────────┘
           │                      └────────┬─────────┘                        │
  ┌────────▼─────────┐            ┌────────▼─────────┐               ┌────────▼─────────┐
  │  config.yml      │            │  config.yml      │               │  OIM metadata    │
  │  repo_status.yml │            │  repo_status.yml │               │  default.yml     │
  │  software_config │            │  software_config │               │  software_config │
  │  image_build_cfg │            │  image_build_cfg │               │  repo_status.yml │
  └────────┬─────────┘            └────────┬─────────┘               └────────┬─────────┘
           │                               │                                  │
           └───────────────┬───────────────┘                                  │
                           │                                                  │
                           └──────────────────┬───────────────────────────────┘
                                              │
                                     ┌────────▼────────┐
                                     │ SHARED BUILD    │
                                     │ PIPELINE        │
                                     │ (same roles,    │
                                     │  same modules,  │
                                     │  same playbooks)│
                                     └─────────────────┘
```

### 3.2 Mode Comparison

| Aspect | Mode A: Bare-Metal | Mode B: Domain Container | Mode C: Omnia Mono-Repo |
|--------|-------------------|--------------------------|------------------------|
| **Ansible source** | User-installed (`pip install ansible-core`) | Pinned in container image | Bundled in `omnia_core` |
| **Python source** | User-installed (system or venv) | Pinned in container image | Bundled in `omnia_core` |
| **Container runtime** | Required on host (Podman/Docker) | Required on host | Required on host |
| **Config source** | `config.yml` + `repo_status.yml` + `functional_group_packages.yml` | Same (volume-mounted) | OIM metadata + default.yml |
| **RPM repos** | `repo_status.yml` (user-provided) | Same (volume-mounted) | `repo_status.yml` from repo_manager |
| **OS type/version** | `repo_status.yml` | `repo_status.yml` | `software_config.json` (Mode C) |
| **Package mapping** | `functional_group_packages.yml` | `functional_group_packages.yml` | `software_config.json` + per-arch JSONs (Mode C) |
| **Core container needed** | **No** | **No** | **Yes** |
| **OIM metadata needed** | **No** | **No** | **Yes** |
| **Air-gap support** | Via local RPM mirror URLs in `repo_status.yml` | Same | Via Pulp (repo_manager) |
| **Container lifecycle** | N/A | Long-running (sshd) — `podman exec` for tags | Long-running (sshd) |
| **OIM connection** | `ansible_connection: local` | `ansible_connection: ssh` (auto-detected via `/run/.containerenv`) | SSH to core container |
| **Functional groups** | `image_build_config.yml` | `image_build_config.yml` | `generate_functional_groups` from CSV |
| **Target users** | DevOps, CI/CD, advanced users | Production, repeatable builds | **NOT SUPPORTED** |

### 3.3 Mode Detection

```yaml
# Priority: explicit var > config.yml detection > Omnia detection
- name: Detect execution mode
  ansible.builtin.set_fact:
    execution_mode: >-
      {{ 'standalone' if (standalone_mode | default(false) | bool)
         else ('standalone' if (lookup('file', playbook_dir + '/../config.yml',
                                       errors='ignore') | default('') | length > 0
                                and not (omnia_input_dir is defined))
               else 'omnia') }}
    cacheable: true
```

---

## 4. Container Strategy — Analysis & Recommendation

### 4.1 Should Each Domain Have Its Own Container?

| Option | Pros | Cons |
|--------|------|------|
| **A. No container — bare-metal** | Zero container overhead, user controls Ansible/Python versions, simplest for CI/CD, works anywhere with pip | User must manage dependencies, version drift possible |
| **B. Per-domain lightweight container** | Reproducible builds, pinned deps, hermetic execution, independent release cycles | Each domain maintains a Dockerfile, ~200MB per container |
| **C. One `omnia_core` container for everything** | Single image to maintain, all domains share deps | Tight coupling, large image (~2GB), can't release domains independently, single point of failure |
| **D. Orchestrator container that git-clones repos** | Thin meta-container, always gets latest, flexible | Requires network at startup, version pinning is harder, clone failures block execution |

### 4.2 Recommendation: **A + B Hybrid (Bare-Metal First, Optional Container)**

```
RECOMMENDED ARCHITECTURE:
─────────────────────────
  1. Primary: BARE-METAL (Mode A)
     - User has Ansible + Python installed
     - git clone → edit config.yml → ansible-playbook
     - Works in CI/CD pipelines, dev environments, air-gapped hosts

  2. Optional: PER-DOMAIN CONTAINER (Mode B)
     - Containerfile in each domain repo: containers/Containerfile
     - Pins exact Ansible + Python + collection versions
     - Long-running container (sshd) — user runs multiple tags via exec/SSH
     - ~300MB image (wolfi-base + ansible-core + deps + sshd)

  3. NOT SUPPORTED: Monolithic core container (Mode C)
     - Mode C code is guarded by `when: not standalone_mode` and will never execute
     - Creates coupling between unrelated domains
     - Can't release image_build_manager without rebuilding all of omnia_core
     - Forces all domains to share the same Ansible/Python version

  4. NOT RECOMMENDED: Git-clone orchestrator container (Mode D)
     - Network dependency at runtime breaks air-gap
     - Version pinning becomes git tags/branches — fragile
     - Adds latency and failure modes (DNS, auth, rate limits)
```

### 4.3 Container Execution Model — Long-Running (Same as `omnia_core`)

The domain container follows the **same pattern as `omnia_core`**: a long-running container
with sshd that stays alive. Users SSH in or use `podman exec` to run playbooks with
different tags. The container does **NOT** run-and-exit.

**Why long-running instead of run-and-exit?**

| Concern | Run-and-Exit | Long-Running (Recommended) |
|---------|-------------|---------------------------|
| **Multiple tags** | Must restart container for each tag | Run any tag via `podman exec` or SSH |
| **State between runs** | Lost — must remount everything | Preserved — credentials, cached facts, logs |
| **Credential prompts** | Interactive prompts require `-it` on each run | One-time setup, then reuse |
| **Debugging** | Container gone after failure — logs lost | Shell into running container, inspect state |
| **Build artifacts** | Must volume-mount everything | Artifacts persist in container filesystem |
| **MinIO/Registry** | Services need to KEEP RUNNING after prepare | Container stays alive → services stay alive |

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    DOMAIN CONTAINER LIFECYCLE                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

  Host                              Container (image_build_runner)
  ────                              ──────────────────────────────
  │                                 │
  │  podman run -d ...              │
  │────────────────────────────────>│ ┌──────────────────────────┐
  │                                 │ │ entrypoint.sh:           │
  │                                 │ │  1. ssh-keygen -A        │
  │                                 │ │  2. Start sshd on :2230  │
  │                                 │ │  3. cd /image_build_mgr  │
  │                                 │ │  4. Wait (sshd keeps     │
  │                                 │ │     container alive)     │
  │                                 │ └──────────────────────────┘
  │                                 │
  │  # Run prepare tag             │
  │  podman exec -it <cid> \       │
  │    ansible-playbook \           │
  │    image_build_manager.yml \    │
  │    --tags prepare               │
  │────────────────────────────────>│ → deploys MinIO + Registry
  │                                 │
  │  # Run build tag (later)       │
  │  podman exec -it <cid> \       │
  │    ansible-playbook \           │
  │    image_build_manager.yml \    │
  │    --tags build                 │
  │────────────────────────────────>│ → builds OS images
  │                                 │
  │  # Run cleanup tag             │
  │  podman exec -it <cid> \       │
  │    ansible-playbook \           │
  │    image_build_manager.yml \    │
  │    --tags cleanup               │
  │────────────────────────────────>│ → cleanup
  │                                 │
  │  # Interactive shell           │
  │  podman exec -it <cid> bash    │
  │────────────────────────────────>│ → debug, inspect logs
  │                                 │
  │  # OR via SSH                  │
  │  ssh -p 2230 root@localhost    │
  │────────────────────────────────>│ → same access via SSH
  │                                 │
  │  podman stop <cid>             │
  │────────────────────────────────>│ → container stops
  │                                 │
```

### 4.4 Per-Domain Container Design (Containerfile)

```dockerfile
# containers/Containerfile — image_build_manager domain runner
# Pattern: Same as omnia_core (long-running, sshd, shell access)
FROM cgr.dev/chainguard/wolfi-base:latest

ARG IMAGE_BUILD_VERSION=staging

# ── System packages ─────────────────────────────────────────
RUN apk update && apk add --no-cache \
    python-3.12 \
    py3.12-pip \
    git \
    openssh \
    sshpass \
    openssl \
    jq \
    wget \
    rsync \
    curl \
    ca-certificates-bundle \
    ca-certificates \
    shadow \
    bash \
    nano

RUN mkdir -p /usr/local/share/ca-certificates

# ── Python deps ─────────────────────────────────────────────
COPY requirements.txt /opt/image_build_manager/requirements.txt
RUN pip install --no-cache-dir -r /opt/image_build_manager/requirements.txt

# ── Ansible Galaxy collections ──────────────────────────────
COPY requirements.yml /opt/image_build_manager/requirements.yml
RUN ansible-galaxy collection install -r /opt/image_build_manager/requirements.yml

# ── SSH configuration (same pattern as omnia_core) ──────────
RUN sed -i 's/^#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/^#Port 22/Port 2230/' /etc/ssh/sshd_config

EXPOSE 2230
RUN ssh-keygen -A

# ── Directory setup ─────────────────────────────────────────
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# ── Clone domain repo (or COPY for local build) ────────────
# Option A: git clone at build time (production)
# RUN git clone https://github.com/dell/image-build-manager.git \
#     -b ${IMAGE_BUILD_VERSION} /image_build_manager

# Option B: COPY local source (development)
COPY . /image_build_manager/

WORKDIR /image_build_manager

RUN echo "cd /image_build_manager" >> /root/.bashrc

# ── Entrypoint (long-running — sshd keeps container alive) ──
COPY containers/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ── Environment ─────────────────────────────────────────────
ENV ANSIBLE_LOG_PATH=/image_build_manager/log/image_build_manager.log
ENV ANSIBLE_REMOTE_TMP=/tmp/.ansible/tmp

ENTRYPOINT ["/entrypoint.sh"]
```

### 4.5 Entrypoint Script

```bash
#!/bin/bash
# containers/entrypoint.sh — keeps container alive (same pattern as omnia_core)

# Start sshd in background
/usr/sbin/sshd

echo "================================================="
echo " image_build_manager container ready"
echo " SSH: ssh -p 2230 root@<host>"
echo " Exec: podman exec -it <cid> bash"
echo "================================================="
echo ""
echo " Run playbooks:"
echo "   ansible-playbook image_build_manager.yml"
echo "   ansible-playbook image_build_manager.yml --tags prepare"
echo "   ansible-playbook image_build_manager.yml --tags build"
echo "   ansible-playbook image_build_manager.yml --tags cleanup"
echo "   ansible-playbook image_build_manager.yml --tags validate"
echo "================================================="

# Keep container alive (wait forever)
exec tail -f /dev/null
```

### 4.6 Container Usage — Running Multiple Tags

```bash
# ═══════════════════════════════════════════════════════════
# Step 1: Build the domain container image
# ═══════════════════════════════════════════════════════════
podman build -t image_build_runner:1.0 -f containers/Containerfile .

# ═══════════════════════════════════════════════════════════
# Step 2: Start the container (long-running — stays alive)
# ═══════════════════════════════════════════════════════════
podman run -d --name image_build_mgr \
  --privileged \
  -p 2230:2230 \
  -v ./config.yml:/image_build_manager/config.yml:ro \
  -v ./repo_status.yml:/image_build_manager/repo_status.yml:ro \
  -v ./input:/image_build_manager/input:rw \
  -v ./output:/image_build_manager/output:rw \
  -v /run/podman/podman.sock:/run/podman/podman.sock \
  image_build_runner:1.0

# Container is now running with sshd — does NOT exit

# ═══════════════════════════════════════════════════════════
# Step 3: Run playbooks with different tags (via podman exec)
# ═══════════════════════════════════════════════════════════

# Validate config
podman exec -it image_build_mgr \
  ansible-playbook image_build_manager.yml --tags validate

# Deploy MinIO + Registry
podman exec -it image_build_mgr \
  ansible-playbook image_build_manager.yml --tags prepare

# Build images
podman exec -it image_build_mgr \
  ansible-playbook image_build_manager.yml --tags build

# Full flow (no tags — runs prepare + build)
podman exec -it image_build_mgr \
  ansible-playbook image_build_manager.yml

# Cleanup
podman exec -it image_build_mgr \
  ansible-playbook image_build_manager.yml --tags cleanup

# ═══════════════════════════════════════════════════════════
# Step 4: Interactive shell for debugging
# ═══════════════════════════════════════════════════════════
podman exec -it image_build_mgr bash

# OR via SSH
ssh -p 2230 root@localhost

# ═══════════════════════════════════════════════════════════
# Step 5: Stop and remove when done
# ═══════════════════════════════════════════════════════════
podman stop image_build_mgr
podman rm image_build_mgr
```

### 4.7 Why NOT a Git-Clone Orchestrator Container

| Problem | Detail |
|---------|--------|
| **Air-gap breaks** | Can't git clone inside air-gapped environments (Omnia first-class constraint) |
| **Version pinning** | Git branches/tags are mutable; a `main` branch changes under you |
| **Startup latency** | Cloning 5+ repos adds 30-60s before any work starts |
| **Auth complexity** | Private repos need SSH keys or tokens mounted into container |
| **Failure modes** | DNS failure, GitHub rate limits, partial clones — all block execution |
| **Testing overhead** | Can't reproduce a build if upstream repos change between runs |

**Better alternative for multi-domain orchestration**: A `release.yml` manifest file (or git submodules) that pins exact versions:

```yaml
# dell-omnia/release/release.yml — version pinning (NOT git-clone at runtime)
domains:
  image_build_manager: "v1.2.0"
  orchestrator: "v1.1.0"
  discovery: "v1.0.0"
  repo_manager: "v1.3.0"
```

---

## 5. Standalone Configuration

### 5.1 Config File — `config.yml`

`config.yml` replaces OIM metadata and project config **only**.
It does NOT contain RPM repos or OS version — those stay in `repo_status.yml`.

```yaml
# image_build_manager/config.yml — Standalone configuration
---
# Project settings (replaces: /opt/omnia/input/default.yml)
project_name: "my_project"
# input/output paths are auto-derived from src/input/<project_name> and src/output/<project_name>

# Build host settings (replaces: /opt/omnia/.data/oim_metadata.yml)
build_host:
  hostname: "localhost"            # For cluster naming (standalone always runs locally)
  shared_path: "/opt/image_build"  # Persistent storage for MinIO + Registry data
  domain_name: "local"
  admin_nic_ip: "10.20.0.1"       # Admin NIC IP — Pulp and S3 endpoint

# Logging (standalone default: local directory)
log_dir: "./log"
```

### 5.2 Config Source Mapping

| Omnia Source | Standalone Equivalent | File |
|-------------|----------------------|------|
| `/opt/omnia/.data/oim_metadata.yml` | `config.yml → build_host` | `config.yml` |
| `/opt/omnia/input/default.yml` | `config.yml → project_name, input_dir, output_dir` | `config.yml` |
| `software_config.json` (OS fields) | `repo_status.yml → cluster_os_type, cluster_os_version` | `repo_status.yml` |
| `software_config.json` (softwares) | Same file — no change | `software_config.json` |
| `repo_status.yml` (from repo_manager) | User-provided `repo_status.yml` — same format | `repo_status.yml` |
| `/opt/omnia/log/` | `config.yml → log_dir` | `config.yml` |
| `image_build_config.yml` | Same file — no change | `image_build_config.yml` |
| `image_build_credentials.yml` | Same file — no change | Ansible Vault |

---

## 6. Changes Required for Standalone Mode

### 6.1 `image_build_setup` Role — Tri-Mode Bootstrap

The `image_build_setup` role is the **only role** that needs significant changes.
All downstream roles (deploy_minio, build_os_images, etc.) remain untouched —
they read facts set by setup, not Omnia paths directly.

```yaml
# roles/image_build_setup/tasks/main.yml — UPDATED FOR TRI-MODE

# --- Step 0: Tag validation (unchanged) ---
# ... existing tag validation logic ...

# --- Step 0.5: Detect execution mode ---
- name: Detect standalone mode
  ansible.builtin.set_fact:
    standalone_mode: >-
      {{ standalone_mode | default(false) | bool
         or (lookup('file', playbook_dir + '/../config.yml', errors='ignore')
             | default('') | length > 0
             and not (omnia_input_dir is defined)) }}
    cacheable: true

# --- Step 1: Upgrade guard (Omnia mode only) ---
- name: Check upgrade lock file
  ansible.builtin.stat:
    path: "{{ upgrade_lock_path }}"
  register: upgrade_lock
  when: not standalone_mode | bool

- name: Block playbook while upgrade is in progress
  ansible.builtin.fail:
    msg: "{{ upgrade_in_progress_msg }}"
  when:
    - not standalone_mode | bool
    - upgrade_lock.stat.exists
    - not (upgrade_mode | default(false) | bool)

# --- Step 2a: Load project config (Omnia mode) ---
- name: Load omnia project config
  when: not standalone_mode | bool
  block:
    - name: Include omnia project config file
      ansible.builtin.include_vars: "{{ omnia_input_config_file }}"
    - name: Set input/output dirs from omnia config
      ansible.builtin.set_fact:
        input_project_dir: "{{ omnia_input_dir }}/{{ project_name }}"
        output_project_dir: "{{ omnia_output_dir }}/{{ project_name }}"
        cacheable: true

# --- Step 2b: Load standalone config ---
- name: Load standalone config
  when: standalone_mode | bool
  block:
    - name: Include standalone config.yml
      ansible.builtin.include_vars:
        file: "{{ playbook_dir }}/../config.yml"
        name: standalone_config
    - name: Set input/output dirs from standalone config
      ansible.builtin.set_fact:
        input_project_dir: "{{ standalone_config.input_dir }}/{{ standalone_config.project_name }}"
        output_project_dir: "{{ standalone_config.output_dir }}/{{ standalone_config.project_name }}"
        project_name: "{{ standalone_config.project_name }}"
        admin_nic_ip: "{{ standalone_config.build_host.admin_nic_ip }}"
        log_dir: "{{ standalone_config.log_dir | default('./log') }}"
        cacheable: true

# --- Step 3: Load OIM metadata or standalone build_host ---
- name: Include oim metadata vars (Omnia mode)
  ansible.builtin.include_vars: "{{ omnia_metadata_file_path }}"
  when: not standalone_mode | bool

- name: Set build host vars (standalone mode)
  when: standalone_mode | bool
  ansible.builtin.set_fact:
    oim_shared_path: "{{ standalone_config.build_host.shared_path }}"
    oim_node_name: "{{ standalone_config.build_host.hostname }}"
    domain_name: "{{ standalone_config.build_host.domain_name }}"
    admin_nic_ip: "{{ standalone_config.build_host.admin_nic_ip }}"
    cacheable: true

# --- Step 3b: Load OS metadata from repo_status.yml ---
# OS type/version come from repo_status.yml (both Omnia and standalone modes)
# repo_status.yml is loaded in image_build_manager.yml Step 4 — these facts
# are set after include_vars of repo_status.yml:
#   cluster_os_type: "{{ repo_status.cluster_os_type }}"
#   cluster_os_version: "{{ repo_status.cluster_os_version }}"
# Downstream roles (fetch_build_packages) use these facts with fallback:
#   rhel_tag: "{{ cluster_os_type | default(software_config.cluster_os_version) }}"

# --- Step 4: Create build host inventory group ---
- name: Create build_host / oim group
  ansible.builtin.add_host:
    hostname: "{{ oim_node_name | default('localhost') }}"
    ansible_host: "{{ oim_node_name | default('localhost') }}"
    ansible_port: "{{ standalone_config.build_host.ssh_port | default(oim_host_port) | default('22') }}"
    ansible_user: "{{ standalone_config.build_host.ssh_user | default(omit) }}"
    groups: "{{ oim_host_group }}"

# --- Step 5: Set guard facts ---
- name: Set image_build_manager guard facts
  ansible.builtin.set_fact:
    image_build_main_flow: true
    skip_subscription_check: true
    standalone_mode: "{{ standalone_mode }}"
    omnia_run_tags: "{{ omnia_run_tags | default(['image_build_manager']) }}"
    image_build_setup_done: true
    cacheable: true
```

### 6.2 `ansible.cfg` — Standalone-Aware Logging

```ini
# Current (Omnia-coupled):
log_path = /opt/omnia/image_build_manager/log/image_build_manager.log
remote_tmp = /opt/omnia/tmp/.ansible/tmp/

# Standalone-ready (use env var fallback):
# NOTE: ansible.cfg doesn't support Jinja — use environment variables instead
log_path = %(LOG_DIR)s/image_build_manager.log
remote_tmp = /tmp/.ansible/tmp/
```

**Practical approach**: Keep `/opt/omnia/` in `ansible.cfg` for mono-repo compatibility.
Override via environment variable in standalone mode:

```bash
export ANSIBLE_LOG_PATH=./log/image_build_manager.log
ansible-playbook image_build_manager.yml
```

### 6.3 `repo_status.yml` — Same Format, User-Provided

In standalone mode, `repo_status.yml` is **user-provided** with the same format as
repo_manager output. It contains RPM repo URLs + `cluster_os_type`/`cluster_os_version`.

The existing Step 4 in `image_build_manager.yml` loads `repo_status.yml` via `include_vars`.
In standalone mode, the path is configured in `config.yml` or defaults to `./repo_status.yml`.

```yaml
# image_build_manager.yml Step 4 — load repo_status.yml (both modes)
- name: Load repo status
  ansible.builtin.include_vars:
    file: "{{ repo_status_path | default(playbook_dir + '/repo_status.yml') }}"
    name: repo_status

- name: Set OS facts from repo_status
  ansible.builtin.set_fact:
    cluster_os_type: "{{ repo_status.cluster_os_type }}"
    cluster_os_version: "{{ repo_status.cluster_os_version }}"
    cacheable: true
  when: repo_status.cluster_os_type is defined
```

### 6.4 omnia.target — Conditional Skip

```yaml
# prepare_image_build_manager.yml — add standalone guard
- name: Update omnia.target with services
  when: not standalone_mode | default(false) | bool
  block:
    # ... existing omnia.target registration ...
```

---

## 7. `/opt/omnia/` Path Decoupling Plan

### 7.1 Files With Hardcoded `/opt/omnia/` Paths

| File | Occurrences | Decoupling Strategy |
|------|------------|---------------------|
| `ansible.cfg` | 2 (log_path, remote_tmp) | Override via `$ANSIBLE_LOG_PATH` env var |
| `playbooks/ansible.cfg` | 2 (same) | Same override |
| `image_build_setup/vars/main.yml` | 5 (input/output dirs, metadata, lock) | Already handled by mode detection |
| `cleanup_build_artifacts/vars/main.yml` | 4 (oim_shared, registry, output) | Use `hostvars['localhost']` facts (already does) |
| `deploy_minio/vars/main.yml` | 1 (oim_shared_path default) | Default fallback OK — overridden by facts |
| `deploy_registry/vars/main.yml` | 2 (oim_shared_path, registry_storage) | Default fallback OK |
| `build_os_images/vars/main.yml` | 1 | Default fallback OK |
| Other role vars | 8 | All use `hostvars['localhost']` with `/opt/omnia/` as default |

### 7.2 Strategy: Facts-First, Defaults-Second

Most role vars already follow the pattern:
```yaml
oim_shared_path: "{{ hostvars['localhost']['oim_shared_path'] | default('/opt/omnia') }}"
```

This means:
- **Omnia mode**: `image_build_setup` loads OIM metadata → sets `oim_shared_path` fact → roles use it
- **Standalone mode**: `image_build_setup` loads `config.yml` → sets `oim_shared_path` from `build_host.shared_path` → roles use it
- **Default `/opt/omnia/`**: Only used if neither mode sets the fact (defensive fallback)

**No changes needed in downstream roles** — the setup role is the single point of configuration.

---

## 8. Standalone Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    STANDALONE EXECUTION FLOW                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
  │  User    │      │  Setup   │      │  Build   │      │  Build   │      │  Output  │
  │ (shell)  │      │ (config) │      │  Host    │      │  Pipeline│      │          │
  └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
       │                 │                 │                 │                 │
       │  1. ansible-    │                 │                 │                 │
       │     playbook    │                 │                 │                 │
       │────────────────>│                 │                 │                 │
       │                 │ ┌───────────────────────────────┐ │                 │
       │                 │ │ 0. Validate tags              │ │                 │
       │                 │ │ 0.5 Detect standalone mode    │ │                 │
       │                 │ │ 1. Skip upgrade guard         │ │                 │
       │                 │ │ 2. Load config.yml            │ │                 │
       │                 │ │ 3. Set build_host facts       │ │                 │
       │                 │ │ 4. Create host group          │ │                 │
       │                 │ │ 5. Set guard facts            │ │                 │
       │                 │ └───────────────────────────────┘ │                 │
       │                 │                 │                 │                 │
       │                 │ Validate config │                 │                 │
       │                 │────────────────>│                 │                 │
       │                 │ Collect creds   │                 │                 │
       │                 │────────────────>│                 │                 │
       │                 │ Deploy MinIO    │                 │                 │
       │                 │────────────────>│                 │                 │
       │                 │ Deploy Registry │                 │                 │
       │                 │────────────────>│                 │                 │
       │                 │                 │                 │                 │
       │                 │  Build images (x86_64 + aarch64)  │                 │
       │                 │──────────────────────────────────>│                 │
       │                 │                 │                 │                 │
       │                 │   Write build_status.yml                            │
       │                 │────────────────────────────────────────────────────>│
  ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐
  │  User    │      │  Setup   │      │  Build   │      │  Build   │      │  Output  │
  └──────────┘      └──────────┘      └──────────┘      └──────────┘      └──────────┘
```

### Usage Commands

```bash
# ═══════════════════════════════════════════════════════════
# MODE A: Bare-metal (user has Ansible + Python installed)
# ═══════════════════════════════════════════════════════════

# Prerequisites check
python3 --version        # 3.11+
ansible --version        # 2.16+
podman --version         # 4.0+ (for MinIO/registry containers)

# Clone and configure
git clone https://github.com/dell/image-build-manager.git
cd image-build-manager
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
cp config.yml.sample config.yml
vim config.yml                   # Set your RPM repos, build host, OS version

# Create input directory
mkdir -p input/my_project/image_build_manager
cp samples/image_build_config.yml input/my_project/image_build_manager/

# Run
ansible-playbook image_build_manager.yml                    # Full flow
ansible-playbook image_build_manager.yml --tags prepare     # Deploy MinIO + Registry
ansible-playbook image_build_manager.yml --tags build       # Build images only
ansible-playbook image_build_manager.yml --tags validate    # Validate config only
ansible-playbook image_build_manager.yml --tags cleanup     # Cleanup

# ═══════════════════════════════════════════════════════════
# MODE B: Per-domain container (zero local setup)
# ═══════════════════════════════════════════════════════════

# Build image
podman build -t image_build_runner:1.0 -f containers/Containerfile .

# Start container (long-running — stays alive)
podman run -d --name image_build_mgr \
  --privileged \
  -p 2230:2230 \
  -v ./config.yml:/image_build_manager/config.yml:ro \
  -v ./repo_status.yml:/image_build_manager/repo_status.yml:ro \
  -v ./input:/image_build_manager/input:rw \
  -v ./output:/image_build_manager/output:rw \
  -v /run/podman/podman.sock:/run/podman/podman.sock \
  image_build_runner:1.0

# Run playbooks via podman exec (container stays alive between runs)
podman exec -it image_build_mgr ansible-playbook image_build_manager.yml --tags prepare
podman exec -it image_build_mgr ansible-playbook image_build_manager.yml --tags build
podman exec -it image_build_mgr ansible-playbook image_build_manager.yml --tags cleanup

# Stop when done
podman stop image_build_mgr && podman rm image_build_mgr

# ═══════════════════════════════════════════════════════════
# MODE C: Inside Omnia mono-repo (existing behavior — unchanged)
# ═══════════════════════════════════════════════════════════

cd src/image_build_manager
ansible-playbook image_build_manager.yml
```

---

## 9. Repository Structure (Standalone)

```
image-build-manager/                      # STANDALONE REPO
├── README.md                             # Getting started (3 modes documented)
├── config.yml.sample                     # Sample standalone config
├── requirements.txt                      # Python: ansible-core, jsonschema, PyYAML, jmespath
├── requirements.yml                      # Ansible collections: ansible.utils, community.general
├── Makefile                              # help, lint, test, build, clean targets
├── .gitignore                            # input/, output/, *.retry, *.log, .vault_pass
├── ansible.cfg                           # Domain config (fully local paths)
├── image_build_manager.yml               # Top-level entrypoint
├── callback_plugins/
│   └── omnia_default.py
├── library/
│   ├── modules/
│   │   ├── base_image_package_collector.py
│   │   ├── image_package_collector.py
│   │   ├── functional_group_parser.py
│   │   ├── generate_functional_groups.py
│   │   └── validate_image_build_config.py
│   └── module_utils/
│       ├── build_image/
│       │   ├── __init__.py
│       │   ├── common_functions.py
│       │   └── config.py
│       └── image_build_validation/
│           ├── __init__.py
│           ├── image_build_validation_flow.py
│           └── schema/
│               ├── image_build_config.json
│               ├── image_build_credentials.json
│               └── functional_groups_config.json
├── playbooks/
│   ├── ansible.cfg
│   ├── prepare_image_build_manager.yml
│   ├── build_image_x86_64.yml
│   ├── build_image_aarch64.yml
│   ├── cleanup_image_build_manager.yml
│   ├── get_build_credentials.yml
│   ├── validate_image_build_config.yml
│   ├── upgrade_image_build_manager.yml
│   └── rollback_image_build_manager.yml
├── roles/
│   ├── image_build_setup/                # Tri-mode bootstrap
│   ├── validate_image_build_input/       # L1 schema + L2 logic
│   ├── collect_build_credentials/        # Credential prompt + vault
│   ├── generate_functional_groups/       # CSV → functional_groups_config.yml
│   ├── validate_build_runtime/           # L3 runtime pre-checks
│   ├── deploy_minio/                     # MinIO S3 container
│   ├── deploy_registry/                  # OCI container registry
│   ├── fetch_build_packages/             # RPM package collection
│   ├── build_os_images/                  # Image build (x86_64 + aarch64)
│   ├── prepare_aarch64_node/             # ARM build host setup
│   └── cleanup_build_artifacts/          # Cleanup all artifacts
├── containers/
│   ├── Containerfile                     # Per-domain runner container (Mode B)
│   ├── build_images.sh                   # Container image builder script
│   └── image_builder/                    # Builder container (for OS image builds)
├── vars/
│   ├── image_vars.yml                    # S3 bucket constants
│   └── openchami_image_cmd.yml           # OpenCHAMI build commands
├── samples/
│   ├── config.yml                        # Sample standalone config
│   ├── image_build_config.yml            # Sample domain config
│   ├── build_status.yml                  # Sample output
│   └── repo_status.yml                   # Sample repo_manager output
├── input/                                # User input (gitignored)
├── output/                               # Build output (gitignored)
├── log/                                  # Logs (gitignored)
├── test/                                 # Unit + integration tests
│   ├── test_validate_config.py
│   └── test_functional_groups.py
├── IMAGE_BUILDER_DESIGN.md
├── INPUT_CONTRACT.md
├── OUTPUT_CONTRACT.md
└── STANDALONE_REPO_DESIGN.md             # This file
```

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Ansible version mismatch (bare-metal) | Module incompatibility | Pin in `requirements.txt`; test matrix in CI |
| Missing Python deps on bare-metal host | Import failures | `requirements.txt` + pre-flight check in setup role |
| RPM repo URL format differs from Pulp | Build failures | Validate URLs in `validate_build_runtime` role |
| No NFS shared path in standalone | Artifacts inaccessible | Support `build_host.hostname: localhost` for local-only builds |
| Credentials on non-containerized host | Vault key exposure | Same Ansible Vault encryption — identical security model |
| Container runtime differences | MinIO/registry deploy fails | Document: Podman 4+ or Docker 24+; test both |
| Standalone container needs podman-in-podman | Nested container execution | Mount host podman socket; document rootless vs rootful |
| Air-gap standalone | Can't pull container images | Document pre-pull + `podman save/load` workflow |

---

## 11. Prerequisites

### System Requirements

| Requirement | Minimum | Notes |
|------------|---------|-------|
| OS | RHEL 9.x / 10.x, Rocky 9.x, Fedora 40+ | |
| Python | 3.11+ | System or venv |
| Ansible | ansible-core 2.16+ | `pip install ansible-core` |
| Container runtime | Podman 4.0+ or Docker 24.0+ | For MinIO + registry containers |
| Disk space | 50 GB free | For OS image builds |
| RAM | 8 GB minimum | 16 GB recommended |
| Network | Access to RPM repos (direct or mirrored) | Air-gap: use local mirror URLs |

### Python Dependencies (`requirements.txt`)

```
ansible-core>=2.16,<2.18
jsonschema>=4.17
PyYAML>=6.0
jmespath>=1.0
```

### Ansible Collections (`requirements.yml`)

```yaml
collections:
  - name: ansible.utils
    version: ">=2.0"
  - name: community.general
    version: ">=7.0"
```

---

## 12. Naming Convention

| Component | Convention | Example |
|-----------|-----------|---------|
| **Playbook** | `verb_noun.yml` | `get_build_credentials.yml`, `build_image_x86_64.yml` |
| **Role** | `verb_noun` | `collect_build_credentials`, `deploy_minio` |
| **Data file** | `noun.yml` | `image_build_credentials.yml`, `build_status.yml` |
| **Task file** | `verb_noun.yml` | `prompt_credential_field.yml`, `cleanup_minio.yml` |
| **Container** | `image_build_runner` | Per-domain runner |
| **Config** | `config.yml` | Standalone all-in-one config |
