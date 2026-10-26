# Changelog

All notable changes to the `omnia.telemetry` collection will be documented in this file.

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
- LDMS deployment (`deploy_ldms` values template, `telemetry_packages.yml`,
  sample catalogs) now uses `docker.io/dellhpcomniaaisolution/ubuntu-ldms:1.2`.
- `rpm_build/build_rpm.sh` clones each OVIS version into
  `~/ovis-code/ovis-<version>` (previously a shared `~/ovis-code/ovis`, so
  `-v` with a new version silently rebuilt the old checkout), refuses a
  checkout at the wrong tag, and validates `-v`.
- `containers/build_images.sh` now builds and pushes the LDMS image as
  `ubuntu-ldms` (previously `ldms`) with default tag `1.2`, matching the image
  consumed by the LDMS deployment.


## [2.3.0] - 2026-09-05

### Changed
- Galaxy version set to 2.3.0.
