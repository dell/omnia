# Deploy OpenLDAP role

## Overview

Deploys the `omnia_auth` OpenLDAP container on the OIM host when OpenLDAP
support is enabled. An already-running container is detected and left in
place.

## Responsibilities

- Load and validate the project-scoped OpenLDAP credentials.
- Create persistent configuration, certificate, data, and initialization
  directories.
- Generate the LDAP TLS certificate and configuration artifacts.
- Pull the configured `omnia_auth` image and install its Quadlet unit.
- Start the systemd-managed container and wait for it to reach the running
  state.
- Report a clear failure if any deployment step cannot complete.

## Role variables

Container settings, persistent paths, LDAP ports, TLS settings, retry values,
and messages are declared in `vars/main.yml`. The role also consumes the
resolved project directory, system address, domain name, and OpenLDAP feature
flag supplied by Orchestrator setup.

## License

Apache-2.0
