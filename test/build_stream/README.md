# Build Stream test automation

Functional automation for the Omnia `build_stream` domain.
It uses the shared `omnia_auto` package for runner dispatch, target access,
synchronization, logging, and HTML/JSON reporting.

## Scope

The automation covers the complete BuildStream lifecycle:

| Scenario | Purpose | Selection |
|---|---|---|
| `buildstream_install` | Install and validate BuildStream, PostgreSQL, GitLab, the runner, TLS, queue access, and repository content | Default lifecycle |
| `build_pipeline` | Upload a catalog, build images, and validate database, registry, and S3 artifacts | Default lifecycle |
| `deploy_pipeline` | Select the image group bound to `job_id`, run deploy/restart/validate, and verify the final state | Default lifecycle |
| `buildstream_cleanup` | Remove and validate GitLab and BuildStream resources | Explicit tag |
| `cleanup_pipeline` | Delete one built image group's database, S3, and registry artifacts through GitLab CI | Explicit suite |
| `manual` | Trigger build or deploy with `PIPELINE_TYPE` instead of a catalog-change pipeline | Explicit suite |

The cleanup scenario is excluded from the default lifecycle. Manual cases use
the separate `manual` marker and therefore do not run with `--marker sanity`.

## First use

```bash
cd test/build_stream
./setup_env.sh --venv
source .venv/bin/activate
```

For password-based SSH to a remote execution OIM, configure the local,
gitignored transport credential:

```bash
./setup_env.sh --set-creds
```

Build Stream product credentials are separate from transport credentials. Run
this command on the execution OIM after sourcing `/etc/omnia/omnia.env`:

```bash
./setup_env.sh --set-domain-creds
```

The BuildStream authentication username and password are required. The helper
also generates the Argon2 registrar hash required by `/api/v1/auth/register`.

That command writes the encrypted pair below
`$OMNIA_DATA_PATH/build_stream/input/$OMNIA_PROJECT_NAME/`:

- `build_stream_credentials.yml`
- `.build_stream_credentials_key`

Review the non-sensitive settings and registered execution surface:

```bash
${EDITOR:-vi} test_config.yml
${EDITOR:-vi} test_run_config.yml
./run_validation.sh --help
./run_validation.sh fvt_build_stream list
```

## Execution model

```text
exec    run the selected playbook or pipeline operation only
verify  inspect existing state without executing the operation
test    run exec, then verify only when execution succeeds
```

Execution tests retain `@pytest.mark.deploy`; `verify` automatically excludes
that marker.

`exec` runs the `deploy`-marked action. `verify` excludes that action and runs
the selected verification cases against existing state. The supported markers
are:

| Marker | Meaning |
|---|---|
| `sanity` | Installation, automatic pipeline, cleanup, and health coverage |
| `manual` | Explicit `PIPELINE_TYPE=build` or `PIPELINE_TYPE=deploy` coverage |
| `deploy` | Performs an infrastructure or pipeline action |
| `security` | Security NFT coverage |
| `resilience` | Recovery and fault-injection NFT coverage |
| `disruptive` | Requires a matching `nft_allow_*` safety control |

## FVT scenarios

| Scenario | Purpose | Suites |
|---|---|---|
| `buildstream_cleanup` | Remove and verify GitLab and BuildStream resources | `gitlab_cleanup`, `buildstream_cleanup` |
| `buildstream_install` | Install and verify GitLab and BuildStream services | `health`, `buildstream_install` |
| `build_pipeline` | Trigger and verify the image build pipeline | `build_pipeline` |
| `deploy_pipeline` | Deploy the image group mapped to `job_id`, restart, validate, and verify | `deploy_pipeline` |

An untagged FVT command runs the `sanity` lifecycle in this order:
`buildstream_install`, `build_pipeline`, then `deploy_pipeline`. For `test`,
each scenario is executed and verified before the runner advances. The
lifecycle stops at the first failure. Cleanup is excluded from untagged
commands and runs only when `buildstream_cleanup` is explicitly selected.
The same lifecycle and explicit-only labels are displayed by both
`./run_validation.sh --help` and
`./run_validation.sh fvt_build_stream list`.

