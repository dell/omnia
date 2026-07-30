# Image Build Manager — Bare-Metal Design

## Status: ACTIVE v1.1

This document describes how `image_build_manager` operates directly on a
RHEL bare-metal host using Ansible + Python, without any container or Omnia core dependency.
This is the only supported execution mode.

---

## 1. Execution Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Mode A — Bare-Metal                                  │
│                                                                             │
│   User runs ansible-playbook on the RHEL host directly.                     │
│   All tasks execute locally (connection: local) or via SSH (aarch64).       │
│   No container runtime required for the playbook itself.                    │
│   Podman is required for building OS images (OpenCHAMI) and deploying       │
│   MinIO + Registry via Quadlet.                                             │
│                                                                             │
│   ┌──────────┐     ┌──────────────────┐     ┌──────────────┐                │
│   │ config   │────>| image_build      │────>│ build_status │                │
│   │  .yml    │     │  _manager.yml    │     │  .yml        │                │
│   └──────────┘     └──────────────────┘     └──────────────┘                │
│                           │                                                 │
│                    ┌──────┴──────┐                                          │
│                    ▼             ▼                                          │
│              ┌──────────┐  ┌──────────┐                                     │
│              │ MinIO S3 │  │ Registry │                                     │
│              │ (Quadlet)│  │ (Quadlet)│                                     │
│              └──────────┘  └──────────┘                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Other Modes (NOT SUPPORTED)

| Mode | Description | Status |
|------|-------------|--------|
| **B — Container** | Run inside a long-running domain container | Commented out. `image_build_runner` container kept as-is but not used by playbooks. |
| **C — Omnia mono-repo** | Run inside `omnia_core` container via NFS | Commented out. All `/opt/omnia/` Omnia coupling removed. |

---

## 2. Directory Layout

### Shared Path Convention

Each Omnia domain gets its own directory under `/opt/omnia/`:

```
/opt/omnia/
├── image_build_manager/        ← this domain's persistent data
│   ├── workdir/                ← OpenCHAMI image build working directory
│   ├── log/                    ← build logs (base + compute images)
│   └── ...                     ← MinIO data, registry data
├── repo_manager/
│   └── output/
│       └── repo_status.yml     ← upstream input (produced by repo_manager)
└── pulp/
    └── settings/
        └── certs/
            ├── pulp_webserver.crt   ← Pulp TLS certificate (read as-is)
            └── pulp_webserver.key   ← Pulp TLS key
```

### Repository Layout

```
image-build-manager/
├── config.yml                   # Host and project settings (edit this)
├── config.yml.sample            # Sample config
├── requirements.txt             # Python dependencies
├── requirements.yml             # Ansible collections
├── Makefile                     # help, setup, lint, test, clean
├── docs/                        # All documentation
│   ├── design/                  # Architecture and design docs
│   ├── migration/               # Migration history
│   ├── contracts/               # Input/output contracts
│   ├── architecture.md          # Architecture overview
│   ├── package-mapping-guide.md # Package customization guide
│   └── troubleshooting.md       # Common issues
├── test/                        # Unit tests
└── src/
    ├── ansible.cfg              # Fully local paths
    ├── image_build_manager.yml  # Main playbook entry point
    ├── roles/                   # All Ansible roles
    ├── playbooks/               # Sub-playbooks
    ├── library/                 # Custom Ansible modules
    ├── callback_plugins/        # Output callback
    ├── vars/                    # Shared variables
    ├── input/                   # User input files
    │   └── project_default/
    │       ├── image_build_config.yml        # Build config
    │       └── repo_manager_output/          # Local dev sample files
    │           ├── repo_status.yml           # Sample repo URLs
    │           ├── functional_group_packages.yml
    │           └── certs/                    # Sample certs
    ├── output/                  # Build output (auto-created)
    ├── samples/                 # Reference samples
    └── containers/              # Container build files (kept, not used by Mode A)
```

---

## 3. Configuration

### `config.yml`

```yaml
project_name: "project_default"

host:
  hostname: "myhost"
  shared_path: "/opt/omnia/image_build_manager"
  domain_name: "local"
  admin_nic_ip: "10.20.0.1"
```

| Field | Description |
|-------|-------------|
| `project_name` | Maps to `input/<name>/` and `output/<name>/` directories |
| `host.hostname` | Short hostname (NOT FQDN) — domain_name appended automatically |
| `host.shared_path` | Persistent storage for MinIO data, registry data, workdir |
| `host.domain_name` | Domain suffix for registry naming |
| `host.admin_nic_ip` | Admin NIC IP — used for Pulp, S3, and registry endpoints |

### `repo_status.yml` (from repo_manager)

In production, repo_manager writes to `/opt/omnia/repo_manager/output/repo_status.yml`.
The `image_build_config.yml` references this path:

```yaml
repo_manager_output_path: "/opt/omnia/repo_manager/output/project_default/repo_status.yml"
```

Certificate paths in `repo_status.yml` are **absolute** and read directly:

