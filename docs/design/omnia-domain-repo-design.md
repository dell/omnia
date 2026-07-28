# Omnia Domain Repository — Generic Design & Coding Standard

**Version**: 1.0
**Audience**: All Omnia domain developers (image_build_manager, repo_manager, provision, telemetry, etc.)
**Purpose**: Standard repository structure, coding rules, and conventions that every Omnia domain repository MUST follow.

---

## 1. Overview

Each Omnia domain (e.g., `image_build_manager`, `repo_manager`, `provision`) is an **independent Ansible-based repository** that:

- Runs standalone on a RHEL host via `ansible-playbook`
- Has its own `config.yml`, input files, and output artifacts
- Communicates with other domains only through well-defined file contracts (YAML)
- Does NOT require `omnia_core` container or the Omnia mono-repo to execute

### Execution Mode

All domains run directly on the RHEL host via `ansible-playbook` (bare-metal).
No container runtime is required for the playbook itself (Podman is used only for image builds).

**Rationale:**
- **No path translation** — all file paths are host-native, no bind-mount gymnastics
- **No privilege escalation** — no need for `--privileged` containers or UID mapping
- **Simpler debugging** — logs, processes, and filesystem are directly accessible
- **Better host integration** — systemd services (MinIO, Registry via Quadlet) are managed natively
- **Air-gap friendly** — no container runtime needed for the playbook itself

### Validated Environment

| Component | Minimum Version | Validated Version |
|-----------|----------------|-------------------|
| **Python** | 3.12+ | 3.12.8 |
| **Ansible Core** | 2.20+ | 2.20.0 |
| **RHEL** | 10.0+ | 10.0 |
| **Podman** | 5.0+ | 5.3.1 (for container builds only) |

> **NOTE**: All code MUST be compatible with Python 3.12+ and Ansible 2.20+. Do NOT use deprecated Ansible modules or Python 2 patterns.

---

## 2. Repository Structure

Every domain repository MUST follow this layout:

```
<domain-name>/
├── config.yml.sample              # Sample config — users copy to config.yml
├── requirements.txt               # Python deps: ansible-core>=2.20, jmespath, etc.
├── requirements.yml               # Ansible Galaxy collections
├── README.md                      # Quick start, prerequisites, usage
├── .gitignore
├── .github/
│   └── workflows/ci.yml          # CI pipeline (lint, test)
├── docs/                          # Domain-specific documentation
│   ├── design/                    # Architecture and design documents
│   ├── code-style/                # Code style guides (ansible, python, jinja2, etc.)
│   └── contracts/                 # Input/output contracts
├── test/                          # Unit + integration tests
└── src/                           # All Ansible code
    ├── ansible.cfg                # Ansible configuration
    ├── <domain_name>.yml          # Entry point playbook — ONLY role/playbook imports
    ├── roles/                     # One role per responsibility
    │   └── <role_name>/
    │       ├── tasks/main.yml     # Entry point
    │       ├── vars/main.yml      # ALL error messages, constants
    │       ├── defaults/main.yml  # User-overridable defaults (rare)
    │       ├── templates/         # Jinja2 templates
    │       ├── files/             # Static files
    │       └── handlers/main.yml  # Handlers
    ├── playbooks/                 # Sub-playbooks per flow
    ├── library/                   # Custom Ansible modules (Python)
    ├── module_utils/              # Shared Python module utilities
    ├── callback_plugins/          # Output callback plugins
    ├── vars/                      # Shared cross-role variables
    └── input/                     # Project input files
        └── <project_name>/        # Per-project input directory
```

### Key Rules

- **`src/<domain>.yml`** is the ONLY entry point. It MUST contain only `roles:` and `import_playbook:` — no inline `tasks:`.
- **No output or log directories under `src/`** — all runtime output goes to `<shared_path>/`.
- Every file MUST start with the Dell Apache 2.0 copyright header.

---

## 3. Configuration Design

### `config.yml` (Repo Root)

Every domain has a `config.yml` at the repo root with this structure:

