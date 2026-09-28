# validate_provisioning

Post-provisioning validation role. Verifies that expected nodes and
administrative interfaces are registered in SMD, functional groups have Boot
Service configurations and Metadata Service data, and generates a provisioning
report.

## Requirements

- At least one `provision_*.yml` playbook must have run successfully.
- OpenCHAMI services must be accessible.

## License

Apache-2.0
