# BuildStream SVT — Test Cases

The `svt/` tree follows the BuildStream lifecycle on one OIM. Each scenario
directory owns its test cases. Test files only select, order and report a
case; reusable behaviour lives in `library/functions`, messages in
`library/messages`, and IDs, commands and SQL in `library/vars`.

Back to the [suite README](../README.md).

## Test case identification

IDs use this format, registered centrally in
[`library/vars/test_case_vars.py`](../library/vars/test_case_vars.py)
(one dictionary per scenario, merged into `TEST_CASES`):

```text
BSM_SVT_<SCENARIO>_<TYPE><NUMBER>
```

- `E` is an execution case: it runs a product entry point (precheck
  playbook, `./omnia.sh`, a domain playbook or a cleanup pass). `E001` is
  always the scenario precheck, `E002` the entry point.
- `V` is a verification case: it checks what the execution produced, or
  triggers and verifies a pipeline on the installed BuildStream.
- The registry key is the test function name without `test_`; a test reads
  its ID and title with `tc = TC["<key>"]`.
- IDs are never reused. Function names and files may change without
  changing a public ID.

Every test also carries `svt`, `sanity` and `br_86010` (the traceability
marker for the system test plan TEST-BR-86010).

## Scenario shape

| Part | Runner phase | Markers | What it does |
|---|---|---|---|
| Precheck `E001` (`test_precheck.py`) | `exec` | `deploy`, `precheck` | Proves, without changing anything, that the entry point can run unattended. If it does not pass, the rest of the scenario is skipped. |
| Entry point `E002` (`test_playbook.py` / `test_auto_cleanup.py`) | `exec` | `deploy` | Runs `omnia.sh`, the playbook or the cleanup pass. If it fails, the scenario's verification is skipped. |
| Verification `V…` (`<suite>/test_<suite>.py`) | `verify` | — | Verifies the result on the live system. |

`auto_cleanup` and `cleanup` verification needs facts that only exist during
exec (the image-group snapshot, the paths to preserve). The exec test
records them in `reports/state/<scenario>.json` (git-ignored, mode 0600, no
secrets); the precheck clears the previous file and verification is skipped
when no exec state exists.

## Execution order

```text
prepare_base   precheck -> omnia.sh --prepare-base -> readiness
installation   precheck -> build_stream.yml -> health -> repository
               -> build -> deploy -> cadence -> cadence disable -> cadence re-enable
auto_cleanup   precheck -> cleanup pass -> verification
cleanup        precheck -> domain cleanups -> postconditions
```

Order is the global `@pytest.mark.order` value: one band per scenario
(`prepare_base` 1000, `installation` 2000, `auto_cleanup` 3000, `cleanup`
4000), +1 precheck, +2 entry point, +100 per verification suite. It does not
depend on directory names.

## Test case table

