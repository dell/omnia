# Full Consumer Example

This shows a complete working `conftest.py` that uses all the major
features of `omnia-auto`.  Copy and adapt this for your own module.

## Directory structure

```
your-module/
├── test/
│   ├── conftest.py               # <-- this file
│   ├── test_config.yml           # your config
│   ├── test_creds.yml            # your credentials (auto-encrypted)
│   ├── .test_creds.key           # vault key (auto-generated)
│   ├── datasets/
│   │   └── data_set_01/
│   │       └── input/            # input files synced to target
│   ├── library/
│   │   ├── __init__.py
│   │   ├── functions/
│   │   │   ├── __init__.py       # re-exports + run_playbook wrapper
│   │   │   └── my_func.py        # your verification functions
│   │   ├── vars/
│   │   │   ├── __init__.py
│   │   │   ├── common_vars.py    # your constants
│   │   │   └── test_case_vars.py # centralized IDs and titles
│   │   └── messages/
│   │       ├── __init__.py
│   │       └── my_msgs.py        # your test/log messages
│   └── fvt/
│       └── my_scenario/
│           └── test_my_feature.py
```

## `test_config.yml`

```yaml
oim_server_ip: "10.20.0.100"
oim_ssh_user: "root"
clone_url: "https://github.com/dell/omnia.git"
clone_path: "/root/omnia"
dataset: "data_set_01"
report_path: "/opt/omnia/reports"
report_name: "my_test_report"
```

## `test_creds.yml`

```yaml
oim_password: "my_ssh_password"
```

## `library/vars/common_vars.py`

```python
# Your module-specific constants
PLAYBOOK_ENTRY_POINT = "image_build_manager.yml"
PLAYBOOK_WORKDIR = "src/image_build_manager/playbooks"
DOMAIN_NAME = "image_build_manager"
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"
```

## `library/vars/test_case_vars.py`

```python
TEST_CASES = {
    "deploy_prepare": {
        "id": "IBM_FVT_PREPARE_E001",
        "title": "Run Image Build Manager prepare",
    },
    "containers_running": {
        "id": "IBM_FVT_PREPARE_V001",
        "title": "Verify prepare containers are running",
    },
}
```

## `library/functions/__init__.py`

```python
# Re-export omnia_auto functions you use
from omnia_auto import (
    TestLogger,
    log,
    get_testinfra_host,
    load_test_config,
    run_on_host,
    connection_params,
    read_remote_env,
    ensure_remote_dir,
    resolve_domain_input_path,
    sync_files,
)

# Wrap run_playbook so tests don't need to pass playbook args
from omnia_auto import run_playbook as _run_playbook
from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

def run_playbook(tag=None, **kwargs):
    """Run the module's playbook with a specific tag."""
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag,
        **kwargs,
    )
```

## `conftest.py`

```python
import sys
import os
import pytest

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

# ── 1. Configure omnia-auto ─────────────────────────────────────────
import omnia_auto

omnia_auto.configure(
    module_root=_TEST_DIR,
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
    env_file="/etc/omnia/omnia.env",
    default_timeout=3600,
)

# ── 2. Import what you need ─────────────────────────────────────────
from omnia_auto import (
    get_testinfra_host,
    load_test_config,
    encrypt_test_credentials,
    connection_params,
    resolve_domain_input_path,
    ensure_remote_dir,
    sync_files,
    clone_repo,
    log,
    get_test_output,
    get_last_tc_id,
    add_session_result,
    print_summary_table,
    TestReport,
    set_current_report,
    get_current_report,
)

# ── 3. Your module's constants ──────────────────────────────────────
from library.vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
)


# ── 4. Session setup ────────────────────────────────────────────────
def pytest_sessionstart(session):
    # Encrypt credentials
    encrypt_test_credentials()

    config = load_test_config()
    host = get_testinfra_host()
    conn = connection_params()

    # Clone/pull repo on target
    result = clone_repo(
        mode=conn["mode"],
        url=config["clone_url"],
        dest=config.get("clone_path", "/root/omnia"),
        ip=conn["ip"],
        user=conn["user"],
        password=conn["password"],
        ssh_opts=conn["ssh_opts"],
    )
    assert result["success"], result["error"]
    log(result["details"], "OK")

    # Resolve remote input path from env vars on target
    remote_input = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    ensure_remote_dir(host, remote_input)

    # Sync dataset input files to target
    local_input = os.path.join(
        _TEST_DIR, "datasets", config["dataset"], "input",
    )
    result = sync_files(
        mode=conn["mode"],
        src=local_input,
        dest=remote_input,
        ip=conn["ip"],
        user=conn["user"],
        password=conn["password"],
        ssh_opts=conn["ssh_opts"],
    )
    assert result["success"], result["error"]
    log(result["details"], "OK")

    # Create test report
    report = TestReport(
        module_name="build",
        report_path=config.get("report_path", "/opt/omnia/reports"),
        report_name=config.get("report_name", "test_report"),
        server_ip=config.get("oim_server_ip", "localhost"),
    )
    set_current_report(report)


# ── 5. Collect test results ─────────────────────────────────────────
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()

    if result.when == "call":
        status = "PASSED" if result.passed else (
            "SKIPPED" if result.skipped else "FAILED"
        )
        tc_id = get_last_tc_id()

        # Add to HTML/JSON report
        report = get_current_report()
        if report:
            report.add_result({
                "test_name": item.name,
                "tc_id": tc_id,
                "status": status,
                "duration": getattr(result, "duration", 0),
                "details": get_test_output(),
                "error": str(result.longrepr) if result.failed else "",
            })

        # Add to session summary table
        add_session_result(
            test_name=item.name,
            status=status,
            duration=getattr(result, "duration", 0),
            tc_id=tc_id,
        )


# ── 6. Session teardown ─────────────────────────────────────────────
def pytest_sessionfinish(session, exitstatus):
    report = get_current_report()
    if report and report.results:
        report.save()
    print_summary_table()


# ── 7. Shared fixtures ──────────────────────────────────────────────
@pytest.fixture(scope="session")
def host():
    """Testinfra host object — available to all tests."""
    return get_testinfra_host()
```

