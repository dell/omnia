# SVT setup: `./setup_env.sh`, the inputs and the dataset generator

How to prepare an OIM for the SVT of `test/system_test` (see its [README](README.md) for
the stages, the run and the report): the setup script, `user_inputs.yml` and the dataset
generator that turns it into the Omnia inputs.

## `./setup_env.sh`

`setup_env.sh` creates (or reuses) the SVT's own `.venv/` and runs every step
with it through the Python wrapper `_setup.py`. That venv is never activated.
With no action it runs every step in order and stops at the first failure.
Running it again is quick: steps with nothing to do are skipped.

| Command | Steps |
|---|---|
| `./setup_env.sh` | configure → install → credentials |
| `./setup_env.sh --force` | configure → cleanup → full install → credentials |
| `./setup_env.sh --configure` | configure |
| `./setup_env.sh --install` | install |
| `./setup_env.sh --install --force` | cleanup → full install |
| `./setup_env.sh --cleanup` | cleanup |
| `./setup_env.sh --set-domain-creds` / `--update-domain-creds` [`--domain <d>`] | prompt every store (or one) |
| `provider \| ./setup_env.sh --domain-creds-stdin` | write the stores from JSON keyed by domain |
| `./setup_env.sh --status` | show the status box (read-only) |

Options: `--theme <theme>` (default `build_stream`; its settings are
`<theme>_test_config.yml`), `--yes` (answer every confirmation), `--force`
(with no action or `--install`), `--domain <d>`, `--recreate-venv` (the SVT
`.venv/`), `--debug` (pip output), `--help`.

### What each step does

**configure**
- The dataset generator writes `user_inputs.yml` into `src/<domain>/input` and
  `src/main/omnia.env`, with the profile `dataset_generator/profiles/<theme>.yml`.
