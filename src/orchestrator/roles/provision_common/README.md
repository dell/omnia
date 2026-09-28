# provision_common

Common provisioning role shared by all category-specific provisioning playbooks
(`provision_kubernetes.yml`, `provision_slurm.yml`, `provision_os.yml`,
`provision_custom.yml`). Handles SMD node registration, Boot Service
configuration, Metadata Service data, DNS setup, and SELinux context
management.

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

The PXE mapping does not supply XNAME. During registration,
`openchami_reconcile` resolves each Service Tag from SMD Hardware Inventory.
Existing mappings are reused; an existing SMD node without a Service Tag
binding may be resolved from consistent admin/BMC MAC evidence; and a new
server receives the first free
Node/NodeBMC XNAME pair. The new Service Tag-to-XNAME relationship is written
to SMD before discovery and then published to every downstream task. CSV row
position never controls persistent identity.

Metadata Service resources are reconciled in place through the same
CA-verified API client. Omnia labels the InstanceInfo, Group, and
ClusterDefaults resources it owns, updates existing resources by UID, and
reduces duplicate ClusterDefaults records to one verified canonical
UID. It deletes a stale owned group only when it is absent from the complete desired
configuration and has no SMD members. Provisioning records nodes whose
metadata changed as `reprovision_required`; only successful PXE and cloud-init
verification clears that state. Rendered cloud-init files are restricted to
the root account because they may contain credentials or private keys. The
provisioning-password hash uses a stable project-and-cluster salt and receives
the plaintext through standard input, preventing unchanged runs from creating
false metadata drift or exposing the password in a process argument.

Kubernetes and Slurm Metadata Service templates resolve NFS and VAST paths only
from storage names declared in `omnia_config.yml` and matching entries in
`storage_config.yml`. Provisioning fails before publishing cloud-init when a
reference is missing, duplicated, or incomplete; no hardcoded mount-path
fallback is used.

## Requirements

- OpenCHAMI services must be deployed and healthy.
- `functional_groups_config.yml` must be generated.

## Role Variables

See `vars/main.yml` for configurable paths, retry settings, and defaults.

Key caller variables are `target_category`, `target_functional_groups`,
`target_fg_names`, and `provision_common_registration_complete`.

## Dependencies

No automatic dependency is declared in `meta/main.yml`. The provision preamble
must establish project inputs, credentials, OpenCHAMI authentication, S3
configuration, functional groups, and the OIM inventory host.

## Example

```yaml
- hosts: oim
  roles:
    - role: provision_common
      vars:
        target_category: os
        target_functional_groups: "{{ os_functional_groups }}"
        target_fg_names: "{{ os_functional_groups | map(attribute='name') | list }}"
```

Category playbooks are the supported callers; use
`orchestrator.yml --tags provision` for the complete flow.

## License

Apache-2.0
