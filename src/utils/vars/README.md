# Domain Variables

This directory contains domain-level variable files for the utils domain.

## Purpose

Domain variables provide constants and configuration values that are used across multiple roles and playbooks within the utils domain. These are distinct from role-specific variables (which live in `roles/<role_name>/vars/`) and input configuration (which lives in `input/`).

## Structure

```
vars/
├── README.md
└── <domain_vars>.yml
```

## Usage

Domain variables can be included in playbooks using:

```yaml
- name: Load domain variables
  ansible.builtin.include_vars:
    file: vars/domain_vars.yml
```

## Variable Types

- **Constants**: Fixed values that should not be modified by users
- **Domain configuration**: Settings that apply across the entire domain
- **Shared defaults**: Common default values used by multiple roles

## Current State

The utils domain currently uses role-specific variables and input configuration files. Domain-level variables are provided for future extensibility and Galaxy collection compliance.

## License

Apache License, Version 2.0
