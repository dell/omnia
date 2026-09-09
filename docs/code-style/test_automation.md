# Test Automation Standard

> This is the normative coding and operating standard for every test domain
> under `test/`.

The architecture in `test/image_build_manager/` is the reference pattern.
Copy its separation of responsibilities, not defects or legacy exceptions
found in that implementation. Existing code that conflicts with this standard
is technical debt, not precedent.

The canonical copy is `docs/code-style/test_automation.md`. The Omnia_Spec
repository mirrors it as `specs/code-styleguides/test_automation.md`.

Change the canonical file first. Update the mirror in the same change set and
verify the two files are byte-for-byte identical. Do not maintain independent
versions.

Related references:

- `docs/design/test-automation-design.md`
- `docs/code-style/general.md`
- `test/plugins/USAGE.md`
- `test/plugins/docs/`

---

## 1. Core Rules

1. Tests describe user-visible behavior, not implementation trivia.
2. Test files orchestrate; reusable functions perform operations.
3. Variable modules hold data; message modules hold operator-facing text.
4. Secrets never enter source control, process arguments, environment
   variables, logs, reports, datasets, or generated templates.
5. Domain code reuses `omnia_auto` before duplicating infrastructure.
6. Configuration, tags, suites, markers, and physical directories agree.
7. Missing or invalid configuration fails closed with an actionable message.
8. Destructive execution is explicit and excluded from implicit `all` runs.
9. Static checks run locally in the same scope as affected files.
10. Runtime checks are proportional to the available environment. A missing
    lab is reported; it is never replaced with a false success claim.

Terms:

- **development host**: the host where the repository is edited;
- **execution OIM**: the Omnia Infrastructure Manager running the playbook;
- **target host**: a node, appliance, cluster, or service under validation;
- **transport credential**: the credential used to reach the execution OIM;
- **domain credential**: a credential used by the product domain or target;
- **FVT**, **NFT**, **UT**: functional, non-functional, and unit tests.

---

## 2. Mandatory Development Sequence

Follow this order for every new domain, feature, or test case.

### 2.1 Establish scope

1. Read the user story, acceptance criteria, and relevant design documents.
2. Read the product playbook entry points and roles.
3. Record each supported playbook tag, host group, created resource, input,
   output, skip path, failure mode, and cleanup effect.
4. Identify which checks require a live environment and which can run locally.
5. Identify destructive flows before defining runner defaults.

Source inspection establishes the contract. Tests MUST NOT import product
internals or duplicate source algorithms merely because source was inspected.
This is a developer analysis step only: the `test-domain-compliance` skill
inspects and scores `test/<domain>` and MUST NOT inspect or score `src/`.

### 2.2 Build a capability map

Map each capability end to end:

```text
source behavior
  -> FVT tag
  -> physical tag directory
  -> suite
  -> marker
  -> test case ID
  -> verification function
  -> expected report output
```

Include success, skipped, disabled, partial-failure, unreachable, idempotency,
and cleanup behavior where supported.

### 2.3 Reuse shared automation first

Before adding a function:

1. Search `test/plugins/omnia_auto/`.
2. Read `test/plugins/USAGE.md` and the relevant plugin API document.
3. Inspect the public exports in `omnia_auto.__all__`.
4. Reuse a suitable shared function.
5. Add a domain helper only for genuinely domain-specific behavior.
6. Propose a plugin change when behavior is generic and useful to two or more
   domains.

Do not wrap a shared function only to rename it. A wrapper is justified when it
adds a stable domain contract, domain validation, or result normalization.

### 2.4 Design before tests

1. Put non-sensitive settings in `test_config.yml`.
2. Put batch-selection settings in `test_run_config.yml`.
3. Define transport and domain credentials separately.
4. Define safe interactive and standard-input provisioning.
5. Define defaults without lab-specific addresses or identities.
6. Implement metadata, variables, messages, functions, fixtures, then tests.
7. Add datasets only when the domain consumes input files.
8. Finish README and configuration references before handoff.

