# Orchestrator credentials role

## Overview

Creates, loads, and updates the credentials owned by the Orchestrator domain.
Credentials are stored in a project-scoped Ansible Vault file and are exposed
as facts for downstream Orchestrator roles during the current playbook run.

## Responsibilities

- Create the credential file and vault key when they do not exist.
- Recover and encrypt a plaintext credential file left by an interrupted run.
- Prompt for mandatory credentials that are missing or no longer satisfy the
  current validation rules.
- Collect conditional credentials for enabled Slurm, OpenLDAP, and PowerScale
  CSI functionality.
- Reload the final values and re-encrypt the credential file.
- Skip repeated collection after credentials are loaded in the current run.

Sensitive credential values are loaded with `no_log: true`. The role reports
only the names of available credential keys, never their values.

When a stored value is invalid, the role requests a replacement through the
same confirmation and update flow used for a missing value. The credential
file is decrypted only for the update and is re-encrypted before the role
continues.

## Role variables

Credential paths, field definitions, and user-facing messages are declared in
`vars/main.yml`. The role relies on project paths and feature flags established
by `orchestrator_setup`.

## License

Apache-2.0
