# Build Stream test automation

Functional automation for the Omnia `build_stream` domain.
It uses the shared `omnia_auto` package for runner dispatch, target access,
synchronization, logging, and HTML/JSON reporting.

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

Generate reproducible non-secret input with:

```bash
cd datasets/generator
./generate_dataset.py my_dataset defaults
cd ../..
```

Datasets never contain Build Stream credentials. Configure those directly on
the execution OIM with `./setup_env.sh --set-domain-creds`.

## Configuration and reports

`test_config.yml` contains only non-sensitive settings. `test_creds.yml` is
created locally only when transport credentials are needed and is ignored by
Git. Reports use `report_path`, `report_name`, and optional `report_id`. Every
run writes both `<report_name>.json` and `<report_name>.html`; all steps in an
ordered lifecycle share one report ID.

Build-pipeline `exec` and `test` always replace any existing `job_id` in
`test_config.yml` with the job created by that execution. They fail if a new
job cannot be identified or persisted. `verify` is read-only and uses the
existing `job_id`.

They also always load the catalog selected by `catalog_path` below
`src/main/samples/catalogs/`, give its catalog identifier a unique value, and
replace the canonical `catalog_rhel.json` in GitLab. For example,
`catalog_path: "10.0/slurm_x86_64_no_vast.json"` selects that RHEL 10.0
catalog. Only a pipeline created after that upload is accepted as the pipeline
for the current execution.

See `docs/test_config.md`, `docs/test_creds.md`,
`docs/test_run_config.md`, and `fvt/README.md` for the complete contracts.

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
