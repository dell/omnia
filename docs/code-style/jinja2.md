# Jinja2 Template Style Guide -- Omnia

Based on [Dell Omnia Jinja2 Style Guide](https://github.com/dell/omnia).

## 1. File Conventions

- Template files SHALL use `.j2` extension
- Name SHALL match the target file: `slurm.conf.j2` → `slurm.conf`
- Store in role's `templates/` directory
- Start with `# {{ ansible_managed }}` comment
- **No copyright header in templates** — the role carries it

## 2. Syntax

| Delimiter | Purpose | Example |
|-----------|---------|---------|
| `{{ }}` | Variable output | `{{ admin_nic_ip }}` |
| `{% %}` | Logic (if/for) | `{% if enable_gpu %}` |
| `{# #}` | Comments | `{# Registry config #}` |

## 3. Variables

- Use dot notation: `{{ node.hostname }}`
- Bracket notation for special chars: `{{ config['my-key'] }}`
- Always provide defaults for optional variables:
  ```jinja
  {{ telemetry_port | default(9090) }}
  ```

## 4. Whitespace Control

- Use `{%-` and `-%}` for clean output in loops
- Use standard `{% %}` when whitespace is acceptable

## 5. Filters

| Filter | Purpose |
|--------|---------|
| `default(val)` | Fallback value |
| `join(',')` | List to string |
| `to_yaml` | Dict to YAML |
| `bool` | Convert to boolean |
| `int` | Convert to integer |
| `lower` / `upper` | Case conversion |

## 6. Error Prevention

- Use `{{ var }}` without `default()` for required variables
- Use `{{ var | default(omit) }}` to skip optional Ansible parameters
- Use `| int` when arithmetic is needed
