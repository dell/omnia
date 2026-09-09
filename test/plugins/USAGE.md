# omnia-auto — Usage Guide

Quick function reference for the `omnia-auto` package.

Each category has a **detailed guide** in the [`docs/`](docs/) folder with
full explanations, prerequisites, every parameter described, and examples.

---

## Quick Reference

| Category | Source File | Functions | Detailed Guide |
|----------|-----------|-----------|---------------|
| Configuration | `vars/common_vars.py` | `configure`, `configured`, `reset_configuration`, `get_setting`, `init_module_root`, `get_module_root` | [docs/01_configuration.md](docs/01_configuration.md) |
| Formatting | `functions/formatting_func.py` | `Colors`, `Symbols`, `TestLogger`, `log`, `set_debug_mode`, `set_verbose_mode`, output/detail accessors, session result helpers | [docs/02_formatting.md](docs/02_formatting.md) |
| Host & Config | `functions/host_func.py` | `load_test_config`, `load_test_credentials`, `encrypt_test_credentials`, `get_testinfra_host`, `is_local_execution`, `run_on_host`, `run_ssh_command`, `connection_params`, `read_remote_env`, `ensure_remote_dir`, `read_remote_yaml`, `read_yaml_key`, `resolve_domain_data_path`, `resolve_domain_input_path`, `get_inventory_hosts`, `get_inventory_host_var` | [docs/03_host_and_config.md](docs/03_host_and_config.md) |
| Sync | `functions/sync_func.py` | `clone_repo`, `sync_files` | [docs/04_sync.md](docs/04_sync.md) |
| Runner | `functions/runner_func.py` | `run_playbook` | [docs/05_runner.md](docs/05_runner.md) |
| Report | `functions/report_func.py` | `TestReport`, `get_current_report`, `set_current_report` | [docs/06_report.md](docs/06_report.md) |
| Credentials | `functions/credential_func.py` | `ensure_vault_key`, `is_vault_encrypted`, `vault_encrypt`, `vault_decrypt_to_dict`, `read_credential_field`, `read_all_fields`, `write_credential_fields`, `prompt_credential`, `prompt_and_confirm`, `prompt_fields_interactive` | [docs/08_credentials.md](docs/08_credentials.md) |
| Credential paths | `vars/credential_vars.py` | `get_data_path`, `get_project_name`, `get_domain_input_path` | [docs/08_credentials.md](docs/08_credentials.md) |
| Validation | `functions/validation_runner.py` | `ValidationRunner` | [docs/09_validation_runner.md](docs/09_validation_runner.md) |

**Full working example** (conftest.py + test file + output): [docs/07_full_example.md](docs/07_full_example.md)

---

## Getting Started

### Step 1 — Install

```bash
# From the test/plugins directory after ./build_wheel.sh
python -m pip install dist/omnia_auto-1.0.0-py3-none-any.whl
```

After an official package release, use
`python -m pip install omnia-auto`.

The host, sync, runner, and credential helpers also require the applicable
system commands: Git, OpenSSH, rsync, sshpass for password-based SSH, and
Bash. `ansible-core` is a Python dependency and provides `ansible-playbook`
and `ansible-vault`.

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
| `load_test_config()` | `RuntimeError` | Neither an explicit path nor `config_file` is available |
| `load_test_config()` | `OSError` / `yaml.YAMLError` | The configured file cannot be read or contains invalid YAML |
| `load_test_config()` | `ValueError` | The YAML root is not a mapping |
| `load_test_credentials()` | `ValueError` | Vault/key/YAML validation or encryption fails |
| `connection_params()` | `ValueError` | `oim_server_ip` or `oim_ssh_user` is missing for remote mode |
| `read_remote_env()` | `ValueError` | Env var not set or empty on target |
| `ensure_remote_dir()` | `ValueError` / `RuntimeError` | Empty path or `mkdir -p` fails |
| `read_remote_yaml()` | `RuntimeError` | The target file cannot be read |
| `read_remote_yaml()` | `ValueError` | YAML is malformed or its root is not a mapping |
| `resolve_domain_data_path()` | `ValueError` | Unsafe domain/path or required fallback env var not set |
| `resolve_domain_input_path()` | `ValueError` | Unsafe domain/path or required project/fallback env var not set |
| `run_playbook()` | Returns `{"success": False}` | Missing `playbook` or `playbook_workdir`, timeout, non-zero exit |
| `clone_repo()` / `sync_files()` | Returns `{"success": False}` | Invalid mode, missing params, subprocess failure |
