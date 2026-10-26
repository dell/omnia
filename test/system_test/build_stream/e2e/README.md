# BuildStream System Test — E2E Test Cases

The e2e tree follows the BuildStream lifecycle on one OIM. Each scenario
directory owns its test cases. Test files hold case selection and ordering;
reusable behavior lives in `library/functions`, messages in
`library/messages`, and IDs, commands and SQL in `library/vars`.

## Scenario shape (same as the module FVT)

Every scenario has the same three parts:

| Part | Runner phase | Marker | What it does |
|---|---|---|---|
| Precheck (`test_precheck.py`) | `exec` | `deploy`, `precheck` | Proves, without changing anything, that the entry point can run unattended. If it does not pass, the rest of the scenario is skipped. |
| Entry point (`test_playbook.py` / `test_auto_cleanup.py`) | `exec` | `deploy` | Runs `omnia.sh`, the playbook or the cleanup pass. Nothing else. |
| Verification suites (`<suite>/test_<suite>.py`) | `verify` | — | Verify what the entry point did, on the live system. |

`auto_cleanup` and `cleanup` verification needs facts that only exist during
exec (the image-group snapshot, the paths to preserve). The exec test
records them in `reports/state/<scenario>.json` (git-ignored, mode 0600, no
secrets); the precheck clears the previous file, and verification is
skipped when no exec state exists.

## Test-case identification

IDs use `TC_<SCENARIO>_<NUMBER>` (`PB` prepare_base, `IN` installation, `AC`
auto_cleanup, `CL` cleanup) in execution order: `001` is the precheck, `002`
the entry point, then the verification cases. They are registered in
`library/vars/test_case_vars.py`. Every test also carries `br_86010`, the
traceability marker for the SysQA system test plan TEST-BR-86010 (NERSC
Backend Buildstream): `--marker br_86010` selects the whole suite.

## Effective execution order

```text
prepare_base   precheck -> omnia.sh --prepare-base -> readiness
installation   precheck -> build_stream.yml -> health -> repository
               -> build -> deploy -> cadence
auto_cleanup   precheck -> cleanup pass -> verification
cleanup        precheck -> domain cleanups -> postconditions
```

Order is the global `order` marker (one band per scenario: +1 precheck, +2
entry point, +100 per verification suite); it does not depend on directory
names. `auto_cleanup` and `cleanup` are never part of an untagged run.

## Test-case registry

All cases carry `e2e`, `br_86010` and `sanity`. "BR-86010 case" names the
plan case a test provides evidence for; "—" is a prerequisite of the plan.

