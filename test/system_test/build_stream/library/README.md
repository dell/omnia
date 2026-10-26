# library

Reusable code for the e2e test cases. Test files only select, order and
report; everything else lives here.

| Package | Contents |
|---|---|
| `functions/` | Behavior, one module per concern (see below). Public API re-exported from `functions/__init__.py`. |
| `vars/common_vars.py` | Constants, order bands, `CMDS` shell templates (every value shell-quoted by `run_cmd`) and `SQL` templates (identifiers validated first). |
| `vars/test_case_vars.py` | Test-case registry: function name -> TC ID and title. |
| `vars/domain_vars.py` | Validation-runner configuration (tags, suites, markers, default lifecycle). |
| `messages/system_test_msgs.py` | `TEST_LOG_MSGS`, `TEST_ASSERT_MSGS` (with HOW TO FIX steps) and `PROGRESS_MSGS` (live progress lines of long-running functions). |

| Module | Responsibility |
|---|---|
| `precheck_func.py` | One precheck per scenario (first exec test). |
| `config_func.py` | Validate `test_config.yml`; installation, pipeline and cleanup settings. |
| `command_func.py` | Streamed `omnia.sh`, playbook and domain-cleanup execution (no timeout). |
| `catalog_func.py` | Catalog selection by number or path and installation. |
| `readiness_func.py` | prepare_base verification: what each base domain's prepare leaves running. |
| `installation_func.py` | `build_stream.yml` run, installation verification (services, GitLab repository) and pipeline flows. |
| `pipeline_func.py`, `gitlab_func.py`, `api_func.py` | GitLab and BuildStream API access, stage monitoring, job verification. |
| `cadence_func.py` | Cadence trigger and playbook-watcher journal monitoring. |
| `auto_cleanup_func.py` | Retention settings, eligibility (cleanup_cron.py rules), one cleanup pass, finalization wait, verification. |
| `cleanup_func.py` | Ordered domain cleanup (exec) and per-domain verification. |
| `*_cleanup_func.py` | Per-domain cleanup pre-checks and postcondition verification. |
| `state_func.py` | Exec -> verify hand-off file for auto_cleanup and cleanup (`reports/state/`). |
| `db_func.py`, `probe_func.py` | `build_stream_db` queries and OIM state probes. |
