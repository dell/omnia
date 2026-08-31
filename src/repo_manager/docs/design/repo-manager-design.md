# Repo Manager -- Design

| Field | Value |
|-------|-------|
| Domain | `repo_manager` |
| Collection | `omnia.repo_manager` |

This document describes implementation boundaries and invariants for Repo
Manager contributors. Operator behavior is documented in
[architecture.md](../architecture.md).

---

## Design Goals

1. Resolve catalog content deterministically by OS version and architecture.
2. Provide retained offline content through a single HTTPS Pulp service.
3. Support subscription and user-provided RPM sources without changing catalog
   semantics.
4. Support public and authenticated private container registries.
5. Make reruns and selective cleanup safe for shared Pulp objects.
6. Keep runtime paths configurable through the Omnia environment contract.

---

## Component Boundaries

| Layer | Responsibility |
|-------|----------------|
| `playbooks/repo_manager.yml` | Tag-based orchestration and operation ordering |
| `roles/repo_manager_setup` | Environment loading and derived runtime paths |
| `roles/deploy_pulp` | HTTPS certificates, Quadlet, Pulp service and managed CLI |
| `roles/validate_input` | JSON Schema and cross-file input validation |
| `roles/validate_subscription` | Subscription/EUS repository and entitlement resolution |
| `roles/parse_and_download` | Catalog task preparation and execution |
| `roles/catalog` | Generate, add, delete and validate catalog JSON |
| `plugins/modules` | Stable Ansible interfaces and result conversion |
| `plugins/module_utils/repo_manager` | Catalog resolution, Pulp operations, downloads, identity and state |
| `playbooks/cleanup` | Full deployment cleanup and selective content cleanup |

Ansible roles own orchestration. Python modules own structured validation and
content operations. Shared Python behavior belongs in `module_utils` rather than
being copied into task files.

---

## Control Flow

```text
environment + staged YAML + catalog JSON
                    |
                    v
        setup and schema validation
                    |
                    v
       subscription/registry resolution
                    |
                    v
       functional-group task preparation
                    |
                    v
        bounded multiprocessing workers
                    |
                    v
       Pulp remotes -> repositories -> versions
                    |
                    v
        distributions + mirror/status state
                    |
                    v
                repo_status.yml
```

The top-level playbook always establishes environment and path facts. Selected
operation tags then run in playbook order; command-line tag order does not
reorder plays.

---

## Runtime Path Model

All domain data derives from these values:

```text
OMNIA_DATA_PATH             default /opt/omnia
REPO_MANAGER_DATA_PATH      default <OMNIA_DATA_PATH>/repo_manager
OMNIA_PROJECT_NAME          default project_default
```

Inputs and outputs are project-scoped. Pulp data, certificates, repository
caches and operational logs are domain-scoped. `REPO_MANAGER_INPUT_PROJECT_DIR`
is an internal/test override for the resolved project input directory.

Path validation requires safe absolute paths and rejects broad system roots.
Source-code paths are never used as persistent runtime paths.

---

## Catalog Resolution

The resolver performs these operations:

1. Select functional layers requested by the catalog.
2. Expand group/component references.
3. Filter sources by OS version and `x86_64` or `aarch64`.
4. Resolve `reponame` against RPM repository configuration.
5. Resolve `registry` against known public registries or configured registries.
6. Deduplicate equivalent tasks using a composite content identity.

The catalog controls which functional groups and architectures are processed.
The host architecture does not remove valid `aarch64` catalog tasks; DNF uses
the target architecture mode for those tasks.

---

## Content Identity

A mirror/status identity includes enough dimensions to avoid collisions:

```text
package type + package/image name + version or tag + architecture + source
```

This prevents these cases from overwriting each other:

- the same package name for `x86_64` and `aarch64`;
- the same image name with multiple tags;
- an `rpm_repo` catalog item whose execution status is recorded by RPM logic;
- identical names from different repository or registry sources.

Legacy name-keyed state is migrated when it can be mapped unambiguously. New
writes use the composite identity and atomic file replacement.

---

## RPM Source Resolution

Repository resolution follows this priority:

```text
explicit repository fields
        > subscription-derived URL and certificates
        > validation failure
```

Empty BaseOS, AppStream and CodeReady Builder mappings request subscription
resolution. A user URL always wins, even when the host is subscribed. Resolution
is performed independently for each catalog version and architecture.

