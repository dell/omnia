# precheck_environment

Validate environment prerequisites before running any utils playbook.

This role runs **after** `utils_setup` (which has `tags: always`), so all
env var facts are already loaded and validated as non-empty.

## Separation of concerns

| Concern | Who handles it | How |
|---------|---------------|-----|
| Env vars SET (non-empty) | `utils_setup` | Environment loading |
| Env vars match system | `precheck_environment` (this role) | `validate_system_environment` module |
| omnia.sh setup | `precheck_environment` (this role) | `stat /etc/omnia/omnia.env` |

## What it checks

| Check | Method | Severity | Description |
|-------|--------|----------|-------------|
| omnia.sh setup | `stat /etc/omnia/omnia.env` | Warning | Verifies `omnia.sh --setup-venv` was run |
| Hostname | `validate_system_environment` (`hostname -s`) | Fail | Short hostname matches SYSTEM_HOSTNAME |
| Domain | `validate_system_environment` (`hostname -d`) | Warning | Domain matches SYSTEM_DOMAIN_NAME |
| Admin IP | `validate_system_environment` (`ip -4 addr`) | Fail | SYSTEM_ADMIN_NIC_IPV4 is assigned to a local NIC |
| Data path | `validate_system_environment` (`stat`) | Fail | OMNIA_DATA_PATH directory exists |

## Usage

```bash
cd src/utils/playbooks
ansible-playbook utils.yml --tags precheck
```

## Alignment

The same validations are performed at three levels:

| Level | Tool | Checks |
|-------|------|--------|
| Shell | `omnia.sh validate_env()` | hostname -s, hostname -d, hostname -I |
| Ansible module | `validate_system_environment.py` | env vars, hostname -s, hostname -d, IP on NIC, data path |
| FVT tests | `check_hostname_domain()`, `check_admin_ip()` | hostname -s, hostname -d, hostname -I |

## Dependencies

None.

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
