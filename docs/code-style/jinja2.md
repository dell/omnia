# Jinja2 Template Style Guide -- Omnia

Based on [Dell Omnia Jinja2 Style Guide](https://github.com/dell/omnia).

## 1. File Conventions

- Template files SHALL use `.j2` extension
- Name SHALL match the target file: `slurm.conf.j2` -> `slurm.conf`
- Store in role's `templates/` directory
- Start with `# {{ ansible_managed }}` comment
- **No copyright header in templates** -- the role carries it

### 1.1 ansible_managed Standardization

Projects SHOULD standardize the `ansible_managed` string in `ansible.cfg`:

```ini
[defaults]
ansible_managed = Managed by Omnia - Do not edit manually
```

A consistent generated-file header improves supportability by making it clear which files are machine-generated and should not be edited directly.

## 2. Syntax

| Delimiter | Purpose | Example |
|-----------|---------|---------|
| `{{ }}` | Variable output | `{{ admin_nic_ip }}` |
| `{% %}` | Logic (if/for) | `{% if enable_gpu %}` |
| `{# #}` | Comments | `{# Registry config #}` |

## 3. Variables

### 3.1 Dot Notation vs Bracket Notation

Prefer dot notation for normal dictionary keys and object attributes:
```jinja
{{ node.hostname }}
{{ cluster.admin_nic_ip }}
```

Use bracket notation when:
- Keys contain special characters or hyphens: `{{ config['my-key'] }}`
- Keys contain spaces: `{{ metadata['display name'] }}`
- Keys collide with Python dict methods (`items`, `keys`, `values`, `get`, `update`): `{{ config['items'] }}`
- Keys are variables themselves: `{{ config[key_var] }}`

```jinja
{# Correct — 'items' collides with dict.items() method #}
{{ software_config['items'] }}

{# Correct — hyphenated key #}
{{ network_spec['admin-network'] }}

{# Correct — normal key, dot notation preferred #}
{{ network_spec.admin_nic_ip }}
```

### 3.2 Default Values

Always provide defaults for optional variables:
```jinja
{{ telemetry_port | default(9090) }}
```

### 3.3 Undefined Variable Safety

Guard access to optional nested objects to avoid `UndefinedError`:

```jinja
{# Safe — check before accessing nested attribute #}
{% if gpu_config is defined and gpu_config %}
driver_version={{ gpu_config.driver_version }}
{% endif %}

{# Safe — default for potentially missing nested key #}
gpu_driver={{ gpu_config.driver_version | default('') }}

{# UNSAFE — fails if gpu_config is undefined #}
driver_version={{ gpu_config.driver_version }}
```

Common failure scenarios:
- Variable is undefined -- use `is defined` test
- Variable is `None` -- use `and variable` after `is defined`
- Nested key is missing -- use `default()` filter on the full expression
- Empty list or dict -- test with `| length > 0` before iterating

## 4. Whitespace Control

### 4.1 Trimming Syntax

- Use `{%-` and `-%}` to strip whitespace around control blocks
- Use standard `{% %}` when whitespace is acceptable or significant

```jinja
{%- for node in compute_nodes %}
NodeName={{ node.hostname }} CPUs={{ node.cpus }} State=UNKNOWN
{%- endfor %}
```

### 4.2 Trimming Risks

Use whitespace trimming only after verifying the rendered output. Excessive trimming can:
- Remove required blank lines between configuration sections
- Collapse separators that some parsers depend on
- Produce hard-to-debug formatting issues

**Before trimming (incorrect output):**
```jinja
{%- for section in config_sections -%}
[{{ section.name }}]
{%- for key, value in section.items -%}
{{ key }}={{ value }}
{%- endfor -%}
{%- endfor -%}
```
Produces: `[network]host=server1port=8080[storage]path=/data` (no newlines).

**After fixing:**
```jinja
{% for section in config_sections %}
[{{ section.name }}]
{% for key, value in section.items %}
{{ key }}={{ value }}
{% endfor %}

{% endfor %}
```
Produces properly separated sections.

Configuration files with significant whitespace (YAML, Python, Makefile) require extra care with trimming.

## 5. Control Structures

### 5.1 Conditionals
```jinja
{% if enable_idrac_telemetry | default(false) %}
[idrac]
endpoint = {{ idrac_endpoint }}
port = {{ idrac_port | default(443) }}
{% endif %}
```

### 5.2 Loops
```jinja
{% for mount in nfs_mounts %}
{{ mount.server }}:{{ mount.path }}  {{ mount.mount_point }}  nfs  {{ mount.options | default('defaults') }}  0  0
{% endfor %}
```

### 5.3 Loop with Index
```jinja
{% for partition in slurm_partitions %}
PartitionName={{ partition.name }} Nodes={{ partition.nodes }} Default={{ 'YES' if loop.first else 'NO' }}
{% endfor %}
```

## 6. Filters

| Filter | Purpose |
|--------|---------|
| `default(val)` | Fallback value |
| `join(',')` | List to string |
| `to_yaml` | Dict to YAML |
| `to_json` | Dict to JSON |
| `bool` | Convert to boolean |
| `int` | Convert to integer |
| `lower` / `upper` | Case conversion |
| `regex_replace` | Regex substitution |

### 6.1 Filter Chaining
```jinja
{{ compute_nodes | map(attribute='hostname') | join(',') }}
```

### 6.2 default(omit) Usage

`default(omit)` is intended **only** for Ansible task module parameters. It tells Ansible to omit the parameter entirely if the variable is undefined.

**Correct -- in Ansible task parameters:**
```yaml
- name: Create user
  ansible.builtin.user:
    name: "{{ user_name }}"
    groups: "{{ user_groups | default(omit) }}"
```

**Incorrect -- in rendered configuration templates:**
```jinja
{# WRONG — omit produces the string 'OMIT_VALUE_...' in rendered output #}
port={{ service_port | default(omit) }}
```

**Correct -- use conditional blocks for optional config values:**
```jinja
{% if service_port is defined %}
port={{ service_port }}
{% endif %}
```

## 7. Template Scope and Complexity

Templates SHOULD focus on **rendering data**, not **processing data**. Keep templates as thin presentation layers.

### 7.1 What Belongs in Templates

- Variable interpolation: `{{ hostname }}`
- Simple conditionals: `{% if feature_enabled %}`
- Simple loops: `{% for node in nodes %}`
- Filter chains (< 3 filters): `{{ list | sort | join(',') }}`
- Comment blocks for section organization

### 7.2 What Does NOT Belong in Templates

Move these into **Python modules** (`plugins/modules/`), **module_utils**, or **Ansible preprocessing tasks** (`set_fact`):

| Anti-Pattern | Why | Alternative |
|-------------|-----|-------------|
| `namespace()` | Mutable Jinja state -- fragile and untestable | Python module |
| Deeply nested loops (>2 levels) | Unreadable, hard to debug | Python module with data transformation |
| Complex filtering chains | Opaque logic in template | `set_fact` or Python pre-processing |
| Multi-step transformations | Templates are not ETL pipelines | Python module |
| Large `{% set %}` blocks | Business logic in presentation layer | Move to `module_utils/` |
| Arithmetic beyond simple `+ 1` | Error-prone in Jinja | Python module |

Templates containing `namespace()`, mutable state, or nested loops deeper than two levels SHALL be reviewed for conversion into Python modules.

See Ansible Style Guide §12 (Module-First Data Processing) for full guidance on when to extract logic into Python modules.

### 7.3 Template Size

Templates exceeding approximately 200 lines SHOULD be reviewed for:
- Splitting into smaller templates with `{% include %}`
- Using template inheritance (`{% extends %}` / `{% block %}`)
- Extracting reusable snippets into separate `.j2` files
- Moving data transformation logic into Python modules

## 8. Template Organization

### 8.1 Complex Templates
- Break large templates into sections with comment blocks
- Use `{% block %}` / `{% extends %}` for template inheritance when appropriate

```jinja
{# ============================================ #}
{# Section: Controller Configuration             #}
{# ============================================ #}
SlurmctldHost={{ slurm_control_node }}
SlurmctldPort={{ slurmctld_port | default(6817) }}

{# ============================================ #}
{# Section: Compute Node Definitions             #}
{# ============================================ #}
{% for node in compute_nodes %}
NodeName={{ node.hostname }} CPUs={{ node.cpus }} RealMemory={{ node.memory }}
{% endfor %}
```

### 8.2 Reusable Snippets
- Extract repeated patterns into separate template files
- Use `{% include %}` for composition

## 9. Security

### 9.1 Forbidden Content

Templates MUST NOT contain:
- Hardcoded passwords or passphrases
- API keys or tokens
- Certificates or private keys
- Connection strings with embedded credentials

Sensitive values MUST come from Ansible variables, preferably Ansible Vault-encrypted:

```jinja
{# CORRECT — value from vault-provided variable #}
db_password={{ vault_db_password }}
api_key={{ vault_api_key }}

{# WRONG — hardcoded credential #}
db_password=admin123
api_key=sk-abc123def456
```

Align with Ansible Style Guide §8 (Secrets Management).

## 10. Error Prevention and Validation

### 10.1 Required vs Optional Variables
- Use `{{ var }}` without `default()` for required variables -- Ansible will fail clearly
- Use `{% if var is defined %}` for conditional blocks with optional variables
- Use `| int` when arithmetic is needed: `{{ port | int + 1 }}`
- Use `| bool` for boolean comparisons: `{% if flag | bool %}`

### 10.2 Template Validation

Configuration templates SHOULD use `validate:` whenever a native validator exists. Validation occurs on a temporary copy before deployment, preventing broken configs from reaching production.

```yaml
- name: Deploy SSH configuration
  ansible.builtin.template:
    src: sshd_config.j2
    dest: /etc/ssh/sshd_config
    mode: "0600"
    validate: "sshd -t -f %s"
  become: true
  notify: restart_sshd

- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    validate: "nginx -t -c %s"
  become: true
  notify: restart_nginx

- name: Deploy sudoers configuration
  ansible.builtin.template:
    src: sudoers.j2
    dest: /etc/sudoers.d/omnia
    validate: "visudo -cf %s"
  become: true
```

### 10.3 FQCN in Examples

All Ansible task examples within this guide and in template-related documentation MUST use FQCN modules:

```yaml
# CORRECT
- name: Deploy configuration
  ansible.builtin.template:
    src: config.conf.j2
    dest: /etc/config.conf

# WRONG — bare module name
- name: Deploy configuration
  template:
    src: config.conf.j2
    dest: /etc/config.conf
```

## 11. Testing

### 11.1 Basic Verification
- Verify templates generate valid configuration files
- Test with edge cases: empty lists, undefined optional vars, special characters

### 11.2 Molecule Testing

- Templates SHOULD be covered by Molecule scenarios that deploy and verify the rendered output
- Critical templates (SSH config, Slurm config, network config) MUST include render-validation tests

### 11.3 Test Cases

Test cases SHOULD cover:
- Undefined optional variables (should render with defaults or be omitted)
- Empty collections (empty node lists, empty mount lists)
- Special characters in variable values (paths with spaces, hostnames with dots)
- Large inventories (1000+ node lists for Slurm, /etc/hosts)
- Production-scale configurations (verify no truncation or timeout)

## 12. Forbidden Patterns

The following patterns are forbidden in Jinja2 templates. If template logic becomes complex enough to require any of these, move the logic into a Python module or Ansible preprocessing step.

| Pattern | Why Forbidden | Alternative |
|---------|--------------|-------------|
| `{% set ns = namespace() %}` | Mutable state in templates is fragile and untestable | Python module |
| `{% call %}` blocks | Rarely needed, obscure Jinja feature | Python function in module_utils |
| Loops nested > 2 levels deep | Unreadable, hard to debug, high cognitive complexity | Python data transformation |
| Complex YAML generation logic | Templates should render, not generate structured data | Python module returning structured data |
| Mutable state tracking | `{% set %}` used to accumulate across loop iterations | Python list/dict processing |
| Business logic | Validation rules, calculations, conditional workflows | Python module or Ansible tasks |

**Rule of thumb:** If the template logic would benefit from unit tests, it belongs in Python.
