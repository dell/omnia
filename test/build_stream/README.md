# Build Stream — Test Automation Module

Automated FVT (Functional Verification Tests) for the Omnia 2.3
build_stream domain, covering BuildStream installation, GitLab setup,
build pipeline execution, and end-to-end verification.

## Structure

```
test/build_stream/
├── conftest.py                     # Session setup, omnia_auto.configure()
├── test_config.yml                 # Non-sensitive settings (IP, catalog, paths)
├── test_creds.yml                  # SSH credentials (auto-encrypted)
├── requirements.txt                # Dependencies
├── run_validation.sh               # CLI runner
├── setup_env.sh                    # One-time venv setup + credential utility
├── datasets/
│   └── generator/                  # Dataset generator
├── library/
│   ├── functions/
│   │   ├── __init__.py             # Public API
│   │   ├── build_stream_func.py    # BSM health verification
│   │   ├── gitlab_func.py          # GitLab verification
│   │   ├── pipeline_func.py        # Pipeline trigger & monitoring
│   │   ├── host_func.py            # Sync functions
│   │   └── validation_func.py      # Config validation
│   ├── vars/
│   │   ├── common_vars.py          # Constants, CMDS dict
│   │   └── test_case_vars.py       # TEST_CASES dict
│   └── messages/
│       └── build_stream_msgs.py    # LOG and ASSERT messages
└── fvt/
    ├── README.md                   # Test case documentation
    ├── buildstream_install/        # Scenario: BuildStream installation
    │   ├── test_playbook.py        # Deploy playbook
    │   └── buildstream_install/    # Suite: install verification
    │       └── test_buildstream_install.py
    ├── buildstream_cleanup/        # Scenario: BuildStream cleanup
    │   └── test_playbook.py        # Deploy cleanup playbook
    ├── gitlab_cleanup/             # Scenario: GitLab cleanup
    │   └── test_playbook.py        # Deploy GitLab cleanup playbook
    └── build_pipeline/             # Scenario: Build pipeline
        ├── test_playbook.py        # Deploy: push catalog, trigger pipeline
        └── build_pipeline/         # Suite: pipeline verification
            └── test_build_pipeline.py
```

## Quick Start

### 1. Environment Setup

```bash
cd /root/test/omnia/test/build_stream

# Create virtual environment and install dependencies
bash setup_env.sh

# Activate virtual environment
source .venv/bin/activate
```

### 2. Configure Test Settings

```bash
# Edit test configuration
vi test_config.yml

# Required settings:
#   oim_server_ip: ""                    # Leave empty for local mode
#   catalog_name: "catalog_rhel.json"    # For build_pipeline tests
```

### 3. Set Domain Credentials (First-time only)

```bash
# Interactive credential setup
bash setup_env.sh --set-domain-creds

# Or provide credentials via JSON
bash setup_env.sh --domain-creds '{
  "gitlab_root_password": "your_password",
  "gitlab_ssh_password": "your_password",
  "build_stream_auth_username": "admin",
  "build_stream_auth_password": "your_password",
  "postgres_user": "postgres",
  "postgres_password": "your_password"
}'
```

## Test Scenarios

### BuildStream Installation

**Deploy (--test):** Runs `build_stream.yml` playbook with `-e standalone_mode=true`

```bash
# Deploy BuildStream (Postgres, GitLab, BSM)
./run_validation.sh fvt_build_stream buildstream_install test --marker sanity
```

**Verify (--verify):** Checks installation without running playbook

```bash
# Verify BuildStream installation
./run_validation.sh fvt_build_stream buildstream_install verify --marker sanity
```

### Build Pipeline

**Deploy (--test):** Pushes catalog to GitLab, triggers pipeline, monitors stages

```bash
# Prerequisites:
#   1. buildstream_install completed successfully
#   2. catalog_name set in test_config.yml

# Push catalog, trigger pipeline, monitor GitLab CI + BSM stages
./run_validation.sh fvt_build_stream build_pipeline test --marker sanity
```

**Verify (--verify):** Verifies pipeline results without triggering new pipeline

```bash
# Verify existing pipeline results (uses job_id from test_config.yml)
./run_validation.sh fvt_build_stream build_pipeline verify --marker sanity
```

### BuildStream Cleanup

**Deploy (--test):** Runs `cleanup/cleanup_build_stream.yml` playbook

