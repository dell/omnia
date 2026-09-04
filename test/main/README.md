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

The `test` command runs deploy + verify. Cleanup is **never automatic** — use the explicit `cleanup` command.

This means:
- `./run_validation.sh setup test` = run `--setup-venv --deps-only`, verify (no cleanup)
- `./run_validation.sh setup verify` = only verify (assumes setup already ran)
- `./run_validation.sh execution test` = setup + init + run, verify (no cleanup)
- `./run_validation.sh execution cleanup` = run cleanup only (when explicitly needed)

### Intelligent Skip for Setup & Cleanup

Setup (`--setup-venv`) and cleanup (`--cleanup`) modify the omnia production
venv.  If you activated the **omnia venv** (`source /opt/omnia/venv/bin/activate`)
instead of the **test venv** (`source test/main/.venv/bin/activate`), these
tests auto-skip to prevent destroying the active interpreter.

## Quick Start

```bash
# 1. Setup test environment
bash setup_env.sh

# 2. Activate test virtual environment (NOT the omnia venv)
source .venv/bin/activate

# 3. Configure target server
vi test_config.yml

# 4. Run tests
run_validation setup test        # Setup + verify
run_validation init test         # Init + verify
run_validation cli verify        # CLI argument tests
run_validation omnia_cli test    # omnia-cli diagnostics
run_validation execution test    # Actual execution: setup, init, run (no cleanup)
run_validation execution cleanup # Cleanup only (when explicitly needed)
run_validation nft test          # Performance + idempotency NFT
run_validation all test          # Run all scenarios (no cleanup)
```

## Structure

```
test/main/
├── conftest.py              # Pytest configuration, fixtures, markers
├── test_config.yml          # Test configuration (non-sensitive)
├── test_creds.yml           # SSH credentials (auto-encrypted)
├── requirements.txt         # Python dependencies
├── setup_env.sh             # One-time venv setup
├── run_validation.sh        # Test runner script
├── README.md                # This file
├── library/                 # Test automation library
│   ├── __init__.py
│   ├── functions/           # Verification functions
│   │   ├── __init__.py
│   │   ├── omnia_main_func.py
│   │   └── validation_func.py
│   ├── vars/                # Constants and commands
│   │   ├── __init__.py
│   │   └── common_vars.py
│   └── messages/            # Test messages
│       ├── __init__.py
│       └── omnia_main_msgs.py
├── fvt/                     # Functional Verification Tests
│   ├── README.md            # FVT test case registry + deploy/verify docs
│   ├── setup/               # omnia.sh --setup-venv tests
│   │   ├── test_deploy_setup.py       # @deploy: run --setup-venv --deps-only
│   │   ├── environment/               # verify: env file, variables, source validation
│   │   ├── venv/                      # verify: Python venv, ansible, pip, Galaxy
│   │   └── directories/               # verify: base directories, activate helper
│   ├── init/                # omnia.sh --init tests
│   │   ├── test_deploy_init.py        # @deploy: run --init
│   │   └── domain_init/              # verify: domain log dirs, input staging
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
│   └── execution/           # Actual omnia.sh operations (full lifecycle)
│       ├── test_deploy_execution.py   # @deploy: setup, init, run; @cleanup: teardown
│       └── setup_exec/               # verify: venv, env, log dirs, input files
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
| `setup` | `omnia.sh --setup-venv --deps-only` | Env files, venv, ansible, dirs, pip packages, Galaxy collections |
| `init` | `omnia.sh --init` | Domain log dirs, input file staging (7 domains) |
| `cli` | `omnia.sh --help` (entry point) | Help output, flag parsing, error handling, tags, --prepare-base |
| `omnia_cli` | `omnia-cli help` | Status, check, version, domain queries, logs, errors |
| `execution` | `--setup-venv --deps-only`, `--init`, `--run --tags precheck/validate` (cleanup via explicit cmd) | Venv+ansible exist, env files installed, log dirs created, input files staged |
| `nft` | `--setup-venv`, `--init`, `omnia-cli status` | Performance thresholds, idempotency, file permissions |

## Markers

| Marker | Description |
|--------|-------------|
| `sanity` | Baseline must-pass tests |
| `functional` | Functional verification tests |
| `deploy` | Script execution tests (setup, init, run — **change state**) |
| `cleanup` | Teardown tests (run after verify — **may destroy state**) |
| `nft` | Non-functional tests (performance, idempotency, permissions) |

### Filtering by Marker

```bash
# Run only sanity tests across all scenarios
./run_validation.sh all verify --marker sanity

# Run only sanity tests for a specific scenario
./run_validation.sh setup verify --marker sanity
./run_validation.sh cli verify --marker sanity

# Run only NFT-marked tests
./run_validation.sh nft verify --marker nft

# Combine markers with AND (all must match)
./run_validation.sh setup verify --marker "sanity+functional"

# Combine markers with OR (any must match)
./run_validation.sh setup verify --marker "sanity,functional"
```

## Configuration

Edit `test_config.yml` to set:
- **`oim_server_ip`**: Target server IP (empty = local mode)
- **`clone_path`**: Path to omnia repo on target
- **`omnia_data_path`**: Runtime data path on target
- **`venv_path`**: Python venv path on target

## Dependencies

- Python 3.12+
- `omnia_auto` wheel (from `test/plugins/dist/`)
- pytest, pytest-testinfra, pytest-order
