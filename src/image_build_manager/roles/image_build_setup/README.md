# image_build_setup

Setup role that runs first (tag: `always`). Loads configuration, validates environment, checks prerequisites, and sets up project directories.

## Requirements

- Valid `omnia.env` sourced (system environment variables)
- Python 3.12+, Ansible 2.20+

## Role Variables

See `defaults/main.yml` and `vars/main.yml` for the full list.

## Dependencies

None (this is the first role to run).

## Example

```yaml
- hosts: localhost
  roles:
    - image_build_setup
```
