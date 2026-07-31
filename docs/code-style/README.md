# Code Style Guides -- Omnia

Coding standards per language/tool. All code PRs are reviewed against these guides.
Based on [Dell Omnia Code Style Guides](https://github.com/dell/omnia).

| Guide | What It Covers |
|-------|---------------|
| [ansible.md](ansible.md) | Playbook structure, FQCN modules, role layout, linting |
| [python.md](python.md) | Naming, docstrings, pylint rules, Ansible module patterns |
| [jinja2.md](jinja2.md) | Template syntax, filters, whitespace, error prevention |
| [general.md](general.md) | Copyright headers, readability, consistency, documentation |

## Validated Environment

| Component | Minimum Version | Validated Version |
|-----------|----------------|-------------------|
| Python | 3.12+ | 3.12.8 |
| Ansible Core | 2.20+ | 2.20.0 |
| RHEL | 10.0+ | 10.0 |
| Podman | 5.0+ | 5.3.1 |
