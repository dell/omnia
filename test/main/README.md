# Omnia Main — Functional Verification Tests (FVT)

Automated FVT for `omnia.sh` and `omnia-cli` — verifies environment setup,
domain initialization, and CLI argument handling.

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
└── fvt/                     # Test scenarios
    ├── TEST_CASES.md        # Test case registry
    ├── setup/               # omnia.sh --setup-venv tests
    │   ├── test_deploy_setup.py
    │   ├── environment/     # Env file and variable tests
    │   ├── venv/            # Python venv tests
    │   └── directories/     # Base directory tests
    ├── init/                # omnia.sh --init tests
    │   ├── test_deploy_init.py
    │   └── domain_init/     # Domain-specific init tests
    ├── cli/                 # CLI argument tests
    │   ├── test_deploy_cli.py
    │   └── commands/        # Command error handling tests
    └── omnia_cli/           # omnia-cli diagnostics tests
        ├── test_deploy_omnia_cli.py
        ├── diagnostics/     # status, check, domain commands
        └── errors/          # Unknown command error tests
```

## Scenarios

| Scenario | What It Tests | Deploy Command |
|----------|--------------|----------------|
| `setup` | Environment install, venv creation, directory setup | `omnia.sh --setup-venv --skip-init` |
| `init` | Domain log directories, input file staging | `omnia.sh --init` |
| `cli` | Help output, error handling, argument parsing | `omnia.sh --help` |
| `omnia_cli` | Diagnostics CLI: status, check, version, domain queries | `omnia-cli help` |

## Markers

| Marker | Description |
|--------|-------------|
| `sanity` | Baseline must-pass tests |
| `functional` | Functional verification tests |
| `deploy` | Script execution tests |

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
