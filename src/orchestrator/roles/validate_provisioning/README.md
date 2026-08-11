# validate_provisioning

Post-provisioning validation role. Verifies that all expected nodes are registered in SMD, boot parameters are correctly configured in BSS, and generates a provisioning report.

## Requirements

- At least one `provision_*.yml` playbook must have run successfully.
- OpenCHAMI services must be accessible.

## License

Apache-2.0