```yaml
repo_manager:
  port: 2225
  certificates:
    server_crt: /opt/omnia/pulp/settings/certs/pulp_webserver.crt
    server_key: /opt/omnia/pulp/settings/certs/pulp_webserver.key
    certs_dir: /opt/omnia/pulp/settings/certs
```

The playbook validates the cert file exists at the specified path — no staging or copying needed.

---

## 4. Ansible Installation

### If Ansible is already installed

Check the installed version:

```bash
ansible --version
```

- **Required**: `ansible-core >= 2.20`
- If your system has an older version, you can install the required version in a virtual environment without affecting the system installation.

### Fresh install (recommended)

```bash
# Create a virtual environment (keeps your system Python clean)
python3 -m venv ~/.venvs/image-build
source ~/.venvs/image-build/bin/activate

# Install dependencies
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

### Install alongside existing Ansible

If you already have Ansible installed system-wide and don't want to disturb it:

```bash
# Option 1: Use a virtual environment (RECOMMENDED)
python3 -m venv ~/.venvs/image-build
source ~/.venvs/image-build/bin/activate
pip install -r requirements.txt

# Option 2: Use pipx for isolated installation
pipx install ansible-core
pipx inject ansible-core -r requirements.txt

# Option 3: User-level install (no sudo needed)
pip install --user -r requirements.txt
```

### Verify installation

```bash
ansible --version          # Should show ansible-core 2.20+
ansible-galaxy collection list | grep containers.podman
python3 -c "import yaml; print('PyYAML OK')"
```

---

## 5. Quick Start (Mode A)

```bash
# 1. Clone and configure
git clone <repo-url> image-build-manager
cd image-build-manager
cp config.yml.sample config.yml
# Edit config.yml — set admin_nic_ip, shared_path, domain_name

# 2. Install dependencies
python3 -m venv ~/.venvs/image-build
source ~/.venvs/image-build/bin/activate
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml

# 3. Ensure repo_manager output is available
# Production: repo_status.yml is at /opt/omnia/repo_manager/output/repo_status.yml
# Development: edit samples/repo_manager_output/repo_status.yml
#              and update repo_manager_output_path in image_build_config.yml

# 4. Configure functional groups
vi input/project_default/image_build_config.yml

# 5. Run
cd src
ansible-playbook image_build_manager.yml --tags validate   # Validate only
ansible-playbook image_build_manager.yml --tags prepare    # Deploy MinIO + Registry
ansible-playbook image_build_manager.yml --tags build      # Build OS images
ansible-playbook image_build_manager.yml --tags cleanup    # Clean up everything
```

---

## 6. Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    IMAGE BUILD MANAGER - DATA FLOW (Mode A)                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
  │          │      │          │      │          │      │          │      │          │
  │  User    │      │  Setup   │      │ Validate │      │ Prepare  │      │  Build   │
  │          │      │          │      │          │      │          │      │          │
  └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
       │                 │                 │                 │                 │
       │  config.yml     │                 │                 │                 │
       │────────────────>│                 │                 │                 │
       │                 │                 │                 │                 │
       │                 │ image_build     │                 │                 │
       │                 │  _config.yml    │                 │                 │
       │                 │────────────────>│                 │                 │
       │                 │                 │                 │                 │
       │                 │ repo_status.yml │                 │                 │
       │                 │────────────────>│                 │                 │
       │                 │                 │                 │                 │
       │                 │                 │ Credentials     │                 │
       │                 │                 │────────────────>│                 │
       │                 │                 │                 │                 │
       │                 │                 │                 │ MinIO + Registry│
       │                 │                 │                 │────────────────>│
       │                 │                 │                 │                 │
       │                 │                 │                 │ ┌─────────────────────────────┐
       │                 │                 │                 │ │ OpenCHAMI image-build:      │
       │                 │                 │                 │ │ - Build base image          │
       │                 │                 │                 │ │ - Build compute images      │
       │                 │                 │                 │ │ - Upload to S3              │
       │                 │                 │                 │ └─────────────────────────────┘
       │                 │                 │                 │                 │
       │  build_status   │                 │                 │                 │
       │<──────────────────────────────────────────────────────────────────────│
       │                 │                 │                 │                 │
  ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐      ┌────┴─────┐
  │          │      │          │      │          │      │          │      │          │
  │  User    │      │  Setup   │      │ Validate │      │ Prepare  │      │  Build   │
  │          │      │          │      │          │      │          │      │          │
  └──────────┘      └──────────┘      └──────────┘      └──────────┘      └──────────┘

Figure: Image Build Manager data flow in Mode A (bare-metal)
```

---

## 7. Dependency Inventory (Mode A)