### 2.5 Validate before handoff

1. Run syntax and import checks.
2. Run applicable repository static checks.
3. Run isolated UT when available.
4. Run FVT/NFT only with a suitable environment and authorization.
5. Record commands, results, skipped runtime checks, and residual risks.
6. Inspect the final diff for secrets, generated noise, and unrelated files.
7. Create a human-authored, DCO-signed commit only after validation.

---

## 3. Capability-Aware Directory Structure

Include only supported capabilities. `[required]` means every domain;
`[when used]` means conditional.

```text
test/<domain>/
├── README.md                              [required]
├── conftest.py                            [required]
├── _run.py                                [required]
├── run_validation.sh                      [required]
├── setup_env.sh                           [required]
├── requirements.txt                       [required]
├── test_config.yml                        [required]
├── test_run_config.yml                    [required]
├── .gitignore                             [required]
├── docs/
│   ├── test_config.md                     [required]
│   ├── test_run_config.md                 [required]
│   └── test_creds.md                      [when credentials are used]
├── library/
│   ├── functions/
│   │   ├── __init__.py                    [required]
│   │   ├── <capability>_func.py           [when domain helpers are needed]
│   │   ├── _config_helpers.py             [when private helpers are needed]
│   │   └── <domain>_func.py               [optional compatibility facade]
│   ├── vars/
│   │   ├── __init__.py                    [required]
│   │   ├── common_vars.py                 [required]
│   │   ├── domain_vars.py                 [required]
│   │   ├── test_case_vars.py              [required]
│   │   └── ut_test_case_vars.py           [when UT metadata is separate]
│   └── messages/
│       ├── __init__.py                    [required]
│       └── <domain>_msgs.py                [required]
├── fvt/
│   ├── README.md                          [required]
│   └── <tag>/
│       ├── test_<tag>.py                  [when the tag itself is verified]
│       └── <suite>/test_<capability>.py   [when suites divide the tag]
├── nft/
│   ├── README.md                          [when NFT is supported]
│   └── test_<quality>.py                  [when NFT is supported]
├── ut/
│   └── test_<unit>.py                     [when UT is supported]
└── datasets/
    ├── generator/
    │   ├── generate_dataset.py            [when inputs are generated]
    │   ├── profiles/                      [when profiles are used]
    │   │   └── defaults.yml               [when profiles are used]
    │   └── templates/                     [when files are rendered]
    └── <dataset>/input/                   [when fixtures are versioned]
```

Do not create empty placeholder capabilities. For example, omit `nft/` when
there is no defined non-functional contract.

Generated local files MUST be ignored:

```text
.venv/
__pycache__/
.pytest_cache/
reports/
test_creds.yml
.test_creds.key
```

Ignore domain credential artifacts if they are ever staged locally. Do not use
a broad ignore pattern that hides tracked examples or test sources.

---

## 4. First-Use Workflow

Every domain README MUST present this order before advanced examples.

```bash
cd test/<domain>
./setup_env.sh --venv
source .venv/bin/activate
```

If password-based SSH is required, create transport credentials locally:

```bash
./setup_env.sh --set-creds
```

If the domain requires product or appliance credentials, run its prompt on the
execution OIM, where `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` resolve to the
real project:

```bash
./setup_env.sh --set-domain-creds
```

Review non-sensitive settings and discover the registered surface:

```bash
${EDITOR:-vi} test_config.yml
${EDITOR:-vi} test_run_config.yml
./run_validation.sh --help
./run_validation.sh fvt_<domain> list
```

Verify prerequisites before mutation:

```bash
./run_validation.sh fvt_<domain> precheck verify
```

Run one supported tag with one explicit action:

```bash
./run_validation.sh fvt_<domain> <tag> exec
./run_validation.sh fvt_<domain> <tag> verify
./run_validation.sh fvt_<domain> <tag> test
```

