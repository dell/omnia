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

### Change the project after it is up

Edit `svt_pipeline_config.yml`, then run the command of the row. A running pipeline keeps the
files it started from; start a new one.

| You change | Run | Notes |
|---|---|---|
| The **theme** of a cluster (`clusters.<name>.theme`, in the cluster block only) | change the variable `<PREFIX>_SVT_THEME` | The pipeline picks the theme from this CI/CD variable (one trigger job per cluster and theme; the child files of every theme are committed), so edit it in Settings > CI/CD > Variables or give it in Run pipeline: no `--update`. To make the config say the same: edit `clusters.<name>.theme`, then `--set-variables`. The first job fails on an unknown theme. Not an SVT input (`user_inputs.yml` is for the cluster's values) |
| The **email** (recipients, SMTP), polling, log limit, a cluster's `skip_stages`, `clean_reinstall`, branch, path, `checkout_mode`, `enabled` | `--set-variables` | Rewrites only the CI/CD variables; no file is committed. One value can also be edited in Settings > CI/CD > Variables (the next `--update`/`--set-variables` writes the config's value again) |
| Timeouts, a new SVT release, the stages | `--update` | They are in the generated CI files |
| A new cluster | `--create` on the existing project | Adds the cluster; `--scan-host-keys` for its OIM |

### Run only some clusters

Every selected cluster is its own child pipeline, so they run in parallel, each on its own OIM
(the runner needs `concurrent` at least the number of clusters, or they queue). By default a
pipeline runs every cluster with `enabled` not `false`. To choose: CI/CD > Pipelines > Run
pipeline, add the variable `SVT_CLUSTERS` = `cluster1,cluster3` (comma separated names of the
config; also for a schedule or the API). The first job, `select_clusters`, prints the clusters
and their themes and fails at once on a name that is not in the config.

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
id, so add it to the role ([next section](#allow-the-project-to-read-the-credentials-openbao-role)).
The GitLab runner is not deleted; it is only released when the project is deleted.

## Allow the project to read the credentials (OpenBao role)

The jobs read the domain credentials from OpenBao: each job asks GitLab for a short-lived token
(`id_tokens: VAULT_ID_TOKEN`, audience = the OpenBao URL), logs in at `auth/jwt/login` with the
role `openbao.auth_role` (default `gitlab-role`) and reads `secret_path/<domain>`. The role's
policy decides what may be read, and its `bound_claims` decide **which GitLab project** may log in.
A new project (also one created again after `--delete`, which gets a new id) must be allowed
once. Run this on a machine with the `bao` CLI and an OpenBao admin token (never put that token in
the project; it is only for you):

```bash
export BAO_ADDR=https://<openbao-host>:8200
export BAO_TOKEN=<an admin token>            # asked for by `bao login`, not stored anywhere

# 1. The id of the GitLab project: Settings > General > Project ID, or
curl -sk -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "https://<gitlab-host>/api/v4/projects/root%2Fomnia-system-test" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])'

# 2. What the role allows now (look at bound_claims, bound_claims_type, bound_audiences, policies)
bao read -format=json auth/jwt/role/gitlab-role

# 3. Allow the project. bound_claims is replaced as a whole: list every project id that
#    may log in (the ones from step 2 and the new one).
bao write auth/jwt/role/gitlab-role bound_claims_type=glob \
    bound_claims='{"project_id":["19","26"]}'

# 4. Check it
bao read -format=json auth/jwt/role/gitlab-role | python3 -c \
  'import sys,json; d=json.load(sys.stdin)["data"]; print(d["bound_claims"], d["policies"], d["bound_audiences"])'
```

The role's policy has to cover the `secret_path` of the `openbao` block in `user_inputs.yml`
(`secret/data/<path>/*`; see [docs/OPENBAO.md](../docs/OPENBAO.md) for the policy, the JWT setup
and the audience rules). To limit by project path instead of id, use
`bound_claims='{"project_path":["root/omnia-system-test"]}'`. Then run the pipeline: the
`initialization` job prints the field names it read (never the values); `OpenBao: could not read
the credentials` or `permission denied` means the role, the policy or the audience does not match
(troubleshooting table below and in [docs/OPENBAO.md](../docs/OPENBAO.md)).

## Troubleshooting

| Message | Meaning |
|---|---|
| `needs --yes when there is no terminal` | Run it in a terminal and type the project path, or add `--yes` |
| `Project has already been marked for deletion` | A deletion was scheduled earlier: run `--delete` again, it removes the project permanently |
| `verify: ... NOT CLEAN` | GitLab removes artifacts in the background: run `--status` after a minute, or `--clean` again |
| `GitLab /projects/<id>/pipelines: HTTP 403` | The token has no access to the project: use an `api` token of an Owner/Maintainer or an administrator |
