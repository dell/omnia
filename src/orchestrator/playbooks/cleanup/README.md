# Orchestrator Cleanup Framework

## Overview

Tag-based cleanup system for Omnia orchestrator components. Selectively cleanup individual components or perform full system cleanup.

## Quick Start

```bash
cd /root/dell/omnia/src/orchestrator

# Cleanup specific component
ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags slurm

# Cleanup multiple components
ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags slurm,k8s

# Full cleanup (all components, preserve credentials)
ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags cleanup

# Cleanup credentials only
ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags cleanup_credentials

# Full cleanup including credentials
ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags cleanup,cleanup_credentials
```

## Via Orchestrator Playbook

```bash
cd /root/dell/omnia/src/orchestrator

# Full cleanup (all components, preserve credentials)
ansible-playbook playbooks/orchestrator.yml --tags cleanup

# Cleanup credentials only
ansible-playbook playbooks/orchestrator.yml --tags cleanup_credentials

# Full cleanup including credentials
ansible-playbook playbooks/orchestrator.yml --tags cleanup,cleanup_credentials
```

**Note:** Cleanup is gated by a `when` condition and will only run when explicit cleanup tags are provided. It will NOT run when orchestrator.yml is called without tags.

## Available Tags

| Tag | Description |
|-----|-------------|
| `slurm` | Cleanup Slurm NFS data and configuration |
| `k8s` | Cleanup K8s NFS data and configuration |
| `storage_mounts` | Cleanup NFS mounts (all orchestrator-deployed) |
| `openchami` | Cleanup OpenCHAMI services, containers, and configs |
| `openldap` | Cleanup OpenLDAP service, container, and data |
| `artifacts` | Cleanup orchestrator deployment outputs and state |
| `credentials` | Cleanup orchestrator credential files (opt-in only) |
| `cleanup` | Cleanup all enabled components (excludes credentials) |

## Dry Run Mode

Test cleanup without making actual changes:

```bash
DRY_RUN=true ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags slurm
```

## NFS Server Cleanup

By default, cleanup deletes NFS server data for Slurm and K8s components. To preserve NFS server data, edit the component configuration:

```bash
# Edit Slurm component configuration
vi /root/catalog/omnia/src/orchestrator/roles/cleanup/components/slurm/vars/component_spec.yml

# Change cleanup_nfs_server to false:
slurm_config:
  cleanup_nfs_server: false
```

**Warning:** NFS server cleanup is destructive. Ensure you have backups before running cleanup.

## Troubleshooting

### Issue: "storage_config.yml not found"
**Solution:** Ensure `storage_config.yml` exists in your orchestrator input directory.

### Issue: Tasks not executing with tags
**Solution:** Ensure you're using the correct tag names from the Available Tags table.

### Issue: Permission errors
**Solution:** Run cleanup with appropriate permissions (root or sudo).
