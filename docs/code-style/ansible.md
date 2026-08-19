# Ansible / YAML Style Guide -- Omnia

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
- No tabs -- spaces only
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
- `src/<domain>.yml` MUST contain only `roles:` and `import_playbook:` -- NO inline `tasks:`.
- **Entry-point playbooks** (`src/<domain>.yml`) MUST target `localhost` with `connection: local`. These are orchestration plays that delegate work to roles.
- **Internal plays** (inside roles, included playbooks, provisioning steps) MAY target remote host groups such as `compute_nodes`, `management_nodes`, `login_nodes`, or `service_nodes` when the play executes tasks directly on those hosts.
- Each play must have a step comment (`# Step N: ...`).

```yaml
# Entry-point playbook (orchestration) — always localhost
- name: Orchestrate cluster provisioning
  hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - orchestrator_setup

# Internal play (execution) — targets remote hosts
- name: Configure compute nodes
  hosts: compute_nodes
  gather_facts: false
  become: true
  tasks:
    - name: Apply node configuration
      ansible.builtin.include_role:
        name: node_config
```

### 2.3 Task Standards
- Every task SHALL have a descriptive `name:` field
- Use **FQCN** (Fully Qualified Collection Names): `ansible.builtin.copy`, not `copy`
- Use `become: true` explicitly -- never rely on implicit privilege escalation
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
- `defaults/main.yml` -- Values the user CAN override
- `vars/main.yml` -- Internal values the user SHOULD NOT change
- **ALL error messages** go in `vars/main.yml` -- never inline

### 4.3 Boolean Values
- Use `true` / `false` -- never `yes` / `no`

### 4.4 String Quoting
- Always quote strings that could be misinterpreted as booleans or numbers
- Always quote strings with special characters: `{{ }}`, `:`, `#`

### 4.5 Fact Caching and Verbosity
- Use `cacheable: true` on `set_fact` when the fact is needed across plays
- Use `verbosity: 1` or `2` on debug tasks (not shown by default)
- Use `quiet: true` on assert tasks to suppress verbose output

```yaml
- name: Show detailed variable state
  ansible.builtin.debug:
    var: _internal_config
    verbosity: 1

- name: Validate prerequisites
  ansible.builtin.assert:
    that:
      - oim_installed | bool
      - admin_nic_ip is defined
    fail_msg: "{{ prereq_fail_msg }}"
    quiet: true
```

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
- `ansible.posix` (firewalld, sysctl, mount)
- `containers.podman` (container management)
- `community.crypto` (certificate handling)
- `community.general` (general utilities)

## 7. Idempotency

- All roles SHALL be idempotent -- running twice produces no changes on second run
- Use `creates:` parameter for `command` tasks that generate files
- Use `stat` + `when` for conditional execution
- Never use `shell` with `rm -rf` without explicit guards

## 8. Secrets Management

- **Never** hardcode credentials in playbooks or variable files
- Use Ansible Vault for sensitive data
- Reference secrets via `{{ vault_secret_name }}`

### 8.1 Sensitive Data Logging

Tasks that handle passwords, API keys, tokens, authentication headers, certificates, or SSH private keys MUST set `no_log: true` to prevent credentials from appearing in Ansible output or CI logs.

```yaml
- name: Set database password from vault
  ansible.builtin.set_fact:
    _db_password: "{{ vault_db_password }}"
  no_log: true

- name: Authenticate to registry
  ansible.builtin.uri:
    url: "{{ registry_url }}/v2/token"
    method: POST
    body_format: json
    body:
      username: "{{ vault_registry_user }}"
      password: "{{ vault_registry_password }}"
  register: _auth_response
  no_log: true

# WRONG — exposes secret in debug output
- name: Show auth response
  ansible.builtin.debug:
    var: _auth_response
```

**Rules:**
- Debug tasks MUST NOT expose secret values
- `register:` variables containing secrets SHOULD be prefixed with `_` and used only internally
- Use `no_log: true` on any task that passes credentials as parameters

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
- **`README.md`** -- Description, requirements, variables, dependencies, usage example.
- **`meta/main.yml`** -- Galaxy metadata: author, description, license, min_ansible_version, dependencies.

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
- **`DOCUMENTATION`** -- Module name, description, options with types.
- **`EXAMPLES`** -- Playbook task examples using FQCN.
- **`RETURN`** -- Return value documentation with types.

See Python Style Guide §5 for the full template.

### 10.4 galaxy.yml Tags

- Tags MUST use `snake_case` -- **no hyphens** (e.g., `image_build` not `image-build`).
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

---

## 11. Security & Quality Gates

