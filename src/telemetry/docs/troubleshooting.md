# Telemetry -- Troubleshooting

Use `./omnia.sh --run telemetry --tags validate` to validate input files and `--tags precheck` to check Kubernetes readiness (`kube_vip` connectivity, SSH access, and cluster state) without deploying.

## Common issues

| Symptom (message) | Cause | Action |
|-------------------|-------|--------|
| `Invalid tag usage detected` | Unsupported tag | Use a supported tag (one lifecycle tag at a time); see the README Tags section |
| `Failed to install Python kubernetes module` | The `kubernetes` Python module could not be installed in the configured `install_mode` (offline or online) | Follow the offline/online guidance in the message, or install the module in the Omnia virtual environment, then re-run |
| `Failed to decrypt or load ... telemetry_credentials.yml` | The vault key does not match, or the credential file is damaged | Verify `.telemetry_credentials_key` is the key for that file, or remove both files and re-run `--tags credentials` |
| `Telemetry credential file not found ... It will be created from template` | First run, or credentials were removed by `cleanup` | Provide the mandatory credentials when prompted; mandatory values cannot be left empty |
| Precheck fails on `kube_vip` or SSH | The service Kubernetes cluster is not reachable from the OIM | Confirm the cluster provisioned by Orchestrator is up and `kube_vip` in `telemetry_config.yml` is correct |
| A source is not deployed | It is not enabled in `telemetry_config.yml` (supported sources: `idrac`, `ldms`, `powerscale`, `ufm`, `vast`, `ome`) | Enable the source and re-run `--tags deploy` |
| Deploying only sinks | `deploy_sinks` needs the sink names | Pass `-e sinks=kafka,victoria_metrics,victoria_logs` (any subset) |
| External client cannot reach Kafka or VictoriaMetrics/VictoriaLogs | Connection details or certificates not shared with the client | Run `--tags external_kafka` or `--tags external_victoria` to print the endpoints and certificates |
| Sink data lost after `cleanup` | Sink volumes were deleted with `-e delete_sinks_volume=true` | By default `cleanup` preserves sink volumes and deletes source volumes; omit the flag to keep sink data |

## Log locations

| Log | Location |
|-----|----------|
| Top-level playbook | `/var/log/omnia/telemetry/telemetry.log` |
| Domain runtime logs | `$OMNIA_DATA_PATH/telemetry/log/<project>/` |