```yaml
project_name: "project_default"

host:
  hostname: "oim"                  # Short hostname (NOT FQDN), alphanumeric + hyphens
  shared_path: "/opt/omnia/<domain_name>"  # Absolute path — persistent storage
  domain_name: "omnia.cluster"     # Domain suffix
  admin_nic_ip: "172.16.107.254"  # Admin NIC IPv4 address
```

### Validation Rules

| Field | Rule |
|-------|------|
| `project_name` | Non-empty string |
| `host.hostname` | Regex: `^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$` |
| `host.admin_nic_ip` | Valid IPv4 (use `ansible.utils.ipv4` filter) |
| `host.shared_path` | Absolute path starting with `/` |
| `host.domain_name` | Non-empty string |

### Derived Paths

From `config.yml`, the setup role derives:

| Variable | Value |
|----------|-------|
| `input_project_dir` | `{{ playbook_dir }}/input/{{ project_name }}` |
| `output_project_dir` | `{{ shared_path }}/output/{{ project_name }}` |
| `log_dir` | `{{ shared_path }}/log/{{ project_name }}` |
| `shared_path` | `{{ config.host.shared_path }}` |
| `host_name` | `{{ config.host.hostname }}` |

---

## 4. Entry Point Playbook Rules

The main playbook (`src/<domain>.yml`) orchestrates the domain workflow.

### Structure

```yaml
---
# <domain_name>.yml — Entry point for <domain_name> domain.
#
# Tags:
#   validate  — Validate configuration only
#   prepare   — Deploy infrastructure
#   build     — Execute main workflow
#   cleanup   — Remove everything
#
# Steps:
#   Step 0: Setup — load config, validate host, check prereqs
#   Step 1: Input validation
#   Step 2: Credential collection

# Step 0: Setup
- name: Domain setup
  hosts: localhost
  connection: local
  gather_facts: false
  tags: always
  roles:
    - <domain>_setup

# Step 1: Validate
- name: Validate configuration
  ansible.builtin.import_playbook: playbooks/validate_config.yml
  tags:
    - always
    - validate

# Step 2: Credentials (skipped for cleanup/validate)
- name: Collect credentials
  ansible.builtin.import_playbook: playbooks/get_credentials.yml
  when: not (skip_credentials | default(false) | bool)
  tags: always

# Flow: prepare
- name: Prepare infrastructure
  ansible.builtin.import_playbook: playbooks/prepare.yml
  tags: prepare

# Flow: build/execute
- name: Execute main workflow
  ansible.builtin.import_playbook: playbooks/execute.yml
  tags: build
```

### Rules

1. **NO `tasks:` blocks** — only `roles:` and `import_playbook:`.
2. **All `hosts:`** MUST be `localhost` with `connection: local`.
3. Each play has a clear step comment.
4. Tag validation, config loading, prereq checks — all in the setup role.

---

## 5. Sub-Playbook Rules

Sub-playbooks live in `src/playbooks/` and handle specific flows.

### Naming

| Pattern | Example | Purpose |
|---------|---------|---------|
| `prepare_*.yml` | `prepare_image_build_manager.yml` | Deploy infrastructure |
| `build_*.yml` | `build_image_x86_64.yml` | Build/execute main task |
| `cleanup_*.yml` | `cleanup_image_build_manager.yml` | Cleanup and teardown |
| `validate_*.yml` | `validate_image_build_config.yml` | Validation only |
| `get_*.yml` | `get_build_credentials.yml` | Credential/input collection |

### Rules

1. **All `hosts:`** MUST be `localhost` with `connection: local`.
2. Must NOT duplicate setup role logic (e.g., loading repo_status.yml).
3. Start with a guard if the play should be skipped conditionally.
4. `gather_facts: false` unless host facts are genuinely needed.

---

## 6. Role Rules

### Setup Role (`<domain>_setup`)

Every domain MUST have a setup role that runs first (tag: `always`). It handles:

