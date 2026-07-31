# Omnia Domain Integration — omnia.sh & omnia-cli

**Version**: 1.0
**Audience**: Domain developers, platform integrators
**Purpose**: Document how each Omnia domain integrates with `omnia.sh` (setup/execution script) and `omnia-cli` (status and diagnostics CLI).

---

## 1. Overview

Omnia domains run as independent Ansible playbooks on a RHEL host. Two system-level scripts tie them together:

| Script | Location | Purpose |
|--------|----------|---------|
| **`omnia.sh`** | `src/main/omnia.sh` | Bootstrap, venv setup, domain execution, orchestration |
| **`omnia-cli`** | `src/main/omnia-cli` | Post-run status query, diagnostics, health checks |

Both scripts are installed to `/usr/local/bin/` (or sourced from the repo) and operate on the shared state directory `<OMNIA_DATA_PATH>` (default `/opt/omnia`).

---

## 2. `omnia.sh` Integration

### 2.1 What `omnia.sh` Does

1. **Sets up system environment** — installs `/etc/omnia/omnia.env` with system-wide variables:
   - `SYSTEM_HOSTNAME`
   - `SYSTEM_DOMAIN_NAME`
   - `SYSTEM_ADMIN_NIC_IPV4`
   - `OMNIA_DATA_PATH` (default `/opt/omnia`)

2. **Creates Python venv** — `python3 -m venv <OMNIA_DATA_PATH>/venv`

3. **Installs dependencies** — `pip install` from each domain's `requirements.txt`

4. **Stages domain inputs** — calls each domain's `domain-init.sh` to copy input files from the domain repo to `<OMNIA_DATA_PATH>/<domain>/input/<project>/`

5. **Runs domain playbooks** — executes `ansible-playbook` for each domain in sequence

### 2.2 Domain Registration

Each domain registers itself with `omnia.sh` via a domain manifest block in the script. The manifest defines:

```bash
# Example domain block in omnia.sh
DOMAIN_NAME="image_build_manager"
DOMAIN_PATH="src/image_build_manager"
DOMAIN_PLAYBOOK="playbooks/image_build_manager.yml"
DOMAIN_DESCRIPTION="Build OS images for compute nodes"
DOMAIN_TAGS="prepare,build,cleanup"
```

### 2.3 Domain Execution Flow

```
omnia.sh --setup-venv
  │
  ├── 1. Source /etc/omnia/omnia.env
  ├── 2. Create/activate Python venv
  ├── 3. pip install -r requirements.txt (per domain)
  ├── 4. ansible-galaxy collection install -r requirements.yml (per domain)
  └── 5. Call domain-init.sh (per domain)

omnia.sh --run <domain> [--tags <tags>]
  │
  ├── 1. Source /etc/omnia/omnia.env
  ├── 2. Activate venv
  ├── 3. ansible-playbook <domain>/playbooks/<domain>.yml --tags <tags>
  └── 4. Write domain status to <OMNIA_DATA_PATH>/<domain>/output/<project>/<domain>_status.yml
```

### 2.4 Domain `domain-init.sh` Contract

Every domain MUST provide a `domain-init.sh` script at the domain root. This script:

- **Input**: Receives `OMNIA_DATA_PATH` and `PROJECT_NAME` as environment variables
- **Action**: Copies input files from `<domain>/input/<project>/` to `<OMNIA_DATA_PATH>/<domain>/input/<project>/`
- **Idempotent**: Safe to run multiple times

```bash
#!/bin/bash
# domain-init.sh — Stage domain input files to OMNIA_DATA_PATH
DEST="${OMNIA_DATA_PATH}/${DOMAIN_NAME}/input/${PROJECT_NAME}"
mkdir -p "$DEST"
cp -r input/"${PROJECT_NAME}"/* "$DEST"/
```

### 2.5 Environment Variables Available to Domains

All domains can access these via `lookup('env', ...)` in Ansible:

| Variable | Source | Example |
|----------|--------|---------|
| `SYSTEM_HOSTNAME` | `/etc/omnia/omnia.env` | `oim` |
| `SYSTEM_DOMAIN_NAME` | `/etc/omnia/omnia.env` | `omnia.cluster` |
| `SYSTEM_ADMIN_NIC_IPV4` | `/etc/omnia/omnia.env` | `172.16.107.254` |
| `OMNIA_DATA_PATH` | `/etc/omnia/omnia.env` | `/opt/omnia` |

---

## 3. `omnia-cli` Integration

### 3.1 What `omnia-cli` Does

`omnia-cli` provides post-run diagnostics and domain status queries. It reads domain status files from `<OMNIA_DATA_PATH>/<domain>/output/<project>/`.

### 3.2 Supported Commands

| Command | Description |
|---------|-------------|
| `omnia-cli status` | Show overall status of all domains |
| `omnia-cli status <domain>` | Show detailed status of a specific domain |
| `omnia-cli check` | Validate input directories, config files, output directories, and status files |
| `omnia-cli logs <domain>` | Show last N lines of domain log |
| `omnia-cli describe <domain>` | Show domain description and configuration |

### 3.3 Domain Status File Contract

Every domain MUST write a status file after execution:

**Location**: `<OMNIA_DATA_PATH>/<domain>/output/<project>/<domain>_status.yml`

**Format**:

