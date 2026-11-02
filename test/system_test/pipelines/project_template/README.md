# Omnia SVT project

> **Not maintained for the current SVT flow.** `test/system_test` now runs
> locally: `./setup_env.sh` (configure, install, credentials) and
> `./run_validation.sh svt_<theme>` (initialization, system_verification,
> summary); see `test/system_test/README.md` in the Omnia repository. These GitLab files still call
> the earlier stages (`cleanup`, `environment_setup`) and `--inputs`, and need
> an update before use.

This project runs the Omnia system verification on your clusters. Each folder
under `clusters/` is one cluster (one OIM).

## Use it

1. **Fill a cluster:** edit these files in `clusters/<cluster>/`:
   - `cluster.yml`: OIM address, Omnia `clone_url` and `clone_ref`,
     `clone_path`, OpenBao address;
   - `user_inputs.yml`: the cluster values. Fill the MANDATORY ones; `""`
     keeps a default;
   - `test_config.yml`: BuildStream test settings (cleanup flags, catalogs).
2. **Secrets:** an admin stores them in OpenBao with `openbao_secrets.py`
   (Omnia repository, `test/system_test/pipelines/`). Never put a secret in this
   project.
3. **Run:** CI/CD > Pipelines > **Run pipeline**:

   | Field | Choices |
   |---|---|
   | THEME | `build_stream` (BuildStream: build, deploy, cadence, automatic cleanup) |
   | CLUSTERS | `all`, or one or more folder names |
   | START_STAGE | where to start; a re-run keeps the commit and inputs of the last run |

   A commit to the default branch that changes `clusters/<name>/` runs that
   cluster. A merge request only validates the files.
4. **Read the result:**
   - the child pipeline graph: per cluster, initialization → cleanup →
     environment_setup → one job per SVT case → summary;
   - the **Tests** tab (JUnit);
   - the `summary` job;
   - the `reports.tgz` artifact of each job (complete logs).

   Every log also stays on the OIM under
   `<clone_path>/test/system_test/reports/<run_id>/`, and a failing job prints
   its path.

Add a cluster by copying a folder and changing its values. To add a theme,
change the Omnia code (`test/system_test`) and `ci/themes/`.

Full documentation: `test/system_test/README.md` and
`test/system_test/pipelines/README.md` in the Omnia repository.
