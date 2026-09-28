# test_config.yml — Configuration Reference

`test_config.yml` contains the non-sensitive settings used by Telemetry FVT,
NFT, and UT reporting. Edit it from `test/telemetry/` before running a suite.

## Execution modes

### Local mode

Leave `oim_server_ip` empty to run tests and playbooks on the current OIM:

```yaml
oim_server_ip: ""
```

`clone_path` remains required by configuration validation, but project sync is
not performed in local mode.

### Remote mode

Set the target OIM address and connection details:

```yaml
oim_server_ip: "<target_ipv4>"
oim_ssh_user: root
oim_ssh_port: 22
clone_path: "/root/monorepo/omnia"
```

The framework connects over SSH, stages a credential-free copy of the local
checkout, and synchronizes it to `clone_path`. Password-based SSH uses
`oim_password` from the encrypted `test_creds.yml`; key-based SSH may be used
without that field.

## Fields

### Target and project sync

| Field | Required | Description | Template value |
|-------|----------|-------------|----------------|
| `oim_server_ip` | Yes | Target OIM IPv4 address. Empty selects local mode. | `""` |
| `oim_ssh_user` | Remote mode | SSH user for the target OIM. | `root` |
| `oim_ssh_port` | No | SSH port for the target OIM. | `22` |
| `clone_path` | Yes | Absolute destination for the staged checkout in remote mode. | `/root/monorepo/omnia` |

### Dataset and input sync

| Field | Required | Description | Template value |
|-------|----------|-------------|----------------|
| `dataset` | No | Name below `datasets/`; empty selects canonical `src/telemetry/input/` when syncing. | `""` |
| `sync_telemetry_input` | No | Copy the selected input directory to the target before the session. | `false` |

With input sync disabled, tests use the input already present on the execution
OIM. With sync enabled, the destination is
`<effective Telemetry data root>/input/$OMNIA_PROJECT_NAME/`, where the root is
a non-empty `TELEMETRY_DATA_PATH` or `$OMNIA_DATA_PATH/telemetry` otherwise.
A named dataset must contain an `input/` directory. Project synchronization
excludes credentials, Vault keys, backups, and lock files. Dataset input sync
copies the selected `input/` directory as provided, so never place secret or
Vault artifacts in a dataset.

### OME integration

| Field | Required | Description | Template value |
|-------|----------|-------------|----------------|
| `ome_ip` | When OME configuration tests are enabled | OME appliance IPv4 address used by its REST API tests. | `""` |
| `configure_ome` | No | Enables certificate, forwarder, Kafka-data, and Victoria-data integration tests. | `true` |
| `ome_identifier` | No | Identifier applied to OME Kafka topics and forwarding configuration. | `ome` |
| `force_external_kafka_playbook` | No | Regenerate the external Kafka certificate export even when valid artifacts exist. | `false` |

When `configure_ome` is true, add `ome_username` and `ome_password` to the
encrypted test credential store. `pfx_secret` is optional.

### SFM integration

| Field | Required | Description | Template value |
|-------|----------|-------------|----------------|
| `configure_sfm` | No | Enables SFM API and SSH integration tests. | `false` |
| `sfm_api_ip` | When SFM is enabled | SFM API IPv4 address. | `""` |
| `sfm_api_port` | When SFM is enabled | SFM API port in the range 1–65535. | `443` |
| `sfm_ssh_ip` | When SFM is enabled | SFM SSH IPv4 address. | `""` |
| `sfm_ssh_port` | When SFM is enabled | SFM SSH port in the range 1–65535. | `22` |
| `force_external_victoria_playbook` | No | Regenerate exported Victoria connection data and force SFM certificate rotation. | `false` |

When `configure_sfm` is true, both endpoint addresses and all four SFM fields
in `test_creds.yml` are required. SSH host keys must already be trusted.

### Reports

| Field | Required | Description | Template value |
|-------|----------|-------------|----------------|
| `report_path` | Yes | Output directory for JSON and HTML reports; spaces are not allowed. | `/opt/omnia/reports` |
| `report_name` | Yes | Base report name containing only letters, numbers, `_`, or `-`. | `telemetry_test_report` |
| `report_id` | No | Reserved configuration field. Current report creation takes its ID from the runner's `REPORT_ID` environment variable. | `""` |

## Credentials

Do not place passwords in `test_config.yml`. Test-runner access credentials
belong in the local encrypted `test_creds.yml`; playbook/runtime Telemetry
credentials belong in the separate encrypted domain store. See
[test_creds.md](test_creds.md).

## Batch overrides

`./run_validation.sh --config` can override `dataset` and
`sync_telemetry_input` for a scenario through `test_run_config.yml`. See
[test_run_config.md](test_run_config.md).
