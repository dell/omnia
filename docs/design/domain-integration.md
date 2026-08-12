# Omnia Domain Integration — omnia.sh & omnia-cli

**Version**: 2.0
**Audience**: Domain developers, platform integrators
**Purpose**: Document how each Omnia domain integrates with `omnia.sh` (setup/execution script) and `omnia-cli` (status and diagnostics CLI).

---

## 1. Overview

Omnia domains run as independent Ansible playbooks on a RHEL host. Two system-level scripts tie them together:

| Script | Location | Purpose |
|--------|----------|---------|
| **`omnia.sh`** | `src/main/omnia.sh` | Bootstrap, venv setup, environment validation, domain execution |
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
   - `OMNIA_VERSION`
   - `OMNIA_PROJECT_NAME`

2. **Validates the environment** — `validate_env()` cross-checks env vars against the actual system (see §2.6)

3. **Creates Python venv** — `python3 -m venv <OMNIA_DATA_PATH>/venv`

4. **Installs dependencies** — `pip install` from each domain's `requirements.txt`

5. **Stages domain inputs** — calls each domain's `domain-init.sh` to copy flat input template files from the domain repo's `input/` to `<OMNIA_DATA_PATH>/<domain>/input/<project>/`

6. **Runs domain playbooks** — executes `ansible-playbook` for each domain in sequence

### 2.2 Domain Registration

Each domain registers itself with `omnia.sh` via a domain manifest block in the script. The manifest defines:

```bash
# Example domain block in omnia.sh
DOMAIN_NAME="<domain_name>"
DOMAIN_PATH="src/<domain_name>"
DOMAIN_PLAYBOOK="playbooks/<domain_name>.yml"
DOMAIN_DESCRIPTION="<description of what this domain does>"
DOMAIN_TAGS="precheck,validate,prepare,build,cleanup,upgrade,rollback"
```

### 2.3 Domain Execution Flow

```
omnia.sh --setup-venv
  │
  ├── 1. Source /etc/omnia/omnia.env
  ├── 2. Validate environment (validate_env)
  ├── 3. Create/activate Python venv
  ├── 4. pip install -r requirements.txt (per domain)
  ├── 5. ansible-galaxy collection install -r requirements.yml (per domain)
  └── 6. Call domain-init.sh (per domain)

omnia.sh --run <domain> [--tags <tags>]   # or: omnia.sh -r <domain> --tags <tags>
  │
  ├── 1. Source /etc/omnia/omnia.env
  ├── 2. Validate environment (validate_env)
  ├── 3. Activate venv
  ├── 4. ansible-playbook <domain>/playbooks/<domain>.yml --tags <tags>
  └── 5. Write domain status to <OMNIA_DATA_PATH>/<domain>/output/<project>/<domain>_status.yml

omnia.sh --validate <domain>              # shortcut for --run <domain> --tags validate
omnia.sh --init                           # run all domain-init.sh scripts
```

### 2.4 Domain `domain-init.sh` Contract

Every domain MUST provide a `domain-init.sh` script at the domain root. This script:

- **Input**: Receives `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` as environment variables
- **Action**: Copies flat input template files from `<domain>/input/` to `<OMNIA_DATA_PATH>/<domain>/input/<project>/`
- **Idempotent**: Safe to run multiple times
- **No project subdirectory in source**: Input files live flat in `input/`; the project subdirectory is created only at the runtime destination

```bash
#!/bin/bash
# domain-init.sh — Stage domain input files to OMNIA_DATA_PATH
DEST="${OMNIA_DATA_PATH}/${DOMAIN_NAME}/input/${OMNIA_PROJECT_NAME}"
mkdir -p "$DEST"
cp -a input/. "$DEST"/
```

### 2.5 Environment Variables Available to Domains

All domains can access these via `lookup('env', ...)` in Ansible:

| Variable | Source | Example |
|----------|--------|---------|
| `SYSTEM_HOSTNAME` | `/etc/omnia/omnia.env` | `oim` |
| `SYSTEM_DOMAIN_NAME` | `/etc/omnia/omnia.env` | `omnia.cluster` |
| `SYSTEM_ADMIN_NIC_IPV4` | `/etc/omnia/omnia.env` | `172.16.107.254` |
| `OMNIA_DATA_PATH` | `/etc/omnia/omnia.env` | `/opt/omnia` |
| `OMNIA_VERSION` | `/etc/omnia/omnia.env` | `2.3` |
| `OMNIA_PROJECT_NAME` | `/etc/omnia/omnia.env` | `project_default` |

### 2.6 Environment Validation (`validate_env`)

`omnia.sh` validates environment variables against the actual system before any domain runs. This prevents misconfigurations from propagating:

| Check | Command | Severity | Description |
|-------|---------|----------|-------------|
| Hostname | `hostname -s` | Error | Must match `SYSTEM_HOSTNAME` |
| Domain | `hostname -d` | Warning | Must match `SYSTEM_DOMAIN_NAME` |
| Admin IP | `hostname -I` | Error | `SYSTEM_ADMIN_NIC_IPV4` must appear in the output |

