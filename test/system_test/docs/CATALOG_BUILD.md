# User Guide: SVT Theme `catalog_build`

Run the Repo Manager and Image Build Manager FVTs against many Omnia catalogs, one
catalog at a time, on one OIM, and get one SVT report for all of them.

```
for every catalog:
  ./omnia.sh --select-catalog <catalog>
  repo_manager        precheck -> prepare -> execute -> status      (exec + verify each)
  image_build_manager precheck -> validate -> prepare -> build      (exec + verify each)
```

No orchestrator deploy and no PXE boot: a catalog is done when its images are built
and verified.

**Compared with the `build_stream` theme.** Both themes use the same SVT framework:
the same `setup_env.sh` / `run_validation.sh` commands and guards, test cases run by
`svt/test_svt.py`, the same report, the same cleanup and the same GitLab pipeline. What
differs comes from the catalog list:

| | `build_stream` | `catalog_build` |
|---|---|---|
| Stages | Fixed: `prepare_build_stream`, `build_deploy`, `cadence`, `automatic_cleanup` | One per catalog: `catalog_01` ... `catalog_NN` |
| When the stages are known | Always | After `--configure` writes the catalog plan (on the OIM), or when the pipeline files are rendered |
| Theme block | `build_stream:` settings written into the build_stream suite | `catalog_build:` (catalogs, repo/image settings, steps), [section 5](#5-settings-reference) |
| Soft stages | `build_deploy`, `cadence`, `automatic_cleanup` | Every catalog stage when `continue_on_failure: true` |
| Extra checks | - | Initialization checks the catalog plan; the pipeline checks that the OIM plan matches its jobs |
| Pipeline timeouts | One key per stage | `catalog_stage` for every catalog job (a per-job key still wins) |

**Contents**

1. [Before you start](#1-before-you-start)
2. [Quick start](#2-quick-start)
3. [The files you edit](#3-the-files-you-edit)
4. [Step by step](#4-step-by-step)
5. [Settings reference](#5-settings-reference)
6. [Reading the results](#6-reading-the-results)
7. [When something fails](#7-when-something-fails)
8. [Common tasks](#8-common-tasks)
9. [Troubleshooting](#9-troubleshooting)
10. [Command reference](#10-command-reference)

---

## 1. Before you start

| You need | Why |
|---|---|
| A RHEL OIM, logged in as `root` | The SVT installs and runs Omnia on this host |
| An Omnia checkout on the OIM | The SVT runs from `<checkout>/test/system_test` |
| Python 3.12+ | `setup_env.sh` builds the SVT's own `.venv` from it |
| A RHEL subscription on the OIM, or `baseos` / `appstream` / `codeready-builder` URLs | Repo Manager reads RHEL content from them |
| Mirrors of the non-public repositories: `slurm_custom`, `ldms` (and `vast` for catalogs without `_no_vast`) | Repo Manager precheck fails a catalog whose repositories have no URL |
| Repo Manager credentials (Pulp, Docker Hub) and Image Build Manager credentials (S3, registry) | Asked once by `setup_env.sh`, kept encrypted in the Omnia data path |
| Free disk space under `OMNIA_DATA_PATH` | Every catalog adds packages to Pulp and images to S3 / the registry |
| An aarch64 build host (optional) | Only for catalogs with aarch64 layers (`include_aarch64: true`) |

> **Destructive option:** `--force` and `--cleanup` remove the previous Omnia installation
> of the OIM, **including everything under `OMNIA_DATA_PATH`** (inputs, credentials,
> Pulp content, images, logs). Back up what you need first. Without `--force` nothing
> is removed.

All commands below run from:

```bash
cd <omnia checkout>/test/system_test
```

---

## 2. Quick start

```bash
# 1. Fill the OIM identity and the repository URLs (section 3.1)
vi user_inputs.yml

# 2. Choose the catalogs and the settings (section 3.2)
vi catalog_build_test_config.yml

# 3. Prepare the OIM: configure (writes the catalog plan) -> install -> credentials
./setup_env.sh --theme catalog_build            # keep the current installation
# ./setup_env.sh --theme catalog_build --force  # or: clean reinstall first (destructive)

# 4. Check it is ready
./setup_env.sh --theme catalog_build --status   # every line [ OK ], then READY

# 5. See what will run
./run_validation.sh svt_catalog_build list

# 6. Run every catalog, then the summary
./run_validation.sh svt_catalog_build all

# 7. Open the report
ls -td reports/svt-*/ | head -1                 # the run folder
#    <run folder>/svt_catalog_build_report.html
```

> **The rule to remember:** whenever you change `user_inputs.yml` or
> `catalog_build_test_config.yml`, run step 3 again
> (`./setup_env.sh --theme catalog_build`). It starts a new run, rewrites the inputs
> and the catalog plan, and installs them. Running only `--configure` after an edit
> leaves the installed inputs old and the next stage refuses to start.

---

## 3. The files you edit

You edit exactly two files. Everything else is generated.

### 3.1 `user_inputs.yml` - the values of your cluster

Shared with the `build_stream` theme. The `catalog_build` theme uses three blocks:

| Block | What to fill | Written to |
|---|---|---|
| `main.omnia_env` | **Mandatory:** `SYSTEM_ADMIN_NIC_IPV4`, `SYSTEM_HOSTNAME`, `SYSTEM_DOMAIN_NAME` of the OIM | `src/main/omnia.env` |
| `repo_manager.repo_manager_config.repositories` | The URLs of every repository your catalogs use, per RHEL version and architecture | `src/repo_manager/input/repo_manager_config.yml` |
| `image_build_manager.image_build_config` | `aarch64_inventory_host_ip` (only with `include_aarch64: true`); optional keys of `image_build_config.yml`, e.g. `build_image.max_parallel` | `src/image_build_manager/input/image_build_config.yml` |

The `orchestrator`, `build_stream` and `openbao` blocks are not used by this theme.

Example (RHEL 10.2, x86_64):

```yaml
main:
  omnia_env:
    SYSTEM_ADMIN_NIC_IPV4: "172.16.0.254"
    SYSTEM_HOSTNAME: "demo"
    SYSTEM_DOMAIN_NAME: "openchami.cluster"

repo_manager:
  repo_manager_config:
    repositories:
      "10.2":
        x86_64:
          baseos:            {url: ""}      # "" = the OIM's RHEL subscription
          appstream:         {url: ""}
          codeready-builder: {url: ""}
          user_repos:
            slurm_custom: {url: "http://<mirror>/omnia/rhel10.2/x86_64/slurm/25.05.2/with_gpu/"}
            ldms:         {url: "http://<mirror>/omnia/rhel10.2/x86_64/ldms/4.5.2/"}
            vast:         {url: "http://<mirror>/omnia/rhel10.2/x86_64/vast/"}

image_build_manager:
  image_build_config:
    aarch64_inventory_host_ip: ""
    build_image:
      max_parallel: 2
```

Rules of the file (checked when you configure):

- A key must exist in the target input file; a typo is reported, not ignored.
- An empty value (`""`) keeps the shipped default.
- Credentials never go here; `setup_env.sh` asks for them.
- RHEL 10.0 catalogs and the `hybrid/` catalogs also need the `"10.0"` entries.

### 3.2 `catalog_build_test_config.yml` - what the theme runs

```yaml
catalog_build:
  catalogs: all                 # "all" (shipped default), or a list in the order to run:
  #  catalogs:
  #    - rhel/10.2/slurm_x86_64_no_vast.json
  #    - rhel/10.2/slurm_service_k8s_x86_64_no_vast.json
  include_aarch64: false
  repo_config: partial
  caching_policy: true
  repo_policies: {}
  force_rebuild: true
  continue_on_failure: true
  cleanup_between: none
  steps:
    - [repo_manager, precheck]
    - [repo_manager, prepare]
    - [repo_manager, execute]
    - [repo_manager, status]
    - [image_build_manager, precheck]
    - [image_build_manager, validate]
    - [image_build_manager, prepare]
    - [image_build_manager, build]

cleanup:   # what --force / --cleanup removes (same flags as build_stream)
  ...
report:    # where the run folder and the report go
  ...
```

Every key is explained in [section 5](#5-settings-reference). To see the catalog
names you can use:

```bash
../../src/main/omnia.sh --list-catalogs      # or: cd ../../src/main && ./omnia.sh --list-catalogs
```

A catalog can be given by its name (`rhel/10.2/slurm_x86_64.json`), by its file name
when that is unique (`slurm_x86_64.json`), or by its number in that list.

---

## 4. Step by step

### 4.1 Prepare the OIM: `./setup_env.sh --theme catalog_build`

With no action, `setup_env.sh` runs every setup step in order:

| Step | What it does | Changes |
|---|---|---|
| **configure** | Starts a **new run** (`svt-<UTC time>`), copies `user_inputs.yml` into the `src` inputs (dataset generator), writes the cleanup and report settings into each `test/<suite>/test_config.yml`, then resolves the catalog list into the **catalog plan** and prints it | `src/.../input`, `src/main/omnia.env`, `test/*/test_config.yml`, `reports/catalog_build_plan.json` |
| **cleanup** (only with `--force`) | Removes the previous installation with each suite's own cleanup FVT: BuildStream (when installed), telemetry (when deployed), orchestrator, image_build_manager, repo_manager, then `omnia.sh --cleanup --all` | **Deletes** `OMNIA_DATA_PATH` and the Omnia services |
| **install** | `omnia.sh -s` (Omnia venv, domain inputs into `OMNIA_DATA_PATH`), then the FVT test requirements in the Omnia venv | Omnia installation |
| **creds** | Asks for the missing repo_manager and image_build_manager credential stores; skips the ones that exist | Encrypted credential files |

The plan printed by configure looks like this (for the two-catalog list example):

```
catalog plan (2 catalog(s), 2 to run) -> .../reports/catalog_build_plan.json:
  catalog_01   run   rhel/10.2/slurm_x86_64_no_vast.json
  catalog_02   run   rhel/10.2/slurm_service_k8s_x86_64_no_vast.json
steps per catalog (exec, then verify): repo_manager precheck, ... image_build_manager build
settings: repo_config=partial, caching_policy=True, force_rebuild=True, ...
```

Configure fails (and tells you what to fix) when a catalog name is unknown, a key is
invalid, or `include_aarch64: true` has no `aarch64_inventory_host_ip`.

Useful variants:

```bash
./setup_env.sh --theme catalog_build --force          # clean reinstall (destructive)
./setup_env.sh --theme catalog_build --force --yes    # same, no 'yes' prompt
./setup_env.sh --theme catalog_build --cleanup --dry-run   # show what cleanup would remove
./setup_env.sh --theme catalog_build --retry          # resume setup at the step that failed
```

### 4.2 Check readiness: `--status`

```bash
./setup_env.sh --theme catalog_build --status
```

```
[ OK ] Inputs configured (user_inputs.yml, catalog_build_test_config.yml)
[ OK ] Omnia installed (omnia.sh -s: omnia.env, data path, venv, domain inputs)
[ OK ] Installed after the last configure
[ OK ] Catalog plan of this run (configure)
[ OK ] Test requirements in the Omnia venv (5 suites)
[ OK ] Credentials: repo_manager
[ OK ] Credentials: image_build_manager
READY: ./run_validation.sh svt_catalog_build all
```

Every `[FAIL]` line says how to fix it. `run_validation.sh` checks the same list in
its `initialization` stage.

### 4.3 See the plan: `list`

```bash
./run_validation.sh svt_catalog_build list
```

```
  initialization
  catalog_01
    SVT_CATALOG_BUILD_0100 rhel/10.2/slurm_x86_64_no_vast.json: select (...)
    SVT_CATALOG_BUILD_0101 rhel/10.2/slurm_x86_64_no_vast.json: repo_manager precheck exec
    SVT_CATALOG_BUILD_0102 rhel/10.2/slurm_x86_64_no_vast.json: repo_manager precheck verify
    ...
  catalog_02
    ...
  summary
```

### 4.4 Run: `all`

```bash
./run_validation.sh svt_catalog_build all           # output on the screen and in the logs
./run_validation.sh svt_catalog_build all --quiet   # output in the logs only
```

The stages run in order:

| Stage | What happens |
|---|---|
| `initialization` | The readiness checks of `--status`; the run stops here when one fails |
| `catalog_NN` | One per catalog (see below) |
| `summary` | Prints every test result, renders the report; fails when any stage failed |

Inside a catalog stage:

| Test | What it does |
|---|---|
| `NN00 select` | Puts back the shared runtime inputs, applies `catalog_overrides/<catalog>/`, writes the global settings (`repo_config`, `caching_policy`, `repo_policies`, `force_rebuild`, `functional_groups_source: catalog`) into `<OMNIA_DATA_PATH>/<domain>/input/<project>/`, then `./omnia.sh --select-catalog <catalog>` |
| `NN01`, `NN02` ... | For each `steps` entry: `fvt_<domain> <tag> exec` (runs the playbook), then `fvt_<domain> <tag> verify` (its verification tests) |
| last (with `cleanup_between`) | The cleanup FVT steps; they run even when the catalog failed |

The first FVT step is the Repo Manager precheck: it validates the catalog against
`repo_manager_config.yml` (repository mapping, URLs, the RHEL subscription), so a
missing repository URL fails a catalog in about a minute, not hours later.

You can also run one stage at a time:

```bash
./run_validation.sh svt_catalog_build initialization
./run_validation.sh svt_catalog_build catalog_01
./run_validation.sh svt_catalog_build summary
```

How long it takes depends on the catalogs, the mirrors and `force_rebuild`. For
reference, two RHEL 10.2 x86_64 catalogs on an OIM whose repositories were already
synced took about 35 and 42 minutes, most of it the image build
(`force_rebuild: true`). A first sync of a large catalog can take much longer.

---

## 5. Settings reference

All keys of the `catalog_build:` block of `catalog_build_test_config.yml`:

| Key | Values | Default | Meaning |
|---|---|---|---|
| `catalogs` | `all` or a list | `all` | `all` = every catalog of `./omnia.sh --list-catalogs`, in that order. A list runs in the order you give |
| `include_aarch64` | `true` / `false` | `false` | `false`: a catalog with any aarch64 layer (aarch64-only, `combined`, `x86_64_aarch64`, the default catalog) is skipped as a whole and its stage says why. `true`: they run; set `aarch64_inventory_host_ip` in `user_inputs.yml` |
| `repo_config` | `always` / `partial` | `partial` | Written as `repo_config` of `repo_manager_config.yml` for every catalog |
| `caching_policy` | `true` / `false` | `true` | Written as `caching_policy` of `repo_manager_config.yml` |
| `repo_policies` | mapping | `{}` | Per repository: `"<version>/<arch>/<repo>": {policy: always\|partial\|never, caching: true\|false}`, e.g. `"10.2/x86_64/epel": {policy: always, caching: false}`. The repository must exist in `repo_manager_config.yml` |
| `force_rebuild` | `true` / `false` | `true` | Written as `build_image.force_rebuild`. `true` builds every image of every catalog from scratch. `false` reuses an image group that was already built (faster, but a reused image is not rebuilt) |
| `continue_on_failure` | `true` / `false` | `true` | `true`: a failed catalog does not stop the next one (the summary still fails). `false`: the run stops at the first failed catalog |
| `cleanup_between` | `none` / `images` / `repos` / `full` | `none` | After every catalog. `images` = `fvt_image_build_manager cleanup_images test`. `repos` = `fvt_repo_manager cleanup test` (removes Pulp; the next catalog prepares it again). `full` = both, plus `fvt_image_build_manager cleanup test` |
| `steps` | list of `[domain, tag]` | the 8 steps shown above | The FVT steps of every catalog, in order. `domain` is `repo_manager` or `image_build_manager`; `tag` is one of its FVT tags (checked at configure). Each step becomes an `exec` test and a `verify` test |

What `repo_config` and `caching_policy` mean for Repo Manager:

| `repo_config` | `caching_policy` | Pulp policy | Effect |
|---|---|---|---|
| `always` | `false` | `immediate` | Every package downloaded and stored |
| `always` | `true` | `on_demand` | Stored when first requested |
| `partial` | `false` | `streamed` | Packages only validated, not stored; the image build then needs the upstream repositories |
| `partial` | `true` | `on_demand` | Stored when first requested |

The `cleanup` and `report` blocks are the same as in `build_stream_test_config.yml`
(see [TEST_CONFIG.md](TEST_CONFIG.md)).

### 5.1 Per-catalog input files (optional)

To give one catalog a different input file, place it under:

```
test/system_test/catalog_overrides/<catalog name>/<domain>/<file name>
e.g. catalog_overrides/rhel/10.2/slurm_x86_64.json/image_build_manager/image_build_config.yml
```

The `select` test of that catalog copies it over the runtime input; the next catalog
gets the shared file back. The global settings of section 5 are written after the
override, so they always apply. Credential files are never overridden.

---

## 6. Reading the results

Everything of one run is in one folder:

```
reports/<run_id>/
├── svt_catalog_build_report.html   the report (open in a browser)
├── svt_catalog_build_report.json   the same data as JSON
├── initialization.log, catalog_01.log, catalog_02.log, summary.log   full output per stage
├── <stage>.status                  passed | skipped | failed <rc>
├── <stage>.progress                the current step of a running stage
├── run.json                        the run manifest (settings, setup, stage outcomes)
├── svt_results.json                one line per SVT test (used by summary)
├── junit_catalog_build_<stage>.xml JUnit per stage
├── fvt/                            the FVT suites' own reports
├── setup/                          the setup_env.sh logs of this run
└── baseline_inputs/                shared inputs kept while an override was active
```

Find the latest run:

```bash
ls -td reports/svt-*/ | head -1
```

The HTML report shows, top to bottom:

| Section | What you see |
|---|---|
| Banner | `OVERALL STATUS: PASSED`, `FAILED` or `RUNNING`, and how many stages ran |
| Cards | SVT steps passed / failed / skipped, pass rate, duration |
| Run Details | theme, run id, OIM, repository, branch, commit |
| Stage Overview | **one row per catalog** (`Catalog 1: rhel/10.2/...`): status, steps passed / failed / skipped, duration - the catalog matrix |
| Stage Details | per catalog, every test: its command, the FVT results (TC ID, test, status, details, error) and its screen output; failed tests open by default |

Follow a running stage from another terminal:

```bash
R=$(ls -td reports/svt-*/ | head -1)
cat "$R"/*.progress                 # the current step of each stage
tail -f "$R"/catalog_01.log         # the full output
```

---

## 7. When something fails

### What happens automatically

| Situation | Behaviour |
|---|---|
| A test of a catalog fails | The later tests of that catalog are skipped (they need what it set up); `cleanup_between` still runs |
| A catalog stage fails, `continue_on_failure: true` | The next catalog runs; the summary fails |
| A catalog stage fails, `continue_on_failure: false` | The run stops; only the summary runs |
| A playbook hits the FVT timeout (7200 s) | The step fails; the theme stops the `ansible-playbook` workers and the `dnf download` it left running, so they cannot overlap the next test (noted in the report) |
| A catalog has aarch64 layers and `include_aarch64: false` | Its stage holds one skipped test with the reason |

### What you do next

1. Open the report, find the failed test, read its error and output (or the stage log).
2. Fix the cause (a repository URL, a credential, disk space, the mirror ...).
3. Choose:

| You want to | Run |
|---|---|
| Repeat the failed stage in the **same run** (same report; the new attempt replaces the old one) | `./run_validation.sh svt_catalog_build all --retry` |
| Repeat only one stage in the same run | `./run_validation.sh svt_catalog_build catalog_02 --retry` |
| Start again from a catalog in a **new run** | `./setup_env.sh --theme catalog_build` then `./run_validation.sh svt_catalog_build all --start-stage catalog_02` |
| Change a setting or an input, then run again | Edit the file, `./setup_env.sh --theme catalog_build`, then `./run_validation.sh svt_catalog_build all` |

A failed run takes no further step except `--retry` and the summary. That is on
purpose: one run is one report, and nothing is added to it after an unhandled
failure. `./setup_env.sh --theme catalog_build` starts a new run; the installation
and the credentials are kept.

---

## 8. Common tasks

**Run every bundled catalog**

```yaml
catalog_build:
  catalogs: all
```

With `include_aarch64: false` only the x86_64-only catalogs run; the others are
listed as skipped. Every catalog's repositories need URLs in `user_inputs.yml`
(RHEL 10.0 and 10.2, `vast` for the catalogs without `_no_vast`).

**Run the aarch64 catalogs too**

```yaml
# catalog_build_test_config.yml
catalog_build:
  include_aarch64: true
# user_inputs.yml
image_build_manager:
  image_build_config:
    aarch64_inventory_host_ip: "<aarch64 build host IP>"
```

Fill the `aarch64` repository entries in `user_inputs.yml` as well.

**Faster re-runs:** `force_rebuild: false` reuses images that were already built;
Repo Manager syncs only what is new.

**Keep the disk usage down on a long run:** `cleanup_between: images` (or `full`).

**Test one Repo Manager policy:** `repo_config: always`, `caching_policy: false`
(every package stored), or a single repository through `repo_policies`.

**Only Repo Manager:** keep only the `repo_manager` entries in `steps`.

**Clean reinstall before the run**

```bash
./setup_env.sh --theme catalog_build --force --yes
./run_validation.sh svt_catalog_build all
```

**Change a credential**

```bash
./setup_env.sh --theme catalog_build --update-domain-creds --domain repo_manager
```

**Leave the checkout clean afterwards.** `--configure` writes into tracked files of
the checkout. Before committing anything:

```bash
cd <omnia checkout>
git checkout -- src/main/omnia.env src/repo_manager/input/repo_manager_config.yml \
  src/image_build_manager/input/image_build_config.yml test/*/test_config.yml
```

Keep cluster-specific values (IPs, mirror URLs) out of `user_inputs.yml` in commits.

### Run it from a GitLab pipeline (one job per catalog)

The SVT pipeline ([PIPELINE.md](PIPELINE.md)) runs this theme too. Set
`svt.theme: "catalog_build"` in `pipeline/svt_pipeline_config.yml` and render the CI files
from a checkout whose `catalog_build_test_config.yml` and `user_inputs.yml` hold the
values to test:

```bash
cd test/system_test/pipeline
./setup_svt_project.py --render                                   # one job per catalog
./setup_svt_project.py --update --gitlab-url https://<gitlab-host> --update-inputs
```

The pipeline is `preflight -> initialization -> catalog_01 -> catalog_02 -> ... -> summary`:
each catalog is its own GitLab job (log, status, Retry button), titled with the catalog
in `.gitlab-ci-svt.yml`. With `continue_on_failure: true` a failed catalog job does not
stop the next one; the summary still fails. `timeouts_hours.catalog_stage` sets the time
limit of every catalog job, and `skip_stages: "catalog_03"` leaves a catalog out of a
run.

The jobs are fixed when the files are rendered. **After changing the catalog list, run
`--update --update-inputs` again.** If the plan written on the OIM differs from the jobs,
the initialization job stops right after configure (see [section 9](#9-troubleshooting)).

---

## 9. Troubleshooting

| Message | Cause | Fix |
|---|---|---|
| `main.omnia_env.SYSTEM_ADMIN_NIC_IPV4: MANDATORY, fill it` | `user_inputs.yml` misses the OIM identity | Fill the three `omnia_env` values, run `./setup_env.sh --theme catalog_build` |
| `Installed after the last configure: the inputs were configured again after the last install` | `--configure` ran after the last install, so the installed inputs are old | `./setup_env.sh --theme catalog_build` (configure + install) |
| `run ... has a failed step: ... A failed run takes no further step` | A step of the current run failed | `--retry` (same run) or `./setup_env.sh --theme catalog_build` (new run) |
| `no catalog plan for run ...` / `the catalog plan ... belongs to run ...` | The plan file is missing or from another run | `./setup_env.sh --theme catalog_build --configure`, then install (`./setup_env.sh --theme catalog_build`) |
| `catalog '...' is not in ./omnia.sh --list-catalogs` | A typo in `catalogs` | Use a name or number from `./omnia.sh --list-catalogs` |
| `include_aarch64 is true but ... aarch64_inventory_host_ip is empty` | aarch64 catalogs without a build host | Set the IP in `user_inputs.yml`, or `include_aarch64: false` |
| `catalog_build.<key>: ...` | An invalid value in the theme block | The message names the key and the allowed values |
| `repo_policies: <key> is not a repository of ...` | A `repo_policies` key that the config does not have | Use `"<version>/<arch>/<repo>"` of an existing repository |
| `repo_manager precheck exec` fails | A repository of the catalog has no URL, or no subscription for RHEL content | Add the URL to `user_inputs.yml`; check `subscription-manager status` |
| `Playbook execution timed out ... Timeout: 7200s` | One FVT playbook took more than two hours (often the first sync of a large catalog) | Run again: synced content is kept, so the next attempt is shorter; use faster mirrors |
| `another SVT step is running on this OIM` | Another `setup_env.sh` / `run_validation.sh` holds the SVT lock | Wait for it; a lock whose process is gone is taken over automatically |
| `Credentials: <domain> [FAIL]` | A credential store is missing (e.g. after `--force`) | `./setup_env.sh --theme catalog_build --set-domain-creds --domain <domain>` |
| Pipeline: `the catalog plan of this run on the OIM differs from the pipeline jobs` | The catalog list was edited in the GitLab project, or the tested branch bundles other catalogs than the checkout the CI files were rendered from | Set the list in your checkout, then `./setup_svt_project.py --update --update-inputs` |

More on the shared parts: [SETUP.md](SETUP.md) (setup, credentials, OpenBao),
[RUNNER.md](RUNNER.md) (the run guard, retry, the report),
[TEST_CONFIG.md](TEST_CONFIG.md) (the cleanup and report blocks).

---

## 10. Command reference

**Setup** (`./setup_env.sh --theme catalog_build ...`)

| Command | Purpose |
|---|---|
| *(no action)* | configure -> install -> missing credentials |
| `--force` | configure -> **cleanup** -> full install -> credentials |
| `--configure` | New run: inputs, suite settings, catalog plan |
| `--install` | `omnia.sh -s` and the test requirements |
| `--cleanup` | **Destructive** cleanup only (asks `yes`) |
| `--cleanup --dry-run` | Show what cleanup would remove |
| `--set-domain-creds [--domain <d>]` | Enter the credential stores |
| `--update-domain-creds --domain <d>` | Change a credential store |
| `--status` | Steps and readiness checks |
| `--retry` | Resume the setup at the failed step, same run |
| `--yes` | Answer every confirmation |

**Run** (`./run_validation.sh svt_catalog_build ...`)

| Command | Purpose |
|---|---|
| `list` | The stages and tests of the current plan |
| `all` | Every stage, then summary |
| `all --start-stage catalog_NN` | Start at a catalog (the earlier ones are not run) |
| `all --retry` | Resume the same run at the first stage that did not pass |
| `<stage>` | One stage: `initialization`, `catalog_NN`, `summary` |
| `<stage> --retry` | Run a failed stage again in the same run |
| `--quiet` | Output to the stage logs only |
| `--help` | All themes and options |
