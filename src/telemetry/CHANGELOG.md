# Changelog

All notable changes to the `omnia.telemetry` collection will be documented in
this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- Rebuilt the `dellhpcomniaaisolution/ubuntu-ldms` container image as tag `1.2`
  with updated Python dependencies:
  - pip 26.1.1 -> 26.2.0 (CVE-2026-13346, CVE-2026-8643)
  - setuptools 80.10.2 -> 83.0.0 (CVE-2026-59890)
  - pip is uninstalled from the final runtime image after installing runtime
    dependencies. pip >= 26.2 ships `pip/_vendor/bom.cdx.json`, which made its
    vendored certifi 2026.6.17, urllib3 2.7.0, msgpack 1.1.2 and setuptools
    (pkg_resources) 70.3.0 visible to Docker Scout (GHSA-6q48-6c7w-9gw2,
    CVE-2026-97687, CVE-2026-97688, CVE-2026-97689, GHSA-6v7p-g79w-8964,
    CVE-2026-57585, CVE-2025-47273, CVE-2026-59890). The rebuilt image scans
    with 0 vulnerabilities.
- Rebuilt the OVIS-ldms RPM on Rocky Linux 10.2 with pip 26.2.0 and
  setuptools 83.0.0 in the build environment.
- Rebuilt the iDRAC telemetry images `dellhpcomniaaisolution/kafkapump`,
  `victoriapump` and `idrac_telemetry_receiver` as tag `1.4` from
  iDRAC-Telemetry-Reference-Tools built with Go 1.26.10 and upgraded
  `golang.org/x/crypto` (v0.58.0), `golang.org/x/net` (v0.61.0),
  `golang.org/x/text` (v0.43.0), `golang.org/x/sys` (v0.49.0) and
  `github.com/klauspost/compress` (v1.20.3), resolving all HIGH/MEDIUM/LOW
  CVEs reported for tag `1.3` (e.g. CVE-2026-111943, CVE-2026-56854,
  CVE-2026-78669, CVE-2026-56851, CVE-2026-63209).
- Upgraded the `docker.io/library/busybox` support image from `1.36` to `1.38`.
- Hardened `rpm_build/ldms/build_ldms.rockylinux10.bash` (OMN-SEC #1161,
  finding 1389918491, CWE-78/CWE-73):
  - The generated-file cleanup loop is now NUL-delimited (`find -print0`,
    `read -r -d ''`, `rm -rf --`), so filenames with spaces, backslashes,
    glob characters or a leading `-` are handled safely.
  - `/usr/include/dcgm_api_export.h` is only patched if it exists and does not
    already define `DCGM_PUBLIC_API`; the build no longer creates or keeps
    appending to a system header.
  - Removed the unverified `epel-release-latest-10` download by URL;
    `epel-release` comes from the GPG-verified Rocky Linux repository.
  - `fpm` 1.15.1 and `dotenv` 2.8.1 are fetched from an explicit
    `https://rubygems.org` source and verified against pinned SHA-256 hashes
    before installation.
  - Fixed the `*.rpm` cleanup, which never matched, and quoted `$pkg_file`.

### Changed
- iDRAC telemetry deployment (`deploy_idrac_telemetry` defaults,
  `telemetry_packages.yml`, sample catalogs) now uses tag `1.4` for
  `kafkapump`, `victoriapump` and `idrac_telemetry_receiver`.
- busybox init/cleanup containers (Victoria templates, telemetry pod cleanup,
  `telemetry_packages.yml`, sample catalogs) now use `busybox:1.38`.
- `containers/build_images.sh` default tags for the iDRAC images are now
  `1.4` and the iDRAC-Telemetry-Reference-Tools commit is pinned to
  `d9890c54a333cdb5dae05ed45a7f1a0f2bac781f`; added an optional
  `idrac_telemetry_commit=` parameter to override it, and an existing
  `.idrac-telemetry-tools/` clone is now moved to the pinned commit instead of
  being reused at a stale commit.
- LDMS deployment (`deploy_ldms` values template, `telemetry_packages.yml`,
  sample catalogs) now uses `docker.io/dellhpcomniaaisolution/ubuntu-ldms:1.2`.
- `rpm_build/build_rpm.sh` clones each OVIS version into
  `~/ovis-code/ovis-<version>` (previously a shared `~/ovis-code/ovis`, so
  `-v` with a new version silently rebuilt the old checkout), refuses a
  checkout at the wrong tag, and validates `-v`.
- `rpm_build/build_rpm.sh` default OVIS LDMS version is now `4.5.3`
  (previously `4.5.2`).
- `containers/build_images.sh` now builds and pushes the LDMS image as
  `ubuntu-ldms` (previously `ldms`) with default tag `1.2`, matching the image
  consumed by the LDMS deployment.


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
- Domain architecture documentation (`docs/architecture.md`).

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
