# `test_config.yml`

This file contains non-sensitive Build Stream automation settings.

| Field | Required | Meaning |
|---|---:|---|
| `oim_server_ip` | yes | Empty for local execution; IPv4 address for remote execution |
| `oim_ssh_user` | remote | SSH user for the execution OIM |
| `oim_ssh_port` | remote | SSH port |
| `clone_path` | remote | Absolute non-root destination for the synchronized checkout |
| `dataset` | yes | Empty for canonical source input, or a generated dataset name |
| `project_name` | yes | Safe project namespace matching the execution OIM |
| `sync_build_stream_input` | yes | Whether execution may synchronize selected input |
| `report_path` | yes | HTML/JSON report directory |
| `report_name` | yes | Safe report base name |
| `report_id` | no | Identifier used to group scenario reports |
| `allow_pipeline_cancel` | yes | Explicit permission to cancel an existing pipeline |
| `catalog_path` | build pipeline exec/test | Catalog path relative to `src/main/samples/catalogs/` |
| `job_id` | deploy pipeline | Mandatory BSM job; must map to exactly one image group |

Input synchronization is performed only when
`sync_build_stream_input: true`. An empty dataset then uses
`src/build_stream/input/`; otherwise it uses
`datasets/<dataset>/input/`.

Credentials must never be added to this file.

Deploy automation never falls back to the latest image. It fails when
`job_id` is empty or invalid, when no image group is mapped, when multiple
groups are mapped, or when the mapped group is not `BUILT` before execution.
Verification resolves the same mapping and never writes or selects a new job.
It also discovers the matching GitLab dynamic child and summary job from the
successful image-selection job, so no GitLab pipeline IDs are user inputs.
