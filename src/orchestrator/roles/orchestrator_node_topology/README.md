# orchestrator_node_topology

Builds shared node-topology facts from a generated OpenCHAMI `nodes.yaml`
artifact. The role publishes hostname, address, BMC, functional-group, and
Slurm category lists used by provisioning metadata and Slurm configuration.

## Requirements

- `nodes_yaml` identifies the generated node file to read.
- `target_category` identifies the caller's active provisioning category.
- The PXE mapping may be available through `hostvars['localhost']` to publish
  the hostname-to-hardware-group mapping.

## Outputs

The role preserves the established facts consumed by existing workflows,
including `ip_name_map`, `name_ip_map`, `ctld_list`, `cmpt_list`, `login_list`,
`compiler_login_list`, `controller_ip`, and the node-presence flags.

## License

Apache-2.0
