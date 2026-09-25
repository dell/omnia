# deploy_openchami

Installs or refreshes the OpenCHAMI 0.2.0 Fabrica deployment and starts the
`openchami.target` services on the OIM.

## What It Does

1. Detects an existing OpenCHAMI installation and validates its state.
2. Checks deployment prerequisites and required input files.
3. Installs OpenCHAMI when it is absent.
4. Renders site-specific network and service configuration.
5. Configures firewall, hosts, packages, HAProxy, TokenSmith, and certificates.
6. Starts and verifies the aggregate OpenCHAMI target.
7. Refreshes network configuration when an installation already exists.

The deployment includes SMD and PostgreSQL, Boot Service, Metadata Service,
TokenSmith, local CA/ACME units, CoreSMD DHCP/DNS, and HAProxy.

## Requirements

- Supported EL-based OIM with root privileges, Podman, and systemd.
- Valid `network_spec.yml` and `orchestrator_config.yml`.
- Repository access to the OpenCHAMI package and required container images.
- OIM, project, data-path, hostname, domain, and network facts established by
  `orchestrator_setup`.

## Role Variables

See `vars/main.yml`; this role has no `defaults/main.yml`. Key internal values
cover the OpenCHAMI shared/configuration paths, package version, service ports,
container images, certificate paths, and readiness retry settings.

## Dependencies

No role dependency is declared in `meta/main.yml`. The deployment playbook
configures S3 access and setup context before invoking the role.

## Example

```yaml
- hosts: oim
  become: true
  roles:
    - deploy_openchami
```

The normal invocation is `orchestrator.yml --tags prepare` or `--tags deploy`.

## License

Apache-2.0