`test` means `exec` followed by `verify`. Execution failure MUST prevent a
misleading successful verification result.

Run enabled batch entries only after reviewing the file:

```bash
./run_validation.sh --config
```

Optional NFT and UT use:

```bash
./run_validation.sh nft_<domain> test
./run_validation.sh ut_<domain> test
```

Replace placeholders with the real domain name in its README and state its
safe lifecycle order. Identify destructive cleanup explicitly.

---

## 5. Credential Contract

### 5.1 Separate scopes

| Scope | Purpose | Storage | Owner |
|---|---|---|---|
| Transport | Reach execution OIM | Local encrypted credential pair | Developer or CI job |
| Domain | Authenticate product targets | Project input on execution OIM | Project operator |

The local transport pair is `test_creds.yml` and `.test_creds.key`. Both MUST
have mode `0600`, be encrypted at rest, and be gitignored. Passwordless SSH may
make transport credentials optional.

Domain credentials MUST be written beneath:

```text
$OMNIA_DATA_PATH/<domain>/input/$OMNIA_PROJECT_NAME/
```

Use the filename defined by the domain contract. Never copy domain credentials
into the repository, a dataset, report directory, or transport credential file.

### 5.2 Interactive provisioning

Interactive secret input uses a hidden prompt and confirmation:

```bash
./setup_env.sh --set-creds
./setup_env.sh --update-creds
./setup_env.sh --set-domain-creds
./setup_env.sh --update-domain-creds
```

Visible prompts are allowed only for non-secret fields. Existing credentials
are preserved unless the user selects an update action.

Each credential-enabled domain defines one ordered, non-secret field
specification. A field entry contains a stable key, display label, whether it
is secret, whether it is optional, and an optional prompt group. The same
specification drives interactive prompts, standard-input allow-list
validation, and `docs/test_creds.md`; do not maintain three independent field
lists. Secret fields use hidden input and confirmation. Use the shared
`omnia_auto` credential API, such as `prompt-fields`, rather than implementing
domain-specific password prompting or vault writes.

### 5.3 Non-interactive provisioning

Automation passes secret payloads through standard input:

```bash
credential_provider | ./setup_env.sh --creds-stdin
domain_credential_provider | ./setup_env.sh --domain-creds-stdin
```

The transport payload is one password or a documented JSON object. The domain
payload is a JSON object with documented fields. One setup invocation accepts
at most one standard-input credential payload. Provision independent scopes in
separate invocations.

Standard-input handlers MUST:

1. enforce a bounded input size;
2. require the expected payload type;
3. validate field names and value types;
4. reject unknown fields unless the schema permits them;
5. never echo the payload;
6. use temporary files under `umask 077`;
7. remove temporary plaintext on every exit path;
8. encrypt and replace the destination atomically;
9. enforce mode `0600` on keys and credential files.

### 5.4 Forbidden secret transport

These patterns are prohibited:

```text
./setup_env.sh --creds '<password>'
./setup_env.sh --password '<password>'
./setup_env.sh --domain-creds '{...}'
PASSWORD='<password>' ./setup_env.sh ...
```

Secrets MUST NOT appear in arguments, process listings, shell history, debug
traces, environment variables, source, tests, fixtures, comments, URLs,
inventory strings, pytest parameters, assertion text, logs, reports, datasets,
or manifests. Redaction is defense in depth, not permission to use an unsafe
channel. Fake examples MUST be unmistakably synthetic.

---

## 6. `setup_env.sh` Contract

`setup_env.sh` owns environment preparation and credential provisioning. It
MUST NOT run a domain playbook or validation suite.

Required behavior:

- default: install missing requirements into the active or documented user
  environment;