1. **Tag validation** — supported tags, invalid combinations
2. **Config loading** — `config.yml` from repo root
3. **Host validation** — hostname, IP, paths
4. **Project dir setup** — create output, log dirs under `shared_path`
5. **Prerequisite checks** — fail-fast for all required files
6. **Data loading** — load domain-specific config files, upstream contracts
7. **Guard facts** — set `<domain>_setup_done: true`

### General Role Rules

1. Role names: `snake_case`, verb-noun (e.g., `deploy_minio`, `fetch_build_packages`).
2. Task file names: `snake_case.yml` (e.g., `install.yml`, `configure.yml`, `validate.yml`).
3. `tasks/main.yml` is the entry point — include other task files from there.
4. **ALL error messages in `vars/main.yml`** — never inline in tasks.
5. Private variables prefixed with `_` (e.g., `_prereq_checks`).
6. Each role is self-contained — no cross-role variable leaking.

---

## 7. Task Rules

### Every task MUST:

- Have a descriptive `name:` field (sentence case, imperative verb).
- Use **FQCN** (Fully Qualified Collection Names): `ansible.builtin.file`, NOT `file`.
- Use `become: true` explicitly where needed (never at play level for entire plays).

### Task patterns

```yaml
# Validation — use assert (cleaner output)
- name: Validate hostname format
  ansible.builtin.assert:
    that:
      - host_name is regex('^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$')
    fail_msg: "{{ host_hostname_fail_msg }}"
    quiet: true

# File existence — use stat + fail
- name: Check required file exists
  ansible.builtin.stat:
    path: "{{ required_file_path }}"
  register: _file_check

- name: Fail if required file not found
  ansible.builtin.fail:
    msg: "{{ file_not_found_fail_msg }}"
  when: not _file_check.stat.exists

# Command tasks — always set changed_when
- name: Check service status
  ansible.builtin.command:
    cmd: systemctl is-active myservice
  register: _service_status
  changed_when: false
  failed_when: false

# Fact caching — use cacheable: true when needed across plays
- name: Set project variables
  ansible.builtin.set_fact:
    project_name: "{{ config.project_name }}"
    cacheable: true

# Debug output — use verbosity
- name: Display loaded config
  ansible.builtin.debug:
    msg: "Project: {{ project_name }}"
    verbosity: 1
```

### Conditional Patterns

```yaml
# Good — simple boolean
when: standalone_mode | bool

# Good — variable check
when: my_var | default('') | length > 0

# Good — defined check
when: my_var is defined

# Bad — Jinja2 in when clause
when: "{{ some_complex_ternary }}"
```

### Loop Patterns

```yaml
# Always use loop_control
loop: "{{ items | dict2items }}"
loop_control:
  loop_var: item
```

### Error Handling

```yaml
# Block/rescue for recoverable errors
- name: Deploy with error handling
  block:
    - name: Install packages
      ansible.builtin.dnf:
        name: "{{ packages }}"
        state: present
  rescue:
    - name: Log failure
      ansible.builtin.debug:
        msg: "Installation failed: {{ ansible_failed_result.msg }}"
```

---

## 8. Variable and Message Rules

### Variable naming

| Pattern | Purpose | Example |
|---------|---------|---------|
| `*_dir` | Directory path | `input_project_dir` |
| `*_path` | File or directory path | `pulp_cert_host_path` |
| `*_file` | Stat register for a file | `_config_file` |
| `*_check` | Validation register | `_pulp_cert_check` |
| `_*` (underscore prefix) | Private/internal variable | `_prereq_checks` |

### Message naming

| Suffix | Used in | Example |
|--------|---------|---------|
| `_fail_msg` | `ansible.builtin.fail` / `assert` | `config_missing_fail_msg` |
| `_warn_msg` | `ansible.builtin.debug` (warnings) | `cert_expiry_warn_msg` |
| `_info_msg` | `ansible.builtin.debug` (info) | `build_done_info_msg` |

### Rules

1. **ALL error messages** go in `vars/main.yml` — never inline.
2. Use `snake_case` for all variables.
3. Role-specific variables MAY be prefixed with role name: `deploy_minio_port`.
4. Booleans: use `true` / `false`, never `yes` / `no`.
5. Always quote strings that could be misinterpreted: `{{ }}`, `:`, `#`.

