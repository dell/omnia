# validate_openchami

Validates the OpenCHAMI aggregate target, SMD API, Boot Service API, Metadata
Service API, TokenSmith, and certificate services before provisioning is
allowed to proceed. It also verifies that HAProxy has a usable certificate.
This role acts as the readiness gate between deployment and provisioning.

## Requirements

- OpenCHAMI must be deployed via `deploy_openchami.yml`.
- OpenCHAMI configuration and authentication facts must be available on the
  OIM host.

## Role Variables

| Variable | Purpose |
|----------|---------|
| `openchami_base_url` | Gateway URL derived from the OIM hostname and domain |
| `openchami_validate_certs` | Certificate-validation setting used by readiness requests |

Readiness endpoints and retry behavior are implemented in `tasks/main.yml`.

## Dependencies

No automatic dependency is declared in `meta/main.yml`. The deployment or
standalone validation preamble must authenticate first.

## Example

```yaml
- hosts: oim
  roles:
    - validate_openchami
```

The normal route is `orchestrator.yml --tags validate-deployment`.

## License

Apache-2.0
