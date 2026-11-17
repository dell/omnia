# `test_config.yml`

This file contains non-sensitive Build Stream automation settings. Every
field is also explained by the comments in the file itself.

| Field | Required | Meaning |
|---|---:|---|
| `oim_server_ip` | yes | Empty for local execution; IPv4 address for remote execution |
| `oim_ssh_user` | remote | SSH user for the execution OIM |
| `oim_ssh_port` | remote | SSH port |
| `clone_path` | remote | Absolute path of the omnia checkout on the remote OIM |
| `dataset` | yes | Empty for canonical source input, or a generated dataset name |
| `sync_build_stream_input` | yes | Whether execution may synchronize selected input |
| `installation.catalog` | execute pipelines | Catalog the build suites (and the cancellation NFT) commit as `catalog_rhel.json`: bundled catalog number (`./omnia.sh --list-catalogs`) or the full path of a catalog on the OIM |
| `installation.cadence_catalog` | no (default `""`) | Catalog the cadence suites upload as `cadence_catalog_rhel.json`, same format as `installation.catalog`; empty = the same catalog as `installation.catalog` |
| `pipeline.allow_pipeline_cancel` | no (default `true`) | `true`: running GitLab pipelines are listed and cancelled before a commit or trigger; `false`: the step fails and lists them |
| `pipeline.build_job_id` | no (default `""`) | Verify-only job for `build_automatic` and `build_manual`; empty = trigger a new build |
| `pipeline.deploy_job_id` | no (default `""`) | Verify-only job for `deploy_automatic` and `deploy_manual` (the build job of the deployed image group); empty = trigger a new deploy |
| `pipeline.cadence_job_id` | no (default `""`) | Verify-only job for `cadence`; empty = trigger a cadence cycle |
| `pipeline.deploy_image_group_id` | deploy-only runs | Image group the deploy suites deploy when no build suite ran in the same run. Empty: the deploy trigger test fails with "image name is not present"; not in `build_stream_db`: "requested image not found". Ignored when a build suite ran: its image group is deployed, and a failed build skips every deploy test |
| `pipeline.cleanup_image_group_id` | no | Image group the `pipeline_cleanup` suite deletes; empty = the newest image group in status BUILT, PASSED or FAILED |
| `pipeline.poll_interval` | no (default 30) | Seconds between pipeline and DB polls |
| `debug_mode` | no (default `true`) | `true` streams pipeline stage, cadence sync and cleanup playbook logs live; `false` prints `tail -f <log>` and status lines |
| `cleanup.postgres_backup` | no (default `false`) | Passed to `--tags cleanup`; `false` deletes the Postgres data and volumes, `true` keeps them |
| `cleanup.cleanup_credentials` | no (default `true`) | Passed to `--tags cleanup`; `true` deletes the BuildStream credentials, `false` keeps them |
| `job_id` | NFT | Job the resilience NFTs inspect when they did not create one (the cancellation NFT commits `installation.catalog`) |
| `nft_allow_*` | NFT | Explicit permission for each disruptive NFT operation (default `false`) |
| `nft_recovery_timeout_seconds` | NFT | Recovery wait, integer >= 10 |
| `report_path` | yes | Absolute HTML/JSON report directory; environment variables are expanded |
| `report_name` | yes | Safe report base name |
| `run_id` | no | Identifier used to group scenario reports |

The installation, pipeline, cleanup and debug settings are validated at
session start; an invalid value (unknown key, catalog that is neither a number
nor an absolute path, malformed job or image group ID) stops the run before
any test starts.

Which image group a deploy suite deploys:

| Run | Image group deployed |
|---|---|
| Build and deploy in one run (`execute test`, `--marker automatic_execution`, ...) | The one the build suite built in this run (`deploy_automatic` <- `build_automatic`, `deploy_manual` <- `build_manual`, else the other build suite) |
| Same, but the build failed | None: every deploy test is skipped with the reason |
| Deploy only (`--suite deploy_automatic`, `--marker deploy_pipeline`) | `pipeline.deploy_image_group_id`; the test fails when it is empty or not found |
| Verify-only (`pipeline.deploy_job_id` set) | The image group of that job; nothing is triggered |

Input synchronization is performed only when
`sync_build_stream_input: true`. An empty dataset then uses
`src/build_stream/input/`; otherwise it uses
`datasets/<dataset>/input/`.

Credentials must never be added to this file.