| Order | ID | Test | Scenario / suite | Extra markers | Phase | Pass criteria |
|---:|---|---|---|---|---|---|
| 1001 | `BSM_SVT_PREPARE_BASE_E001` | `test_precheck_prepare_base` | `prepare_base` | `deploy`, `precheck` | exec | `OMNIA_DATA_PATH`, `OMNIA_PROJECT_NAME`, `OMNIA_VENV_PATH` set; venv and `omnia.sh` present; repo_manager, image_build_manager and orchestrator credential stores (file + key) present. |
| 1002 | `BSM_SVT_PREPARE_BASE_E002` | `test_run_prepare_base` | `prepare_base` | `deploy` | exec | `./omnia.sh --prepare-base` exits 0. |
| 1101 | `BSM_SVT_PREPARE_BASE_V001` | `test_verify_repo_manager_readiness` | `prepare_base/readiness` | — | verify | Pulp quadlet present, `pulp.service` active, Pulp container running. |
| 1102 | `BSM_SVT_PREPARE_BASE_V002` | `test_verify_image_build_manager_readiness` | `prepare_base/readiness` | — | verify | MinIO and registry containers running, units active, ports 9000/9001/5000 listening. |
| 1103 | `BSM_SVT_PREPARE_BASE_V003` | `test_verify_orchestrator_readiness` | `prepare_base/readiness` | — | verify | All OpenCHAMI units and `openchami-cert-renewal.timer` active; long-running containers running (healthcheck honoured); data and `haproxy-certs` volumes present; OpenLDAP quadlet, `omnia_auth.service` and healthy container when `openldap_support` is set. |
| 2001 | `BSM_SVT_INSTALLATION_E001` | `test_precheck_installation` | `installation` | `deploy`, `precheck` | exec | `installation.catalog` resolves to a valid catalog; `CATALOG_FILE_PATH` valid; `build_stream_config.yml` and the BuildStream credential store present; at least 2 PXE node rows; `build_stream.yml --tags precheck` exits 0. |
| 2002 | `BSM_SVT_INSTALLATION_E002` | `test_run_build_stream_installation` | `installation` | `deploy` | exec | Selected catalog installed at `CATALOG_FILE_PATH` (a different one backed up); `build_stream.yml` exits 0. |
| 2101 | `BSM_SVT_INSTALLATION_V001` | `test_verify_build_stream_services` | `installation/health` | — | verify | `omnia_build_stream`, `omnia_postgres` running; playbook-watcher active; every `build_stream_db` table; API `/health` healthy. |
| 2201 | `BSM_SVT_INSTALLATION_V002` | `test_verify_gitlab_repository_sync` | `installation/repository` | — | verify | Project reachable; the `.gitlab-ci*.yml` files and `omnia.env` present; every domain input file on the OIM is in `input/<domain>/` with identical content. |
| 2301 | `BSM_SVT_INSTALLATION_V003` | `test_build_pipeline_trigger_and_verify` | `installation/build` | `pipeline` | verify | The selected catalog is committed as `catalog_rhel.json` with the next unused version; right after `upload`, `CATALOG_FILE_PATH` on the host holds that catalog and version (else the test stops: later stages would build another catalog); `upload`, `parse-catalog`, `create-local-repository`, `build-image` COMPLETED (each verified in `job_stages` and the API as it finishes); GitLab pipeline success; jobs/image_groups/images rows and the API job view agree. |
| 2401 | `BSM_SVT_INSTALLATION_V004` | `test_deploy_pipeline_trigger_and_verify` | `installation/deploy` | `pipeline` | verify | Two PXE mapping rows swapped; `deploy`, `restart`, `validate` COMPLETED; image group PASSED; `deploy_count` incremented. Skipped when `V003` failed in the same run. |
| 2501 | `BSM_SVT_INSTALLATION_V005` | `test_cadence_pipeline_trigger_and_verify` | `installation/cadence` | `pipeline`, `cadence` | verify | Selected catalog uploaded as `cadence_catalog_rhel.json` with `[skip ci]` and no pipeline started; cycle triggered (command printed); repo sync succeeds; the cycle bumps to the expected version and commits; all seven build + deploy stages COMPLETED; image group PASSED. Skipped when `cadence.enabled` is false. |
| 2601 | `BSM_SVT_INSTALLATION_V006` | `test_cadence_disable_takes_effect_live` | `installation/cadence` | `cadence` | verify | `cadence.enabled: false` set without a restart; the triggered cycle logs *Cadence polling is disabled*; no catalog fetch, repo sync or commit; original value restored. |
| 2602 | `BSM_SVT_INSTALLATION_V007` | `test_cadence_reenable_resumes_cycle` | `installation/cadence` | `cadence` | verify | From a disabled watcher, the selected catalog is uploaded (`[skip ci]`), `cadence.enabled: true` set without a restart; the reload logs *enabled False -> True*; the cycle syncs, bumps to the expected version and completes; original value restored. |
| 3001 | `BSM_SVT_AUTO_CLEANUP_E001` | `test_precheck_auto_cleanup` | `auto_cleanup` | `deploy`, `precheck` | exec | Retention settings valid; `omnia_build_stream` running; playbook-watcher active. Skipped when `auto_cleanup_enabled` is false. |
| 3002 | `BSM_SVT_AUTO_CLEANUP_E002` | `test_run_auto_cleanup_pass` | `auto_cleanup` | `deploy`, `destructive` | exec | One `cleanup_cron.main()` pass finishes without a fatal error and no submitted group is left CLEANING. |
| 3101 | `BSM_SVT_AUTO_CLEANUP_V001` | `test_verify_auto_cleanup_eligible_groups` | `auto_cleanup/verification` | — | verify | Exactly the expected groups submitted and CLEANED with tombstoned jobs, audit events, no S3 objects or NFS artifacts left; every other group and object untouched. |
| 4001 | `BSM_SVT_CLEANUP_E001` | `test_precheck_cleanup` | `cleanup` | `deploy`, `precheck` | exec | At least one block enabled; omnia.env variables set; each enabled playbook present. |
| 4002 | `BSM_SVT_CLEANUP_E002` | `test_run_full_domain_cleanup` | `cleanup` | `deploy`, `destructive` | exec | Each enabled playbook (build_stream -> orchestrator -> image_build_manager -> repo_manager) exits 0; `fail_fast` stops at the first failure. |
| 4101 | `BSM_SVT_CLEANUP_V001` | `test_postcondition_build_stream_cleanup` | `cleanup/postconditions` | — | verify | BuildStream containers, watcher, API port and runtime dirs removed; Postgres data and credentials match their flags. |
| 4102 | `BSM_SVT_CLEANUP_V002` | `test_postcondition_orchestrator_cleanup` | `cleanup/postconditions` | — | verify | OpenCHAMI and OpenLDAP containers and units gone; credentials match the flag. |
| 4103 | `BSM_SVT_CLEANUP_V003` | `test_postcondition_image_build_manager_cleanup` | `cleanup/postconditions` | — | verify | MinIO, registry, ports and build status gone; credentials match the flag. |
| 4104 | `BSM_SVT_CLEANUP_V004` | `test_postcondition_repo_manager_cleanup` | `cleanup/postconditions` | — | verify | Pulp container, quadlet and data gone; logs and credentials match their flags. |

