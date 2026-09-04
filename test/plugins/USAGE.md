# omnia-auto — Usage Guide

Complete function reference for the `omnia-auto` package.

Each category has a **detailed guide** in the [`docs/`](docs/) folder with
full explanations, prerequisites, every parameter described, and examples.

---

## Quick Reference

| Category | Source File | Functions | Detailed Guide |
|----------|-----------|-----------|---------------|
| Configuration | `vars/common_vars.py` | `configure`, `get_setting`, `init_module_root`, `get_module_root` | [docs/01_configuration.md](docs/01_configuration.md) |
| Formatting | `functions/formatting_func.py` | `Colors`, `Symbols`, `TestLogger`, `log`, `set_debug_mode`, `add_session_result`, `print_summary_table` | [docs/02_formatting.md](docs/02_formatting.md) |
| Host & Config | `functions/host_func.py` | `load_test_config`, `load_test_credentials`, `encrypt_test_credentials`, `get_testinfra_host`, `is_local_execution`, `run_on_host`, `run_ssh_command`, `connection_params`, `read_remote_env`, `ensure_remote_dir`, `resolve_domain_input_path` | [docs/03_host_and_config.md](docs/03_host_and_config.md) |
| Sync | `functions/sync_func.py` | `clone_repo`, `sync_files` | [docs/04_sync.md](docs/04_sync.md) |
| Runner | `functions/runner_func.py` | `run_playbook` | [docs/05_runner.md](docs/05_runner.md) |
| Report | `functions/report_func.py` | `TestReport`, `get_current_report`, `set_current_report` | [docs/06_report.md](docs/06_report.md) |

**Full working example** (conftest.py + test file + output): [docs/07_full_example.md](docs/07_full_example.md)

---

## Getting Started

### Step 1 — Install

```bash
pip install omnia_auto-1.0.0-py3-none-any.whl
```

### Step 2 — Configure in your `conftest.py`

```python
import os
import omnia_auto

omnia_auto.configure(
    module_root=os.path.dirname(os.path.abspath(__file__)),
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
    default_timeout=3600,
)
```

### Step 3 — Use any function

```python
from omnia_auto import (
    TestLogger, load_test_config, get_testinfra_host,
    connection_params, sync_files, run_playbook,
    TestReport, set_current_report,
)
```

For a complete working example, see [docs/07_full_example.md](docs/07_full_example.md).

---

## Error Handling Summary

| Function | Error Type | When |
|----------|-----------|------|
| `get_module_root()` | `RuntimeError` | `module_root` never configured |
| `load_test_config()` | `RuntimeError` | `config_file` not configured |
| `load_test_credentials()` | `ValueError` | Encrypted file exists but key file missing |
| `connection_params()` | `ValueError` | `oim_server_ip` or `oim_ssh_user` missing for remote mode |
| `read_remote_env()` | `ValueError` | Env var not set or empty on target |
| `ensure_remote_dir()` | `ValueError` / `RuntimeError` | Empty path or `mkdir -p` fails |
| `resolve_domain_input_path()` | `ValueError` | Empty domain or env var not set on target |
| `run_playbook()` | Returns `{"success": False}` | Missing `playbook` or `playbook_workdir`, timeout, non-zero exit |
| `clone_repo()` / `sync_files()` | Returns `{"success": False}` | Invalid mode, missing params, subprocess failure |
