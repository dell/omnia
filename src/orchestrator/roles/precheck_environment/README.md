# Precheck environment role

## Overview

Performs read-only checks of the OIM environment before Orchestrator proceeds
with deployment and provisioning operations.

## Responsibilities

- Check whether the system-wide `omnia.env` file is installed.
- Cross-validate the configured hostname, domain, management address, and data
  paths.
- Locate the Image Build Manager `build_status.yml` for the active project.
- Inspect functional-group image status when build results are available.
- Display a consolidated environment precheck summary.

Missing `omnia.env` and build-status artifacts are reported as warnings by the
current role implementation. Environment inconsistencies reported by the
validation module remain validation failures.

## Role variables

The environment-file path and warning messages are declared in
`vars/main.yml`. Resolved environment and project facts are supplied by
`orchestrator_setup`.

## License

Apache-2.0