Scenario details: [prepare_base](prepare_base/README.md),
[installation](installation/README.md), [auto_cleanup](auto_cleanup/README.md),
[cleanup](cleanup/README.md).

## Dependencies between test cases

| Test | Depends on | Effect when the dependency fails |
|---|---|---|
| Every test of a scenario | The scenario precheck `E001` | Skipped |
| A scenario's `V…` cases | The scenario entry point `E002` | Skipped |
| `BSM_SVT_INSTALLATION_V004` (deploy) | `BSM_SVT_INSTALLATION_V003` (build) in the same run | Skipped |
| Cadence `V005`–`V007` | — (independent: the cadence cycle builds and deploys by itself) | Run |

These skips apply even with `continue_on_failure: true`; with `false` every
test after the first failure is skipped as well. See
[docs/test_config.md](../docs/test_config.md#continue_on_failure).

## Verify-only mode

Set `pipeline.build_job_id`, `deploy_job_id` or `cadence_job_id` in
`test_config.yml` to a BuildStream job UUID from `build_stream_db.jobs` to
verify an existing run: nothing is committed or triggered. For deploy, use
the build job of the deployed image group (`image_groups.job_id`).

## Running a subset

```bash
./run_validation.sh svt_build_stream installation verify --marker cadence   # cadence V005-V007
./run_validation.sh svt_build_stream installation verify --suite build      # V003
./run_validation.sh svt_build_stream installation verify --marker pipeline  # V003-V005
./run_validation.sh svt_build_stream prepare_base verify                    # readiness V001-V003
```