---

## 9. Path Conventions

### Two Distinct Path Concepts

| Concept | Description | Example | Configurable? |
|---------|-------------|---------|---------------|
| **Code location** | Where `dell/omnia` (or a domain) is cloned | `/root/omnia/`, `~/omnia/`, anywhere | User chooses at `git clone` time |
| **State location** (`<shared_path>`) | Where persistent runtime data lives (MinIO data, registry, logs, output) | `/opt/omnia/image_build_manager/` | Yes — via `config.yml → host.shared_path` |

**`/opt/omnia`** is NOT the code checkout location. It is the **default state location**. Users clone code anywhere and configure `shared_path` in `config.yml` to point at the persistent storage directory.

### `<shared_path>` — Administration

| Question | Answer |
|----------|--------|
| **In source control?** | No — runtime data, not code. Gitignored. |
| **Backed up?** | Yes — contains build artifacts, MinIO S3 data, registry images. Loss = rebuild from scratch. |
| **Sensitive information?** | Low — credentials are Ansible Vault encrypted in `src/input/`. MinIO stores OS images (not sensitive). Logs may contain hostnames/IPs. |
| **Who creates it?** | The playbook creates it automatically on first run. |
| **Permissions?** | `0755` root-owned. MinIO/Registry containers access via bind-mount. |

### Runtime paths

| Path | Purpose |
|------|---------|
| `<shared_path>/` | Root persistent storage (domain state) |
| `<shared_path>/output/<project_name>/` | Domain output artifacts |
| `<shared_path>/log/<project_name>/` | Domain logs |
| `<shared_path>/log/<domain>.log` | Ansible playbook log |
| `<shared_path>/s3/` | MinIO S3 data (if applicable) |
| `<shared_path>/registry/` | Local container registry storage (if applicable) |
| `<shared_path>/workdir/` | Build workdir (if applicable) |
| `src/input/<project_name>/` | Input config files (in repo) |

### Upstream contract paths

| Path | Purpose |
|------|---------|
| `/opt/omnia/repo_manager/output/<project_name>/` | repo_manager contract output |
| `/opt/omnia/pulp/settings/certs/` | Pulp TLS certificates |

### Rules

- **Never hardcode `/opt/omnia` in task files** — use variables from config.yml.
- Output and log directories go under `<shared_path>/output/<project_name>/` and `<shared_path>/log/<project_name>/`, NOT under `src/`.
- Certificate paths are read as absolute paths from upstream contracts.
- `*_output_dir` variables are always **directories**, never file paths.

---

## 10. Input/Output Contracts

Every domain communicates via YAML contracts.

### Input Contract

Document in `docs/contracts/input-contract.md`:

```yaml
# What this domain reads
inputs:
  - file: config.yml
    source: user
    required: true
  - file: <domain>_config.yml
    source: src/input/<project_name>/
    required: true
  - file: repo_status.yml
    source: /opt/omnia/repo_manager/output/<project_name>/
    required: true
```

### Output Contract

Document in `docs/contracts/output-contract.md`:

```yaml
# What this domain produces
outputs:
  - file: <domain>_status.yml
    location: <shared_path>/output/<project_name>/
    format: YAML
```

### Rules

1. Every input file has a stat check in the setup role.
2. Fail-fast with actionable error messages for each missing file.
3. Output files use a `*_status.yml` naming pattern.

---

## 11. Ansible Style Guide

### YAML Conventions

- **2-space indentation** — no tabs, no trailing whitespace.
- Every YAML file starts with copyright header + `---`.
- Every playbook has a descriptive `name:` in the play definition.

### Module Rules

- **Always FQCN**: `ansible.builtin.file`, `containers.podman.podman_container`, etc.
- Set `changed_when` for all `command`/`shell` tasks.
- Set `failed_when` for non-standard failure conditions.
- Prefer `ansible.builtin.assert` over `fail` + `when` for validation.
- Use `ansible.builtin.dnf` for RHEL 10+ (not `yum`).

### Idempotency

