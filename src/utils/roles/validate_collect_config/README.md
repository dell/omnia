# validate_collect_config

Validates `collect_pxe.yml` before cluster log collection runs.

## What it does

- Resolves the config path as `<input_project_dir>/collect_pxe.yml` (falling back to `$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME`) and fails if the file is missing.
- Validates every top-level key as a functional group name: `<role>_<arch>` with an optional OS/version segment before the architecture (for example `slurm_node_aarch64` or `slurm_node_rhel_10_0_aarch64`).
  - Roles: `service_kube_control_plane_first`, `service_kube_control_plane`, `service_kube_node`, `slurm_control_node`, `slurm_node`, `login_node`, `login_compiler_node`.
  - Architectures: `x86_64`, `aarch64`.
- Validates that IP addresses are valid IPv4 and that at least one functional group contains an address.
- Reports the groups found and the total IP count.

## Used by

`playbooks/utils.yml`, when the `collect` tag is run.

## License

Apache-2.0