- `--venv`: create or reuse `.venv/`;
- `--force`: reinstall declared requirements;
- `--venv --force`: recreate or safely refresh `.venv/` and reinstall;
- `--debug`: increase diagnostics without enabling secret echo;
- interactive and standard-input credential options from section 5;
- domain credential options only when the domain needs them;
- `--help`: document every option and storage effect.

The script MUST:

1. use strict shell behavior appropriate to its control flow;
2. resolve its directory without assuming the current directory;
3. quote paths and variable expansions;
4. use a restrictive `umask` before credentials;
5. reject incompatible options before changing files;
6. be idempotent without force/update options;
7. install `requirements.txt`, including the repository wheel path;
8. print next safe commands without secrets;
9. return non-zero on installation or credential failure.

Do not add tab completion, shell-profile mutation, system-wide configuration,
or network-side effects merely as setup convenience.

---

## 7. Runner and Configuration

### 7.1 Entry points

`run_validation.sh` is a small, strict delegator:

```text
locate domain -> select Python -> invoke _run.py -> preserve exit code
```

It does not perform setup, prompt for credentials, parse domain configuration,
or contain test logic.

`_run.py` imports the catalog from `library/vars/domain_vars.py` and delegates
to the shared `ValidationRunner`. The catalog defines:

```python
DOMAIN_NAME = "<domain>"
FVT_TAGS = ["precheck", "validate", "deploy", "cleanup"]
MARKERS = ["sanity", "functional"]
SUITES = {
    "precheck": ["environment"],
    "deploy": ["services", "data"],
    "cleanup": ["cleanup"],
}
EXCLUDE_TAGS = ["cleanup"]
```

These values illustrate structure only. Domains use their real catalog.

### 7.2 CLI grammar

```text
run_validation.sh fvt_<domain> list
run_validation.sh fvt_<domain> [<tag>] <exec|verify|test> [options]
run_validation.sh nft_<domain> <test|verify> [options]
run_validation.sh ut_<domain> <test|verify> [options]
run_validation.sh --config
run_validation.sh --help
```

No-tag FVT behavior, if supported, MUST be shared-runner behavior and be
documented. Marker expressions are validated before reaching pytest.

### 7.3 Batch configuration

`test_run_config.yml` selects execution and never contains credentials:

```yaml
fvt_<domain>:
  <tag>:
    run: false
    command: verify
    suite: ""
    marker: ""
    dataset: ""
    sync_input: false
    sync_output: false

nft_<domain>:
  run: false
  command: test

ut_<domain>:
  run: false
  command: test
```

Only supported fields are allowed. Unknown sections, tags, suites, markers,
commands, or incompatible options fail before execution.

### 7.4 Fail-closed mapping invariant

For every FVT tag, all of these MUST agree:

1. product playbook tag or documented verification-only capability;
2. entry in `FVT_TAGS`;
3. physical `fvt/<tag>/` directory;
4. `SUITES[<tag>]` entries and physical suite directories;
5. registered pytest markers used beneath the tag;
6. `test_run_config.yml` entry;
7. README command and lifecycle documentation.

`EXCLUDE_TAGS` includes cleanup and every destructive or explicit-only tag.
Unknown values fail closed; they are not silently ignored.

---

## 8. `conftest.py` Session Lifecycle

`conftest.py` calls `omnia_auto.configure()` before consumers that depend on
configured paths.

```text
configure omnia_auto
  -> load and validate non-secret config
  -> load encrypted transport credentials when needed
  -> establish local, execution, and target host objects
  -> resolve dataset and sync policy
  -> initialize TestReport and hooks
  -> execute tests
  -> collect artifacts and render summary
  -> close connections and remove temporary plaintext
```

Rules:

- session fixtures own session resources;
- function fixtures isolate mutable per-test state;
- fixtures yield resources and clean up in `finally`;
- missing credentials fail with the exact safe setup command;
- optional capabilities skip with a documented reason;
- connection failures preserve the cause without secrets;
- hooks record the final pytest result once;
- no fixture mutates product state outside the declared execution phase.