| Order | TC ID | Test | Scenario / suite | Markers | Phase | Pass criteria | BR-86010 case |
|---:|---|---|---|---|---|---|---|
| 1001 | `TC_PB_001` | `test_precheck_prepare_base` | `prepare_base` | `deploy`, `precheck` | exec | `OMNIA_DATA_PATH`, `OMNIA_PROJECT_NAME`, `OMNIA_VENV_PATH` set; venv and `omnia.sh` present; repo_manager, image_build_manager and orchestrator credential stores (file + key) present. | — |
| 1002 | `TC_PB_002` | `test_prepare_base` | `prepare_base` | `deploy` | exec | `./omnia.sh --prepare-base` exits 0. | — |
| 1101 | `TC_PB_003` | `test_repo_manager_ready` | `prepare_base/readiness` | — | verify | Pulp quadlet present, `pulp.service` active, Pulp container running. | — |
| 1102 | `TC_PB_004` | `test_image_build_manager_ready` | `prepare_base/readiness` | — | verify | MinIO and registry containers running, units active, ports 9000/9001/5000 listening. | — |
| 1103 | `TC_PB_005` | `test_orchestrator_ready` | `prepare_base/readiness` | — | verify | All 14 OpenCHAMI units and `openchami-cert-renewal.timer` active; 9 long-running containers running (healthcheck honoured); data and `haproxy-certs` volumes present; OpenLDAP quadlet, `omnia_auth.service` and healthy container when `orchestrator_state.yml` sets `openldap_support` (product component spec). | — |
| 2001 | `TC_IN_001` | `test_precheck_installation` | `installation` | `deploy`, `precheck` | exec | Catalog selection resolves to a valid catalog; `CATALOG_FILE_PATH` valid; `build_stream_config.yml` and the BuildStream credential store present; at least 2 PXE node rows; `build_stream.yml --tags precheck` exits 0. | — |
| 2002 | `TC_IN_002` | `test_build_stream_installation` | `installation` | `deploy` | exec | Catalog installed at `CATALOG_FILE_PATH` (a different one backed up); `build_stream.yml` exits 0. | — |
| 2101 | `TC_IN_003` | `test_build_stream_services` | `installation/health` | — | verify | `omnia_build_stream`, `omnia_postgres` running; playbook-watcher active; all `build_stream_db` tables; API `/health` healthy. | — |
| 2201 | `TC_IN_004` | `test_gitlab_repository` | `installation/repository` | — | verify | Project reachable; the 7 `.gitlab-ci*.yml` files and `omnia.env` present; every domain input file found on the OIM is in `input/<domain>/` with identical content. | — |
| 2301 | `TC_IN_005` | `test_build_pipeline` | `installation/build` | `pipeline` | verify | `upload`, `parse-catalog`, `create-local-repository`, `build-image` COMPLETED; GitLab pipeline success; jobs/job_stages/image_groups/images rows and the API job view agree. | `tc_bsb_pipeline_stages` (build, partial) |
| 2401 | `TC_IN_006` | `test_deploy_pipeline` | `installation/deploy` | `pipeline` | verify | `deploy`, `restart`, `validate` COMPLETED; image group PASSED; deploy_count incremented. | `tc_bsb_pipeline_stages` (deploy, partial) |
| 2501 | `TC_IN_007` | `test_cadence_pipeline` | `installation/cadence` | `pipeline`, `cadence` | verify | Repo sync succeeds, `cadence_catalog_rhel.json` committed with the bumped version, all seven stages COMPLETED, image group PASSED. | `tc_bsb_cadence_build` (partial) |
| 3001 | `TC_AC_001` | `test_precheck_auto_cleanup` | `auto_cleanup` | `deploy`, `precheck` | exec | Retention settings valid; `omnia_build_stream` running; playbook-watcher active. Skipped when `auto_cleanup_enabled` is false. | — |
| 3002 | `TC_AC_002` | `test_auto_cleanup` | `auto_cleanup` | `deploy`, `destructive` | exec | One `cleanup_cron.main()` pass finishes without a fatal error and no submitted group is left CLEANING. | `tc_bsb_retention_prune` |
| 3101 | `TC_AC_003` | `test_auto_cleanup_result` | `auto_cleanup/verification` | — | verify | Exactly the expected groups submitted and CLEANED with tombstoned jobs, audit events, no S3 objects or NFS artifacts left; every other group and object untouched. | `tc_bsb_retention_prune`; `tc_bsb_retention_deployed_kept`, `tc_bsb_retention_min_keep`, `tc_bsb_retention_protected` (data-dependent) |
| 4001 | `TC_CL_001` | `test_precheck_cleanup` | `cleanup` | `deploy`, `precheck` | exec | At least one block enabled; omnia.env variables set; each enabled playbook present. | — |
| 4002 | `TC_CL_002` | `test_full_cleanup` | `cleanup` | `deploy`, `destructive` | exec | Each enabled playbook (build_stream -> orchestrator -> image_build_manager -> repo_manager) exits 0; `fail_fast` stops at the first failure. | — |
| 4101 | `TC_CL_003` | `test_build_stream_cleanup` | `cleanup/postconditions` | — | verify | BuildStream containers, watcher, API port, runtime dirs removed; Postgres data and credentials match their flags. | — |
| 4102 | `TC_CL_004` | `test_orchestrator_cleanup` | `cleanup/postconditions` | — | verify | OpenCHAMI and OpenLDAP containers/units gone; credentials match the flag. | — |
| 4103 | `TC_CL_005` | `test_image_build_manager_cleanup` | `cleanup/postconditions` | — | verify | MinIO, registry, ports and build status gone; credentials match the flag. | — |
| 4104 | `TC_CL_006` | `test_repo_manager_cleanup` | `cleanup/postconditions` | — | verify | Pulp container, quadlet and data gone; logs and credentials match their flags. | — |

Scenario details: [prepare_base](prepare_base/README.md),
[installation](installation/README.md), [auto_cleanup](auto_cleanup/README.md),
[cleanup](cleanup/README.md).

## Verify-only mode

Set `pipeline.build_job_id`, `deploy_job_id` or `cadence_job_id` in
`test_config.yml` to a BuildStream job UUID from `build_stream_db.jobs` to
verify an existing run. Nothing is committed or triggered. For deploy, use the
build job of the deployed image group (`image_groups.job_id`). With a job ID
empty, the pipeline verification cases commit to GitLab and trigger the
pipeline themselves (they exercise the installed BuildStream).