```bash
# Execute only
./run_validation.sh fvt_build_stream buildstream_install exec --marker sanity

# Execute, then verify
./run_validation.sh fvt_build_stream buildstream_install test --marker sanity

# Re-run read-only checks against an existing installation
./run_validation.sh fvt_build_stream buildstream_install verify --marker sanity

# Trigger and verify the existing build pipeline automation
./run_validation.sh fvt_build_stream build_pipeline test --marker sanity

# Run the complete ordered lifecycle
./run_validation.sh fvt_build_stream test --marker sanity

# Verify an existing build job using job_id from test_config.yml
./run_validation.sh fvt_build_stream build_pipeline verify --marker sanity

# Deploy the unique image group mapped to mandatory job_id
./run_validation.sh fvt_build_stream deploy_pipeline test --marker sanity

# Explicit destructive cleanup
./run_validation.sh fvt_build_stream buildstream_cleanup test --marker sanity
```

## Recommended end-to-end run

Use one `run_id` in `test_config.yml` for one logical run. Cleanup must run
first because the next step installs BuildStream again. Leave `run_id` empty
when each command should create a separate report entry.

```bash
cd test/build_stream
source .venv/bin/activate

# 1. Full GitLab and BuildStream cleanup plus cleanup verification
./run_validation.sh fvt_build_stream buildstream_cleanup test --marker sanity

# 2. Install and verify GitLab, runner, API, DB, TLS, queue, and watcher
./run_validation.sh fvt_build_stream buildstream_install test --marker sanity

# 3. Upload catalog_path, build images, and verify DB/registry/S3 state
./run_validation.sh fvt_build_stream build_pipeline test --marker sanity

# 4. Deploy the job-bound image group and run restart plus validate
./run_validation.sh fvt_build_stream deploy_pipeline test --marker sanity
```

The non-destructive installation/build/deploy lifecycle can also be run with:

```bash
./run_validation.sh fvt_build_stream test --marker sanity
```

To generate a clean final-state report without repeating any action, set a new
`run_id` in `test_config.yml` and run the three read-only verification phases:

```bash
./run_validation.sh fvt_build_stream buildstream_install verify --marker sanity
./run_validation.sh fvt_build_stream build_pipeline verify --marker sanity
./run_validation.sh fvt_build_stream deploy_pipeline verify --marker sanity
```

Reports retain earlier failures and retries for auditability. Use a new
`run_id` for a final-state-only report instead of deleting or manually
editing historical results.

## Explicit pipeline suites

Installation sanity must pass before the manual suites. Manual build stages the
catalog with `[skip ci]`, triggers `PIPELINE_TYPE=build`, and persists the new
`job_id`. Manual deploy uses that same job and triggers
`PIPELINE_TYPE=deploy`.

```bash
./run_validation.sh fvt_build_stream buildstream_install verify --marker sanity

./run_validation.sh fvt_build_stream build_pipeline test \
  --suite manual --marker manual
./run_validation.sh fvt_build_stream deploy_pipeline test \
  --suite manual --marker manual
```

The image cleanup pipeline is destructive and explicit. It resolves the image
group from `job_id`, triggers `PIPELINE_TYPE=cleanup`, and verifies `CLEANED`
database state plus removal of the associated S3 and registry artifacts.

```bash
./run_validation.sh fvt_build_stream buildstream_cleanup test \
  --suite cleanup_pipeline --marker sanity

# Read-only verification of an already completed cleanup
./run_validation.sh fvt_build_stream buildstream_cleanup verify \
  --suite cleanup_pipeline --marker sanity
```

The cleanup suite is idempotent: when the selected image group is already
`CLEANED`, it verifies that result and does not launch a duplicate pipeline.

Batch execution uses the YAML order and explicit `run` values in
`test_run_config.yml`:

```bash
./run_validation.sh --config
```

## Inputs and datasets

With `dataset: ""` and `sync_build_stream_input: false`, the target's existing
input is untouched. When input synchronization is enabled, an empty dataset
uses `src/build_stream/input/`; a named dataset uses
`datasets/<dataset>/input/`.

The destination is resolved from `OMNIA_DATA_PATH` and
`OMNIA_PROJECT_NAME` on the execution OIM. Credential files, vault keys,
backups, and symlinks are never synchronized.

