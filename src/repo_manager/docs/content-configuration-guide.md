# Content Configuration Guide

## Overview

The catalog is the source of truth for content selection. Each catalog package
declares its type and one or more sources. Repo Manager maps those sources to
RPM repositories or container registries in `repo_manager_config.yml`.

**Catalog location**: Exact `.json` file from `CATALOG_FILE_PATH`

**Repository configuration**:
`<REPO_MANAGER_DATA_PATH>/input/<project>/repo_manager_config.yml`

---

## Resolution Flow

```text
functional layer -> group -> package -> source
                                      |      |
                                      |      +--> registry -> public/configured registry
                                      +---------> reponame -> version + arch repository
                                                     |
                                                     +--> Pulp content
```

Only packages reachable from selected functional layers and groups are processed.
The source's OS version and architecture determine which repository definition is
used.

## Catalog Package Structure

### RPM Example

```json
{
  "bash": {
    "name": "bash",
    "packagetype": "rpm",
    "sources": [
      {
        "architecture": "x86_64",
        "name": "rhel",
        "version": ["10.0"],
        "reponame": "baseos"
      }
    ]
  }
}
```

This resolves to:

```yaml
repositories:
  "10.0":
    x86_64:
      baseos: {}
```

### Container Image Example

```json
{
  "registry_k8s_io/kube_controller_manager": {
    "name": "registry.k8s.io/kube-controller-manager",
    "packagetype": "image",
    "tag": "v1.35.1",
    "sources": [
      {
        "architecture": "x86_64",
        "registry": "registry.k8s.io",
        "name": "rhel",
        "version": ["10.0"]
      }
    ]
  }
}
```

`registry.k8s.io` is a known public registry, so a `registries` entry is not
required unless custom authentication or TLS settings are needed.

---

## Supported Content Types

| `packagetype` | Required package fields | Source mapping | Pulp plugin |
|---------------|-------------------------|----------------|-------------|
| `rpm` | `name` | `reponame` | RPM |
| `rpm_repo` | `name` | `reponame` | RPM |
| `rpm_file` | `name` and direct source | `reponame` when applicable | RPM |
| `image` | `name`, `tag` | `registry` | Container |
| `pip_module` | `name` with optional exact `==version`, or separate `version` | package source | Python |
| `tarball` | `name`, `version` | URL/source metadata | File |
| `manifest` | `name`, `version` | URL/source metadata | File |
| `git` | `name`, version/ref | URL/source metadata | File |
| `iso` | `name`, `version` | URL/source metadata | File |
| `shell` | `name`, `version` | URL/source metadata | File |
| `ansible_galaxy_collection` | collection name, version | Galaxy source | File |

Python packages may use either `name: "cffi==1.17.1"` or the equivalent
`name: "cffi"` with `version: "1.17.1"`. Repo Manager canonicalizes both to
`cffi==1.17.1` for download, Pulp identity, status tracking and selective
cleanup. When both forms provide a version, the values must match.

Python downloads always target the selected node context. For RHEL 10 this
means CPython 3.12 (`cp312`) plus the selected `x86_64` or `aarch64` manylinux
platforms. If no compatible wheel exists, Repo Manager permits only an
explicit source-distribution download with dependency resolution disabled; it
never retries using the OIM host interpreter or architecture.

## Verified cross-version artifact reuse

Public Pulp repositories, distributions, base paths, status rows, and log paths
remain OS-version qualified. Internally, Repo Manager can avoid a second source
transfer when the prior bytes are still provably identical:

| Type | Reuse proof and compatibility boundary |
|------|----------------------------------------|
| `manifest` | Matching strong HTTP validator and SHA-256; OS-version and architecture independent |
| URL `tarball` | Matching strong HTTP validator and SHA-256; reusable only for the same architecture |
| Local `tarball` | Exact source digest and SHA-256; reusable only for the same architecture |
| `git` | Exact remote branch/tag resolved to an immutable commit, plus archive SHA-256; OS-version and architecture independent |
| `shell` | Matching strong HTTP validator and SHA-256; OS-version and architecture independent |
| `ansible_galaxy_collection` | Exact collection and version plus SHA-256; OS-version and architecture independent |
| `iso` | Exact local digest or matching strong HTTP validator plus SHA-256; reusable only for the same architecture |
| `pip_module` | Exact pinned requirement, target Python ABI compatibility, wheel-platform compatibility, and SHA-256 |
| `image` | One Pulp container repository and layer set per image source; readiness is verified for every requested architecture |
| `rpm`, `rpm_repo`, `rpm_file` | Not shared across OS-version or architecture repository contexts |

