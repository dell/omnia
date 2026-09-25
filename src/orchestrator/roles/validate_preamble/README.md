# Validate preamble role

## Overview

Loads the persistent state required when deployment validation is run as a
standalone Orchestrator phase. The role reconstructs facts that would normally
have been established by earlier deployment or provisioning plays.

## Responsibilities

- Load and normalize the project network specification when network facts are
  not already available.
- Ensure the OpenCHAMI cluster hostname is present in `/etc/hosts`.
- Normalize the PXE mapping data. The validation play resolves permanent
  XNAMEs from SMD Hardware Inventory.
- Load the generated functional-group configuration.
- On the OIM host, load persisted OpenCHAMI configuration and establish the
  authentication and S3 facts used by readiness validation.

Most tasks are guarded so facts already set by an earlier lifecycle phase are
preserved. Standalone validation requires a previously completed deployment
and its persisted configuration artifacts.

## Requirements

- Existing Orchestrator project input and generated functional-group output.
- Deployed OpenCHAMI configuration on the OIM.
- Valid PXE mapping and network specification.

## Role Variables

The role consumes project paths, network facts, the PXE mapping path, and the
functional-groups configuration path established by `orchestrator_setup`.

## Dependencies

No automatic dependency is declared in `meta/main.yml`. The standalone
validation playbook invokes `orchestrator_setup` before this role.

## Example

```yaml
- hosts: localhost
  connection: local
  roles:
    - validate_preamble
```

## License

Apache-2.0
