# k8s_config

## Overview
Creates Kubernetes configuration files for the service cluster and stores them in NFS-shared storage.

## Purpose
- Generates Kubernetes manifests for cluster services
- Creates Helm chart values files
- Prepares ConfigMaps and Secrets for deployments
- Stores configurations in NFS for service cluster access

## Key Tasks
- **Create Config Directory**: Creates NFS directory structure for K8s configurations
- **Generate Manifests**: Creates Namespaces, RBAC, ConfigMaps, Secrets, Services, Deployments
- **Create Helm Values**: Generates Helm chart values files for services
- **Set Permissions**: Sets appropriate file permissions and ownership

## PowerScale CSI

PowerScale CSI is controlled only by `enable_powerscale_csi` on the
`service_k8s_cluster` entry whose `deployment` value is `true`:

```yaml
service_k8s_cluster:
  - cluster_name: service_cluster
    deployment: true
    enable_powerscale_csi: true
    csi_powerscale_driver_secret_file_path: "/path/to/secret.yaml"
    csi_powerscale_driver_values_file_path: "/path/to/values.yaml"
```

| Flag value | Behavior |
|------------|----------|
| Omitted or `false` | Skip CSI credential prompts, input validation, dependency staging, cloud-init script generation, and deployment |
| `true` | Require CSI credentials and input files, stage dependencies, and deploy CSI from the first Kubernetes control-plane node |

When enabled, the role resolves exactly one `csi-powerscale`, `helm-charts`,
and `external-snapshotter` artifact from `repo_status.yml` under
`file_repos.x86_64.git`. The catalog does not enable or disable CSI at
Orchestrator runtime.

## Requirements

- Kubernetes functional groups selected in the generated group configuration.
- Active service-cluster configuration and required NFS storage available.
- Repository Manager output and Pulp certificate for offline artifacts.
- PowerScale CSI inputs and credentials when CSI is enabled.

## Role Variables

See `vars/main.yml`; this role has no `defaults/main.yml`. Key caller facts
include `service_k8s_support`, Kubernetes version, NFS paths, offline artifact
paths, cluster node lists, and PowerScale CSI configuration.

## Dependencies

No automatic dependency is declared in `meta/main.yml`. The category playbook
runs setup, storage preparation, and credential loading before this role.

## Example

```yaml
- hosts: oim
  roles:
    - k8s_config
```

The supported lifecycle invocation is `orchestrator.yml --tags provision`.

## License

Apache-2.0
