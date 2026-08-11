# validate_openchami

Validates that OpenCHAMI services (SMD, BSS, cloud-init) are running and healthy before provisioning is allowed to proceed. Acts as a readiness gate between deployment and provisioning.

## Requirements

- OpenCHAMI must be deployed via `deploy_openchami.yml`.

## License

Apache-2.0
