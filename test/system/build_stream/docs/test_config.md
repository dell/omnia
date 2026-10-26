# test_config.yml — Configuration Reference

`test_config.yml` holds the non-secret settings of the suite. Unknown keys
are rejected at session start with the list of supported keys. Secrets never
belong in this file.

## Connection

`clone_path` is required (absolute) when `oim_server_ip` is set.

| Field | Default | Purpose |
|---|---|---|
| `oim_server_ip` | `""` | Empty runs on this host; an address runs every command over SSH. |
| `oim_ssh_user` | `root` | SSH user (remote mode). |
| `oim_ssh_port` | `22` | SSH port (remote mode). |
| `clone_path` | `/omnia` | Omnia checkout on the remote OIM; ignored locally. |

Password-based SSH uses `oim_password` from `test_creds.yml`.

## installation

| Field | Default | Purpose |
|---|---|---|
| `catalog` | `1` | Number from `./omnia.sh --list-catalogs` (resolved on the OIM) or the full path of a catalog on the OIM. |

## pipeline

| Field | Default | Purpose |
|---|---|---|
| `allow_pipeline_cancel` | `false` | Cancel busy GitLab pipelines before a trigger; false fails and lists them. |
| `build_job_id` | `""` | Verify-only job UUID for the build pipeline. |
| `deploy_job_id` | `""` | Verify-only job UUID for deploy (the image group's build job). |
| `cadence_job_id` | `""` | Verify-only job UUID for the cadence pipeline. |
| `poll_interval` | `30` | Seconds between pipeline/DB polls (also used by auto_cleanup). |

TLS has no setting. The BuildStream API is verified against the certificate
`build_stream.yml` generates (`<OMNIA_DATA_PATH>/build_stream_ssl/ssl/bs_cert.pem`),
the same one the pipelines pass to `curl --cacert`. GitLab is not verified,
matching Omnia's own playbooks (`validate_certs: false`).

## auto_cleanup

No settings. The rules come from the `retention` group of the project
`build_stream_config.yml`; the scenario is skipped when `auto_cleanup_enabled`
is false.

## cleanup

| Field | Default | Purpose |
|---|---|---|
| `fail_fast` | `true` | Stop at the first domain whose cleanup playbook fails; the rest are not run (and their verification is skipped). |
| `<block>.enabled` | `true` | Clean and verify that domain. |
| `cleanup_build_stream.postgres_backup` | `false` | true keeps the Postgres data and volumes. |
| `*.cleanup_credentials` | `true` | true deletes that domain's credential store. |
| `cleanup_orchestrator.cleanup_slurm` / `cleanup_k8s` | `true` | Delete Slurm / Kubernetes data on the shared path. |
| `cleanup_repo_manager.cleanup_logs` | `true` | Delete the repo_manager log directory. |

The order is fixed: build_stream -> orchestrator -> image_build_manager ->
repo_manager.

## Report

| Field | Default | Purpose |
|---|---|---|
| `report_path` | `/opt/omnia/reports` | Directory for the JSON and HTML reports. |
| `report_name` | `system_build_stream_report` | Report file name without extension. |
| `run_id` | `""` | Run identifier in the report; empty uses the timestamp. |
