# Discovery -- Troubleshooting

Run `./omnia.sh --run discovery --tags precheck` first to check the data path and OME reachability without loading credentials, and `--tags validate` to validate `discovery_config.yml` and `network_spec.yml`.

## Common issues

| Symptom (message) | Cause | Action |
|-------------------|-------|--------|
| `Invalid tag usage detected` / `Invalid tag combination detected` | Unsupported tag, or a combination other than `cleanup` + `cleanup_credentials` | Use one supported tag; see the README Tags table |
| `Discovery input directory does not exist` | Inputs were not staged for the active project | Create the directory (`sudo ./omnia.sh --init discovery` stages the templates) and populate `discovery_config.yml` and `network_spec.yml` |
| `Discovery configuration file is missing or is not a regular file` | `discovery_config.yml` absent or not a regular file | Restore the file and verify its YAML syntax |
| `OME endpoint configuration is incomplete. Required value: ome_ip` | `ome_ip` is not set | Set `ome_ip` to the reachable OME IPv4 address |
| `OME endpoint connectivity check failed` | OME is not reachable on HTTPS port 443 from the OIM within the timeout | Check routing, firewall, and the OME appliance, then re-run `--tags precheck` |
| `Failed to connect to OME` | Wrong credentials or a network problem | Verify the OME credentials and network connectivity |
| `Failed. Please provide valid credential for mandatory input.` | `ome_username` or `ome_password` left empty | Provide both values |
| `No servers found in OME inventory` | OME has no discovered or managed servers | Verify the servers are discovered and managed by OME |
| `Discovery configuration validation failed` | `discovery_config.yml` or `network_spec.yml` failed L1 schema or L2 checks | Read the errors in the validation log and fix the file |
| `Refusing Discovery cleanup because the resolved ... path exists but is not a regular directory` | The project output or log path is a file or link | Remove or fix the path manually, then re-run cleanup |
| `Invalid Discovery cleanup configuration` | `DISCOVERY_DATA_PATH` is not a safe absolute path, `OMNIA_PROJECT_NAME` is not a single path segment, or a cleanup flag is not boolean | Correct the variable or flag |

If servers fall into the default functional group, check the OME static group name against `<prefix>_rhel_<major>_<minor>_(x86_64|aarch64)`; the module warns for every invalid group.

## Log locations

| Log | Location |
|-----|----------|
| Top-level playbook | `/var/log/omnia/discovery/discovery.log` |
| Validation and runtime logs | `<DISCOVERY_DATA_PATH>/log/<project>/` (`discovery_validation_<project>.log`) |
| Status of the last run | `<DISCOVERY_DATA_PATH>/output/<project>/discovery_status.yml` |
