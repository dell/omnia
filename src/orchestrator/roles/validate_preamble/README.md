# Validate preamble role

## Overview

Loads the persistent state required when deployment validation is run as a
standalone Orchestrator phase. The role reconstructs facts that would normally
have been established by earlier deployment or provisioning plays.

## Responsibilities

- Load and normalize the project network specification when network facts are
  not already available.
- Ensure the OpenCHAMI cluster hostname is present in `/etc/hosts`.
- Normalize the PXE mapping data without generating row-based XNAMEs. The
  validation play resolves permanent XNAMEs from SMD Hardware Inventory.
- Load the generated functional-group configuration.
- On the OIM host, load persisted OpenCHAMI configuration and establish the
  authentication and S3 facts used by readiness validation.

Most tasks are guarded so facts already set by an earlier lifecycle phase are
preserved. Standalone validation requires a previously completed deployment
and its persisted configuration artifacts.

## Role variables

The role consumes project paths, network facts, the PXE mapping path, and the
functional-groups configuration path established by `orchestrator_setup`.

## License

Apache-2.0
