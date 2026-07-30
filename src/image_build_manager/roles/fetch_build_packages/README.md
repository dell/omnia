# fetch_build_packages

Collects and resolves RPM packages required for OS image building from configured repositories and package JSON files.

## Requirements

- Network access to RPM repositories (or local Pulp mirror)
- Valid `repo_status.yml` with repository URLs

## Role Variables

See `vars/main.yml` for the full list.

## Dependencies

- `image_build_setup` — environment and config loading

## Example

```yaml
- hosts: localhost
  roles:
    - fetch_build_packages
```
