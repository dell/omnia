# deploy_openchami

Installs the OpenCHAMI 0.2.0 package, applies site-specific Fabrica
configuration, and starts the `openchami.target` services on the OIM host. The
deployment includes SMD and PostgreSQL, Boot Service, Metadata Service,
TokenSmith, local-CA and ACME certificate units, CoreSMD DHCP/DNS, and HAProxy.
Boot Service and Metadata Service replace the standalone BSS and
cloud-init-server services used by older OpenCHAMI layouts.

## Role Variables

See `vars/main.yml` for role constants. Cluster-specific values are supplied by
`orchestrator_setup` and the deployment playbook.

## License

Apache-2.0
