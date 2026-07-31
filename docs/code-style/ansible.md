# Ansible / YAML Style Guide — Image Build Manager

Based on [Dell Omnia Ansible Style Guide](https://github.com/dell/omnia).

## 1. File Conventions

### 1.1 File Headers
- Every YAML file SHALL start with the Dell Apache 2.0 copyright header (see `general.md`)
- Copyright header SHALL be followed by `---`
- Every playbook SHALL have a descriptive `name:` in the play definition

### 1.2 File Naming
- Playbooks: `<component>.yml` (e.g., `image_build_manager.yml`)
- Role tasks: `main.yml`, `<action>.yml` (e.g., `validate_tags.yml`, `load_config.yml`)
- Variables: `main.yml` in `defaults/` and `vars/`
- Templates: `<name>.j2` in `templates/`

### 1.3 Indentation
- **2-space indentation** for all YAML files
- No tabs — spaces only
- No trailing whitespace

## 2. Playbook Standards

### 2.1 Play Structure
```yaml
---
# playbook_name.yml — Brief description of purpose
- name: Descriptive play name
  hosts: localhost
  connection: local
  gather_facts: false

  roles:
    - role_name
```

### 2.2 Entry Point Rules
- `src/<domain>.yml` MUST contain only `roles:` and `import_playbook:` — NO inline `tasks:`.
- All `hosts:` MUST be `localhost` with `connection: local`.
- Each play must have a step comment (`# Step N: ...`).

### 2.3 Task Standards
- Every task SHALL have a descriptive `name:` field
- Use **FQCN** (Fully Qualified Collection Names): `ansible.builtin.copy`, not `copy`
- Use `become: true` explicitly — never rely on implicit privilege escalation
- Set `changed_when` for all `command`/`shell` tasks
- Set `failed_when` for tasks with non-standard failure conditions

### 2.4 Example Task
```yaml
- name: Ensure log directory exists
  ansible.builtin.file:
    path: "{{ log_dir }}"
    state: directory
    mode: "0755"
  become: true

- name: Check if service is running
  ansible.builtin.command:
    cmd: systemctl is-active minio
  register: service_status
  changed_when: false
  failed_when: false
```

## 3. Role Structure

```
roles/<role_name>/
├── defaults/main.yml      # Default variables (overridable)
├── vars/main.yml           # Role variables (internal) — ALL error messages here
├── tasks/
│   ├── main.yml            # Entry point (include other task files)
│   ├── validate_tags.yml   # Tag validation
│   ├── load_config.yml     # Configuration loading
│   └── validate_prereqs.yml # Prerequisite validation
├── templates/              # Jinja2 templates
├── files/                  # Static files
├── handlers/main.yml       # Handlers (restart/reload)
└── meta/main.yml           # Role metadata and dependencies
```

## 4. Variable Standards

### 4.1 Naming
- Use **snake_case** for all variable names
- Prefix private variables with `_`: `_prereq_checks`, `_pulp_cert_check`
- Use descriptive names: `repo_manager_output_dir`, not `dir`

### 4.2 Defaults vs Vars
- `defaults/main.yml` — Values the user CAN override
- `vars/main.yml` — Internal values the user SHOULD NOT change
- **ALL error messages** go in `vars/main.yml` — never inline

### 4.3 Boolean Values
- Use `true` / `false` — never `yes` / `no`

### 4.4 String Quoting
- Always quote strings that could be misinterpreted as booleans or numbers
- Always quote strings with special characters: `{{ }}`, `:`, `#`

### 4.5 Fact Caching
- Use `cacheable: true` on `set_fact` when the fact is needed across plays
- Use `verbosity: 1` or `2` on debug tasks (not shown by default)
- Use `quiet: true` on assert tasks to suppress verbose output

## 5. Error Handling

### 5.1 Block/Rescue/Always
```yaml
- name: Deploy component with error handling
  block:
    - name: Install packages
      ansible.builtin.dnf:
        name: "{{ packages }}"
        state: present
  rescue:
    - name: Log failure
      ansible.builtin.debug:
        msg: "Deployment failed: {{ ansible_failed_result.msg }}"
```

### 5.2 Assertions
- Use `ansible.builtin.assert` for prerequisite validation
- Provide actionable `fail_msg` messages defined in `vars/main.yml`

## 6. Linting

### 6.1 Required Tools
- **ansible-lint** with production profile
- **yamllint** for raw YAML files

### 6.2 Enforced Rules
- No unnamed tasks
- No bare variables in `when:` clauses
- Use FQCN for `ansible.builtin.*` modules
- No `command`/`shell` when a module exists

### 6.3 Collection Requirements
Required collections in `requirements.yml`:
- `ansible.utils` (IP validation)
- `containers.podman` (container management)
- `community.crypto` (certificate handling)
- `community.general` (general utilities)

## 7. Idempotency

- All roles SHALL be idempotent — running twice produces no changes on second run
- Use `creates:` parameter for `command` tasks that generate files
- Use `stat` + `when` for conditional execution
- Never use `shell` with `rm -rf` without explicit guards

## 8. Secrets Management

- **Never** hardcode credentials in playbooks or variable files
- Use Ansible Vault for sensitive data
- Reference secrets via `{{ vault_secret_name }}`

## 9. Validated Environment

| Component | Minimum | Validated |
|-----------|---------|-----------|
| Ansible Core | 2.20+ | 2.20.0 |
| Python | 3.12+ | 3.12.8 |
| RHEL | 10.0+ | 10.0 |

## 10. Ansible Galaxy Collection Requirements

Every domain is packaged as an Ansible Galaxy collection. The following rules ensure Galaxy import validation passes.

### 10.1 Role Documentation

Every role MUST have:
- **`README.md`** — Description, requirements, variables, dependencies, usage example.
- **`meta/main.yml`** — Galaxy metadata: author, description, license, min_ansible_version, dependencies.

Galaxy import **fails** if any role is missing `README.md` or `meta/main.yml`.

### 10.2 Role Structure (Galaxy-compliant)

```
roles/<role_name>/
├── README.md              # REQUIRED — role documentation
├── meta/main.yml          # REQUIRED — Galaxy metadata
├── tasks/main.yml         # Entry point
├── vars/main.yml          # Internal variables + error messages
├── defaults/main.yml      # User-overridable defaults
├── templates/             # Jinja2 templates
├── files/                 # Static files
└── handlers/main.yml      # Handlers
```

### 10.3 Module Documentation

Every Python module under `plugins/modules/*.py` MUST contain:
- **`DOCUMENTATION`** — Module name, description, options with types.
- **`EXAMPLES`** — Playbook task examples using FQCN.
- **`RETURN`** — Return value documentation with types.

See Python Style Guide (§5) for the full template.

### 10.4 galaxy.yml Tags

- Tags MUST use `snake_case` — **no hyphens** (e.g., `image_build` not `image-build`).
- Galaxy rejects tags with hyphens, spaces, or special characters.

### 10.5 Pre-Publish Validation

```bash
# Validate module docs
ansible-doc omnia.<collection>.<module_name>

# Verify role files exist
find roles -name README.md
find roles -path "*/meta/main.yml"

# Build and check
ansible-galaxy collection build
```
