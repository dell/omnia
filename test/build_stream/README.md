# Build Stream — Test Automation Module

Automated FVT (Functional Verification Tests) for the Omnia 2.3
build_stream domain, covering GitLab installation, BuildStream
service health, and infrastructure verification.

## Structure

```
test/build_stream/
├── conftest.py                     # Session setup, omnia_auto.configure()
├── test_config.yml                 # Non-sensitive settings (IP, paths)
├── test_creds.yml                  # SSH credentials (auto-encrypted)
├── requirements.txt                # Dependencies
├── run_validation.sh               # CLI runner
├── setup_env.sh                    # One-time venv setup
├── datasets/
│   └── generator/                  # Dataset generator
├── library/
│   ├── functions/
│   │   ├── __init__.py             # Public API
│   │   ├── build_stream_func.py    # BSM health verification
│   │   ├── gitlab_func.py          # GitLab verification
│   │   ├── host_func.py            # Sync functions
│   │   └── validation_func.py      # Config validation
│   ├── vars/
│   │   ├── common_vars.py          # Constants, CMDS dict
│   │   └── test_case_vars.py       # TEST_CASES dict
│   └── messages/
│       └── build_stream_msgs.py    # LOG and ASSERT messages
└── fvt/
    ├── README.md                   # Test case documentation
    └── gitlab_install/             # Scenario: GitLab installation
        ├── test_playbook.py        # Deploy playbook
        ├── gitlab_install/         # Suite: install verification
        │   └── test_gitlab_install.py
        └── health/                 # Suite: health verification
            └── test_health.py
```

## Quick Start

```bash
cd test/build_stream/

# 1. Setup environment
bash setup_env.sh
source .venv/bin/activate

# 2. Configure
vi test_config.yml   # Set oim_server_ip

# 3. Run tests
./run_validation.sh gitlab_install verify --marker sanity
./run_validation.sh gitlab_install verify --suite health
```

## Test Coverage

- **Section A**: GitLab Installation & Infrastructure (22 TCs)
- **Section B**: BuildStream Service Health (11 TCs)

See `fvt/README.md` for the full test case list.