```bash
# Clean up BuildStream domain (containers, services, directories, credentials)
./run_validation.sh fvt_build_stream buildstream_cleanup test --marker sanity
```

### GitLab Cleanup

**Deploy (--test):** Runs `cleanup/cleanup_gitlab.yml` playbook

```bash
# Clean up GitLab from target host
./run_validation.sh fvt_build_stream gitlab_cleanup test --marker sanity
```

## Test Coverage

| Scenario | Test Cases | Description |
|----------|------------|-------------|
| **buildstream_install** | 1 TC | BuildStream playbook deployment + verification |
| **build_pipeline** | 11 TCs | Catalog push, pipeline trigger, stage monitoring, artifact verification |
| **buildstream_cleanup** | 1 TC | BuildStream domain cleanup |
| **gitlab_cleanup** | 1 TC | GitLab removal |

See `fvt/README.md` for the full test case list.

## Common Workflows

### Full End-to-End Test

```bash
# 1. Install BuildStream
./run_validation.sh fvt_build_stream buildstream_install test --marker sanity

# 2. Run build pipeline
./run_validation.sh fvt_build_stream build_pipeline test --marker sanity

# 3. Verify pipeline results
./run_validation.sh fvt_build_stream build_pipeline verify --marker sanity

# 4. Clean up
./run_validation.sh fvt_build_stream buildstream_cleanup test --marker sanity
```

### Re-verify Without Re-deploying

```bash
# Verify BuildStream installation (no playbook execution)
./run_validation.sh fvt_build_stream buildstream_install verify --marker sanity

# Verify pipeline results (uses existing job_id from test_config.yml)
./run_validation.sh fvt_build_stream build_pipeline verify --marker sanity
```

### Troubleshooting

```bash
# Check test configuration
cat test_config.yml

# Check credentials (encrypted)
cat test_creds.yml

# View latest test report
cat /opt/omnia/reports/build_stream_test_report.json

# Re-run with verbose output
./run_validation.sh fvt_build_stream buildstream_install test --marker sanity -v
```

## Test Modes

| Flag | Mode | Description |
|------|------|-------------|
| `test` | Deploy + Verify | Runs playbook (or triggers pipeline) then verifies results |
| `verify` | Verify Only | Skips deployment, only runs verification tests |

## Markers

| Marker | Description |
|--------|-------------|
| `@sanity` | Core functionality tests (recommended for CI/CD) |
| `@deploy` | Playbook deployment tests (excluded in verify mode) |

## Configuration Files

### test_config.yml

Non-sensitive settings:

```yaml
oim_server_ip: ""                          # Leave empty for local mode
catalog_name: "catalog_rhel.json"          # Catalog for build_pipeline
allow_pipeline_cancel: false               # Auto-cancel running pipelines
report_path: /opt/omnia/reports            # Test report directory
```

### test_creds.yml (auto-generated)

Encrypted credentials (created by `setup_env.sh --set-domain-creds`):

```yaml
oim_ssh_password: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  ...
```

## Reports

Test reports are saved to `/opt/omnia/reports/`:

- `build_stream_test_report.json` — JSON format
- `build_stream_test_report.html` — HTML format (human-readable)

## Advanced Usage

### Run Specific Test Suite

```bash
# Run only buildstream_install verification tests
./run_validation.sh fvt_build_stream buildstream_install verify --marker sanity

# Run only build_pipeline verification tests
./run_validation.sh fvt_build_stream build_pipeline verify --marker sanity
```

### Remote Execution

Set `oim_server_ip` in `test_config.yml` to run tests against a remote server:

```yaml
oim_server_ip: "10.0.0.100"
oim_ssh_user: root
oim_ssh_port: 22
```

Then set SSH password:

```bash
bash setup_env.sh --set-ssh-creds
```

### Custom Catalog

Place your catalog in `src/main/samples/` and update `test_config.yml`:

```yaml
catalog_name: "my_custom_catalog.json"
```

## Dependencies

- Python 3.8+
- Ansible 2.15+
- pytest 7.0+
- testinfra 9.0+
- omnia_auto (test framework)

All dependencies are installed automatically by `setup_env.sh`.

## Support

For issues or questions:
- Check `fvt/README.md` for detailed test case documentation
- Review test logs in `/opt/omnia/reports/`
- Verify credentials with `bash setup_env.sh --set-domain-creds`