All code quality and security gates are defined in §14. This section provides a brief summary for quick reference.

**Key gates:** ansible-lint (production profile), gitleaks, shellcheck, Checkmarx, SonarQube, pylint, bandit, pip-audit.

See **§14. Security & Compliance Gates** for the full authoritative table, thresholds, and enforcement details.

---

## 12. Module-First Data Processing

Prefer **Python Ansible modules** (`plugins/modules/`) over complex Jinja2 templates embedded in `set_fact` tasks for data processing logic.

### 12.1 When to Use a Python Module

Use a module when the task involves **any** of:

| Indicator | Example |
|-----------|--------|
| Nested loops with filtering | Iterating layers -> groups -> packages with type/arch filters |
| JSON/YAML file parsing + transformation | Loading catalog JSON, extracting structured data |
| `namespace()` pattern in Jinja2 | Using `{% set ns = namespace(...) %}` for mutable state |
| String manipulation or regex | Splitting package names, extracting versions from tags |
| >10 lines of Jinja2 in a single `set_fact` | Complex template logic that obscures intent |

### 12.2 When Ansible Tasks Are Sufficient

Keep as Ansible tasks when the logic is:

- Simple variable assignment (`set_fact` with defaults)
- File operations (`stat`, `copy`, `template`, `file`)
- Service management (`systemd`, `service`)
- Package management (`dnf`, `pip`)
- Simple loops with `when` filters (e.g., building a list by appending items)
- Flow control (`include_tasks`, `block/rescue`)
- Assertions and validation (`assert`, `fail`)

### 12.3 Benefits of Modules Over Jinja2

| Aspect | Jinja2 in set_fact | Python Module |
|--------|-------------------|---------------|
| **Performance** | Template rendering per task | Native Python execution |
| **Testability** | Requires full Ansible run | Unit-testable with pytest |
| **Debugging** | Opaque template errors | Standard Python tracebacks |
| **Readability** | YAML-embedded templates | Explicit Python functions |
| **Type safety** | String-based, late binding | Python type hints |
| **Reusability** | Copy-paste between roles | Import and call |

### 12.4 Module Conventions

- Place modules in `plugins/modules/<name>.py`
- Place shared utilities in `plugins/module_utils/`
- Follow Galaxy documentation requirements (see Python Style Guide §5)
- Module functions SHOULD be independently callable for unit testing
- Use `module.fail_json()` for errors -- never `sys.exit()`
- Set `supports_check_mode=True` for read-only modules

### 12.5 Examples

**Before (Jinja2 -- avoid):**
```yaml
- name: Resolve packages from catalog
  ansible.builtin.set_fact:
    compute_images_dict: >-
      {% set result = {} -%}
      {% for layer in _catalog.functionallayer -%}
        {% for comp in layer.components -%}
          {% set group = _catalog.groups[comp] -%}
          {# ... 30+ lines of nested filtering ... #}
        {% endfor -%}
      {% endfor -%}
      {{ result }}
```

**After (Python module -- preferred):**
```yaml
- name: Resolve packages from catalog
  omnia.image_build.parse_catalog:
    catalog_file: "{{ catalog_file }}"
    build_arch: "{{ build_arch }}"
  register: _catalog_result
```

---

## 13. HPC Production Scale Rules (1000-Node Clusters)

Omnia deploys to production HPC clusters with 500-2,000 nodes. Every task that touches multiple nodes MUST be designed for parallel execution and minimal wall-clock time.

### 13.1 Prefer Threaded Modules for Multi-Node Operations

**Rule:** When a task must execute the same operation on hundreds or thousands of compute nodes (e.g., update `/etc/hosts`, distribute SSH keys, copy files), prefer a **Python Ansible module** with `ThreadPoolExecutor` over serial Ansible loops.

**Why:** A serial `loop:` with `delegate_to:` over 1,000 hosts takes O(N) time. A threaded module takes O(N / max_workers) time. At 1,000 nodes with `ssh_max_parallel=20`, this is a **50x speedup**.

Standard Ansible modules (`ansible.builtin.copy`, `ansible.builtin.dnf`, etc.) remain the preferred default for small-scale or single-host operations. The threading pattern is reserved for massive fan-out where Ansible's built-in parallelism (`forks`) is insufficient.

**Anti-Pattern (avoid for multi-node fan-out):**
```yaml
# Serial loop over 1000 hosts — takes 30+ minutes
- name: Update /etc/hosts on all nodes
  ansible.builtin.lineinfile:
    path: /etc/hosts
    line: "{{ item.ip }} {{ item.hostname }}"
  loop: "{{ all_hosts }}"
  delegate_to: "{{ item.hostname }}"
```

