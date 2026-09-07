# Module Utils

This directory contains shared Python utility modules for Ansible modules in the utils domain.

## Purpose

Module utils provide reusable Python functions and classes that can be imported by multiple Ansible modules. This promotes code reuse and maintainability across the domain.

## Structure

```
plugins/module_utils/
├── README.md
└── <utility_modules>/
```

## Usage

To use a module util in an Ansible module:

```python
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.omnia.utils.plugins.module_utils.<utility_name> import <function>
```

## Current State

The utils domain currently does not require custom module utilities as all functionality is implemented through standard Ansible modules and roles. This directory is provided for future extensibility and Galaxy collection compliance.

## License

Apache License, Version 2.0
