# installation

Back to the [test case table](../README.md).

| Order | ID | Test | Suite | Phase |
|---:|---|---|---|---|
| 2001 | `BSM_SVT_INSTALLATION_E001` | `test_precheck_installation` | root | exec |
| 2002 | `BSM_SVT_INSTALLATION_E002` | `test_run_build_stream_installation` | root | exec |
| 2101 | `BSM_SVT_INSTALLATION_V001` | `test_verify_build_stream_services` | `health` | verify |
| 2201 | `BSM_SVT_INSTALLATION_V002` | `test_verify_gitlab_repository_sync` | `repository` | verify |
| 2301 | `BSM_SVT_INSTALLATION_V003` | `test_build_pipeline_trigger_and_verify` | `build` | verify |
| 2401 | `BSM_SVT_INSTALLATION_V004` | `test_deploy_pipeline_trigger_and_verify` | `deploy` | verify |
| 2501 | `BSM_SVT_INSTALLATION_V005` | `test_cadence_pipeline_trigger_and_verify` | `cadence` | verify |
| 2601 | `BSM_SVT_INSTALLATION_V006` | `test_cadence_disable_takes_effect_live` | `cadence` | verify |
| 2602 | `BSM_SVT_INSTALLATION_V007` | `test_cadence_reenable_resumes_cycle` | `cadence` | verify |

## Precheck — BSM_SVT_INSTALLATION_E001

1. `installation.catalog` (a number resolved on the OIM in
   `./omnia.sh --list-catalogs` order, or a full path) is a valid catalog and
   `CATALOG_FILE_PATH` is an absolute `.json` path.
2. `build_stream_config.yml` and the BuildStream credential store exist.
3. `pxe_mapping_file.csv` has at least two node rows (the deploy test swaps two).
4. `build_stream.yml --tags precheck` passes: repo_manager and
   image_build_manager are ready for BuildStream.

## Entry point — BSM_SVT_INSTALLATION_E002

Install the `installation.catalog` catalog at `CATALOG_FILE_PATH` (a different active catalog is
kept as `<file>.backup.<timestamp>`) and run `build_stream.yml` (default flow).

## Verification

| Suite | ID | Checks |
|---|---|---|
| `health` | `V001` | `omnia_build_stream` and `omnia_postgres` running, playbook-watcher active, every `build_stream_db` table, API `/health` healthy |
| `repository` | `V002` | Project reachable; the `.gitlab-ci*.yml` files and `omnia.env`; every domain input file present on the OIM synced to `input/<domain>/` with identical content (runs before the pipelines change GitLab) |
| `build` | `V003` | Commit the `installation.catalog` catalog as `catalog_rhel.json` with the next unused version; then upload, parse-catalog, create-local-repository, build-image, each verified in `job_stages` and the API as soon as it finishes. Right after `upload`, the host `CATALOG_FILE_PATH` must hold the committed catalog and version, or the test stops there |
| `deploy` | `V004` | Swap two rows of `input/orchestrator/pxe_mapping_file.csv`, select the image group, play deploy; deploy, restart, validate. Skipped when `V003` failed in the same run |
| `cadence` | `V005` | Upload the `installation.catalog` catalog as `cadence_catalog_rhel.json` with `[skip ci]` (no pipeline), run `trigger_cadence.sh` (the command is printed), follow the playbook-watcher journal (every cadence record is printed); the cycle syncs, bumps to the expected version and commits, which starts the cadence pipeline; all seven build + deploy stages |
| `cadence` | `V006` | Set `cadence.enabled: false` without a restart, trigger: the cycle logs *Cadence polling is disabled* and does no fetch, sync or commit |
| `cadence` | `V007` | From a disabled watcher, upload the catalog, set `cadence.enabled: true` without a restart, trigger: the reload logs *enabled False -> True* and the cycle runs to completion |

The pipeline suites trigger when their `pipeline.<name>_job_id` is empty and
only verify that job when it is set. All three pipelines also check the
GitLab pipeline result, the `jobs`, `job_stages`, `image_groups` and
`images` rows and the API job view. `pipeline.allow_pipeline_cancel` decides
whether busy GitLab pipelines are cancelled or reported.

The cadence tests do not depend on the build pipeline test. `V005` is
skipped when `cadence.enabled` is false; `V006` and `V007` restore the
original `cadence.enabled` value. The commit made by the `V007` cycle starts
a cadence pipeline that keeps running after the test.

With `debug_mode: true` every stage log and the cadence repo sync log stream
live; otherwise the progress lines show `tail -f <log>`
([details](../../docs/test_config.md#debug_mode)).

```bash
./run_validation.sh svt_build_stream installation test
./run_validation.sh svt_build_stream installation verify --suite health
./run_validation.sh svt_build_stream installation verify --marker cadence    # V005-V007
```