Do not put verification algorithms, command catalogs, or message dictionaries
in `conftest.py`.

---

## 9. Functions, Variables, and Messages

### 9.1 Functions

`library/functions/__init__.py` is the domain public test API. Re-export
approved `omnia_auto` functions and explicit domain helpers. Define `__all__`;
never use wildcard imports.

Split domain logic into focused capability modules, as Image Build Manager
does for containers, storage, registries, status, cleanup, and validation.
Keep private configuration helpers private. A `<domain>_func.py` file may
remain as a compatibility facade, but it MUST NOT become a monolith.

Domain helpers MUST:

- represent one stable domain operation or verification;
- validate untrusted input at the boundary;
- use command templates from `common_vars.py`;
- execute through approved `omnia_auto` helpers;
- return structured results;
- avoid assertions and test metadata;
- close files, sessions, and connections deterministically.

Verification result contract:

```python
{
    "success": True,
    "details": {"resource": "example", "state": "ready"},
    "error": "",
    "skipped": False,
}
```

`success`, `details`, and `error` remain stable. Use `skipped` when a disabled
optional capability is valid.

Use `omnia_auto` for configuration, encrypted credentials, host construction,
SSH/local execution, synchronization, playbook execution, dataset selection,
runner dispatch, logging, symbols, timing, and reporting.

Use a domain helper to interpret a domain resource, build a validated domain
API request, verify domain data shape/freshness, or normalize a domain failure.
Do not add plugin APIs containing a product name or fixed lab topology.

### 9.2 Variables and commands

`common_vars.py` contains immutable non-sensitive constants, paths, safe
defaults, resource names, timeouts, retry limits, and a centralized `CMDS`
mapping. `domain_vars.py` contains only runner registration.
`test_case_vars.py` contains centralized test metadata.

Never put credentials, mutable fixture state, or executable behavior in a
variable module.

Commands MUST be centralized in `CMDS` and run without a shell when possible.
Prefer argument lists. If a remote helper needs a string, choose a fixed
template, strictly validate identifiers, quote at the final boundary, keep
secrets out, use a timeout, and check the return code.

Prohibited:

```python
os.system(user_value)
subprocess.run(user_value, shell=True)
eval(user_value)
exec(user_value)
yaml.load(untrusted_text)
```

Use `yaml.safe_load()`. Never deserialize untrusted pickle data.

### 9.3 Messages

`library/messages/<domain>_msgs.py` contains reusable messages:

```python
TEST_LOG_MSGS = {
    "wait_for_resource": "Waiting up to {timeout}s for {resource}",
}

TEST_ASSERT_MSGS = {
    "resource_not_ready": (
        "{resource} did not become ready. "
        "HOW TO FIX: verify service health and rerun the check."
    ),
}
```

Use named placeholders. Failures state what failed, safe diagnostic context,
and a concrete `HOW TO FIX` action. Never place credentials or raw authenticated
responses in a message.

---

## 10. Tests, Metadata, and Output

A test function should only obtain fixtures, load metadata, log its start,
call one reusable operation, render safe details, and assert the structured
result. Do not build SSH commands, parse large responses, load credentials, or
encode retry loops in tests.

Stable test-case IDs MUST use a domain-qualified identifier:

| Level | Required format | Example |
|---|---|---|
| FVT | `<DOMAIN>_FVT_<TAG>_<TYPE><SEQ>` | `IMGBM_FVT_PREPARE_V001` |
| NFT | `<DOMAIN>_NFT_<SEQ>` | `IMGBM_NFT_001` |
| UT | `<DOMAIN>_UT_<SEQ>` | `IMGBM_UT_001` |

- `<DOMAIN>` is the domain's documented, stable uppercase code. Image Build
  Manager uses `IMGBM`.
