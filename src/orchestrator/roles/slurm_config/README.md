# slurm_config

Builds and maintains Slurm controller, database, compute, login, and shared
filesystem configuration for the functional groups selected by Orchestrator.

## What It Does

1. Detects selected Slurm functional groups and reads their hostnames.
2. Resolves the active Slurm NFS/VAST paths and prepares shared directories.
3. Creates Slurm and Munge identities, keys, certificates, and configuration
   trees on shared storage.
4. Builds hardware-aware node definitions from user-provided homogeneous specs
   or parallel iDRAC discovery.
5. Merges shipped, generated, and user-provided `slurm.conf`,
   `slurmdbd.conf`, and `cgroup.conf` content.
6. Validates path overrides and creates their effective directories.
7. Detects removed or busy nodes and applies the configured drain/removal
   policy.
8. Publishes HPC tool, container, benchmark, UCX, OpenMPI, CUDA, and NVHPC
   assets required by generated cloud-init.
9. Backs up configuration when upgrading or changing a running cluster.

## Requirements

- Slurm control and compute/login functional groups resolved from the mapping.
- Active Slurm configuration in `omnia_config.yml`.
- Referenced NFS or VAST storage available on the OIM.
- Repository Manager artifacts and Pulp certificate for offline packages.
- BMC credentials when hardware specifications are discovered from iDRAC.
- SSH reachability to an existing controller when modifying a running cluster.

## Role Variables

See `vars/main.yml` and `defaults/main.yml`. Important caller-controlled values
include Slurm storage paths, custom configuration inputs, homogeneous discovery
settings, database configuration, node drain timeout/delay, force-removal
behavior, and enabled HPC tool features.

The role publishes controller, compute, login, group, mount, and generated
configuration facts used by Metadata Service templates.

## Modules Used

| Module | Purpose |
|--------|---------|
| `slurm_conf` | Parse, merge, validate, and write Slurm configuration |
| `bulk_discover_node_specs` | Discover node hardware through iDRAC in parallel |

## Dependencies

No automatic dependency is declared in `meta/main.yml`. The Slurm category
playbook runs setup, mapping, credential, mount, OpenLDAP, and OpenCHAMI
prerequisites before publication.

## Example

```yaml
- hosts: oim
  roles:
    - slurm_config
```

The supported lifecycle invocation is `orchestrator.yml --tags provision`.

## License

Apache-2.0
