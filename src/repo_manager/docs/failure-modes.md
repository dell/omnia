# Repo Manager -- Failure Modes

Defaults come from `plugins/module_utils/repo_manager/repo_settings.py` and are
overridable by configuration. Recovery steps are in
[troubleshooting.md](troubleshooting.md). Logging and redaction rules are in
[security.md](security.md).

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