- `<TAG>` is the registered FVT runner tag converted to uppercase. Preserve
  word boundaries as underscores; for example, `cleanup_images` becomes
  `CLEANUP_IMAGES`. `FULL` is reserved for a documented untagged full-domain
  execution.
- `<TYPE>` is `E` for a case that executes the product operation or playbook
  and `V` for a read-only verification case.
- `<SEQ>` is a three-digit sequence beginning at `001`, unique within its
  complete ID prefix.
- The runner action `test` has no separate `T` identifier. It runs the
  applicable `E` case and, only after success, the corresponding `V` cases.
- NFT and UT IDs do not add FVT tag or E/V segments; this matches the Image
  Build Manager registry.

IDs and titles are centralized, unique within the domain, and stable when a
title or execution order changes. Retired IDs MUST NOT be reused. Never
hardcode IDs in `TestLogger` calls. A legacy-ID migration MUST update the
central registry, README tables, runtime output, and legacy-to-current mapping
atomically.

Register every marker before use. Markers represent useful selection axes such
as architecture, source, sink, feature, or `sanity`, not temporary labs.
`domain_vars.py`, pytest configuration, README, batch examples, and decorators
must agree.

Output uses `TestLogger`, shared symbols, and indentation helpers. It includes:

- one start record with ID and title;
- one final pass, fail, or skip record;
- concise named details;
- UTC timestamps when time is material;
- counts and endpoints without credentials;
- an actionable failure message.

Use a shared check symbol for each verified item. Do not print entire raw JSON
records on one line. Select safe keys and truncate samples. Compute earliest
and latest timestamps independently from returned records. Freshness and range
checks use timezone-aware UTC values.

Skip only a documented optional or disabled capability. Connection errors,
malformed config, and missing required resources fail. `xfail` requires an
issue reference and bounded removal plan.

---

## 11. Datasets and Synchronization

Create `datasets/` only when the domain consumes input files or needs stable
fixtures. Datasets contain non-secret inputs, never runtime credentials.

A generator SHOULD provide safe defaults, named profiles, Jinja templates with
`StrictUndefined`, validated overrides, deterministic names, safe YAML,
staging plus atomic publish, and checksums when reproducibility matters.

The generator rejects credential-like keys and secret-store values.
`--from-src`, if supported, copies non-sensitive templates only, never live
input, vault files, keys, passwords, or tokens.

Synchronization is directional:

```text
dataset/input -> execution OIM project input     sync_input
execution OIM project output -> local artifacts sync_output
```

Rules:

1. `exec` may perform explicitly selected input sync.
2. `verify` is read-only and never overwrites target input.
3. Output goes to an ignored artifact directory.
4. Paths remain beneath documented project directories.
5. Traversal, symlink escape, and broad-root destinations are rejected.
6. Credentials are excluded in both directions.

---

## 12. FVT, NFT, and UT Boundaries

FVT validates product behavior in a representative environment:

- `exec`: run the selected product operation;
- `verify`: observe existing state without mutation;
- `test`: run `exec`, then verify only after successful execution.

Cleanup checks both removed resources and intentionally preserved data.
Unreachable nodes are reported according to the product contract, never
silently discarded.

NFT measures a stated quality contract such as duration, idempotency, scale,
or recovery. Every threshold has a rationale and unit. NFT reuses FVT functions
where contracts fit and records environment assumptions.

UT exercises isolated parsing, validation, formatting, and decisions. It does
not require SSH, a cluster, appliance, live API, or real credentials. Mock at
the I/O boundary, not inside the tested logic.

A UT may read product files only when the domain explicitly declares a
source-contract capability. That exception does not expand compliance scoring
to product source or make source inspection mandatory for other domains.

Without a runtime environment, UT, imports, static analysis, and configuration
validation remain valid evidence. Report FVT/NFT as not run and identify the
missing prerequisite.

---

## 13. Changing `omnia_auto`

An `omnia_auto` change affects multiple domains. Treat source and wheel as one
interface even when the declared version is unchanged.

