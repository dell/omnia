# Orchestrator -- Security

## Credentials

- Orchestrator credentials are collected by the `credentials` tag and stored in `<input project dir>/orchestrator_credentials.yml` with mode `0600`, Ansible Vault encrypted, with the vault key in `.orchestrator_credentials_key` in the same directory.
- `cleanup` removes the credential file and vault key by default; `-e cleanup_credentials=false` keeps them, and `--tags cleanup_credentials` removes only them.
- Tasks that handle credentials use `no_log`.

## Provisioning passwords

Provisioning-password hashes use a stable project-and-cluster salt so unchanged cloud-init stays idempotent. Plaintext is supplied to OpenSSL over standard input rather than as a process argument.

## OpenCHAMI services

Metadata Service resources are reconciled in place with CA verification of the OpenCHAMI APIs (`openchami_reconcile`). See [Troubleshooting](troubleshooting.md) for authentication and TLS validation failures.