If any error-level check fails, `omnia.sh` exits immediately with an actionable message.

The same validation is available as an Ansible module (`validate_system_environment`) for use within playbooks — see §5.

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
domain: "<domain_name>"
project_name: "project_default"
overall_status: "success"          # success | failed | partial | skipped
execution_time: "2026-07-27T10:30:00Z"
duration_seconds: 1234
tags_executed:
  - prepare
  - build
details:
  <component_1>: "success"
  <component_2>: "success"
  <component_3>: "skipped"
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
# Run a domain standalone (provide upstream contract manually)
mkdir -p /opt/omnia/<upstream_domain>/output/project_default/
cp <upstream_contract>.yml /opt/omnia/<upstream_domain>/output/project_default/
ansible-playbook <domain>/playbooks/<domain>.yml --tags <tag>
```

---

## 5. Environment Validation Architecture

Three layers validate system environment, each using the same checks but at different stages:

```
┌─────────────────────────────────────────────────────────────┐
│                 validate_system_environment.py              │
│                 (Ansible module — single source of truth)   │
│                                                             │
│  Checks:                                                    │
│    - Env vars SET (SYSTEM_HOSTNAME, SYSTEM_ADMIN_NIC_IPV4,  │
│      SYSTEM_DOMAIN_NAME, OMNIA_DATA_PATH)                   │
│    - hostname -s matches SYSTEM_HOSTNAME                    │
│    - hostname -d matches SYSTEM_DOMAIN_NAME                 │
│    - SYSTEM_ADMIN_NIC_IPV4 assigned to a local NIC          │
│    - OMNIA_DATA_PATH exists or parent is writable           │
│                                                             │
│  Returns: structured per-check results with pass/fail       │
└──────┬──────────────────┬───────────────────────────────────┘
       │                  │
┌──────┴───────┐  ┌───────┴──────────┐  ┌──────────────────┐
│ omnia.sh     │  │ Domain playbook  │  │ FVT tests        │
│ validate_env │  │ setup role       │  │ (test automation) │
│ (bash)       │  │ + precheck role  │  │                  │
│              │  │ (Ansible)        │  │                  │
└──────────────┘  └──────────────────┘  └──────────────────┘
```

### 5.1 Usage in Setup Role (env vars only)

The domain setup role calls the module to validate env vars are SET but does NOT cross-validate against the system (that is the precheck role's job):

```yaml
- name: Validate system environment
  validate_system_environment:
    required_vars:
      - SYSTEM_ADMIN_NIC_IPV4
      - SYSTEM_HOSTNAME
      - SYSTEM_DOMAIN_NAME
      - OMNIA_DATA_PATH
    validate_hostname: false
    validate_domain: false
    validate_ip: false
    validate_paths: false
  register: _env_validation
```

### 5.2 Usage in Precheck Role (full cross-validation)

The precheck role calls the module with all cross-validation enabled:

```yaml
- name: Cross-validate system environment
  validate_system_environment:
    required_vars: []
    validate_hostname: true
    validate_domain: true
    validate_ip: true
    validate_paths: true
  register: _sys_validation
```

### 5.3 Module Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `required_vars` | list | `[SYSTEM_ADMIN_NIC_IPV4, SYSTEM_HOSTNAME, SYSTEM_DOMAIN_NAME, OMNIA_DATA_PATH]` | Env vars that must be set (non-empty) |
| `validate_hostname` | bool | `true` | Cross-check SYSTEM_HOSTNAME against `hostname -s` |
| `validate_domain` | bool | `true` | Cross-check SYSTEM_DOMAIN_NAME against `hostname -d` |
| `validate_ip` | bool | `true` | Check SYSTEM_ADMIN_NIC_IPV4 is assigned to a local NIC |
| `validate_paths` | bool | `true` | Verify OMNIA_DATA_PATH exists or parent is writable |

---

## 6. Checklist for New Domain Integration

When creating a new Omnia domain, ensure:

- [ ] `domain-init.sh` exists at domain root
- [ ] Domain writes `<domain>_status.yml` to `<OMNIA_DATA_PATH>/<domain>/output/<project>/`
- [ ] Domain reads system env vars from `/etc/omnia/omnia.env` (via `lookup('env', ...)`)
- [ ] Setup role calls `validate_system_environment` module for env var validation
- [ ] Precheck role calls `validate_system_environment` module with full cross-validation
- [ ] Domain is registered in `omnia.sh` domain list
- [ ] Domain description added to `omnia-cli` `DOMAIN_DESCRIPTIONS` map
- [ ] Domain input file added to `omnia-cli` `DOMAIN_INPUT_FILES` map
- [ ] Domain can run standalone with manually-provided upstream contracts
- [ ] Domain status file follows the standard YAML format documented above
- [ ] Test automation updated for the domain (see `general.md` §6)
