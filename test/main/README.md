# Omnia Main — Test Automation (FVT + NFT)

Automated FVT and NFT for `omnia.sh` and `omnia-cli` — verifies environment
setup, domain initialization, CLI argument handling, actual execution,
performance, idempotency, and file permissions.

## Deploy vs Verify Architecture

Every scenario follows a three-phase pattern:

| Phase | What it does | Marker |
|-------|-------------|--------|
| `deploy` | **Executes** the actual omnia.sh / omnia-cli command. Changes state on target. | `@pytest.mark.deploy` |
| `verify` | **Checks results** after deploy. Read-only — inspects files, dirs, env vars. | *(no marker)* |
| `cleanup` | **Tears down** state (e.g. `--cleanup`). Must be explicitly requested. | `@pytest.mark.cleanup` |

The `test` command runs execution plus verification. Cleanup is **never
automatic** and remains a separately selected scenario.

The aggregate FVT order follows the production prerequisites and lifecycle:
`setup → init → precheck → validate → cli → omnia_cli`. Cleanup remains
explicit and runs only when selected.

This means:
- `./run_validation.sh fvt_main test` = execute the positive lifecycle once, then verify all FVTs
- `./run_validation.sh fvt_main verify` = verify all FVT scenarios in one pytest session
- `./run_validation.sh fvt_main setup test` = execute and verify setup only
- `./run_validation.sh fvt_main cleanup exec` = run cleanup explicitly

### Intelligent Skip for Setup & Cleanup

Setup (`--setup-venv`) and cleanup (`--cleanup`) modify the omnia production
venv. If you activated the **omnia venv** (for example,
`source /opt/omnia/venv/bin/activate` when that is `OMNIA_VENV_PATH`)
instead of the **test venv** (`source test/main/.venv/bin/activate`), these
tests auto-skip to prevent destroying the active interpreter.

## Quick Start

```bash
# 1. Create an isolated test venv (optional)
./setup_env.sh --venv

# 2. Activate the optional test venv (NOT the Omnia runtime venv)
source .venv/bin/activate

# 3. Configure target server
vi test_config.yml

# 4. Optional: create encrypted SSH credentials for remote password access
./setup_env.sh --set-creds

# 5. Run tests
./run_validation.sh fvt_main test                # Complete FVT lifecycle
./run_validation.sh fvt_main verify              # All read-only FVT checks
./run_validation.sh fvt_main setup test          # Setup only
./run_validation.sh fvt_main init test           # Init only
./run_validation.sh fvt_main precheck exec       # Precheck execution only
./run_validation.sh fvt_main cleanup exec        # Explicit cleanup only
./run_validation.sh nft_main test                # Performance + idempotency NFT
```

### Setup modes

| Mode | Command | Description |
|------|---------|-------------|
| Baremetal | `./setup_env.sh` | Installs test dependencies with `pip --user` |
| Active venv | `./setup_env.sh` | Uses the currently activated virtual environment |
| New test venv | `./setup_env.sh --venv` | Creates and installs into `test/main/.venv` |
| Force reinstall | `./setup_env.sh --force` | Reinstalls requirements in the selected environment |
| Recreate test venv | `./setup_env.sh --venv --force` | Recreates `.venv` and reinstalls requirements |

The Omnia runtime venv is separate and is created by
`./src/main/omnia.sh --setup-venv` at `OMNIA_VENV_PATH`. The test setup script
does not create or manage that production environment.

### SSH credentials

SSH credentials are optional when passwordless SSH works. Create or update the
local encrypted credential file with:

```bash
./setup_env.sh --set-creds
./setup_env.sh --update-creds
```

The generated `test_creds.yml` and `.test_creds.key` remain local and are
gitignored.

## Structure

