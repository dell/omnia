# provision_common

Common provisioning role shared by all category-specific provisioning playbooks (`provision_kubernetes.yml`, `provision_slurm.yml`, `provision_os.yml`, `provision_custom.yml`). Handles SMD node registration, BSS boot parameters, cloud-init configuration, DNS setup, and SELinux context management.

Kubernetes and Slurm provisioning use two explicit phases:

1. `registration.yml` registers nodes and initializes functional-group facts.
2. The category playbook prepares OIM storage and bolt-on content, generates
   node mount and swap cloud-init data, and then invokes the role normally to
   publish the completed Boot Service and Metadata Service configuration.

Set `provision_common_registration_complete: true` only for the publication
invocation after `registration.yml` has completed. This prevents publication
from preceding shared-storage preparation.

Shared OpenCHAMI provisioning data is reset once by
`provision_preamble.yml`. Category registration is additive, so Kubernetes,
Slurm, OS-only, and custom nodes, interfaces, groups, and Boot Service
configurations coexist after a complete provision run.

## Requirements

- OpenCHAMI services must be deployed and healthy.
- `functional_groups_config.yml` must be generated.

## Role Variables

See `vars/main.yml` for configurable paths, retry settings, and defaults.

## License

Apache-2.0