**Correct Pattern (use for HPC-scale operations):**
```yaml
# Parallel module — completes in ~1 minute
- name: Update /etc/hosts on all nodes
  bulk_update_hosts:
    hosts: "{{ reachable_hosts }}"
    ip_name_map: "{{ ip_name_map }}"
    ssh_key_path: "/root/.ssh/oim_rsa"
    ssh_max_parallel: 20
    ssh_connect_timeout: 10
  register: bulk_update_result
```

### 13.2 Threading Pattern for Custom Modules

All multi-node modules MUST follow this pattern (reference: `bulk_update_hosts.py`):

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_module():
    module = AnsibleModule(argument_spec={
        "hosts": {"type": "list", "required": True, "elements": "str"},
        "ssh_max_parallel": {"type": "int", "default": 20},
        "ssh_connect_timeout": {"type": "int", "default": 10},
    })

    hosts = module.params["hosts"]
    max_parallel = module.params["ssh_max_parallel"]

    with ThreadPoolExecutor(max_workers=min(max_parallel, len(hosts))) as pool:
        futures = {pool.submit(process_host, h): h for h in hosts}
        for future in as_completed(futures):
            host = futures[future]
            # collect per-host results
```

**Key design rules:**
- `ssh_max_parallel` caps concurrency (default: 20, max: 50)
- `ssh_connect_timeout` prevents hung connections (default: 10s)
- Build content/payload once, distribute to all nodes
- Collect per-host results in a dict for reporting
- Use `module.warn()` for partial failures -- never fail the entire play for one node
- Support `check_mode=True` for dry-run safety

### 13.3 ThreadPoolExecutor Trade-Offs

Threaded Ansible modules bypass the normal Ansible execution model. Before writing one, understand these trade-offs:

| Concern | Impact | Mitigation |
|---------|--------|------------|
| Connection plugins bypassed | Ansible connection settings (become, SSH args) are not applied | Manage SSH args explicitly in subprocess calls |
| Callback plugins may miss events | Execution details may not appear in Ansible output/logs | Return per-host results via `module.exit_json()` |
| Handlers not triggered | `notify:` does not fire from within a threaded module | Trigger handlers from the calling playbook after the module completes |
| No automatic retry/backoff | Ansible retry logic does not apply inside the module | Implement retry loops in the worker function |
| Privilege escalation not automatic | `become:` is not inherited inside subprocess calls | Use explicit SSH as root or sudo in the remote script |

**When to use:** Operations on hundreds or thousands of hosts where Ansible forks are insufficient (e.g., `/etc/hosts` updates, SSH key distribution, munge key sync).

**When NOT to use:** Single-host operations, small host groups (<20), operations that require Ansible facts or handlers.

### 13.4 Prefer Ansible Modules Over Shell/Command

| Instead of | Use | Why |
|------------|-----|-----|
| `ansible.builtin.shell: dnf install -y pkg` | `ansible.builtin.dnf: name=pkg state=present` | Idempotent, no injection risk |
| `ansible.builtin.shell: systemctl restart svc` | `ansible.builtin.systemd: name=svc state=restarted` | Idempotent, proper return codes |
| `ansible.builtin.shell: cp src dest` | `ansible.builtin.copy: src=... dest=...` | Idempotent, checksum verification |
| `ansible.builtin.shell: mkdir -p /dir` | `ansible.builtin.file: path=/dir state=directory` | Idempotent, mode/owner support |
| `ansible.builtin.shell: cat file \| grep pattern` | `ansible.builtin.slurp:` + Python filter | No shell injection, proper encoding |
| `ansible.builtin.shell: curl url -o file` | `ansible.builtin.get_url: url=... dest=...` | Checksum, retries, timeout |
| `ansible.builtin.command: pip install pkg` | `ansible.builtin.pip: name=pkg` | Idempotent, virtualenv support |
| `ansible.builtin.shell: useradd user` | `ansible.builtin.user: name=user` | Idempotent, cross-platform |
| `ansible.builtin.shell: firewall-cmd ...` | `ansible.posix.firewalld: ...` | Idempotent, proper zone support |
| `ansible.builtin.shell: sysctl -w key=val` | `ansible.posix.sysctl: name=key value=val` | Persistent, idempotent |

### 13.5 Execution Time Budgets

| Operation | Target Time (1000 nodes) | Approach |
|-----------|-------------------------|----------|
| /etc/hosts update | < 2 minutes | `bulk_update_hosts` module (threaded) |
| SSH key distribution | < 3 minutes | `parallel_file_copy` module (threaded) |
| Node discovery/inventory | < 5 minutes | `bulk_discover_node_specs` module (threaded) |
| Package installation (per node) | < 10 minutes | `ansible.builtin.dnf` with `async` |
| Full OIM deployment | < 30 minutes | Parallelized role execution |
| Full cluster provisioning | < 60 minutes | Phased parallel execution |

### 13.6 Async Tasks for Long-Running Operations

For operations that take > 60 seconds per host (package install, image build):

```yaml
- name: Install packages on all compute nodes
  ansible.builtin.dnf:
    name: "{{ compute_packages }}"
    state: present
  async: 600         # 10-minute timeout
  poll: 0            # Fire-and-forget
  register: pkg_job

