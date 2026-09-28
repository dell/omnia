# test_creds.yml — Credentials Reference

Telemetry uses two separate encrypted credential stores. Test-runner access to
the OIM, OME, and SFM belongs in `test/telemetry/test_creds.yml`. Credentials
consumed by the Telemetry playbook belong in its runtime domain store. Do not
put either set of values in `test_config.yml` or a dataset.

## Test-runner credential fields

| Field | Required when | Description |
|-------|---------------|-------------|
| `oim_password` | Remote OIM uses password authentication | SSH password for `oim_ssh_user` |
| `ome_username` | `configure_ome: true` | OME REST API username |
| `ome_password` | `configure_ome: true` | OME REST API password |
| `pfx_secret` | Optional OME certificate flow | Password protecting the generated PFX file |
| `sfm_api_username` | `configure_sfm: true` | SFM API username |
| `sfm_api_password` | `configure_sfm: true` | SFM API password |
| `sfm_ssh_username` | `configure_sfm: true` | SFM SSH username |
| `sfm_ssh_password` | `configure_sfm: true` | SFM SSH password |

Create or update this store through the setup script so it is encrypted
immediately:

```bash
bash setup_env.sh --set-creds
bash setup_env.sh --update-creds
```

The interactive command always handles OIM SSH and prompts for OME or SFM only
when that integration is enabled in `test_config.yml`. For pipeline use, only
the OIM SSH password can be supplied on standard input:

```bash
printf '%s' '<OIM_SSH_PASSWORD>' | bash setup_env.sh --creds-stdin
```

If SSH key authentication is configured, `oim_password` may be omitted.

## Runtime domain credential fields

The separate `telemetry_credentials.yml` supports only these fields:

| Component | Fields |
|-----------|--------|
| iDRAC BMC | `bmc_username`, `bmc_password` |
| MySQL | `mysqldb_user`, `mysqldb_password`, `mysqldb_root_password` |
| PowerScale CSI | `csi_username`, `csi_password` |
| LDMS sampler | `ldms_sampler_password` |
| UFM | `ufm_username`, `ufm_password` |
| VAST | `vast_username`, `vast_password` |

Only fields required by enabled Telemetry components need values. Create or
update the store on the execution OIM:

```bash
bash setup_env.sh --set-domain-creds
bash setup_env.sh --update-domain-creds
```

For non-interactive use, pipe one JSON object containing the required fields:

```bash
credential-json-provider | bash setup_env.sh --domain-creds-stdin
```

The store is written beneath a non-empty `TELEMETRY_DATA_PATH`, or beneath
`$OMNIA_DATA_PATH/telemetry` otherwise, and requires `OMNIA_PROJECT_NAME`.

## Security

- `test_creds.yml` and `.test_creds.key` are local, encrypted test artifacts.
- The runtime credential file and its key are separate from the test store.
- Credential files, keys, backups, and lock files must not be committed or
  copied through project/dataset sync.
- Do not pass secret values as command-line arguments or edit encrypted YAML
  manually.