Effective sync policy is resolved in this order:

```text
repository policy  > repo_config
repository caching > caching_policy
```

`rpm_repo` requires retained Pulp content and is rejected when it resolves to
`streamed`.

---

## Container Registry Resolution

The execution path uses one registry model for both public and configured
registries:

```text
catalog source.registry
       -> public registry defaults OR registries.<name>
       -> optional auth.credentials.vault_path
       -> encrypted registry_credentials entry
       -> authenticated Pulp container remote
```

Configuration keys are lowercase. User values remain unchanged. Secrets are
passed as command arguments or module parameters with redacted/no-log handling;
they are not written into catalog, status, or distribution URLs.

Same-name images share a Pulp repository. Tags remain distinct content and
status identities. Cleanup by exact tag removes only that tag; untagged cleanup
removes the complete repository.

---

## Concurrency and State Safety

| Control | Purpose |
|---------|---------|
| `parallel_config.default_nthreads` | Bounds general catalog worker processes (`1-5`) |
| `rpm_repo_config.thread_pool_size` | Bounds repository synchronization threads (`1-10`) |
| `dnf_config.max_concurrent_commands` | Bounds DNF commands independently (`1-5`, default `1`) |
| Resource locks | Serialize creation/update of the same Pulp object |
| DNF semaphore | Protect shared per-architecture DNF metadata caches |
| File locks | Serialize CSV/log updates within the process tree |
| Atomic replacement | Prevent partial Vault, CSV, text and mirror-index files |

Default worker and DNF limits are one for stability. Raising general workers
does not raise DNF concurrency. The supported operating model is one Repo
Manager playbook instance at a time; process-local locks do not coordinate two
independent playbook invocations.

The parent process polls asynchronous results and writes a progress heartbeat
approximately every 60 seconds. Heartbeats are observational and do not change
timeouts or task results.

---

## Pulp Object Lifecycle

Downloads use type-specific Pulp commands while preserving the same lifecycle:

```text
remote -> repository -> sync/upload -> repository version -> distribution
```

Creation checks are idempotent. Existing objects are updated or reused. Pulp
task completion is verified before mirror state is marked successful.

The deployment uses a systemd-enabled Podman Quadlet. The configured host port
maps to container HTTPS port `443`. Certificates and the Pulp CLI CA configuration
are generated from the runtime path, not endpoint input fields.

---

## Error Handling

| Failure | Required behavior |
|---------|-------------------|
| Invalid environment or input | Fail before content changes |
| Pulp endpoint unavailable | Fail immediately with endpoint context |
| Worker/package failure | Record package and group result, return non-success |
| Timeout | Stop the worker pool and report timeout |
| Credential re-encryption failure | Fail and report possible plaintext exposure |
| SELinux certificate labeling failure | Fail before repository synchronization |
| Cleanup target ambiguity | Reject the request |
| Pulp delete failure | Preserve local mirror/status state |

Secret-bearing commands must use redaction or `no_log`. Error messages may
identify a registry or Vault key path, but never a password or token.

---

## Cleanup Invariants

1. Exact Pulp names or hrefs are used; substring matching is not accepted.
2. Tagged container cleanup affects only the selected tag.
3. Untagged container cleanup intentionally affects all tags in that repository.
4. Digest-only container cleanup is rejected.
5. Local state is updated only after Pulp confirms deletion.
6. Cleanup state files are written atomically.
7. Full cleanup preserves logs or credentials only when explicitly requested.

---

## Extension Checklist

When adding a content type or input field:

1. Update the JSON Schema and logic validation together.
2. Add catalog-to-task resolution and a composite identity.
3. Implement idempotent Pulp creation, update and distribution behavior.
4. Add selective cleanup and post-delete verification.
5. Add status/mirror migration behavior if identity changes.
6. Add unit tests for both architectures and duplicate names/tags.
7. Update the input/output contracts and troubleshooting guide.

## Test Boundaries

| Test level | Coverage |
|------------|----------|
| Unit | Validators, paths, identities, policies, registry mapping and state writes |
| Syntax/lint | Ansible task structure and collection conventions |
| Integration | Live Pulp command forms and object lifecycle |
| End-to-end | Subscription/non-subscription, public/private registry, both architectures, rerun and cleanup |

Production validation must include same-image multiple-tag cleanup and a rerun
after partial success.
