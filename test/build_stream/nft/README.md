# Non-Functional Tests — BuildStream

BuildStream NFTs exercise operational recovery and deployed API security. They
use the same shared runner, ordered `nft` markers, centralized test-case
registry, and JSON/HTML reporting framework as Image Build Manager.

The retained source-level tests under `nft/unit/` and `nft/others/` are not
part of `nft_build_stream`; the runner selects only the registered NFT cases.

## Test cases

| ID | Test | Markers | Purpose |
|---|---|---|---|
| `BSM_NFT_RESILIENCE_001` | `test_gitlab_cancel_then_create_new_job` | `nft,resilience,disruptive` | Cancel the exact test-created GitLab pipeline and require a different pipeline and BSM job |
| `BSM_NFT_RESILIENCE_002` | `test_bsm_container_restart_recovery` | `nft,resilience,disruptive` | Restart BSM and retain health and persisted job access |
| `BSM_NFT_RESILIENCE_003` | `test_bsm_restart_during_active_stage` | `nft,resilience,disruptive` | Restart BSM while its test-created job is active without duplicating stages |
| `BSM_NFT_RESILIENCE_004` | `test_watcher_restart_during_queued_request` | `nft,resilience,disruptive` | Pause the watcher, observe the exact NFT job request, restore it, and verify that it claims the request |
| `BSM_NFT_SECURITY_001` | `test_protected_endpoints_reject_invalid_tokens` | `nft,security` | Reject missing, malformed, and tampered bearer tokens |
| `BSM_NFT_SECURITY_002` | `test_scope_authorization_enforced` | `nft,security` | Reject a write operation made with a catalog-read token |
| `BSM_NFT_SECURITY_003` | `test_upload_path_and_filename_protection` | `nft,security` | Reject path traversal without creating a file or changing stage state |
| `BSM_NFT_SECURITY_004` | `test_oversized_upload_rejected_without_partial_state` | `nft,security` | Reject a file over 5 MiB without a partial artifact or stage mutation |
| `BSM_NFT_SECURITY_005` | `test_secret_redaction_in_logs_and_responses` | `nft,security` | Keep an invalid client-secret canary out of responses and container logs |

## Safety controls

All disruptive or state-creating operations default to `false` in
`test_config.yml`:

```yaml
nft_allow_pipeline_cancel: false
nft_allow_service_restart: false
nft_allow_active_stage_restart: false
nft_allow_watcher_restart: false
nft_allow_security_mutation: false
nft_recovery_timeout_seconds: 120
nft_pipeline_timeout_seconds: 300
```

The cancellation case records the pipeline it creates and cancels only that
pipeline through the GitLab API, which is equivalent to clicking its Cancel
button. It never selects an arbitrary running pipeline. Session teardown also
cancels the replacement test pipeline after the recovery cases finish, so it
does not occupy the GitLab runner for the next NFT execution.

The BSM and watcher restart cases use their systemd services so Quadlet manages
the containers correctly. Each restart waits for service recovery; BSM restart
also requires `/health` to recover. The watcher test restores the service in a
`finally` path even when its expected job-specific request does not appear.

## Run

From `test/build_stream`:

```bash
# List cases
./run_validation.sh nft_build_stream list

# Safe authentication, authorization, and redaction checks
./run_validation.sh nft_build_stream test --marker security

# Resilience cases; enable only the matching test_config.yml gates first
./run_validation.sh nft_build_stream test --marker resilience

# All registered NFTs; disabled operations are reported as skipped
./run_validation.sh nft_build_stream test
```

The security mutation cases create one disposable BSM job only when
`nft_allow_security_mutation: true`. They do not upload product inputs that can
progress a real build stage. The job remains clearly labeled
`omnia-nft-security` for auditability.

Reports are written using `report_path` and `report_name` from
`test_config.yml` in both JSON and HTML formats.
