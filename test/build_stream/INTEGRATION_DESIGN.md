# BuildStream Integration Design

## Suites

`integration/` is parallel to `fvt/` and contains two independently collected suites:

- `cadence`: install BuildStream, run the full build prerequisite, trigger cadence, and verify the unified result.
- `automatic_cleanup`: explicitly execute and verify production automatic cleanup.

The integration runner has its own command dispatch and configuration. Test code does not invoke or collect tests from `fvt/`. Shared BuildStream host/API functions remain in the domain library.

## Catalog contract

`integration/test_config.yml` contains one deterministic catalog selector:

```yaml
cadence_catalog_path: "rhel/10.2/slurm_x86_64_no_vast.json"
```

The value must be a full relative JSON file below `src/main/samples/catalogs/`. A directory is insufficient because directories such as `rhel/10.2` and `hybrid` contain multiple catalogs.

Before deployment, the integration suite resolves and validates the selected file. It passes the controller-visible absolute path to Ansible as:

```yaml
gitlab_cadence_catalog_json_source: <selected file>
```

The existing hosted-GitLab role still writes the file to the fixed repository destination `cadence_catalog_rhel.json`. The tracked default `src/main/samples/cadence_catalog_rhel.json` is not overwritten.

## Cadence flow

1. Validate `cadence_catalog_path` and determine its local or remote-controller path.
2. Deploy BuildStream with `gitlab_cadence_catalog_json_source` set before hosted GitLab pushes repository files.
3. Push the same selected catalog through the normal `catalog_rhel.json` build trigger.
4. Wait for the complete build pipeline and its repository/image stages. This creates the repositories required by `repo_sync.yml`.
5. Trigger the cadence watcher.
6. Wait for `repo_sync.yml`, the cadence catalog version bump, and the unified cadence child pipeline.
7. Persist only the cadence pipeline Job ID to `job_id`.
8. Verify installation health, GitLab jobs, repository synchronization, database stages, artifacts, and final state.

The prerequisite build Job ID is session-only state and is not added to configuration.

## Automatic-cleanup flow

Automatic cleanup remains explicit and requires:

```yaml
automatic_cleanup_job_id: "<failed-job-uuid>"
automatic_cleanup_allow_execution: true
```

Execution resolves exactly one ImageGroup for that Job and uses the existing fail-closed check that it is the sole failed cleanup target. Verification checks the `CLEANED` state and removal of NFS, S3, and registry artifacts.

## Commands

```bash
cd test/build_stream/integration
./integration.sh list
./integration.sh cadence test
./integration.sh cadence verify
./integration.sh automatic_cleanup test
./integration.sh automatic_cleanup verify
```
