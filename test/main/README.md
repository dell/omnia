# Omnia Main — Test Automation (FVT + NFT)

Automated FVT and NFT for `omnia.sh` and `omnia-cli` — verifies environment
setup, domain initialization, CLI argument handling, performance, idempotency,
and file permissions.

## Quick Start

```bash
# 1. Setup test environment
bash setup_env.sh

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Configure target server
vi test_config.yml

# 4. Run tests
run_validation setup test        # Setup + verify
run_validation init test         # Init + verify
run_validation cli verify        # CLI argument tests
run_validation omnia_cli test    # omnia-cli diagnostics
run_validation nft test          # Performance + idempotency NFT
run_validation all test          # Run all scenarios
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
│   ├── README.md            # FVT test case registry
│   ├── setup/               # omnia.sh --setup-venv tests
│   │   ├── test_deploy_setup.py
│   │   ├── environment/     # Env file, variable, and source validation tests
│   │   ├── venv/            # Python venv tests
│   │   └── directories/     # Base directory tests
│   ├── init/                # omnia.sh --init tests
│   │   ├── test_deploy_init.py
│   │   └── domain_init/     # Domain-specific init tests (incl. orchestrator, discovery)
│   ├── cli/                 # CLI argument tests
│   │   ├── test_deploy_cli.py
│   │   ├── commands/        # Command error handling + flag verification + skip-catalog
│   │   └── tags/            # Tag verification tests (precheck, validate, prepare, execute, cleanup)
│   └── omnia_cli/           # omnia-cli diagnostics tests
│       ├── test_deploy_omnia_cli.py
│       ├── diagnostics/     # status, check, domain commands (incl. orchestrator, telemetry, build-stream)
│       ├── errors/          # Unknown command error tests
│       └── logs/            # Log command tests
└── nft/                     # Non-Functional Tests
    ├── README.md            # NFT test cases and thresholds
    ├── __init__.py
    ├── test_performance.py      # Performance threshold tests (setup, init, check-deps)
    ├── test_idempotency.py      # Idempotency tests (setup, init)
    ├── test_permissions.py      # File permission tests (env, omnia.sh, omnia-cli, domain-init)
    └── test_cli_performance.py  # CLI performance tests (status, help)
```

## Scenarios

| Scenario | What It Tests | Deploy Command |
|----------|--------------|----------------|
| `setup` | Environment install, venv creation, directory setup, env source validation | `omnia.sh --setup-venv --deps-only` |
| `init` | Domain log directories, input file staging (all 7 domains incl. orchestrator, discovery, utils) | `omnia.sh --init` |
| `cli` | Help output, error handling, flag verification (--cleanup, --check-deps, --force-deps, --skip-catalog), generic tags, argument parsing | `omnia.sh --help` |
| `omnia_cli` | Diagnostics CLI: status, check, version, domain queries (all 7 domains incl. orchestrator, telemetry, build-stream, utils), logs, errors | `omnia-cli help` |
| `nft` | Performance thresholds, idempotency, file permissions, CLI performance | `omnia.sh --setup-venv`, `--init`, `omnia-cli status` |

## Markers

| Marker | Description |
|--------|-------------|
| `sanity` | Baseline must-pass tests |
| `functional` | Functional verification tests |
| `deploy` | Script execution tests |
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
