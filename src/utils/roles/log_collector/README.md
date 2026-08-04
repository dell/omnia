# log_collector

Collects system logs from various cluster nodes for troubleshooting and analysis.

## Description

This role gathers logs from Kubernetes masters/workers, Slurm controllers/compute nodes, and login nodes. It supports selective log collection based on node type and can bundle collected logs for easy transfer and analysis.

## Requirements

- SSH access to target nodes
- Sufficient disk space on control node for log storage
- Python 3.12+ on control node

## Role Variables

Available variables are listed below, along with default values (see `vars/main.yml`):

```yaml
# Collection stages and supported node types
log_collection_stages:
  - setup
  - prepare 
  - k8s_master
  - k8s_worker
  - slurm_ctl
  - slurm_node
  - login_node
  - login_compiler_node
  - bundle
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  gather_facts: false
  tags:
    - setup
    - prepare
  roles:
    - role: log_collector
      vars:
        stage: setup

- hosts: k8s_masters
  gather_facts: false
  ignore_unreachable: true
  roles:
    - role: log_collector
      vars:
        stage: k8s_master
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