```yaml
---
domain: "image_build_manager"
project_name: "project_default"
overall_status: "success"          # success | failed | partial | skipped
execution_time: "2025-07-27T10:30:00Z"
duration_seconds: 1234
tags_executed:
  - prepare
  - build
details:
  x86_64_base_image: "success"
  x86_64_compute_images: "success"
  aarch64_base_image: "skipped"
errors: []
```

### 3.4 Domain Description Map

`omnia-cli` maintains a description map for each domain:

```bash
declare -A DOMAIN_DESCRIPTIONS=(
  ["image_build_manager"]="Build and publish OS images for compute nodes (x86_64/aarch64)"
  ["repo_manager"]="Configure package repositories and sync packages from upstream"
  ["discovery"]="Discover hardware via OME and generate node inventory"
  ["orchestrator"]="Orchestrate node provisioning and configuration"
  ["telemetry"]="Deploy telemetry collection and monitoring infrastructure"
)
```

### 3.5 Domain Input Files Map (for `check` command)

`omnia-cli check` validates that required input files exist for each domain:

```bash
declare -A DOMAIN_INPUT_FILES=(
  ["image_build_manager"]="image_build_config.yml"
  ["repo_manager"]="repo_config.yml"
  ["discovery"]="discovery_config.yml"
  ["orchestrator"]="orchestrator_config.yml"
  ["telemetry"]="telemetry_config.yml"
)
```

### 3.6 Adding a New Domain to `omnia-cli`

When creating a new domain, update `omnia-cli` with:

1. **Add domain description** to `DOMAIN_DESCRIPTIONS` map
2. **Add domain input file** to `DOMAIN_INPUT_FILES` map
3. **Write status file** from the domain playbook's final task

---

## 4. Domain Execution Order

Domains execute in a specific order because of inter-domain data contracts:

```
┌──────────────┐     repo_status.yml     ┌─────────────────────┐
│ repo_manager │ ──────────────────────▶ │ image_build_manager │
└──────────────┘                         └──────────┬──────────┘
                                                    │
                                          build_status.yml
                                                    │
                                                    ▼
                                         ┌──────────────────┐
                                         │   orchestrator   │
                                         └──────────────────┘
```

Each domain reads its upstream contract from a well-known path under `<OMNIA_DATA_PATH>/`:

| Consumer | Upstream Contract | Path |
|----------|-------------------|------|
| `image_build_manager` | `repo_status.yml` | `<OMNIA_DATA_PATH>/repo_manager/output/<project>/repo_status.yml` |
| `orchestrator` | `build_status.yml` | `<OMNIA_DATA_PATH>/image_build_manager/output/<project>/build_status.yml` |

### 4.1 Running Domains Independently

Each domain can run standalone by providing its upstream contract files:

```bash
# Run image_build_manager standalone (provide repo_status.yml manually)
cp repo_status.yml /opt/omnia/repo_manager/output/project_default/
ansible-playbook image_build_manager/playbooks/image_build_manager.yml --tags build
```

---

## 5. `image_build_manager` Specific Integration

### 5.1 Build Type Selection

The `image_build_manager` supports two build backends via `image_build_type` in `image_build_config.yml`:

| Build Type | Binary | Container Image | Config Format |
|------------|--------|-----------------|---------------|
| `image-builder` | Python `image-build` | `quay.io/openchami/image-builder:latest` | `options:` + `repos:` + `cmds:` |
| `image-thrillhouse` | Go `image-thrillhouse` | `ghcr.io/openchami/image-thrillhouse:latest` | `meta:` + `layer:` + `publish:` |

### 5.2 Status File Fields

The `image_build_manager` status file includes build-specific fields:

```yaml
---
domain: "image_build_manager"
image_build_type: "image-builder"     # or "image-thrillhouse"
architectures_built:
  - x86_64
  - aarch64
base_images:
  x86_64: "rhel-x86_64_base:10.0"
  aarch64: "rhel-aarch64_base:10.0"
compute_images:
  - name: "rhel-compute_default-omnia:10.0"
    arch: x86_64
    status: success
registry_host: "172.16.107.254"
s3_endpoint: "http://172.16.107.254:9000"
```

### 5.3 `omnia-cli` Output for Image Build Manager

```
$ omnia-cli status image_build_manager

  Domain: image_build_manager
  Description: Build and publish OS images for compute nodes (x86_64/aarch64)
  Status: SUCCESS
  Build Type: image-builder
  Duration: 20m 34s
  Last Run: 2025-07-27 10:30:00

  Images Built:
    ✓ rhel-x86_64_base:10.0
    ✓ rhel-compute_default-omnia:10.0
    ✓ rhel-aarch64_base:10.0

  Infrastructure:
    Registry: 172.16.107.254:5000 (running)
    MinIO S3: http://172.16.107.254:9000 (running)
```

---

## 6. Checklist for New Domain Integration

When creating a new Omnia domain, ensure:

- [ ] `domain-init.sh` exists at domain root
- [ ] Domain writes `<domain>_status.yml` to `<OMNIA_DATA_PATH>/<domain>/output/<project>/`
- [ ] Domain reads system env vars from `/etc/omnia/omnia.env` (via `lookup('env', ...)`)
- [ ] Domain is registered in `omnia.sh` domain list
- [ ] Domain description added to `omnia-cli` `DOMAIN_DESCRIPTIONS` map
- [ ] Domain input file added to `omnia-cli` `DOMAIN_INPUT_FILES` map
- [ ] Domain can run standalone with manually-provided upstream contracts
- [ ] Domain status file follows the standard YAML format documented above
