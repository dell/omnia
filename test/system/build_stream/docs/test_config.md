# test_config.yml — Configuration Reference

`test_config.yml` holds every non-secret setting of the BuildStream SVT
suite. It is validated at session start: a wrong type (for example
`debug_mode: "true"` in quotes) or an unknown key inside a block stops the
run with a message naming the field. Secrets never belong in this file; they
live in the credential stores described in [test_creds.md](test_creds.md).

Back to the [suite README](../README.md).

## Connection

| Field | Default | Purpose |
|---|---|---|
| `oim_server_ip` | `""` | Empty runs every command on this host (local mode); an address runs them over SSH. |
| `oim_ssh_user` | `root` | SSH user (remote mode). |
| `oim_ssh_port` | `22` | SSH port (remote mode). |
| `clone_path` | `/omnia` | Absolute path of the omnia checkout on the remote OIM; required in remote mode, ignored locally. |

Password-based SSH uses `oim_password` from `test_creds.yml`.

## installation

| Field | Default | Purpose |
|---|---|---|
| `catalog` | `29` | The catalog under test: a number from `./omnia.sh --list-catalogs` (resolved on the OIM at run time) or the full path of your own catalog on the OIM. |

The same catalog is used everywhere:

| Test | What it does with the catalog |
|---|---|
| Installation entry point (`BSM_SVT_INSTALLATION_E002`) | Installs it at `CATALOG_FILE_PATH`; a different active catalog is backed up as `<file>.backup.<timestamp>`. |
| Build pipeline (`BSM_SVT_INSTALLATION_V003`) | Commits it to GitLab as `catalog_rhel.json` with the next unused version, which starts the build pipeline. |
| Cadence pipeline (`V005`) and cadence re-enable (`V007`) | Uploads it to GitLab as `cadence_catalog_rhel.json` with `[skip ci]` (no pipeline) one minor below the next unused version; the cadence cycle fetches it, syncs it and bumps it to that next version, and its commit starts the cadence pipeline. |

**Next unused version.** The tests never re-commit a version that is already
in use. They take the highest `X.Y` version of the same catalog identifier
found in the selected file, GitLab `catalog_rhel.json`, GitLab
`cadence_catalog_rhel.json`, the active catalog at `CATALOG_FILE_PATH` and
`build_stream_db.image_groups`, add one to the minor number and skip any
version that already has an image group. Example: the selected file says
`1.0`, GitLab already has `1.1`, so the build commits `1.2`. Versions of
other catalog identifiers are ignored. The report shows every version found
(`Versions in use`).

## pipeline

| Field | Default | Purpose |
|---|---|---|
| `allow_pipeline_cancel` | `false` | `true` cancels running or pending GitLab pipelines before a trigger; `false` fails the test and lists them. |
| `build_job_id` | `""` | Empty: trigger the build pipeline. A BuildStream job UUID: only verify that job. |
| `deploy_job_id` | `""` | Same for deploy; use the build job of the deployed image group (`image_groups.job_id`). |
| `cadence_job_id` | `""` | Same for the cadence pipeline. |
| `poll_interval` | `30` | Seconds between pipeline and database polls (also used by auto_cleanup). |

List job UUIDs on the OIM with:

```bash
podman exec omnia_postgres sh -c 'psql -U "$POSTGRES_USER" -d build_stream_db -c "select job_id, job_state, created_at from jobs order by created_at desc"'
```

TLS has no setting. The BuildStream API is verified against the certificate
`build_stream.yml` generates (`<OMNIA_DATA_PATH>/build_stream_ssl/ssl/bs_cert.pem`),
the one the pipelines pass to `curl --cacert`. GitLab is not verified,
matching Omnia's own playbooks (`validate_certs: false`).

## auto_cleanup

No settings. The rules come from the `retention` group of the project
`build_stream_config.yml`; the scenario is skipped when
`auto_cleanup_enabled` is false.

## cleanup

| Field | Default | Purpose |
|---|---|---|
| `fail_fast` | `true` | Stop at the first domain whose cleanup playbook fails; the remaining domains are not cleaned or verified. |
| `<block>.enabled` | `true` | Clean and verify that domain. |
| `cleanup_build_stream.postgres_backup` | `false` | `true` keeps the Postgres data and volumes. |
| `*.cleanup_credentials` | `true` | `true` deletes that domain's credential store. |
| `cleanup_orchestrator.cleanup_slurm` / `cleanup_k8s` | `true` | Delete the Slurm / Kubernetes data on the shared path. |
| `cleanup_repo_manager.cleanup_logs` | `true` | Delete the repo_manager log directory. |

The order is fixed: build_stream -> orchestrator -> image_build_manager ->
repo_manager. The full flow (`./run_validation.sh svt_build_stream test`)
ends with this scenario, so disable the domains you want to keep.

## Run control

| Field | Default | Purpose |
|---|---|---|
| `continue_on_failure` | `false` | What happens after a failure (below). |
| `debug_mode` | `false` | How much log output pipeline and cadence tests print (below). |

### continue_on_failure

| Value | Behaviour |
|---|---|
| `false` | The run stops at the first failure. In a pytest session every remaining test is skipped with *"… failed and continue_on_failure is false"*; the runner does not start the next scenario or the verify phase. |
| `true` | Independent tests keep running: the other scenarios, the cadence tests and auto_cleanup. |

Dependent tests are skipped in both modes because they cannot pass. The skip
says which test they depend on:

| Dependent test | Skipped when |
|---|---|
| Every test of a scenario | Its precheck (`E001`) did not pass |
| A scenario's verification cases | Its entry point (`E002`) failed |
| Deploy pipeline (`BSM_SVT_INSTALLATION_V004`) | The build pipeline test (`V003`) failed in the same run |

The cadence pipeline and the cadence disable/re-enable tests do not depend
on the build pipeline test: the cadence cycle builds and deploys the
selected catalog by itself.

### debug_mode

| Value | Output |
|---|---|
| `true` | Every pipeline stage playbook log (`create-local-repository`, `build-image`, `deploy`, …) and the cadence repo sync log stream live as `│` lines, like a playbook run. Each line prints the moment Ansible writes it (`tail -F` in the background, no polling interval); long lines wrap at `line_width` (160). |
| `false` | Only progress lines are printed. While a stage or the cadence sync runs they end with `tail -f <log>`, so you can follow the log in another terminal. |

The log of the current attempt is picked automatically: the playbook watcher
names logs `<stage>_<playbook>_<YYYYmmdd_HHMMSS>_attempt<N>.log` under
`/var/log/omnia/<domain>/`; logs that started before the stage was monitored
are ignored, then the attempt recorded in `job_stages` (or the highest
attempt) and the newest timestamp win.

In both modes, the cadence tests print every playbook-watcher journal record
about the cadence cycle (`[journal] … cadence_manager - INFO - …`) and the
exact trigger command they run.

## Report

| Field | Default | Purpose |
|---|---|---|
| `report_path` | `/opt/omnia/reports` | Directory for the JSON and HTML reports. |
| `report_name` | `system_build_stream_report` | Report file name without extension (prefixed with the CI pipeline ID in GitLab CI). |
| `run_id` | `""` | Run identifier in the report; empty uses the current timestamp. |
