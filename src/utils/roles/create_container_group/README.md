# create_container_group

Creates container groups for Omnia infrastructure management.

## Description

This role creates and manages container groups required for Omnia's containerized infrastructure components. It handles OIM (Omnia Infrastructure Manager) group creation and container orchestration setup.

## Requirements

- Container runtime (Podman or Docker)
- Sufficient system resources for container orchestration
- Network access for container image pulls

## Role Variables

Available variables are listed below, along with default values (see `vars/main.yml`):

```yaml
# Container group configuration
oim_group: false
container_group_name: "omnia_containers"
group_network_mode: "bridge"
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: create_container_group
      vars:
        oim_group: true
        container_group_name: "oim_group"
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
