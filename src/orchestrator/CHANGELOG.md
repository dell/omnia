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

### Security
- Security hardening for functional-group configuration (ER-ORCH-009).