- It starts a new SVT run, first of all: a new `run_id` (`svt-<UTC time>`,
  unless `report.run_id` is set), the theme and the run folder
  `<report_path>/<run_id>/`. Every later step (cleanup, install, creds,
  `./run_validation.sh`) adds to this run; see [The run](#the-run).
- The `cleanup` flags and the `build_stream` block (catalog,
  cadence_catalog, allow_pipeline_cancel) of `build_stream_test_config.yml`
  are written into each `test/<suite>/test_config.yml`.
- The FVT report settings of the run (`<run folder>/fvt`, `fvt_report`, the
  run id) are written into every suite's `test_config.yml` (main,
  repo_manager, image_build_manager, orchestrator, build_stream), so their
  results can be shown in the [SVT report](#the-svt-report).
- It checks `main.catalog` against `./omnia.sh --list-catalogs`.
- It stops on a YAML error, an unknown key, a credential-like key, an empty
  MANDATORY value or an unknown catalog.

**cleanup** (DESTRUCTIVE)
- It writes the cleanup flags again, lists the steps and asks for `yes`; `--yes`
  confirms without asking.
- It then runs, in order:
  1. `fvt_build_stream cleanup test` (only when BuildStream is installed);
  2. `fvt_orchestrator cleanup test`;
  3. `fvt_image_build_manager cleanup test`;
  4. `fvt_repo_manager cleanup test --marker destructive`;
  5. with `cleanup.main.cleanup_all: true` (default): every
     `src/<domain>/domain-init.sh --cleanup` (each domain's input and log
     artifacts). `omnia.sh --cleanup --all` runs the same helpers, but only
     after a preflight that refuses while `<data>/<domain>/log` holds a file;
     the validate playbooks write logs there and no domain cleanup tag removes
     them, so without this step `--all` stops and removes nothing;
  6. `fvt_main cleanup test` from `test/main/.venv`: `omnia.sh --cleanup --all
     --skip-approval` (the whole `OMNIA_DATA_PATH`, credential stores
     included), or `omnia.sh --cleanup` with `cleanup_all: false`; then the
     verify cases MAIN_FVT_CLEANUP_V001-V005 check what was removed.
- **Complete reset:** after `cleanup_all` nothing of the previous installation
  is left, so the next install asks no "overwrite existing files?" question.
  omnia.sh refuses, and deletes nothing, while a domain still holds deployed
  state; the cleanup block of the report shows which.
- **Report location:** with `cleanup_all` the cleanup refuses when the report
  directory is inside `OMNIA_DATA_PATH`, which it would delete.
- **test/main venv:** test/main skips `omnia.sh --cleanup` when the Omnia venv
  is the active virtualenv, so the SVT always runs it with `test/main/.venv`.
- It is skipped when there is no `/etc/omnia/omnia.env`. A suite with
  `enabled: false` is skipped.

**install**
- It runs `src/main/omnia.sh -s` with its full output, outside any active venv
  (`omnia.sh` creates the venv, every `domain-init.sh`, the catalog and
  `omnia-cli`).
- With `main.catalog` set in `user_inputs.yml` it then runs
  `./omnia.sh --select-catalog <name>` (answering its replace question).
- It then installs the test requirements into the Omnia venv, in order:
  repo_manager, image_build_manager, orchestrator, build_stream. Each suite's
  `setup_env.sh` runs with the venv active and `omnia.env` exported.
- **Inputs must be current:** it needs the inputs configured and unchanged
  since.
- **omnia.env:** after a clean reinstall (`--force`) `/etc/omnia/omnia.env` is
  created fresh from `src/main/omnia.env`. An install on top of an existing
  setup adds `--force-env` when the two differ, so the configured values are
  used. There is no setting for it.
- **Inputs already on the OIM:** domain-init asks on the terminal before
  overwriting them. With `--yes` (or without a terminal), each domain whose
  runtime inputs still differ from src is re-staged with
  `domain-init.sh --force`. Any file that still differs is reported.
- **When a new install is needed:** only when configure changed what the last
  install installed: the src inputs the generator writes (checksum of every
  file of the theme profile) or the selected catalog. A comment or a value
  the generator leaves unchanged in `user_inputs.yml` needs only
  `--configure`.
- **Requirements are not reinstalled when nothing changed:** a suite is only
  installed again when its `requirements.txt`, its `setup_env.sh` or the
  omnia_auto wheel changed. The checksums are kept in
  `<venv>/.svt_test_requirements.json`.
- **`--force`:** cleanup first, then `omnia.sh -s --force-deps`, and every
  test requirement again.

**credentials**
- Only the missing stores are written: repo_manager, image_build_manager,
  orchestrator, build_stream.
- On a terminal you are prompted for each one. Unattended, the JSON on stdin
  is passed once to `--domain-creds-stdin`.
- It runs `test/build_stream/setup_env.sh` with the Omnia venv activated. It
  needs the installed Omnia.
- The prompts and the JSON are never logged.
- The output you see is that script's. Its closing "Next steps"
  (`./run_validation.sh fvt_build_stream list`) and its "No SSH credentials
  (test_creds.yml)" warning are written for the FVT and do not apply to the
  SVT, where `./run_validation.sh` accepts only `svt_<theme>`. After the
  stores are written, the SVT prints that and its own next step
  (`./run_validation.sh svt_<theme> all`).

**`--set-domain-creds` / `--update-domain-creds` / `--domain-creds-stdin`**
- These run the same `test/build_stream/setup_env.sh` flag for every store (or
  `--domain <d>`), with the Omnia venv activated.
- They need the installed Omnia; otherwise: "Omnia is not set up (omnia.sh -s
  has not run)".

Every value about the installation is read from `/etc/omnia/omnia.env`: the
venv, the data path, the project and the domain data paths
(`<DOMAIN>_DATA_PATH`, else `<OMNIA_DATA_PATH>/<domain>`).

**Why credentials are not placed in `src/<domain>/input`:** domain-init copies
every file of `src/<domain>/input` to `<data>/<domain>/input/<project>`, but
with `rsync --exclude='.*'`. Each store's vault key is a dot file
(`.<store>_key`), so it would not be copied, and the stores would sit in the
git checkout. They are therefore written directly to the runtime folders,
after `omnia.sh -s` has created them.

### `--status`

