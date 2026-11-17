# Repo Manager -- Failure Modes

Defaults come from `plugins/module_utils/repo_manager/repo_settings.py` and are
overridable by configuration. Recovery steps are in
[troubleshooting.md](troubleshooting.md). Logging and redaction rules are in
[security.md](security.md).

## Security Boundaries

Repo Manager (`omnia.repo_manager`) is an Ansible collection that the Omnia orchestrator (or another calling application) invokes to deploy Pulp, mirror RPM, container, and artifact content, and report status. Its playbooks run locally on the Omnia Infrastructure Manager (OIM) with root privileges, and it has no user interface, API endpoint, or user model of its own. Two security properties therefore depend on where the boundary lies: who is allowed to run Repo Manager, which is decided by the caller, and which third-party code Repo Manager runs, which is decided by its declared dependencies. The rules below state these boundaries, and the matching failure modes are listed in the table that follows.

- **Default deny access (REQ-CH2-002):** Repo Manager does not implement access control. The calling application (e.g., the Omnia orchestrator) MUST authenticate and authorize callers and deny all access unless explicitly granted.
- **Dependency trustworthiness (REQ-CH8-001):** Only dependencies listed in `requirements.txt`, `requirements.yml`, and the Pulp image in `vars/default.yml` are used. Each is sourced from its official registry (PyPI, Ansible Galaxy, Docker Hub) and evaluated before adoption or upgrade for vulnerability history (OSV, GitHub Advisory Database, NVD), maintainer activity, and license compatibility with Apache-2.0. Copyleft (GPL) dependencies are consumed only as separately installed, unmodified components.

## General Rules

- Fail closed on malformed, template-bearing, or unknown configuration.
- Retry only transient failures (timeout, gateway error, connection error).
- `rpm_repo_config.continue_on_failure` defaults to `true`: one bad repository
  does not stop the run.
- Status and mirror state are written atomically.
- Passwords, tokens, keys, usernames, and URL userinfo are masked in all output.

## Failure Modes

| Component | Failure mode | Expected behavior |
|-----------|--------------|-------------------|
| Input validation | Unknown or invalid key | Reject the run (schema error) |
| Input validation | Template syntax in YAML (`{{`, `{%`, `{#`) | Reject before use (`YamlTemplateSyntaxError`) |
| Catalog | Invalid artifact URL (credentials or non-HTTP(S)) | `ArtifactUrlValidationError`; reject |
| Catalog | Unresolved repository or registry | `CatalogResolutionError`; reject |
| Subscription | Repository unavailable and no explicit URL | `SubscriptionRepositoryError`; precheck fails |
| Credentials | Vault key missing or not mode `0600` | Fail; do not decrypt |
| Credentials | Re-encryption fails | Fatal |
| Pulp CLI query | Transient failure | Retry `RPM_CLI_QUERY_RETRIES` (3) times, `RPM_CLI_QUERY_RETRY_DELAY` (5s) between attempts |
| Pulp command | Timeout | Stop after `PULP_COMMAND_TIMEOUT` (300s); orphan cleanup 1800s |
| RPM sync | No progress | Fail after `RPM_SYNC_STUCK_TIMEOUT` (600s); cleanup per `RPM_CLEANUP_ON_TIMEOUT` |
| RPM sync | Pulp API unavailable | Stop after `RPM_API_UNAVAILABLE_TIMEOUT` (600s) |
| DNF download | Transient metadata failure | Retry 3 times, 30s fixed delay; then fail that package |
| Artifact reuse | SHA-256 mismatch | Reject reuse; fail that artifact |
| Shared artifact state | Index corrupt or unreadable | `SharedArtifactStateError`; fail closed |
| Cleanup | Unsafe target path | Refuse |
| Cleanup | Pulp delete not confirmed | Keep local state unchanged |
| Status output | Pulp state incomplete after selective cleanup | Write `overall_status: failed`; status play fails |
| Access control | Caller invokes Repo Manager without authorization | Not detected by Repo Manager; the caller MUST deny by default |
| Dependencies | Pulp image cannot be pulled | Retry `pull_image_retries` times; then fail deployment |
| Dependencies | Dependency not evaluated, or has an open applicable advisory | Do not adopt; evaluate first |