Universal `none-any` wheels and source distributions may be reused across
architectures for the same target Python. Compiled wheels remain isolated by
architecture. Unpinned Python requirements are always downloaded normally.
Missing, corrupt, stale, or unverifiable cache state disables reuse and cannot
make a Pulp endpoint ready; the normal processor path is used instead.
When an exact File or Python content digest already exists in Pulp, Repo Manager
associates that content with the new version-qualified repository instead of
uploading the same bytes again. The repositories, distributions, and endpoint
URLs remain separate; only Pulp's immutable content blob is shared.
For containers, every catalog context retains its own status row, but a second
compatible context reuses the already synchronized tag and distribution instead
of downloading the image layers again.

### rpm and rpm_repo

| Type | Behavior |
|------|----------|
| `rpm` | Validate or synchronize the named RPM according to repository policy |
| `rpm_repo` | Use DNF to download the named package plus dependencies, then make them available through Pulp |

An `rpm_repo` item may not explicitly declare `policy: never`. Other
policy/caching combinations follow the effective-policy table; a `streamed`
result selects validation-only handling.

### Multiple Tags for One Image

The same image name can appear with multiple tags:

```text
docker.io/victoriametrics/operator:v0.68.3
docker.io/victoriametrics/operator:config-reloader-v0.68.3
```

Both tags use one Pulp container repository but remain separate catalog, status
and mirror identities. Synchronizing or cleaning one tag does not remove its
sibling tag.

Before a tag or digest is treated as ready, Repo Manager reads its Pulp OCI
manifest metadata. A direct manifest must match the selected architecture
(`amd64` for `x86_64`, `arm64` for `aarch64`); a multiarch index must contain a
matching Linux child. Missing, incompatible, or unreadable platform metadata
cannot make the context successful.

---

## RPM Repository Mapping

The lookup key is:

```text
catalog source version + architecture + reponame
```

Example:

```yaml
repositories:
  "10.0":
    x86_64:
      epel:
        url: "https://download.example.com/epel/10/Everything/x86_64/"
        gpgkey: "https://download.example.com/keys/RPM-GPG-KEY-EPEL-10"
        policy: partial
        caching: true
        priority: 99
```

### Subscription and Explicit Repository Sources

Repo Manager first resolves the RPM repositories referenced by the selected
catalog functional layers. It then applies the repository-source rules only to
those repositories and selected architectures. Unused repository entries,
architectures and version sections do not become download requirements.

The only repositories eligible for RHEL subscription discovery are the exact
names `baseos`, `appstream` and `codeready-builder`. Every other referenced
repository requires a non-empty explicit URL, regardless of subscription state.

| Referenced repository | RHEL subscription | Configured URL | Result |
|-----------------------|-------------------|----------------|--------|
| `baseos`, `appstream` or `codeready-builder` | Enabled | Non-empty | Use the explicit URL and configured settings |
| `baseos`, `appstream` or `codeready-builder` | Enabled | Empty or missing | Discover the subscription URL and entitlement certificates |
| Any other repository | Enabled | Non-empty | Use the explicit URL |
| Any other repository | Enabled | Empty or missing | Fail before Pulp synchronization |
| Any referenced repository | Disabled | Non-empty | Use the explicit URL |
| Any referenced repository | Disabled | Empty or missing | Fail before Pulp synchronization |
| Any unreferenced repository | Either | Any value | Ignore for this catalog execution |

Repo Manager checks the host subscription once for an execution and uses that
same result for input validation and repository URL resolution. For a
subscription-provided repository, it prefers an available EUS URL, falls back to
the standard URL and substitutes the active catalog minor version. When
subscription access is enabled, every resolved referenced URL is checked for
`repodata/repomd.xml` before Pulp synchronization.

#### Subscription-enabled example

In this example, the selected catalog packages reference only BaseOS and EPEL:

```yaml
repositories:
  "10.2":
    x86_64:
      baseos: {}
      epel:
        url: "https://mirror.example/epel/10.2/x86_64/"
```

Repo Manager discovers BaseOS from the active RHEL subscription and uses the
explicit EPEL URL. AppStream and CodeReady Builder are not required because the
catalog does not reference them. An explicit BaseOS URL would take precedence
over subscription discovery.

The complete form can retain repository-specific settings while allowing the
subscription to supply only the URL and entitlement certificates:

```yaml
repositories:
  "10.2":
    x86_64:
      baseos:
        policy: partial
        caching: true
        priority: 99
```

A missing `baseos` entry is also eligible for discovery when BaseOS is
referenced, but the matching `repositories."10.2".x86_64` section must exist.

#### Non-subscription example

Without a valid RHEL subscription, every catalog-referenced RPM repository must
have a non-empty URL, including BaseOS, AppStream and CodeReady Builder:

```yaml
repositories:
  "10.2":
    x86_64:
      baseos:
        url: "https://mirror.example/rhel/10.2/x86_64/baseos/"
      epel:
        url: "https://mirror.example/epel/10.2/x86_64/"
```

This configuration is sufficient only when the catalog references BaseOS and
EPEL. If it also references AppStream or CodeReady Builder, their URLs are
mandatory. Repo Manager reports all missing referenced repositories together,
grouped by selected architecture.

