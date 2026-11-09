# `build_stream_test_config.yml`: every setting

`build_stream_test_config.yml` holds the settings of the SVT **theme** `build_stream`: which
catalogs the stages use, what the cleanup removes, and where the report goes. (The cluster
values are in `user_inputs.yml`, see [SETUP.md](SETUP.md); passwords are in neither file.)
Its name is `<theme>_test_config.yml`, so another theme has its own file. The file has four
blocks: `build_stream`, `cleanup`, `report`, and inside `cleanup` the SVT-only `nfs` block.

## How it is used

- `./setup_env.sh --configure` (the first step of `./setup_env.sh`) reads it, checks it, and
  writes parts of it into the FVT suites' `test/<suite>/test_config.yml`, so they override the
  suites' own values: the `build_stream` block into `test/build_stream`, each `cleanup.<suite>`
  block into that suite, and the report settings into every suite.
- Only a value that differs is rewritten, and the comments and layout of the suite's file stay
  as they were. This edits the tracked `test/<suite>/test_config.yml` files of the checkout.
- **A change needs a new run.** The file's checksum is kept with the run: after you edit it,
  every later step says "changed after the last configure" until you run
  `./setup_env.sh --configure` (or `./setup_env.sh`), which starts a new run.
- Only the keys listed here are accepted; an unknown key, a wrong type or an invalid catalog
  stops `--configure` and names the key.
- In the GitLab pipeline each cluster has its own copy,
  `clusters/<name>/svt/build_stream_test_config.yml` in the project; the checkout job copies it
  into the OIM before every run (see [PIPELINE.md](PIPELINE.md)).

## `build_stream`

Written into `test/build_stream/test_config.yml`.

| Key | Default | Meaning | FVT key |
|---|---|---|---|
| `catalog` | `29` | The catalog the `build_deploy` stage commits to GitLab as `catalog_rhel.json`. A number from `./omnia.sh --list-catalogs` (29 = `rhel/10.2/slurm_service_k8s_x86_64_no_vast.json`) or the absolute path of your own catalog on the OIM. `./setup_env.sh --configure` checks the number against `--list-catalogs` | `installation.catalog` |
| `cadence_catalog` | `29` | The catalog the `cadence` stage uploads as `cadence_catalog_rhel.json`. Same format; `""` = the same as `catalog` | `installation.cadence_catalog` |
| `allow_pipeline_cancel` | `true` | `true`: GitLab pipelines still running or pending before a commit or a trigger are cancelled and the test continues. `false`: nothing is cancelled; the test fails and lists them | `pipeline.allow_pipeline_cancel` |
| `debug_mode` | `false` | `true`: the stage, cadence and cleanup playbook logs are streamed live into the test output. `false`: only progress lines and a status line per poll. The FVT suite itself defaults to `true`, so `--configure` sets it to `false` unless you change it here | `debug_mode` (top level) |

## `cleanup`

