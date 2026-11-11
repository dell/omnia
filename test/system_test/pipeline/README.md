# SVT pipeline scripts

The GitLab side of the SVT: the scripts that create, update, check, clean and delete the
project that runs the SVT on your OIMs. The full guide is [docs/PIPELINE.md](../docs/PIPELINE.md);
every setting is in [docs/PIPELINE_CONFIG.md](../docs/PIPELINE_CONFIG.md).

| File | What it is |
|---|---|
| `svt_pipeline_config.yml` | Your settings: the project, the theme, timeouts, email, the clusters |
| `setup_svt_project.py` | `--render`, `--create`, `--update`, `--validate`: builds the project from the config |
| `cleanup_svt_project.py` | `--status`, `--clean`, `--delete`, `--verify-gone`: checks, empties or removes the project |
| `svt_ci.py` | What each pipeline job runs on the GitLab runner (standard library only) |

Both scripts read the project (`gitlab.namespace` and `gitlab.project_name`) from
`svt_pipeline_config.yml`, take the GitLab token from `GITLAB_TOKEN` (or ask for it; it is never
printed or stored) and need `--gitlab-url https://<gitlab-host>`. Add `--no-verify-ssl` for a
GitLab with a self-signed certificate. The token needs the `api` scope and the Owner or
Maintainer role on the project (an administrator token is the simplest).

## Build and update the project

```bash
cd test/system_test/pipeline
export GITLAB_TOKEN=<token>
./setup_svt_project.py --render                                   # look at the CI files
./setup_svt_project.py --create   --gitlab-url https://<gitlab-host> --scan-host-keys
./setup_svt_project.py --update   --gitlab-url https://<gitlab-host> [--update-inputs]
./setup_svt_project.py --validate --gitlab-url https://<gitlab-host>   # GitLab CI lint
```

`--update` commits the generated CI files and `svt_ci.py` and sets the CI/CD variables.
`--update-inputs` also replaces each cluster's `clusters/<name>/svt/` inputs in the project with the
`user_inputs.yml` and `<theme>_test_config.yml` of this checkout: use it to push new lab values.

## Check, clean or delete the project

`cleanup_svt_project.py` is for resetting the environment: it empties the project of everything
the pipelines produced, or removes the project, and then checks the result.

```bash
./cleanup_svt_project.py --status      --gitlab-url https://<gitlab-host>            # read only
./cleanup_svt_project.py --clean       --gitlab-url https://<gitlab-host> --dry-run  # what would go
./cleanup_svt_project.py --clean       --gitlab-url https://<gitlab-host>            # asks to confirm
./cleanup_svt_project.py --delete      --gitlab-url https://<gitlab-host>            # asks to confirm
./cleanup_svt_project.py --verify-gone --gitlab-url https://<gitlab-host>
```

| Command | What it does | Keeps |
|---|---|---|
| `--status` | Shows the project, its pipelines (and how many are active), jobs, job artifacts (count and size), variables and enabled runners | everything |
| `--clean` | Cancels the running pipelines, deletes **every pipeline** (which removes their jobs, logs and artifacts), deletes the remaining job artifacts, then verifies that no pipeline, job or artifact is left | the project, its files (`.gitlab-ci*.yml`, `svt_ci.py`, `clusters/`), the CI/CD variables, the runner assignment |
| `--delete` | Deletes the **whole project**: pipelines, artifacts, files, variables. GitLab first only schedules the deletion (and renames the project `<name>-deletion_scheduled-<id>`); the script then removes it for good and verifies that it is gone | nothing |
| `--verify-gone` | Exits 0 only when the project does not exist at all. A project that is only scheduled for deletion still exists, so it exits 1 and tells you to run `--delete` | nothing |

Safety:

- `--clean` and `--delete` ask you to **type the project path** (`<namespace>/<project>`, for example
  `root/omnia-system-test`). `--yes` skips the question; without `--yes` and without a terminal
  they refuse.
- `--dry-run` lists what `--clean` would delete (or says that `--delete` would remove the project)
  and removes nothing.
- The project is always the one in the config. To work on another one, pass another file with
  `--config`.

Exit codes: `0` done (and verified), `1` the project is not clean or not gone, the project does
not exist for `--status`/`--clean`, a refused confirmation, or a GitLab error.

### Typical flows

Start again with an empty project (same files, same variables):

```bash
./cleanup_svt_project.py --clean --gitlab-url https://<gitlab-host>
```

Remove everything and build it again:

```bash
./cleanup_svt_project.py --delete --gitlab-url https://<gitlab-host>
./cleanup_svt_project.py --verify-gone --gitlab-url https://<gitlab-host>
./setup_svt_project.py --create --gitlab-url https://<gitlab-host> --scan-host-keys
```

`--create` asks for the OIM password of each cluster again, because the variables went with the
project. The runner (a project runner) has to be enabled on the new project: Settings > CI/CD >
Runners.

### What it does not touch

Only GitLab. On the OIM, the Omnia checkout (`clusters.<name>.omnia.install_path`), `/opt/omnia`,
the NFS shares and the SVT reports (`test/system_test/reports/`) are cleaned there:
`./setup_env.sh --cleanup` (destructive; see [docs/SETUP.md](../docs/SETUP.md)). The OpenBao role
that allows the project (`bound_claims` `project_id`) is not changed: a project created again has a new
id, so add it to the role. The GitLab runner is not deleted; it is only released when the project is
deleted.

## Troubleshooting

| Message | Meaning |
|---|---|
| `needs --yes when there is no terminal` | Run it in a terminal and type the project path, or add `--yes` |
| `Project has already been marked for deletion` | A deletion was scheduled earlier: run `--delete` again, it removes the project permanently |
| `verify: ... NOT CLEAN` | GitLab removes artifacts in the background: run `--status` after a minute, or `--clean` again |
| `GitLab /projects/<id>/pipelines: HTTP 403` | The token has no access to the project: use an `api` token of an Owner/Maintainer or an administrator |