1. Prove no existing public function meets the need.
2. Confirm behavior is domain-neutral with at least two plausible consumers.
3. Preserve compatibility unless an approved migration is included.
4. Update code, explicit exports, types, docstrings, API docs, and focused tests.
5. Run package syntax, import, static, security, and available unit checks.
6. Build the wheel from the plugin packaging directory:

   ```bash
   cd test/plugins
   python -m build --wheel
   ```

7. Keep the version unless the release owner requests a bump.
8. Include the rebuilt tracked same-version wheel when repository policy tracks
   the artifact.
9. Force-reinstall that exact wheel in each affected domain environment:

   ```bash
   python -m pip install --force-reinstall dist/omnia_auto-*.whl
   ```

10. Verify installed path, version, and public symbols:

    ```bash
    python -c "import omnia_auto; print(omnia_auto.__file__); print(omnia_auto.__version__)"
    python -c "import omnia_auto; print(sorted(omnia_auto.__all__))"
    ```

11. Run focused checks for every affected domain.
12. Commit plugin source, docs, wheel, and required consumers together.

Do not publish to PyPI, change the version, commit a venv, or push unless the
maintainer explicitly requests it.

---

## 14. Security and Hardcoding

Validated configuration, inventory, fixtures, or non-secret datasets provide:

- IPs, hostnames, ports, namespaces, and project names;
- usernames and identities;
- file, mount, inventory, certificate, and kubeconfig paths;
- resource, service, container, topic, and metric names;
- timeouts, retries, sizes, thresholds, and counts;
- repository URLs and registry endpoints.

Protocol names and schema keys may be literal when part of a stable contract.
A lab value is never a stable contract.

Required properties:

- no plaintext credentials;
- no secret-bearing argv or environment variables;
- no `shell=True`, `os.system`, `eval`, or `exec` with dynamic data;
- no unsafe YAML loader or untrusted pickle;
- no disabled TLS verification by default;
- no blanket `failed_when: false`, `ignore_errors`, or swallowed exception;
- no broad recursive deletion or synchronization target;
- no output containing credentials, keys, tokens, or authenticated URLs.

For a suspected scanner false positive, trace source to sink and document why
attacker-controlled data cannot reach it. Do not weaken code or add a
suppression only to make a dashboard green.

---

## 15. Repository Check Applicability

Workflow files are authoritative. Re-read `.github/workflows/` before changing
this table because scope can change.

| Check | Current scope and enforcement |
|---|---|
| Pylint | Blocking for changed Python; each checked file must score at least 8.0. Manual runs can cover a full test domain. |
| Ansible Lint | Blocking production-profile check for changed YAML in its workflow scope. Workflow YAML is excluded. |
| Bandit | Blocking `-ll -ii` scan for changed Python, subject to workflow test-file exclusions. Reusable test helpers can remain in scope. |
| ShellCheck | Changed shell files are scanned; findings classified as errors block. Warnings still require review. |
| HPC compliance | Blocks patterns such as `shell=True`, `os.system`, dynamic `eval`/`exec`, and unsafe YAML. Pickle is advisory but must be justified. |
| Gitleaks | PR-range redacted secret scan; currently advisory through `continue-on-error`. A real leak still blocks release. |
| pip-audit | Build Stream requirements only; scanner failure is currently tolerated with `|| true`. It is not a domain dependency gate. |
| Pytest workflow | Changed `src/build_stream` Python only, with coverage. It does not execute domain FVT/NFT/UT. |
| Commit hygiene | Author, message, and repository-policy checks. It is distinct from DCO. |
| DCO | External check requiring a valid human `Signed-off-by` trailer. No local DCO workflow substitutes for it. |

There is no repository Flake8 workflow at this revision. Do not claim a Flake8
CI gate. Follow PEP 8 and any tool declared by the affected package.

Workflow exclusions are not coding exemptions. Test code remains subject to
credential and process-safety rules even when a scanner excludes a path.

