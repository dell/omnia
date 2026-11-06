# Changelog

All notable changes to the `omnia.telemetry` collection will be documented in
this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-09-05

### Added
- Kustomize-oriented deployment flow for all telemetry components on
  Kubernetes.
- Selective sink deployment (`deploy_sinks` tag) for Kafka, VictoriaMetrics,
  and VictoriaLogs independently of source components.
- Granular per-source cleanup tags: `cleanup_idrac`, `cleanup_ldms`,
  `cleanup_ome`, `cleanup_powerscale`, `cleanup_ufm`, `cleanup_vast`.
- `cleanup_sinks` tag with dependency checking to prevent removing sinks that
  active sources depend on.
- Sink volume preservation by default during cleanup; `delete_sinks_volume=true`
  opt-in for full volume removal.
- `cleanup_credentials=false` and `cleanup_logs=false` options for selective
  cleanup retention.
- Kafka cluster and PVC identity recovery during redeployment to preserve
  topic data.
- External Kafka connection export (`external_kafka_connect`) with TLS
  certificates, bootstrap endpoints, and port details.
- External VictoriaMetrics/VictoriaLogs connection export
  (`external_victoria_connect`) with TLS CA, endpoints, and PowerScale syslog
  commands.
- VictoriaLogs deployment alongside VictoriaMetrics for log aggregation.
- LDMS version upgraded to 4.5.2 with RPM build scripts moved from utils to
  telemetry domain.
- LDMS RPM build infrastructure: `rpm_build/` directory with Podman-based
  Rocky Linux 10 build container and OVIS clone/build scripts.
- Container image registry override support for offline mode with private
  registries (#5486).
- RHEL 10.2 dynamic OS version support (#5434).
- PowerScale CSI driver upgraded to v2.18.0 and CSM components to v1.18.0
  (#5502).
- Telemetry and catalog package version updates (#5583).
- BMC group data validation module (`validate_bmc_group_data`).
- iDRAC IP management modules: `fetch_idrac_ips`, `insert_idracips_mysqldb`,
  `read_idracips_from_mysqldb`, `delete_idracips_from_mysqldb`.
- `enable_telemetry_service` and `disable_idrac_telemetry` modules for
  reconciliation-based source management.
- `idrac_telemetry_filter` module for iDRAC data filtering.
- `update_bmc_group_entry` module for BMC group management.
- `validate_input` and `validate_system_environment` modules for input and
  environment validation.
- `precheck` role with Kubernetes node, control-plane, worker, and pod health
  checks.
- `collect_telemetry_credentials` role with encrypted credential storage.
- `telemetry_setup` role with `omnia.env` loading, path derivation, and
  directory creation.
- Sampler config preparation delegated to Slurm control node with optimized
  node reachability (#5507).
- `domain-init.sh` with idempotent input staging and `--cleanup` mode.
- Input/output contract documentation (`docs/contracts/`).
- Domain design documentation (`docs/design.md`).

### Changed
- Galaxy version set to 2.3.0.
- Precheck runs automatically for default, `deploy`, and `execute` flows.
- Reconciliation-based source management: enabled/disabled sources are
  reconciled rather than blindly redeployed.
- Replaced all hardcoded `/opt/omnia` paths with `OMNIA_DATA_PATH` and
  `TELEMETRY_DATA_PATH` environment variables.
- Cleanup behavior aligned with cross-domain conventions.
- Kube-vip cleanup handling and messaging improved (#5273).
- Default inventory, BMC group, and Pulp path resolution logic fixed (#5295).
- OIM iDRAC IP variable removed from telemetry config (#5287).
- Precheck called every time telemetry playbook executes (#5289).

### Fixed
- BMC data path validation for iDRAC and Kafka identity preservation during
  cleanup (#5303).
- NFT test case flow logic and BMC group path default resolution (#5315).
- Catalog `base_os` group type renamed to `baseos` for consistency (#5585).

### Security
- Remediated CWE-78 (shell injection), CWE-94 (code injection), and
  clone-cache poisoning (CWE-494/CWE-349) in telemetry (#5597).
- Remediated shell injection, credential exposure, and LDAP TLS
  vulnerabilities (#5482).
- Callback plugin redacts sensitive keys from result dictionaries (#5604).
- Vaulted input reading operates in memory and reports validator errors
  completely (#5602).
- Tag and registry inputs validated in build scripts; credentials cleared from
  memory (#5600).
- LDMS build security hardening.
