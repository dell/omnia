# precheck_environment

Performs read-only checks of the OIM environment before deployment or
provisioning.

## What It Does

- Checks whether `/etc/omnia/omnia.env` is installed.
- Cross-validates configured hostname, domain, management address, and data
  paths through `validate_system_environment`.
- Locates Image Build Manager `build_status.yml` for the active project.
- Checks functional-group image coverage when build results are available.
- Verifies referenced kernel artifacts in S3.
- Displays a consolidated per-check summary.

Missing environment and build-status artifacts are warnings in this role;
environment inconsistencies reported by the validation module remain failures.

## Requirements

- Local execution on the OIM/controller.
- Resolved environment and project facts from the calling setup workflow.
- Network access to S3 when image artifacts are validated.

## Role Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `system_env_file` | `/etc/omnia/omnia.env` | Installed environment file |
| `build_status_path` | Project-derived | Image Build Manager output checked by the role |

Messages are defined in `vars/main.yml`.

## Dependencies

No automatic dependency is declared in `meta/main.yml`.

## Example

```yaml
- hosts: localhost
  connection: local
  roles:
    - precheck_environment
```

## License

Apache-2.0