```
test/main/
├── conftest.py              # Pytest configuration, fixtures, markers
├── test_config.yml          # Test configuration (non-sensitive)
├── test_creds.yml           # Generated SSH credentials (encrypted, gitignored)
├── requirements.txt         # Python dependencies
├── setup_env.sh             # Dependency, optional venv, and credential setup
├── run_validation.sh        # Thin wrapper around omnia_auto ValidationRunner
├── _run.py                  # Main runner entry point and domain configuration loader
├── README.md                # This file
├── library/                 # Test automation library
│   ├── __init__.py
│   ├── functions/           # Verification functions
│   │   ├── __init__.py
│   │   ├── omnia_main_func.py
│   │   ├── output_func.py   # Structured CLI and report details
│   │   └── validation_func.py
│   ├── vars/                # Constants and commands
│   │   ├── __init__.py
│   │   ├── common_vars.py
│   │   ├── domain_vars.py   # FVT scenarios, suites, markers, exclusions
│   │   └── test_case_vars.py # Stable FVT/NFT IDs and titles
│   └── messages/            # Test messages
│       ├── __init__.py
│       └── omnia_main_msgs.py
├── fvt/                     # Functional Verification Tests
│   ├── README.md            # FVT test case registry + deploy/verify docs
│   ├── setup/               # omnia.sh --setup-venv tests
│   │   ├── test_deploy_setup.py       # @deploy: run --setup-venv --deps-only
│   │   ├── environment/               # verify: env file, variables, source validation
│   │   ├── virtual_environment/       # verify: Python venv, ansible, pip, Galaxy
│   │   ├── directories/               # verify: base directories, activate helper
│   │   └── lifecycle/                 # extended setup workflow checks
│   ├── init/                # omnia.sh --init tests
│   │   ├── test_deploy_init.py        # @deploy: run --init
│   │   ├── domain_init/              # verify: domain log dirs, input staging
│   │   └── lifecycle/                # extended domain-init workflow checks
│   ├── precheck/            # @deploy: run image_build_manager precheck
│   ├── validate/            # @deploy: run image_build_manager validate
│   ├── cli/                 # CLI argument tests
│   │   ├── test_deploy_cli.py         # @deploy: run --help (entry point)
│   │   ├── commands/                  # verify: flag parsing, error handling
│   │   │   ├── test_commands.py       # verify: existing CLI commands
│   │   │   └── test_skip_dryrun.py    # verify: --skip, --dry-run
│   │   ├── prepare_base/             # verify: --prepare-base CLI tests
│   │   │   └── test_prepare_base.py  # verify: --prepare-base, --dry-run, --skip
│   │   └── tags/                      # verify: tag verification
│   ├── omnia_cli/           # omnia-cli diagnostics tests
│   │   ├── test_deploy_omnia_cli.py   # @deploy: run omnia-cli help
│   │   ├── diagnostics/              # verify: status, check, domain commands
│   │   ├── errors/                   # verify: unknown command errors
│   │   └── logs/                     # verify: log commands
│   └── cleanup/             # explicit destructive cleanup scenario
└── nft/                     # Non-Functional Tests
    ├── README.md            # NFT test cases and thresholds
    ├── __init__.py
    ├── test_performance.py      # Performance threshold tests (setup, init, check-deps)
    ├── test_idempotency.py      # Idempotency tests (setup, init)
    ├── test_permissions.py      # File permission tests (env, omnia.sh, omnia-cli, domain-init)
    └── test_cli_performance.py  # CLI performance tests (status, help)
```

## Scenarios

| Scenario | Deploy (what it runs) | Verify (what it checks) |
|----------|----------------------|------------------------|
| `setup` | `omnia.sh --setup-venv --deps-only` | Env files, venv, Ansible, directories, core Python tooling, merged requirements from all seven domains, and Galaxy collection versions |
| `init` | `omnia.sh --init` | Domain log dirs, input file staging (7 domains) |
| `precheck` | `--run image_build_manager --tags precheck` | Command completion and precheck contract |
| `validate` | `--run image_build_manager --tags validate` | Command completion and validation contract |
| `cli` | `omnia.sh --help` (entry point) | Help output, flag parsing, error handling, tags, --prepare-base |
| `omnia_cli` | `omnia-cli help` | Status, check, version, domain queries, logs, errors |
| `cleanup` | `omnia.sh --cleanup` | Explicit cleanup only; excluded from aggregate runs |
| `nft` | `--setup-venv`, `--init`, `omnia-cli status` | Performance thresholds, idempotency, file permissions |

## Result output

FVT results use a short PASS, FAIL, or SKIP summary followed by structured
key/value details. Successful command tests show the command, expected return
code, actual return code, and duration. Verification tests show the resolved
paths, counts, versions, or missing items relevant to the check. Long command
output is not printed on success, and diagnostic text is compacted on failure.
Credential values and other secrets are never included.

The same test-case ID and structured fields are preserved in the JSON and HTML
reports generated under the configured report path.

## Markers

| Marker | Description |
|--------|-------------|
| `sanity` | Positive, repeat-safe baseline tests only |
| `functional` | Extended behavior, force, filtering, and rerun tests |
| `regression` | Negative input and error-handling tests |
| `deploy` | Script execution tests (setup, init, run — **change state**) |
| `cleanup` | Teardown tests (run after verify — **may destroy state**) |
| `nft` | Non-functional tests (performance, idempotency, permissions) |

### Filtering by Marker

```bash
# Run only positive sanity checks across all FVT scenarios
./run_validation.sh fvt_main verify --marker sanity

# Run only sanity tests for a specific scenario
./run_validation.sh fvt_main setup verify --marker sanity
./run_validation.sh fvt_main cli verify --marker sanity

# Run only NFT-marked tests
./run_validation.sh nft_main test --marker nft

# Combine markers with AND (all must match)
./run_validation.sh fvt_main setup verify --marker "sanity+functional"

# Combine markers with OR (any must match)
./run_validation.sh fvt_main setup verify --marker "sanity,functional"
```

## Configuration

Edit `test_config.yml` to set:
- **`oim_server_ip`**: Target server IP (empty = local mode)
- **`clone_path`**: Path to omnia repo on target

Runtime paths are not duplicated in the test configuration. The tests read
`OMNIA_DATA_PATH`, `OMNIA_PROJECT_NAME`, and `OMNIA_VENV_PATH` from the
target's `/etc/omnia/omnia.env`. During initial bootstrap, they use
`<clone_path>/src/main/omnia.env`, followed by the production defaults.

## Dependencies

- Python 3.12+
- `omnia_auto` wheel (from `test/plugins/dist/`)
- pytest, pytest-testinfra, pytest-order