| # | Dependency | Resolution |
|---|-----------|------------|
| 1 | OIM metadata | Replaced by `config.yml → host` section |
| 2 | Project config | Replaced by `config.yml → project_name` |
| 3 | Upgrade lock | Commented out (Omnia mode only) |
| 4 | `repo_status.yml` | Read from `/opt/omnia/repo_manager/output/repo_status.yml` |
| 5 | `software_config.json` | Replaced by `functional_group_packages.yml` |
| 6 | Core container | Not required — runs on bare-metal |
| 7 | OIM host group | Created as localhost with `connection: local` |
| 8 | `omnia.target` | Skipped in Mode A |
| 9 | `/opt/omnia/` defaults | Config-driven via `host.shared_path` |
| 10 | Credential utility | Replaced by `collect_build_credentials` role |
| 11 | `common/callback_plugins/` | Local copy at `callback_plugins/omnia_default.py` |
| 12 | `common/library/modules/` | All modules local at `library/modules/` |
| 13 | `common/library/module_utils/` | Fully local at `library/module_utils/` |
| 14 | `common/vars/` | Inlined into `image_build_setup/vars/main.yml` |
| 15 | `playbooks/utils/` | Absorbed into domain roles |
| 16 | Pulp certificates | Read directly from absolute path in `repo_status.yml` |

---

## 8. Upgrade & Rollback (Image Build Manager)

### Tags

```bash
ansible-playbook image_build_manager.yml --tags upgrade     # Upgrade to new version
ansible-playbook image_build_manager.yml --tags rollback    # Rollback to previous version
```

### Version File

After successful deployment, the playbook writes:

```yaml
# <state_path>/.domain_version.yml
---
domain: "image_build_manager"
version: "1.0.0"
installed_at: "2026-07-27T10:30:00Z"
ansible_version: "2.20.0"
python_version: "3.12.8"
config_hash: "sha256:abc123..."
previous_version: null
```

### Upgrade Flow (image_build_manager)

```
  1. Pre-upgrade validation
     ├── Read .domain_version.yml → current version
     ├── Verify target version is newer
     ├── Check disk space (snapshot needs ~equal space to state_path)
     └── Verify MinIO + Registry services are healthy

  2. Snapshot current state
     ├── Create <state_path>/.upgrade_snapshot/
     ├── Copy MinIO data, registry data, Quadlet configs
     └── Save current .domain_version.yml

  3. Stop services
     ├── systemctl stop minio
     └── systemctl stop registry

  4. Apply migrations
     ├── Update Quadlet service files (if container image changed)
     ├── Migrate config format (if schema changed)
     └── Move/rename data directories (if path convention changed)

  5. Restart services
     ├── systemctl daemon-reload
     ├── systemctl start minio
     └── systemctl start registry

  6. Post-upgrade verification
     ├── MinIO health check (s3cmd ls)
     ├── Registry health check (podman pull test)
     └── Validate S3 buckets exist

  7. Update version file
     └── Write .domain_version.yml with new version
```

### Rollback Flow (image_build_manager)

```
  1. Validate snapshot
     └── Check <state_path>/.upgrade_snapshot/ exists

  2. Stop services
     ├── systemctl stop minio
     └── systemctl stop registry

  3. Restore from snapshot
     ├── Remove current Quadlet files
     ├── Restore Quadlet files from snapshot
     ├── Restore MinIO data from snapshot
     └── Restore registry data from snapshot

  4. Restart services
     ├── systemctl daemon-reload
     ├── systemctl start minio
     └── systemctl start registry

  5. Verify rollback
     ├── MinIO health check
     ├── Registry health check
     └── Restore .domain_version.yml from snapshot

  6. Cleanup
     └── Remove .upgrade_snapshot/ (optional — keep for safety)
```

### Playbook Structure

```
src/
├── playbooks/
│   ├── upgrade_image_build_manager.yml    # Upgrade entry point
│   └── rollback_image_build_manager.yml   # Rollback entry point
└── roles/
    └── image_build_upgrade/               # Upgrade/rollback role
        ├── tasks/
        │   ├── main.yml                   # (empty — not called directly)
        │   ├── pre_upgrade.yml            # Version check, disk space, health
        │   ├── snapshot.yml               # Create state snapshot
        │   ├── migrate.yml                # Apply data/config migrations
        │   ├── verify.yml                 # Post-upgrade/rollback verification
        │   ├── validate_snapshot.yml       # Check snapshot exists
        │   └── restore.yml                # Restore from snapshot
        └── vars/
            └── main.yml                   # Error messages, version constants
```

### Invalid Tag Combinations

Upgrade and rollback are mutually exclusive with all other operational tags:

```yaml
# In image_build_setup/vars/main.yml
invalid_tag_combinations:
  - [prepare, upgrade]
  - [build, upgrade]
  - [cleanup, upgrade]
  - [prepare, rollback]
  - [build, rollback]
  - [cleanup, rollback]
  - [upgrade, rollback]
```

---

## 9. Container Files (Kept, Not Required)

The `src/containers/` directory contains:

| Container | Purpose | Status |
|-----------|---------|--------|
| `image_builder/` | OpenCHAMI image-build container (ochami) | **USED** — pulled from Docker Hub for image builds |
| `image_build_runner/` | Domain runner container (sshd, long-running) | **KEPT** — not used by Mode A playbooks |
| `build_images.sh` | Build script for containers | **KEPT** — used for image_builder builds |

The `image_build_runner` container and its Mode B integration are kept in the codebase
for future use but are not invoked by any Mode A playbook flow.