## `fvt/my_scenario/test_my_feature.py`

```python
import pytest
from library.functions import run_playbook, TestLogger
from library.vars.test_case_vars import TEST_CASES as TC

@pytest.mark.sanity
def test_prepare_phase():
    """Verify the prepare phase completes."""
    tc = TC["deploy_prepare"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Running prepare tag...")
    result = run_playbook(tag="prepare", timeout=1800)

    if result["success"]:
        tl.passed(f"Prepare completed in {result['duration']:.1f}s")
    else:
        tl.failed(f"Prepare failed (rc={result['rc']})", result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
def test_containers_running(host):
    """Verify the expected containers are running."""
    tc = TC["containers_running"]
    tl = TestLogger(tc["title"], tc["id"])

    expected = ["minio-server", "registry"]
    result = host.run("podman ps --format '{{.Names}}'")
    running = result.stdout.strip().split("\n")

    missing = [c for c in expected if c not in running]
    if not missing:
        tl.passed(f"All {len(expected)} containers running")
    else:
        tl.failed(f"Missing containers: {missing}")

    assert not missing, f"Missing containers: {missing}"
```

---

## What you get when you run this

```bash
cd test/
source .venv/bin/activate
python3 -m pytest fvt/ -s -m sanity
```

```
[14:30:00] [OK] Cloned https://... -> /root/omnia
[14:30:01] [INFO] Resolved remote input path: /opt/omnia/image_build_manager/input/project_default
[14:30:02] [OK] Synced .../input -> root@10.20.0.100:/opt/omnia/.../project_default

┌────────────────────────────────────────────────────────────────────┐
│  SERVER:      10.20.0.100                                          │
│  MODULE:      build                                                │
│  REPORT ID:   20260730143000                                       │
└────────────────────────────────────────────────────────────────────┘

  ▶ [IBM_FVT_PREPARE_E001] Run Image Build Manager prepare
  → Running prepare tag...
  ✔ PASS: Prepare completed in 45.2s

  ▶ [IBM_FVT_PREPARE_V001] Verify prepare containers are running
  ✔ PASS: All 2 containers running

┌────────────────────────────────────────────────────────────────────┐
│  REPORT SAVED                                                     │
├────────────────────────────────────────────────────────────────────┤
│  Results:       2 passed, 0 failed, 0 skipped                      │
│  JSON: /opt/omnia/reports/test_report.json                          │
│  HTML: /opt/omnia/reports/test_report.html                          │
└────────────────────────────────────────────────────────────────────┘

========================================================================================
  TEST EXECUTION SUMMARY
========================================================================================
  TC ID                     Test Name                                Status     Duration
  ------------------------- ---------------------------------------- ---------- --------
  IBM_FVT_PREPARE_E001    test_prepare_phase                       PASSED       45.20s
  IBM_FVT_PREPARE_V001  test_containers_running                  PASSED        0.42s
  ------------------------- ---------------------------------------- ---------- --------
  2 passed, 0 failed, 0 skipped / 2 total (45.62s)
========================================================================================
```