---

## 16. Local Preflight and DCO

Run CI-parity checks from the repository root. The commands below are broader
full-domain examples; `.github/workflows/` remains authoritative for the exact
changed-file filters and thresholds.

```bash
git diff --check
python -m compileall -q test/<domain>
python -m pylint test/<domain>
find test/<domain> -type f -name '*.sh' -print0 \
  | xargs -0 --no-run-if-empty shellcheck
python -m bandit -ll -ii -r test/<domain>
```

Run Ansible Lint only for valid Ansible YAML within its workflow scope:

```bash
ansible-lint --config=.config/ansible-lint.yml <changed-ansible-yaml>
```

The domain-compliance skill is an additional static review, not a replacement
for repository workflows:

```bash
python <omnia-spec-root>/.agents/skills/engineering/\
test-domain-compliance/check_tests.py test/<domain> --tools
```

When an authorized environment exists, add focused evidence:

```bash
cd test/<domain>
./run_validation.sh ut_<domain> test
./run_validation.sh fvt_<domain> <affected-tag> verify
```

Run `exec`, `test`, cleanup, or NFT only with required authorization and
infrastructure. State “not run” when prerequisites are absent.

Before committing:

```bash
git status --short
git diff --check
git diff --name-only
git diff
```

Create a human-authored DCO commit:

```bash
git commit -s -m "test(<domain>): describe the behavior change"
```

Configured `user.name` and `user.email` identify the human author. Never
fabricate another person's signoff or add an AI identity trailer.

---

## 17. Review Checklists

### Domain checklist

- [ ] Source behavior and design documents were reviewed.
- [ ] Capability map covers resources, states, failures, and cleanup.
- [ ] Directory tree contains only supported capabilities.
- [ ] README first-use flow is complete and safe.
- [ ] Domain, tags, suites, markers, directories, and batch config agree.
- [ ] Destructive tags are excluded from implicit execution.
- [ ] Transport and domain credentials are separate and encrypted.
- [ ] Non-interactive secrets use bounded standard input only.
- [ ] Tests orchestrate; helpers contain reusable logic.
- [ ] Commands, variables, messages, and metadata are centralized.
- [ ] IDs and titles are unique and not hardcoded at call sites.
- [ ] Datasets contain no credentials and sync in the declared direction.
- [ ] FVT, NFT, and UT boundaries are respected.
- [ ] Documentation matches commands and defaults.

### `omnia_auto` checklist

- [ ] Shared need and consumers are documented.
- [ ] Existing APIs were checked first.
- [ ] Exports, docs, types, and focused tests were updated.
- [ ] Package static and security checks passed.
- [ ] Wheel was rebuilt from changed source.
- [ ] Version was preserved unless a bump was requested.
- [ ] Exact wheel was force-reinstalled and its API verified.
- [ ] Plugin, wheel, and consumers remain synchronized.
- [ ] Nothing was published or pushed without authorization.

### Handoff checklist

- [ ] Diff contains only intended test, plugin, artifact, and docs files.
- [ ] No secret, key, credential file, report, cache, or venv is tracked.
- [ ] Applicable workflow-equivalent checks passed.
- [ ] Runtime tests ran where an authorized environment existed.
- [ ] Unavailable runtime checks and risks are stated accurately.
- [ ] Human author and valid DCO signoff are present on each commit.
- [ ] Canonical guide and specification mirror are identical when changed.

---

## 18. Definition of Done

Test automation is complete when:

1. documented commands match the registered execution surface;
2. configuration and credential flows fail safely;
3. tests produce consistent, actionable output;
4. shared and domain responsibilities are separated;
5. datasets and synchronization preserve source-of-truth boundaries;
6. applicable static and security checks pass;
7. runtime evidence exists, or missing infrastructure is stated;
8. the diff is secret-free, focused, reviewed, and DCO-ready.
