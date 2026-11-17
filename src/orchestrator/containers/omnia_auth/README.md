# Omnia Authentication Container

Container image used by Orchestrator to provide the optional OpenLDAP
authentication service on the OIM.

## Base Image

`cgr.dev/chainguard/wolfi-base`

## Contents

- OpenLDAP 2.7 server and client tools
- MDB, LDAP, and Meta backends
- CA certificate bundle
- Non-login `ldap` runtime user and group with fixed ids (`LDAP_UID` and
  `LDAP_GID` build arguments, default 55)
- Persistent OpenLDAP data directory

## Files

| File | Description |
|------|-------------|
| `Containerfile` | Wolfi-based OpenLDAP runtime image |
| `entrypoint.sh` | Container entrypoint: initializes the directory, verifies the mounted TLS certificate (validity, key match, self-signed or signed by the CA in `LDAP_TLS_CA_FILE`, optional `LDAP_TLS_CERT_SHA256` pin), then starts `slapd` as `ldap` |

Runtime `slapd.conf`, bootstrap LDIF, and TLS certificates are not embedded in
the image. The `deploy_openldap` role renders and bind-mounts them through the
`omnia_auth` Podman Quadlet.

## Building

The normal deployment workflow pulls the published image. The developer build
helper can build it locally or publish it with Docker Buildx:

```bash
cd src/orchestrator/containers

# Local Podman build: omnia_auth:1.3
./build_images.sh

# Local Docker build with a custom tag
./build_images.sh build_tool=docker auth_tag=<tag>

# Publish with provenance and SBOM
./build_images.sh build_tool=docker build_action=push \
  registry=<registry> auth_tag=<tag>
```

`build_action=push` is supported only with Docker. The default registry is
`docker.io/dellhpcomniaaisolution`.

## Runtime

The container:

- exposes LDAP on port 389 and LDAPS on port 636;
- persists directory data under `/var/lib/openldap/openldap-data`;
- initializes the directory once from `/container-init/bootstrap.ldif`;
- starts as root only to initialize the directory, verify the certificate, and
  bind ports 389 and 636, then runs `slapd` as the `ldap` user (`-u ldap -g ldap`);
- refuses to start when the certificate or private key is not readable by the
  `ldap` group; and
- uses `ldapwhoami` for its health check.

The deployed image, tag, volumes, ports, and service lifecycle are controlled
by `roles/deploy_openldap/`. Do not place credentials or private keys in the
container build context.

## License

Apache License, Version 2.0