#### Multiple architectures

Each architecture has an independent repository mapping. An x86_64 URL never
satisfies an aarch64 source:

```yaml
repositories:
  "10.2":
    x86_64:
      baseos: {}
      user_repos:
        slurm_custom:
          url: "https://mirror.example/slurm/10.2/x86_64/"

    aarch64:
      baseos: {}
      user_repos:
        slurm_custom:
          url: "https://mirror.example/slurm/10.2/aarch64/"
```

Subscription discovery is performed only for the subscription repositories
referenced by each architecture. Explicit repositories remain architecture
specific. For a multi-version catalog, the same rules are applied sequentially
to each numeric minor-version context.

### Additional and User Repositories

```yaml
repositories:
  "10.0":
    x86_64:
      additional_repos:
        internal-tools:
          url: "https://repo.example.com/internal-tools/"
          priority: 99
      user_repos:
        slurm_custom:
          url: "https://repo.example.com/slurm/"
          priority: 100
```

The catalog must use the same `reponame` value.

`additional_repos` are published as one aggregated Pulp repository per
architecture. All entries in that section must therefore have the same effective
priority. An omitted priority has the DNF default value of 99; mixing that default
with another value fails precheck rather than publishing an ambiguous priority.

---

## Container Registry Mapping

### Public Registry

Known public registries are resolved directly:

```yaml
registries:
```

Docker Hub credentials remain optional and are collected using the existing
Docker credential prompts.

### Private Registry with Basic Authentication

Configuration:

```yaml
registries:
  private_registry:
    base_url: "https://harbor.example.com"
    port: 443
    auth:
      type: basic
      credentials:
        vault_path: "registries/harbor-production"
    tls:
      ca_path: ""
      client_cert_path: ""
      client_key_path: ""
      insecure: false
```

Encrypted credential mapping:

```yaml
registry_credentials:
  registries/harbor-production:
    registry: "private_registry"
    username: "omnia-pull-user"
    password: "<secret>"
```

Catalog package and source:

```json
{
  "name": "harbor.example.com:443/library/nginx",
  "packagetype": "image",
  "sources": [{
    "architecture": "x86_64",
    "registry": "private_registry",
    "version": ["10.0"]
  }],
  "tag": "1.25.2"
}
```

Repo Manager passes the resolved username and password to the Pulp container
remote. Credentials are not placed in the catalog, main configuration or logs.
The image name must use the exact configured endpoint. Names such as
`private_registry/library/nginx` are rejected; no alias-prefix fallback exists.

---

## Policy Resolution

Per-repository fields have priority over global settings:

```text
repository policy  > repo_config
repository caching > caching_policy
```

| Effective policy | Effective caching | Pulp RPM policy |
|------------------|-------------------|-----------------|
| `always` | `false` | `immediate` |
| `always` | `true` | `on_demand` |
| `partial` | `false` | `streamed` |
| `partial` | `true` | `on_demand` |
| `never` | either | `streamed` |

Container synchronization is independent of RPM policy. Its default is
`container_sync_policy: immediate` so OCI content is retained for offline use.

---

## Architecture Support

Repo Manager resolves every package source independently:

| Catalog source | Required configuration |
|----------------|------------------------|
| `x86_64`, RHEL 10.0 | `repositories."10.0".x86_64` |
| `aarch64`, RHEL 10.0 | `repositories."10.0".aarch64` |
| Both architectures | Both repository maps |

A single catalog may contain x86_64 management groups and aarch64 compute
groups. Only packages reachable from those groups are synchronized. Repository,
status and mirror identities include architecture, preventing cross-architecture
collisions.

---

## Concurrency Controls

These controls are independent:

| Setting | Default | Purpose |
|---------|---------|---------|
| `parallel_config.default_nthreads` | `4` | General catalog package worker processes |
| `rpm_repo_config.thread_pool_size` | `2` | RPM repositories processed in each Pulp stage |
| `dnf_config.max_concurrent_commands` | `1` | Maximum simultaneous DNF commands |

Increasing general workers does not increase DNF concurrency. Keep DNF at one;
reduce the other controls when Pulp CPU, memory, network, or storage is
constrained.

## Validation Checklist

- Catalog path exists and ends in `.json`.
- Every package source has a supported architecture and OS version.
- Every RPM source `reponame` exists in the matching repository map.
- Every referenced non-subscription repository has a non-empty explicit URL.
- Without a subscription, every referenced BaseOS, AppStream and CodeReady
  Builder repository also has a non-empty explicit URL.
- Subscription discovery is used only for referenced `baseos`, `appstream` and
  `codeready-builder` entries whose URL is empty or missing.
- Every non-public registry exists in `registries`.
- Every basic-auth registry has a matching Vault credential entry.
- Repository priority is between 1 and 100.
- `rpm_repo` does not explicitly declare repository `policy: never`.
- Both architectures are configured when selected by the catalog.