- name: Wait for package installation
  ansible.builtin.async_status:
    jid: "{{ pkg_job.ansible_job_id }}"
  register: pkg_result
  until: pkg_result.finished
  retries: 60
  delay: 10
```

### 13.7 Fact Gathering Optimization

```yaml
# For large clusters, disable fact gathering by default
- name: Configure compute nodes
  hosts: compute_nodes
  gather_facts: false    # REQUIRED for 1000-node plays
  strategy: free         # Allow parallel task execution

  tasks:
    - name: Gather only needed facts
      ansible.builtin.setup:
        gather_subset:
          - "!all"
          - network
          - hardware
      when: need_facts | default(false)
```

---

## 14. Security & Compliance Gates (Production HPC)

All code MUST pass these gates before merge to any release branch. This is the single authoritative gate table for both Ansible and Python code in this project.

| Gate | Tool | Requirement | Enforcement |
|------|------|-------------|-------------|
| **Ansible Lint** | `ansible-lint` | Zero errors with `production` profile | CI PR gate |
| **Python Lint** | `pylint` | Score >= 8.0 per file | CI PR gate |
| **Python SAST** | `bandit` | Zero High/Critical findings | CI PR gate |
| **Secret Leak Detection** | `gitleaks` | Zero findings | CI PR gate |
| **Dependency CVE** | `pip-audit` | Zero known vulnerabilities | CI PR gate |
| **Shell Lint** | `shellcheck` | Zero errors | CI PR gate |
| **Unit Tests** | `pytest` | All tests pass | CI PR gate |
| **SAST** | Checkmarx | Zero High/Critical | Scheduled / release gate |
| **Code Quality** | SonarQube | Zero bugs/vulns (Blocker/Critical) | Scheduled / release gate |
| **Commit Hygiene** | custom | No AI-only authors, conventional format | CI PR gate |

### 14.1 Ansible-Lint Production Profile

Key rules enforced:
- `name[missing]`: Every task MUST have a name
- `fqcn[action-core]`: FQCN required (`ansible.builtin.copy`, not `copy`)
- `no-changed-when`: `command`/`shell` tasks MUST set `changed_when`
- `risky-shell-pipe`: Avoid piped shell commands -- use modules
- `command-instead-of-module`: Use module when one exists (e.g., `dnf` not `shell: dnf install`)
- `no-jinja-when`: No Jinja2 delimiters in `when:` clauses

Suppressions allowed with `# noqa: <rule>` and a justification comment.

### 14.2 Checkmarx Compliance

- Zero High or Critical SAST findings in merged code
- Medium findings SHOULD be addressed within the same sprint
- Common HPC Checkmarx issues to avoid:
  - **OS Command Injection**: Use `subprocess.run()` with list args, never `os.system()` or `shell=True`
  - **Path Traversal**: Validate all file paths with `os.path.realpath()` + allowlist
  - **Hardcoded Credentials**: Use Ansible Vault -- never embed passwords, keys, or tokens
  - **Insecure Deserialization**: Use `json.loads()`, never `eval()` or `pickle.loads()` on user input

### 14.3 SonarQube Compliance

- Zero bugs (Blocker, Critical)
- Zero vulnerabilities (Blocker, Critical)
- Zero code smells (Blocker)
- Technical debt ratio < 5%
- Code coverage > 70% for new modules
- Common SonarQube issues in HPC code:
  - **Cognitive Complexity**: Break complex functions into smaller functions (max 15 per function)
  - **Duplicate Code**: Extract shared logic into `module_utils/`
  - **Unused Variables**: Remove or prefix with `_`
  - **Broad Exception Handling**: Catch specific exceptions, not `Exception`

### 14.4 Gitleaks (Secret Leak Prevention)

- No hardcoded passwords, API keys, tokens, or credentials in any file
- Use Ansible Vault for sensitive data -- reference via `{{ vault_secret_name }}`
- Custom `.gitleaks.toml` rules for Omnia-specific patterns
- CI runs `gitleaks detect` on every PR

