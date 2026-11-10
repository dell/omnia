# ome_discovery

Runs the OME discovery pipeline and writes the Discovery output artifacts.

## What it does

In order:

1. Verifies OME HTTPS connectivity (`discovery_common` / `check_ome_connectivity.yml`).
2. Loads the OME credentials (`get_ome_credentials.yml`).
3. Collects server inventory from OME (`collect_inventory.yml`).
4. Generates the PXE mapping (`generate_pxe_mapping.yml`).
5. Generates the BMC discovery report (`generate_discovery_report.yml`).
6. Writes `discovery_status.yml` with `overall_status`, the mapping file path, and the number of servers discovered. On any failure it writes a failed status and stops with the failure message.

## Outputs

Written to `$DISCOVERY_DATA_PATH/output/<project>/`: `bmc_pxe_mapping_file_<timestamp>.csv` (with a `bmc_pxe_mapping_file.csv` symlink to the latest), `bmc_discovery_report_<timestamp>.csv`, and `discovery_status.yml`. See the [output contract](../../docs/contracts/output-contract.md).

## Variables

`defaults/main.yml` sets the hostname generation defaults (`hostname_prefix`, `hostname_start_number`, `hostname_padding`) and the default group name. The default functional group applied to servers without a valid OME static group is defined in the `generate_pxe_mapping` module (`slurm_node_rhel_10_0_aarch64`); a valid OME static group follows `<prefix>_rhel_<major>_<minor>_(x86_64|aarch64)`.

## License

Apache-2.0
