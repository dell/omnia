# configure_ochami

Shared OpenCHAMI resource role containing group, Boot Service, Metadata
Service, inventory, and cloud-init templates used by Orchestrator.

The v2.3 provisioning pipeline is coordinated by `provision_common`, which
uses the templates and focused service tasks from this role while performing
SMD and Metadata Service reconciliation through `openchami_reconcile`.

## What It Does When Invoked Directly

- Refreshes the OpenCHAMI access token.
- Creates functional and common SMD groups.
- Resolves additional Metadata Service configuration.
- Configures Boot Service and Metadata Service content.
- Generates inventories and completion output.

## Requirements

- Deployed and reachable OpenCHAMI services.
- Functional groups and resolved mapping facts on `localhost`.
- OpenCHAMI configuration and TokenSmith authentication facts on the OIM.
- Boot image and cluster metadata facts prepared by the caller.

## Role Variables

Templates, OpenCHAMI work paths, service retry values, metadata group names,
and service constants are defined in `vars/main.yml`.

## Dependencies

No automatic dependency is declared in `meta/main.yml`. The role includes
`orchestrator_common` authentication tasks at runtime.

## Example

The supported top-level invocation runs the coordinated provisioning flow:

```bash
cd src/orchestrator/playbooks
ansible-playbook orchestrator.yml --tags provision
```

## License

Apache-2.0
