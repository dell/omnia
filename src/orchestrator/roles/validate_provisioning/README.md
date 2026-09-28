# validate_provisioning

Post-provisioning validation role. Verifies that expected nodes and
administrative interfaces are registered in SMD, functional groups have Boot
Service configurations and Metadata Service data, and generates a provisioning
report.

## Requirements

- At least one `provision_*.yml` playbook must have run successfully.
- OpenCHAMI services must be accessible.

## Role Variables

| Variable | Purpose |
|----------|---------|
| `openchami_base_url` | OpenCHAMI gateway queried for validation |
| `functional_groups_config_path` | Expected functional-group definition |
| `orchestrator_output_dir` | Report and aggregate-state destination |

The role also consumes the resolved mapping, access token, CA certificate,
identity-change results, and Metadata Service change facts.

## Dependencies

No automatic dependency is declared in `meta/main.yml`. The validation
playbook resolves SMD identities and runs `generate_inventories` first.

## Example

```yaml
- hosts: oim
  roles:
    - validate_provisioning
```

## Outputs

| File | Purpose |
|------|---------|
| `provisioning_report.yml` | Registration, interface, group, boot, and metadata summary |
| `orchestrator_status.yml` | Persistent per-node provisioning and reprovision state |

## License

Apache-2.0