- All roles SHALL be idempotent — running twice produces no changes on second run.
- Use `creates:` parameter for `command` tasks that generate files.
- Use `stat` + `when` for conditional execution.
- Never use `shell` with `rm -rf` without explicit guards.

### Secrets Management

- **Never** hardcode credentials in playbooks or variable files.
- Use Ansible Vault for sensitive data.
- Reference secrets via `{{ vault_secret_name }}`.

### Linting

- **ansible-lint** with `production` profile.
- **yamllint** for raw YAML files.
- Enforced rules: named tasks, FQCN for `ansible.builtin.*`, no bare variables in `when:`.

---

## 12. Python Style Guide (Custom Modules)

### Requirements

- Python 3.12+ compatible
- Type hints on all public functions
- Google-style docstrings (`Args:`, `Returns:`, `Raises:`)
- `pylint` score ≥ 8.0

### Module Structure

```python
#!/usr/bin/python
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
# Licensed under the Apache License, Version 2.0

"""Module docstring describing purpose."""

from ansible.module_utils.basic import AnsibleModule


def main():
    """Main module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            param1=dict(type='str', required=True),
        ),
        supports_check_mode=True,
    )
    # Module logic here
    module.exit_json(changed=False, result="ok")


if __name__ == '__main__':
    main()
```

### Naming

- `snake_case` for modules, functions, methods, variables.
- `PascalCase` for classes.
- `ALL_CAPS` for constants.
- `_prefix` for internal/private members.

---

## 13. Jinja2 Template Rules

- Templates use `.j2` extension, named to match target file.
- Start with `# {{ ansible_managed }}` comment.
- Use `{{ var | default(value) }}` for optional variables.
- Use `{%- -%}` for whitespace control in loops.
- No copyright header in templates (the role carries it).

---

## 14. Git Conventions

- **Branch naming**: `feature/<short-name>` or `fix/<short-name>`
- **Commit messages**: `<type>(<scope>): <description>`
  - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
  - Example: `feat(setup): add host validation for config.yml`
- **One logical change per commit** — don't mix refactoring with features.
- Always sync before commit: `git fetch origin && git merge origin/main`.

---

## 15. Upgrade & Rollback Standard

Every domain MUST support `upgrade` and `rollback` tags with dedicated playbooks.

### Tags

| Tag | Purpose | Playbook |
|-----|---------|----------|
| `upgrade` | Migrate domain to a new version | `playbooks/upgrade_<domain>.yml` |
| `rollback` | Revert domain to the previous version | `playbooks/rollback_<domain>.yml` |

### Entry Point Integration

```yaml
# In <domain>.yml — add upgrade/rollback alongside other flows

# Upgrade flow
- name: Upgrade <domain>
  ansible.builtin.import_playbook: playbooks/upgrade_<domain>.yml
  tags:
    - never
    - upgrade

# Rollback flow
- name: Rollback <domain>
  ansible.builtin.import_playbook: playbooks/rollback_<domain>.yml
  tags:
    - never
    - rollback
```

Both use `tags: [never, upgrade/rollback]` — they only run when explicitly requested via `--tags`.

### Version Tracking

Each domain writes a version file after successful deployment:

```yaml
# <state_path>/.domain_version.yml
---
domain: "image_build_manager"
version: "1.2.0"
installed_at: "2026-07-27T10:30:00Z"
ansible_version: "2.20.0"
python_version: "3.12.8"
config_hash: "sha256:abc123..."
previous_version: "1.1.0"
```