`./setup_env.sh --cleanup` (and `--force`, which the pipeline's initialization job runs) removes
the previous installation, in this order, each with that suite's own cleanup FVT:

`build_stream`, `telemetry`, `orchestrator`, `image_build_manager`, `repo_manager`, then
`main` (`omnia.sh --cleanup`), then the NFS shares.

Every suite block has `enabled` (SVT only, default `true`): `false` skips that suite's cleanup
step. The other keys are the suite's own flags, written into its `test_config.yml` before its
cleanup runs. All values are booleans.

| Suite | Key | Default here | Meaning |
|---|---|---|---|
| `build_stream` | `postgres_backup` | `false` | `false`: delete the Postgres data directory and the `omnia_postgres` volumes. `true`: keep them (the database is reused by the next install) |
| | `cleanup_credentials` | `true` | Delete the BuildStream credential files and keys. `false` keeps them, so the next install does not ask again |
| `telemetry` | `delete_sinks_volume` | `true` | Also delete the sink PVCs (Kafka, VictoriaMetrics, VictoriaLogs) and the log, input and output directories. A complete reset needs this: `omnia.sh --cleanup --all` refuses while telemetry's `log` and `output` folders hold files. The FVT default is `false` |
| | `cleanup_credentials` | `true` | Delete the telemetry credential files |
| | `cleanup_logs` | `true` | Delete the telemetry log directory |
| `orchestrator` | `cleanup_credentials` | `true` | Remove `orchestrator_credentials.yml`, its vault key and lock files |
| | `cleanup_slurm` | `true` | Delete the Slurm shared data (the Slurm storage is unmounted and its fstab entry removed either way) |
| | `cleanup_k8s` | `true` | Delete the Kubernetes shared data (same) |
| | `cleanup_benchmark_tools` | `true` | Remove the tools downloaded in the benchmark FVT workspaces |
| `image_build_manager` | `cleanup_credentials` | `true` | Remove its credential store |
| `repo_manager` | `cleanup_credentials` | `true` | Remove its credential store |
| `main` | `cleanup_all` | `true` | `true`: a **complete reset**: every `src/<domain>/domain-init.sh --cleanup`, then `omnia.sh --cleanup --all`, which deletes the whole `OMNIA_DATA_PATH` (`/opt/omnia`), the credential stores included (whatever `cleanup_credentials` says), and the next install starts from nothing. `false`: `omnia.sh --cleanup` removes the Omnia venv, `/etc/omnia/omnia.env`, `omnia-cli` and the dependency cache; the data is kept |

- **Telemetry** is cleaned before the orchestrator because it runs on the Kubernetes cluster
  the orchestrator deploys. This theme does not deploy telemetry, so the step runs only when
  telemetry holds deployed state (a file under `<data>/telemetry/output` or `log`, the rule
  `omnia.sh --cleanup --all` applies); otherwise it is skipped and the log says so.
- **Keeping credentials:** `cleanup_credentials: false` keeps a store, but a `cleanup_all`
  reset deletes it anyway (the cleanup warns).
- **A full reset refuses** while a domain still holds deployed state; the report's cleanup
  block shows which.

### `cleanup.nfs`

SVT only: written into no suite. Data left on the NFS shares survives a reinstall, so the cleanup
empties them (the confirmation lists them; `--cleanup --dry-run` shows them too).

| Key | Default | Meaning |
|---|---|---|
| `slurm_share` | `true` | Empty the share of the `storage_config.yml` mount named `nfs_slurm` |
| `k8s_share` | `true` | Empty the share of the mount named `nfs_k8s` |

How it works: every share is first mounted read-only and unmounted again, so a share that cannot
be reached fails the cleanup before anything is deleted; then it is mounted on a private
temporary folder, emptied completely (the export itself stays) and unmounted. A mount that is
absent or not `host:/export` is skipped; system directories and an export on the OIM that
contains the checkout or `OMNIA_DATA_PATH` are refused. If a live node still writes to the share
(a kubelet), the share is emptied again, up to 6 passes, and a persistent failure names the
connected NFS clients. It needs root, `nfs-utils` and an export without root squash.
Details: [SETUP.md](SETUP.md).

## `report`

One folder and one SVT report per run.

| Key | Default | Meaning |
|---|---|---|
| `report_path` | `""` = `test/system_test/reports` | Parent of the run folders (`<report_path>/<run_id>/`). Absolute, or relative to `test/system_test`. Keep it outside `OMNIA_DATA_PATH`: a `cleanup_all` reset deletes that directory, and the cleanup refuses when the report folder is inside it |
| `report_name` | `""` = `svt_build_stream_report` | File name of the SVT report (`.json`, `.html`) in the run folder. Letters, digits, `_`, `-` |
| `run_id` | `""` = a new `svt-<UTC time>` per configure | The run id. A fixed value reuses that run folder, for the same theme only. Letters, digits, `.`, `_`, `-` |

The same three settings are also written into every suite's `test_config.yml`, so the FVT results
of each step go to `<run folder>/fvt/` and appear in the SVT report.

## Examples

Keep the databases and credentials, empty nothing on NFS (a partial cleanup):

```yaml
cleanup:
  build_stream: {enabled: true, postgres_backup: true, cleanup_credentials: false}
  main: {enabled: true, cleanup_all: false}
  nfs: {slurm_share: false, k8s_share: false}
```

Skip a suite's cleanup, for example when you test only repo_manager:

```yaml
cleanup:
  orchestrator: {enabled: false}
  image_build_manager: {enabled: false}
```

A different catalog for the build and the cadence:

```yaml
build_stream:
  catalog: 29
  cadence_catalog: "/root/catalogs/my_cadence_catalog.json"
```
