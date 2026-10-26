# installation

| Order | TC ID | Test | Suite | Phase |
|---:|---|---|---|---|
| 2001 | `TC_IN_001` | `test_precheck_installation` | root | exec |
| 2002 | `TC_IN_002` | `test_build_stream_installation` | root | exec |
| 2101 | `TC_IN_003` | `test_build_stream_services` | `health` | verify |
| 2201 | `TC_IN_004` | `test_gitlab_repository` | `repository` | verify |
| 2301 | `TC_IN_005` | `test_build_pipeline` | `build` | verify |
| 2401 | `TC_IN_006` | `test_deploy_pipeline` | `deploy` | verify |
| 2501 | `TC_IN_007` | `test_cadence_pipeline` | `cadence` | verify |

## Precheck — TC_IN_001

1. `installation.catalog` (a number resolved on the OIM in
   `./omnia.sh --list-catalogs` order, or a full path) is a valid catalog and
   `CATALOG_FILE_PATH` is an absolute `.json` path.
2. `build_stream_config.yml` and the BuildStream credential store exist.
3. `pxe_mapping_file.csv` has at least two node rows (the deploy test swaps two).
4. `build_stream.yml --tags precheck` passes: repo_manager and
   image_build_manager are ready for BuildStream.

## Entry point — TC_IN_002

Install the catalog at `CATALOG_FILE_PATH` (a different active catalog is
kept as `<file>.backup.<timestamp>`) and run `build_stream.yml` (default flow).

## Verification

| Suite | Checks |
|---|---|
| `health` | `omnia_build_stream` and `omnia_postgres` running, playbook-watcher active, every `build_stream_db` table, API `/health` healthy |
| `repository` | Project reachable; the 7 `.gitlab-ci*.yml` files and `omnia.env`; every domain input file present on the OIM synced to `input/<domain>/` with identical content (runs before the pipelines change GitLab) |
| `build` | Bump the catalog version, commit `catalog_rhel.json`; upload, parse-catalog, create-local-repository, build-image |
| `deploy` | Swap two rows of `input/orchestrator/pxe_mapping_file.csv`, select the image group, play deploy; deploy, restart, validate |
| `cadence` | `trigger_cadence.sh` (SIGUSR1), follow the playbook-watcher journal; all seven build + deploy stages |

The pipeline suites trigger when their `pipeline.<name>_job_id` is empty and
only verify that job when it is set. All three also check the GitLab
pipeline result, the `jobs`, `job_stages`, `image_groups` and `images` rows
and the API job view. `pipeline.allow_pipeline_cancel` decides whether busy
GitLab pipelines are cancelled or reported.

```bash
./run_validation.sh e2e_build_stream installation test
./run_validation.sh e2e_build_stream installation verify --suite health
./run_validation.sh e2e_build_stream installation verify --suite cadence
```
