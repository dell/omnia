# orchestrator_credentials

Creates, validates, loads, and updates the project-scoped credential store used
by Orchestrator.

## What It Does

1. Creates the credential template and a root-owned Vault key when absent.
2. Recovers a plaintext credential file left by an interrupted run.
3. Loads existing values without printing secret content.
4. Prompts for missing or invalid provisioning credentials.
5. Collects conditional Slurm, OpenLDAP, and PowerScale CSI credentials only
   when those features are enabled.
6. Reloads the final values as facts and re-encrypts the file.
7. Skips repeated collection after credentials are loaded in the current run.

## Requirements

- Interactive input for credentials that are not already valid.
- `ansible-vault` available in the active Omnia environment.
- Project paths and feature flags established by `orchestrator_setup`.

## Role Variables

| Variable | Purpose |
|----------|---------|
| `credential_files` | Credential, Vault-key, template, and permission definitions |
| `orchestrator_credentials_definitions` | Mandatory and conditional credential fields |
| `orchestrator_credentials_loaded` | Prevent duplicate collection in one run |

Complete field rules and messages are in `vars/main.yml`.

## Outputs

```text
<ORCHESTRATOR_DATA_PATH>/input/<project>/orchestrator_credentials.yml
<ORCHESTRATOR_DATA_PATH>/input/<project>/.orchestrator_credentials_key
```

The credential file is Ansible Vault encrypted. Sensitive task output uses
`no_log`; summary output contains key names only.

## Dependencies

No automatic dependency is declared in `meta/main.yml`.

## Example

```yaml
- hosts: localhost
  connection: local
  roles:
    - orchestrator_credentials
```

The normal entry point is `orchestrator.yml --tags credentials` or
`orchestrator.yml --tags prepare`.

## License

Apache-2.0