### Upgrade Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    UPGRADE FLOW                                  │
└─────────────────────────────────────────────────────────────────┘

  1. Pre-upgrade validation
     ├── Check current version from .domain_version.yml
     ├── Verify target version compatibility
     ├── Check disk space for snapshot
     └── Validate all services are healthy

  2. Snapshot current state
     ├── Copy <state_path>/ → <state_path>/.upgrade_snapshot/
     ├── Export service configs (MinIO, Registry)
     └── Record current .domain_version.yml

  3. Stop domain services
     ├── Stop MinIO (systemctl stop minio)
     ├── Stop Registry (systemctl stop registry)
     └── Verify services stopped

  4. Apply data migrations
     ├── Schema changes (config file format updates)
     ├── Path migrations (directory renames/moves)
     └── Data transformations (format changes)

  5. Start services with new config
     ├── Deploy updated Quadlet files
     ├── Reload systemd (systemctl daemon-reload)
     └── Start services

  6. Post-upgrade verification
     ├── Verify services are healthy
     ├── Validate data integrity
     └── Run smoke tests (MinIO connectivity, registry pull)

  7. Update version file
     └── Write new .domain_version.yml
```

### Rollback Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    ROLLBACK FLOW                                 │
└─────────────────────────────────────────────────────────────────┘

  1. Validate snapshot exists
     └── Check <state_path>/.upgrade_snapshot/ is present

  2. Stop domain services
     ├── Stop MinIO
     └── Stop Registry

  3. Restore state from snapshot
     ├── Remove current state directories
     ├── Restore from .upgrade_snapshot/
     └── Restore service configs

  4. Restart services
     ├── Reload systemd
     └── Start services with restored config

  5. Verify rollback
     ├── Check services are healthy
     ├── Validate data integrity
     └── Restore .domain_version.yml from snapshot

  6. Cleanup
     └── Optionally remove .upgrade_snapshot/ after verified rollback
```

### Upgrade Playbook Structure

```yaml
# playbooks/upgrade_<domain>.yml
---
- name: Upgrade <domain>
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: Run pre-upgrade validation
      ansible.builtin.include_role:
        name: <domain>_upgrade
        tasks_from: pre_upgrade.yml

    - name: Snapshot current state
      ansible.builtin.include_role:
        name: <domain>_upgrade
        tasks_from: snapshot.yml

    - name: Apply data migrations
      ansible.builtin.include_role:
        name: <domain>_upgrade
        tasks_from: migrate.yml

    - name: Post-upgrade verification
      ansible.builtin.include_role:
        name: <domain>_upgrade
        tasks_from: verify.yml
```

### Rollback Playbook Structure

```yaml
# playbooks/rollback_<domain>.yml
---
- name: Rollback <domain>
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: Validate snapshot exists
      ansible.builtin.include_role:
        name: <domain>_upgrade
        tasks_from: validate_snapshot.yml

    - name: Restore from snapshot
      ansible.builtin.include_role:
        name: <domain>_upgrade
        tasks_from: restore.yml

    - name: Post-rollback verification
      ansible.builtin.include_role:
        name: <domain>_upgrade
        tasks_from: verify.yml
```

### Rules

1. **Upgrade MUST create a snapshot** before modifying any state.
2. **Rollback MUST NOT require the new version's code** — it should work with the snapshot data alone.
3. **Version file** is updated only after successful post-upgrade verification.
4. **Credentials are skipped** during upgrade/rollback (same as cleanup/validate).
5. **Data migrations** are idempotent — running upgrade twice on the same version is a no-op.
6. **Snapshot directory** is `<state_path>/.upgrade_snapshot/` — only one snapshot is kept at a time.

---

## 16. Validation Checklist

Before submitting a PR, verify:

- [ ] Entry point playbook has NO inline `tasks:` — only `roles:` / `import_playbook:`
- [ ] All `hosts:` are `localhost` with `connection: local`
- [ ] All error messages defined in `vars/main.yml`, not inline
- [ ] All prerequisite files checked in setup role (fail-fast)
- [ ] Config validation includes hostname regex, IPv4, absolute path checks
- [ ] Output and log directories created under `<shared_path>/output/<project_name>/` and `<shared_path>/log/<project_name>/`
- [ ] No `src/log/` or `src/output/` directories
- [ ] No OIM, oim, or inventory group references — everything is localhost
- [ ] All modules use FQCN (`ansible.builtin.*`)
- [ ] `changed_when` set on all `command`/`shell` tasks
- [ ] Copyright header on all source files
- [ ] `ansible-lint` passes with no errors
- [ ] Python modules pass `pylint` with score ≥ 8.0
