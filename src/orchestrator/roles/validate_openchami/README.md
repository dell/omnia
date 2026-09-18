# validate_openchami

Validates the OpenCHAMI aggregate target, SMD API, Boot Service API, Metadata
Service API, TokenSmith, and certificate services before provisioning is
allowed to proceed. It also verifies that HAProxy has a usable certificate.
This role acts as the readiness gate between deployment and provisioning.

## Requirements

- OpenCHAMI must be deployed via `deploy_openchami.yml`.

## License

Apache-2.0
