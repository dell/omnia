# SVT Theme `catalog_build` — Design

Status: **Implemented** on the merged SVT framework (PR #5711)
Runner category: `svt_catalog_build`

## 1. Goal

A manual run on one OIM (no GitLab needed). For **every catalog**, one at a time:

```
select catalog -> repo_manager FVTs (exec + verify) -> image_build_manager FVTs (exec + verify)
```

Every step is the domain's own FVT run (`test/<domain>/_run.py fvt_<domain> <tag>
exec|verify`); the theme adds no test logic. Scope ends after the image build: no
orchestrator deploy, no PXE boot.

```bash
./setup_env.sh --theme catalog_build             # configure (plan) -> install -> creds
./run_validation.sh svt_catalog_build list       # catalog stages and their tests
./run_validation.sh svt_catalog_build all        # every catalog stage, then summary
./run_validation.sh svt_catalog_build all --start-stage catalog_02
./run_validation.sh svt_catalog_build all --retry
```

## 2. Aligned with the build_stream theme

A theme of the merged framework is **data**: its stages and `stage_info` in
`theme_vars.THEMES`, its tests in `test_case_vars.TEST_CASES` (ID, title, order,
stage, FVT step), run by the generic `svt/test_svt.py` through
`stage_func.run_tests` (pytest `-m "<theme> and <stage>"`). catalog_build is the
same; only its data is generated:

| Part | build_stream | catalog_build |
|---|---|---|
| Theme entry (`theme_vars.py`) | fixed stages | stages, `soft_stages`, `stage_info` from the catalog plan |
| Tests (`test_case_vars.py`) | written by hand | generated from the plan (`catalog_vars.catalog_test_cases`) |
| Test runner | `svt/test_svt.py` -> `run_svt_test` | the same |
| Report (JSON/HTML) | `svt_report_func` / `svt_report_html` | the same (stage titles name the catalog) |
| Failure handling | soft stages, skip the rest of a stage, `--retry`, `--start-stage` | the same (`continue_on_failure` -> soft stages) |
| Setup (`setup_env.sh`) | configure, cleanup, install, creds | the same; configure also writes the plan |
| Cleanup steps | build_stream, telemetry, orchestrator, image, repo, main | the same steps and flags |
| Credential helper | `test/build_stream/setup_env.sh` | the same (`creds_suite: build_stream`), repo_manager and image_build_manager only |
| Input profile | 9 input files | `omnia.env`, `repo_manager_config.yml`, `image_build_config.yml` |

## 3. The catalog plan

The catalog list lives in `catalog_build_test_config.yml`, but the stages and tests
must exist when the vars modules are imported (`domain_vars`, pytest markers, the
pipeline generator). So `./setup_env.sh --configure` (the `_configure` step of
`_setup.py`) resolves the list and freezes it:

1. `catalogs: all` = every `./omnia.sh --list-catalogs` entry in that order; a list
   keeps its own order (names or numbers, `setup_func.resolve_catalog`).
2. A catalog with an aarch64 functional layer is marked skipped unless
   `include_aarch64: true`; `true` needs `aarch64_inventory_host_ip` in
   user_inputs.yml, else configure fails.
3. The plan is written to `reports/catalog_build_plan.json` with the run id and the
   normalized settings, and printed.

`catalog_vars.load_plan()` reads it at import time. A changed
`catalog_build_test_config.yml` already needs a new `--configure` (the run guard),
so the plan always belongs to the current run; `initialization` checks it
(`Catalog plan of this run`). Without a plan the theme has no catalog stage.

## 4. Tests of a catalog stage

IDs `SVT_CATALOG_BUILD_<catalog NN><step NN>`, order `2000 + NN*100 + step`:

| Test | What it does | Step |
|---|---|---|
| `NN00 select` | SVT action (`catalog_func.run_action`): put back the shared runtime inputs, apply `catalog_overrides/<catalog>/<domain>/<file>`, write the global settings into `<OMNIA_DATA_PATH>/<domain>/input/<project>/`, then `./omnia.sh --select-catalog` | `svt select <catalog>` |
| `NN00 skip` | Instead of all the others, for a skipped catalog: one skipped test with the reason | `svt skip <catalog>` |
| `NN01`... | For every `steps` entry `[domain, tag]`: `<tag> exec` (the playbook), then `<tag> verify` | `fvt_<domain> <tag> exec` / `verify` |
| last | `cleanup_between` steps (`always`: they run even after a failure) | `fvt_<domain> cleanup... test` |

Global settings written before every catalog: `repo_config`, `caching_policy`,
`repo_policies` (`"<version>/<arch>/<repo>": {policy, caching}`) into
`repo_manager_config.yml`; `build_image.force_rebuild` (default **true**) and
`functional_groups_source: catalog` into `image_build_config.yml`.

The first test of a stage is the repo_manager precheck after select, so the existing
subscription-aware repository validation runs for every catalog; the theme adds no
repository check of its own. The FVT playbook timeout stays the omnia_auto default
(7200 s).

## 5. Hooks in shared code (build_stream unchanged)

| File | Change |
|---|---|
| `library/functions/test_func.py` | Optional test-case fields: `action` (an SVT action instead of an FVT step), `always` (runs after an earlier failure of the stage), `stop_leftovers` (after a failed exec, stop the orphaned `ansible-playbook <domain>.yml` workers and their children, which run in their own session and survive the FVT timeout). build_stream's tests carry none of them. |
| `library/functions/fvt_func.py` | `describe_step` labels an SVT action `svt <action> ...` |
| `library/functions/config_func.py` | A theme with `catalog_plan` loads its block with `catalog_settings.py` |
| `library/functions/readiness_func.py` | `Catalog plan of this run` check for catalog themes |
| `library/functions/setup_func.py` | `bundled_catalogs` and `select_catalog` made public (reused by the plan and the select action) |
| `_setup.py` | `_configure`: configure, then the plan for catalog themes |
| `library/vars/theme_vars.py`, `test_case_vars.py` | The catalog_build entry and its generated tests |
| `pipeline/setup_svt_project.py`, `pipeline/svt_ci.py` | One job per catalog, and the plan check at initialization (section 7) |

New files: `library/vars/catalog_vars.py`, `library/functions/catalog_settings.py`,
`library/functions/catalog_func.py`, `catalog_build_test_config.yml`,
`dataset_generator/profiles/catalog_build.yml`, `ut/test_catalog_build.py`.

## 6. Settings (`catalog_build_test_config.yml`)

| Key | Default | Effect |
|---|---|---|
| `catalogs` | `all` | `all` or an ordered list of `--list-catalogs` names / numbers |
| `include_aarch64` | `false` | `false` skips catalogs with an aarch64 layer |
| `repo_config` | `partial` | `always` / `partial` |
| `caching_policy` | `true` | repo_manager caching |
| `repo_policies` | `{}` | per-repository policy (`always` / `partial` / `never`) and caching |
| `force_rebuild` | `true` | `true` rebuilds every image; `false` reuses a matching image |
| `continue_on_failure` | `true` | every catalog stage is soft |
| `cleanup_between` | `none` | `none` / `images` / `repos` / `full` after every catalog |
| `steps` | 8 steps | `[domain, tag]` FVT steps of every catalog |

`cleanup` and `report` blocks: as in `build_stream_test_config.yml`.

## 7. GitLab pipeline

The SVT pipeline (`pipeline/`) creates one job per theme stage when the CI files are
rendered, before any `--configure` on the OIM. For a catalog theme,
`setup_svt_project.catalog_plan()` therefore resolves the plan on the generating host
with the same `catalog_func.plan()` (this checkout's `catalog_build_test_config.yml`,
`user_inputs.yml` and `./omnia.sh --list-catalogs`), and renders:

* one job per catalog (`catalog_01` ...), titled with the catalog, `allow_failure`
  when `continue_on_failure` is true, timeout `timeouts_hours.catalog_stage`;
* `SVT_CATALOG_PLAN` = `<stage>=<catalog>,...`.

`svt_ci.py initialization` compares `SVT_CATALOG_PLAN` with the plan `--configure`
wrote on the OIM, before cleanup and install, and fails when they differ (a catalog list
edited in the project, or a tested branch with other bundled catalogs), because those
catalogs would have no job. The fix is `./setup_svt_project.py --update --update-inputs`.
build_stream's CI files are unchanged (no `SVT_CATALOG_PLAN`).
