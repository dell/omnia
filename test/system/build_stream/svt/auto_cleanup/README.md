# auto_cleanup

Back to the [test case table](../README.md).

| Order | ID | Test | Suite | Phase |
|---:|---|---|---|---|
| 3001 | `BSM_SVT_AUTO_CLEANUP_E001` | `test_precheck_auto_cleanup` | root | exec |
| 3002 | `BSM_SVT_AUTO_CLEANUP_E002` | `test_run_auto_cleanup_pass` | root | exec |
| 3101 | `BSM_SVT_AUTO_CLEANUP_V001` | `test_verify_auto_cleanup_eligible_groups` | `verification` | verify |

Verifies BuildStream automated (retention) cleanup. The `AutoCleanupScheduler`
in `omnia_build_stream` runs `cleanup_cron.main()` every
`retention.evaluation_interval_hours` while `retention.auto_cleanup_enabled`
is true. The exec test runs that same pass once, with its log streamed,
instead of waiting for the interval.

## Eligibility (mirrors cleanup_cron.py)

| Phase | Cleaned image groups |
|---|---|
| FAILED | Every group in `FAILED`. |
| Retention (after the FAILED phase) | Not protected, `deploy_count = 0`, older than `retention_age_days`, not `CLEANED`/`CLEANING`; oldest first, only while the group's `catalog_identifier` keeps more than `min_keep_count` active groups. Groups without a catalog identifier are never cleaned by retention. |

Groups in `DEPLOYING`, `RESTARTING` or `VALIDATING` are refused by the
cleanup use case and counted as pass errors.

## Flow

1. **Precheck:** clear the previous exec state; validate `retention` from the
   project `build_stream_config.yml`; check `omnia_build_stream` is running
   and playbook-watcher is active. Skipped (and the scenario with it) when
   `auto_cleanup_enabled` is false.
2. **Exec:** snapshot every image group (DB clock) and every
   `s3://boot-images/` object, log the expected decision for each group, run
   one pass and wait, without a timeout, until no submitted group is
   `CLEANING`. The facts are saved to `reports/state/auto_cleanup.json`.
3. **Verify:** compare the pass with the saved facts.

## Pass criteria (verify)

- The pass exit code matches the expectation, used the configured settings,
  and submitted exactly the expected groups.
- Each submitted group is `CLEANED`, its job is tombstoned, the audit trail has
  `JOB_CLEANUP_SUBMITTED` and `JOB_CLEANED` (plus `RETENTION_DELETED` for
  retention), and its S3 objects and NFS artifacts
  (`build_stream_root/artifacts/<job_id>`) are gone.
- Every other image group keeps its state and its S3 objects.

Groups whose age is within 5 minutes of the cutoff are tolerated either way.
With no eligible group the pass must change nothing.

```bash
./run_validation.sh svt_build_stream auto_cleanup test
```