```text
┌─ SVT setup status - theme build_stream ─────────────────────────────────────┐
│        step       status   started (UTC)              duration              │
│ [ OK ] configure  passed   2026-11-03T09:00:01+00:00  3s                    │
│ [ -- ] cleanup    not run                                                   │
│ [ OK ] install    passed   2026-11-03T09:00:04+00:00  14m21s                │
│ [ OK ] creds      passed   2026-11-03T09:14:25+00:00  1m02s                 │
├─ ready for ./run_validation.sh svt_build_stream? ───────────────────────────┤
│ [ OK ] Inputs configured (user_inputs.yml, build_stream_test_config.yml)    │
│ [ OK ] Omnia installed (omnia.sh -s: omnia.env, data path, venv, ...)       │
│ [ OK ] Installed after the last configure                                   │
│ [ OK ] Test requirements in the Omnia venv (4 suites)                       │
│ [ OK ] Credentials: repo_manager                                            │
│ ...                                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ READY: ./run_validation.sh svt_build_stream all                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

A failed check shows its HOW TO FIX line under it. The same box is printed at
the end of `./setup_env.sh` and `--install`.

## Unattended runs

Every question the SVT asks can be answered on the command line:

| Question | Unattended answer |
|---|---|
| cleanup: "Type 'yes'" | `--yes` (without it and without a terminal, cleanup is refused) |
| domain-init: "Overwrite existing files?" | `--yes`: `omnia.sh -s` gets no stdin, then `domain-init.sh --force` for the stale domains |
| credential prompts | JSON keyed by domain on stdin (`provider \| ./setup_env.sh --yes`, or `--domain-creds-stdin`) |
| `./run_validation.sh` | asks nothing; FVT steps run with an empty stdin. `--quiet` writes to the stage logs only |

## `user_inputs.yml` and the dataset generator

`user_inputs.yml` holds the values of one cluster. It uses the same key names
and indentation as the real input files, so a value goes into the same place
in the matching file.

- **Order:** one block per module: main → repo_manager → image_build_manager →
  orchestrator → build_stream.
- **MANDATORY values:** OIM identity, admin network, BuildStream and GitLab
  IPs. configure stops and lists any left empty.
- **Optional values:** `""` (or `[]`) is written as empty, so clearing a value
  in `user_inputs.yml` clears it in the input file too. A blank never changes
  a boolean, a number, a block or a list of items.
- **Paths:** `OMNIA_DATA_PATH`, `OMNIA_PROJECT_NAME` and `OMNIA_VENV_PATH` are
  not asked; they keep the values of `src/main/omnia.env`.
- **Catalog:** `main.catalog` is a number or a name of
  `./omnia.sh --list-catalogs` (`""` = the default catalog). configure checks
  it and records the name; install then runs
  `./omnia.sh --select-catalog <name>`, which copies it to `CATALOG_FILE_PATH`
  of `omnia.env` (and keeps a backup of the previous one).
- **PXE mapping:** the CSV keeps its header line; all its rows are replaced by
  `row1`, `row2`, ...
- **DNS:** `orchestrator.orchestrator_config.dns_enabled` (`true` | `false`)
  goes into `src/orchestrator/input/orchestrator_config.yml`. The product's
  default is `true`, and then every HOSTNAME of the PXE mapping must be
  `nid001` ... `nid999`. The generator stops (naming each row) when
  `dns_enabled` is true and a hostname is not a nid name, before anything is
  installed. With `false`, nodes use `/etc/hosts` and may have free-form names.
- **VAST:** without a VAST `source`, the generator comments out the whole
  `vast_storage` mount and `vast_storage_name` (the product then skips VAST),
  and does not merge the `vast_storage` item of `user_inputs.yml`. Giving a
  source restores them.

The generator can also run alone:

```bash
cd dataset_generator
../.venv/bin/python generate_dataset.py --dry-run   # what would change
../.venv/bin/python generate_dataset.py             # fill src/<domain>/input
../.venv/bin/python generate_dataset.py /abc        # or: a full input tree in /abc
```

The output-folder mode creates the folder and copies every non-credential
input file into it; an existing file that would change is moved to
`/abc/.backup/<UTC time>/`. To fill another input file, add a block to
`user_inputs.yml` and a target to `dataset_generator/profiles/<theme>.yml`.

## Files of this part

```text
test/system_test/
├── SETUP.md                     this file
├── setup_env.sh, _setup.py      prepare the OIM: configure, cleanup, install, credentials, status
├── user_inputs.yml              the cluster values
├── dataset_generator/           user_inputs.yml -> src inputs (profiles/<theme>.yml)
└── library/functions/           setup_func (setup steps), cleanup_func (cleanup),
                                 status_func (status box)
```

## Local checks

```bash
cd <repository root>
find test/system_test -name '*.sh' ! -path '*/.venv/*' -print0 | xargs -0 shellcheck -f gcc
ansible-lint --config=.config/ansible-lint.yml test/system_test/user_inputs.yml
```
