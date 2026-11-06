# Discovery -- Security

## Credentials

- OME credentials (`ome_username`, `ome_password`) are collected by the `credentials` tag and stored in `<DISCOVERY_DATA_PATH>/input/<project>/discovery_credentials.yml` with mode `0600`, Ansible Vault encrypted.
- The vault key is `<DISCOVERY_DATA_PATH>/input/<project>/.discovery_credentials_key`.
- `cleanup` removes the credential file and vault key; `-e cleanup_credentials=false` keeps them, and `--tags cleanup_credentials` removes only them.
- Tasks that handle credentials use `no_log` so values do not appear in Ansible output.

## Network access

Discovery connects to OME over HTTPS (port 443). The `precheck` tag and every discovery run verify TCP reachability first.

## Output handling

Values written to the PXE mapping CSV are sanitized by the `generate_pxe_mapping` module before they are written.

## Cleanup safety

`discovery_cleanup` refuses to run when `DISCOVERY_DATA_PATH` does not resolve to a safe absolute path, when `OMNIA_PROJECT_NAME` is not a single path segment, or when the project output or log path exists but is not a regular directory. Cleanup is limited to the selected project and preserves the output and log directories themselves; other files in the input project directory are never removed.
