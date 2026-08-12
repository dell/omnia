# precheck_environment

Validate environment prerequisites before running any image_build_manager playbook.

This role runs **after** `image_build_setup` (which has `tags: always`), so all
env var facts (`admin_nic_ip`, `host_name`, `domain_name`, etc.) are already
loaded and validated as non-empty.

## Separation of concerns

| Concern | Who handles it | How |
|---------|---------------|-----|
| Env vars SET (non-empty) | `image_build_setup/load_config.yml` | `validate_system_environment` module with `validate_hostname/ip/domain=false` |
| Env vars match system | `precheck_environment` (this role) | `validate_system_environment` module with `validate_hostname/ip/domain=true` |
| omnia.sh setup | `precheck_environment` (this role) | `stat /etc/omnia/omnia.env` |
| repo_status.yml exists | `precheck_environment` (this role) | `stat` |
| Directories created | `image_build_setup/load_config.yml` | `file: state=directory` |

**No duplication.** Both roles use the `validate_system_environment` Python
module but with different parameters — `load_config.yml` only checks env vars
are SET; this role checks they MATCH the actual system.

## What it checks

| Check | Method | Severity | Description |
|-------|--------|----------|-------------|
| omnia.sh setup | `stat /etc/omnia/omnia.env` | Warning | Verifies `omnia.sh --setup-venv` was run |
| Hostname | `validate_system_environment` (`hostname -s`) | Fail | Short hostname matches SYSTEM_HOSTNAME |
| Domain | `validate_system_environment` (`hostname -d`) | Warning | Domain matches SYSTEM_DOMAIN_NAME |
| Admin IP | `validate_system_environment` (`ip -4 addr`) | Fail | SYSTEM_ADMIN_NIC_IPV4 is assigned to a local NIC |
| Data path | `validate_system_environment` (`stat`) | Fail | OMNIA_DATA_PATH directory exists |
| repo_status.yml | `stat` | Warning | repo_manager output exists |

## Usage

```bash
cd src/image_build_manager/playbooks
ansible-playbook image_build_manager.yml --tags precheck
```

## Alignment

The same validations are performed at three levels:

| Level | Tool | Checks |
|-------|------|--------|
| Shell | `omnia.sh validate_env()` | hostname -s, hostname -d, hostname -I |
| Ansible module | `validate_system_environment.py` | env vars, hostname -s, hostname -d, IP on NIC, data path |
| FVT tests | `check_hostname_domain()`, `check_admin_ip()` | hostname -s, hostname -d, hostname -I |