### 14.5 Pylint for Ansible Modules

- Score >= 8.0 (CI threshold: `PYLINT_THRESHOLD=8`)
- Type hints on all public functions
- Google-style docstrings on all public functions
- No `# pylint: disable` without a justification comment
- Allowed suppressions: `import-error` (Ansible module_utils), `no-name-in-module`

---

## 15. Tags

### 15.1 Tag Naming
- Tags MUST use `snake_case` -- no spaces, no hyphens
- Tags MUST be descriptive and specific to the operation

### 15.2 Recommended Tags

| Tag | Purpose |
|-----|---------|
| `install` | Package installation, binary deployment |
| `configure` | Configuration file generation, service setup |
| `validate` | Prerequisite checks, input validation |
| `cleanup` | Removal of temporary files, stale state |
| `upgrade` | Version upgrade operations |
| `rollback` | Undo or restore operations |

### 15.3 Example
```yaml
- name: Install required packages
  ansible.builtin.dnf:
    name: "{{ required_packages }}"
    state: present
  become: true
  tags:
    - install

- name: Validate prerequisites
  ansible.builtin.assert:
    that:
      - admin_nic_ip is defined
    fail_msg: "{{ prereq_fail_msg }}"
    quiet: true
  tags:
    - validate
```

---

## 16. Ansible Configuration (ansible.cfg)

### 16.1 Recommended HPC Defaults

```ini
[defaults]
# Parallelism — scale for HPC cluster size
forks = 50

# SSH timeout — prevent hung connections on unreachable nodes
timeout = 30

# Fact gathering — disable by default for large inventories
gathering = explicit

# Ansible managed header — standardize generated file markers
ansible_managed = Managed by Omnia - Do not edit manually

# Interpreter
interpreter_python = /usr/bin/python3

[ssh_connection]
# Pipelining — reduces SSH round trips (2-3x speedup)
pipelining = true

# SSH args — multiplexing for connection reuse
ssh_args = -o ControlMaster=auto -o ControlPersist=60s -o ConnectTimeout=10

[privilege_escalation]
become = false
become_method = sudo
```

### 16.2 Key Settings

| Setting | Default | HPC Recommendation | Why |
|---------|---------|-------------------|-----|
| `forks` | 5 | 50 | Parallelize across more hosts |
| `timeout` | 10 | 30 | Allow time for loaded nodes to respond |
| `gathering` | implicit | explicit | Avoid gathering facts on 1000 nodes unnecessarily |
| `pipelining` | false | true | 2-3x SSH speedup by reducing round trips |
| `ControlPersist` | N/A | 60s | Reuse SSH connections across tasks |

---

## 17. Handler Standards

### 17.1 Rules
- Handlers MUST have descriptive names
- Handlers MUST use FQCN modules
- Handlers MUST use explicit `become: true` when privilege escalation is required
- Prefer `listen:` for grouping related handlers

### 17.2 Example
```yaml
# handlers/main.yml
- name: Restart slurmctld service
  ansible.builtin.systemd:
    name: slurmctld
    state: restarted
    daemon_reload: true
  become: true
  listen: restart_slurm

- name: Restart slurmd service
  ansible.builtin.systemd:
    name: slurmd
    state: restarted
  become: true
  listen: restart_slurm
```

```yaml
# tasks/configure_slurm.yml
- name: Deploy slurm.conf
  ansible.builtin.template:
    src: slurm.conf.j2
    dest: /etc/slurm/slurm.conf
    mode: "0644"
  notify: restart_slurm
```

---

## 18. Role Testing

### 18.1 Molecule

- Roles SHOULD provide Molecule scenarios for integration testing
- New roles SHOULD support: converge, idempotence, verify
- Molecule scenarios live in `roles/<role_name>/molecule/default/`

### 18.2 Custom Module Testing

- Custom modules (`plugins/modules/`) MUST include pytest tests
- Tests live in `test/<domain>/` mirroring the source structure
- See Python Style Guide §8 and `general.md` §6 for co-change requirements

---

## 19. Cross-References

- **Test co-change rule**: Changes to roles, playbooks, or modules MUST include corresponding FVT/UT test updates -- see `general.md` §6.
- **AI agent policy**: AI agents MUST NOT be used for PR sign-off -- see `general.md` §7.
- **Commit format**: All commits MUST follow `<type>(<scope>): <description>` -- see `general.md` §8.
- **Jinja2 templates**: See `jinja2.md` for template-specific rules.
- **Python modules**: See `python.md` for Python coding standards.
