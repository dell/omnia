# generate_inventories

Generates Ansible inventory files from SMD-registered node data. Called after provisioning to produce `orchestrator_inventory.yaml` and `bmc_group_data.csv`.

## Requirements

- OpenCHAMI services must be running and accessible.
- Nodes must be registered in SMD before inventory generation.

## Role Variables

See `vars/main.yml` for configurable paths and defaults.

## License

Apache-2.0
