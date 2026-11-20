# Changelog

All notable changes to the `omnia.orchestrator` collection will be documented
in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-09-05

### Added
- Ownership-aware Metadata Service reconciliation and persistent per-node
  metadata application status in `orchestrator_status.yml`.
- Persistent Service Tag-to-XNAME identity resolution through native SMD
  Hardware Inventory and a CA-verified `openchami_reconcile` Ansible module.
- Custom inventory (`-i`) support for `pxeboot.yml` playbook for BuildStream
  retry/resume (#432).
- Boot freshness check via `/proc/uptime` in phone-home verification.
- Race-free PXE failure collection using localhost loop over BMC hostvars.
- `verify_node_registration` tag for externally or hypervisor-booted node
  verification over SSH without iDRAC.
- `external_boot_verification` role for post-boot verification of manually
  booted nodes.
- `orchestrator_lifecycle_status` role for lifecycle status persistence and
  reconciliation.
- `orchestrator_node_topology` role publishing shared node and functional-group
  topology facts.
- `validate-deployment` tag for standalone OpenCHAMI and OpenLDAP service
  validation.
- `cleanup_credentials` standalone tag to remove only the Orchestrator
  credential file and vault key.
- Flexible functional-group lifecycle, discovery, and log collection
  (ER-ORCH-009) with `functional_group_config.yml` per-group configuration.
- Single `manage-functional-group` tag for add/remove/configure operations
  with boot/cloud-init/both publication scopes (HLD v13).
- Kubernetes HA settings merged into `omnia_config.yml` (#5452).
- OS version suffix enforcement in PXE functional group names
  (`<prefix>_rhel_<major>_<minor>_<arch>`) (#5484).
- RHEL 10.2 dynamic OS version support (#5434).
- Catalog-specified CUDA toolkit version per OS (#5477).
- IPv6 InfiniBand configuration with dual-stack, IPv6-only, and IPv4-only
  address modes.
- IPv6 subnet membership validation for InfiniBand addresses.
- IPv6 address normalization for duplicate detection across compressed and
  expanded representations.
- IPv6-conditional netmask validation in IB network configuration templates.
- CoreDNS and default hostname configuration changes.
- Additional subnet firewall trust zones for multi-subnet ORTE/MPI
  communication.
- Open MPI MCA parameter configuration for dynamic port ranges.
- `additional_images_collector` module for catalog-driven container image
  collection.
- `bulk_discover_node_specs` and `bulk_update_hosts` modules.
- `orchestrator_status_reconcile` module for lifecycle status reconciliation.
- `generate_argon2_password` module for provisioning password hashes.
- `node_boot_status` action plugin converting transient SSH failures into
  structured retryable results.
- Architecture, hardware-identity-mapping, troubleshooting, contract, and
  container documentation.
- OpenCHAMI service deployment and lifecycle management for SMD, Boot Service,
  Metadata Service, CoreDHCP, CoreDNS, and supporting service containers.
- OpenCHAMI release pinning and service-token renewal before provisioning.
- OpenCHAMI certificate generation, trust distribution, automatic renewal, and
  CA-verified API communication.
- Catalog-driven OpenLDAP deployment with TLS/SSL configuration and
  project-scoped credential handling.
- Slurm controller, compute, login, and NFS-node configuration from generated
  functional-group inventories.
- Slurm accounting, Munge, `slurmdbd`, MariaDB, and workload-manager service
  configuration.
- Slurm node-to-controller communication over the configured InfiniBand
  network, including IPv4, IPv6, and dual-stack address selection.
- Slurm configuration rendering through the `slurm_conf` module, including
  controller, partition, node, GRES, and memory settings.
- Kubernetes control-plane and worker-node bootstrapping with configurable
  bootstrap-token lifetime and optional local etcd storage.
- Service Kubernetes high-availability configuration with kube-vip and
  catalog-controlled component deployment.
- PowerScale CSI deployment, snapshotter integration, and secure temporary
  credential handling.
- Storage configuration for NFS, PowerScale, and VAST, including workload-aware
  OIM mount selection and shared mount preparation.
- Administration, BMC, and InfiniBand network validation and configuration.
- IPv4-only, IPv6-only, and dual-stack InfiniBand modes with normalized address
  comparison, subnet validation, and mode-aware Slurm `NodeAddr` selection.
- Bonding, VLAN, route, DNS, DHCP, NTP/chrony, firewall, and host identity
  configuration for provisioned clusters.
- CoreDNS enablement and hostname validation, including the supported
  `nid<digits>` node-hostname convention when DNS is enabled.
- Dedicated firewalld isolation for Podman interfaces and trusted-zone support
  for all configured administration subnets.
- Catalog-driven CUDA, UCX, Open MPI, DCGM, and additional container-image
  configuration.
- Configurable Open MPI ORTE port ranges and multi-subnet firewall rules.
- Image-driven provisioning using kernel, initrd, rootfs, and S3 data from
  Image Build Manager's `build_status.yml` contract.
- Repository and certificate consumption from Repository Manager's
  `repo_status.yml` contract.
- Boot Service session and configuration reconciliation for every selected
  functional group.
- Common and exact-group kernel-parameter and cloud-init publication through
  `functional_group_config.yml`.
- Additional validated cloud-init `write_files` and `runcmd` content.
- Inventory generation for Kubernetes, Slurm, login, BMC, and PXE workflows.
- Passwordless SSH distribution and validated `/etc/hosts` updates for managed
  nodes.
- Bulk hardware discovery and managed-host updates through dedicated Ansible
  modules.
- Dell iDRAC Redfish PXE boot orchestration with per-node retry handling.
- Configurable node-registration pauses, retries, delays, and completion
  verification.
- Structured provisioning, lifecycle, and PXE failure reports for automation
  and recovery.
- Component-aware cleanup for OpenCHAMI, OpenLDAP, Kubernetes, Slurm, storage
  mounts, generated artifacts, base state, and credentials.
- Selective cleanup, credential preservation, and guarded cleanup behavior for
  mounted or active workload data.
- Project-scoped input, output, state, report, credential, and log paths derived
  from `OMNIA_DATA_PATH`, `ORCHESTRATOR_DATA_PATH`, and `OMNIA_PROJECT_NAME`.
- L1 JSON Schema and L2 semantic validation for Orchestrator, network, storage,
  security, high-availability, functional-group, and PXE mapping inputs.
- Fail-closed lifecycle-tag validation and rejection of unknown or conflicting
  execution modes.
- PXE mapping permission, ownership, CSV-format, hostname, address, and
  command-injection validation.
- Callback output and validation-error redaction for credentials, mappings, and
  other sensitive values.
- Secure tmpfs-based Ansible Vault handling without persistent plaintext
  credential files.

### Changed
- Metadata Service InstanceInfo, Group, and ClusterDefaults resources are now
  updated in place with CA verification; stale Omnia-owned groups are removed
  only when they have no SMD members.
- Provisioning-password hashes now use a stable project-and-cluster salt so
  unchanged cloud-init stays idempotent; plaintext is supplied to OpenSSL over
  standard input rather than a process argument.
- Provision, validation, and PXE workflows consume only SMD-resolved
  identities; the PXE mapping does not contain XNAME values.
- Galaxy version set to 2.3.0.
- Node-registration timing and verification use the
  `enable_node_registration`, `node_registration_pause_minutes`,
  `node_registration_retries`, and `node_registration_delay` controls.
- Node completion is verified directly through SSH, boot freshness, and
  cloud-init status.
- Automatic NFS data cleanup disabled for K8s and Slurm (#5589).
- Slurm data cleanup gracefully skipped when mount is unmounted (#5492).
- Cleanup behavior aligned with cross-domain conventions.
- BuildStream pre- and post-PXE processing separated (#5567).
- Unsupported upgrade and rollback flows removed (#5446).

### Fixed
- Removed the invalid generic cloud-init phone-home fragment; Metadata Service
  reserves that route for optional WireGuard bootstrap peer removal.
- Boot Service now uses the NoCloud datasource name `nocloud`.
- Disabled root filesystem resize for the live overlay image and made Slurm
  tracking mounts and controller-marker waits explicit and bounded.
- Inventory generation `Recursive loop detected in template` -- renamed
  template var from `kube_vip` to `inventory_kube_vip` to avoid self-reference
  when fact is not set.
- `validate_preamble` OIM tasks fail with undefined `pxe_mapping_file_path` --
  resolve from localhost hostvars and add defensive `when` guards.
- `validate_preamble` playbook uses `roles:` which doesn't resolve OIM hostvars
  -- changed to `tasks:` with `include_role:` for proper variable resolution.
- Metadata-service configuration fails with `File not found: nodes_slurm.yaml`
  during K8s provisioning -- `nodes_yaml` forced to current category (#473).
- `generate_xname_in_mapping_file` module replaced pandas with Python stdlib
  `csv` module (#473).
- `symmetric_difference` NoneType error on `--tags provision` --
  `provision_preamble.yml` was missing the first-control-plane rename step
  (#472).
- K8s nodes receive random DHCP IPs instead of ADMIN_IPs when both K8s and
  Slurm catalogs are provisioned -- `delete_smd_endpoints.yml` no longer uses
  `--all` (#463).
- Stale phone-home detection: verify node boot time is after PXE start epoch
  (#461).
- `failed_nodes.json` wrong count due to `set_fact` + `delegate_to` race
  condition when multiple BMC hosts fail PXE boot simultaneously (#460).
- Orchestrator inventory includes `kube_vip_group` even for slurm-only
  clusters (#459).
- Provision report shows wrong `missing_nodes` by comparing GROUP_NAMEs
  against xnames (#458).
- Missing `configs_vars.yaml` pre-check causes unclear error during provision
  (#450).
- OS-versioned FG names (e.g. `slurm_control_node_rhel_10_0_x86_64`) fail
  metadata-service template lookup -- normalized template path.
- Fail-closed input validation for orchestrator configuration (#560792c).

### Security
- Remediated shell injection, credential exposure, and LDAP TLS
  vulnerabilities (#5482).
- Security hardening for functional-group configuration (ER-ORCH-009).
- Callback plugin redacts sensitive keys from result dictionaries (#5604).
- Security input validation and cleartext memory remediation (#5600).
- Validate tag/registry inputs in container build scripts.