The runner does not assume `/opt/omnia` or `project_default` for runtime input,
queue, artifact, or Orchestrator validation paths. A custom environment such as
the following is supported:

```text
OMNIA_DATA_PATH=/opt/omnia_custom
OMNIA_PROJECT_NAME=custom_project

/opt/omnia_custom/build_stream/input/custom_project
/opt/omnia_custom/orchestrator/input/custom_project
/opt/omnia_custom/playbook_queue
```

`report_path` remains independently configurable in `test_config.yml`.

Generate reproducible non-secret input with:

```bash
cd datasets/generator
./generate_dataset.py create my_dataset --profile defaults
cd ../..
```

Run deployed-system non-functional tests with:

```bash
./run_validation.sh nft_build_stream list
./run_validation.sh nft_build_stream test --marker security
```

Resilience tests that cancel a GitLab pipeline or restart BuildStream services
require explicit `nft_allow_*` authorization in `test_config.yml`. See
[`nft/README.md`](nft/README.md) for the test registry and safety controls.

Datasets never contain Build Stream credentials. Configure those directly on
the execution OIM with `./setup_env.sh --set-domain-creds`.

## Configuration and reports

`test_config.yml` contains only non-sensitive settings. `test_creds.yml` is
created locally only when transport credentials are needed and is ignored by
Git. Reports use `report_path`, `report_name`, and optional `run_id`. Every
run writes both `<report_name>.json` and `<report_name>.html`; all steps in an
ordered lifecycle share one report ID.

Build-pipeline `exec` and `test` always replace any existing `job_id` in
`test_config.yml` with the job created by that execution. They fail if a new
job cannot be identified or persisted. `verify` is read-only and uses the
existing `job_id`. Do not commit a live job UUID or environment-specific server
values.

They also always load the catalog selected by `catalog_path` below
`src/main/samples/catalogs/`, give its catalog identifier a unique value, and
replace the canonical `catalog_rhel.json` in GitLab. For example,
`catalog_path: "10.0/slurm_x86_64_no_vast.json"` selects that RHEL 10.0
catalog. Only a pipeline created after that upload is accepted as the pipeline
for the current execution.

Deploy requires `job_id` and resolves exactly one associated image group. It
never falls back to the latest image.

The deploy validate stage invokes Orchestrator FVT. Test selection is based on
the deployed configuration:

- Slurm tests run only when Slurm is configured.
- Kubernetes tests run only when Kubernetes is configured.
- VAST, PowerVault, PowerScale CSI, GPU, LDAP, MPI, and Apptainer checks use
  their existing feature-detection logic.
- Feature-absent and destructive tests skip with an explicit reason.

Pipeline logs and stage artifacts are written below the runtime data path:

```text
$OMNIA_DATA_PATH/build_stream/logs/<job_id>/
$OMNIA_DATA_PATH/build_stream_root/artifacts/<job_id>/<stage>/attempt_<n>/
```

The validate artifact includes the Orchestrator test summary. Expected skips
are not failures; evaluate `failed` and `errors` separately.

See `docs/test_config.md`, `docs/test_creds.md`,
`docs/test_run_config.md`, and `fvt/README.md` for the complete contracts.

## Troubleshooting

- Missing `job_id`: run build-pipeline `exec`/`test`, or enter the exact UUID
  before build verify, deploy, or image cleanup.
- Wrong image selected: confirm that the job maps to exactly one image group;
  latest-image fallback is intentionally prohibited.
- No tests collected: verify the suite/marker pair. Manual tests require
  `--suite manual --marker manual`; cleanup-pipeline tests require
  `--suite cleanup_pipeline --marker sanity`.
- Optional test skipped: confirm whether the feature is enabled in the
  deployed configuration. Package presence alone is not feature enablement.
- Artifact API unavailable: node-result verification can validate the
  canonical artifact file, but the API failure should be investigated.
- Slow GitLab checks: repository-file API checks can wait for their configured
  remote timeout. Use `--debug` for detailed timing.

## Local checks

```bash
python -m compileall -q test/build_stream
python -m pylint test/build_stream
find test/build_stream -type f -name '*.sh' -print0 \
  | xargs -0 --no-run-if-empty shellcheck
git diff --check
```

Live FVT requires a suitable authorized environment. A missing lab is reported
as not run; it is not treated as a successful result.
