# Report — `TestReport`, `build_report_name()`, `record_playbook_failure()`

**Source file:** `src/omnia_auto/functions/report_func.py`

## What is this?

An enterprise-grade test report generator that produces **JSON** and **HTML**
report files. The HTML report includes:

- Dark/light theme toggle with localStorage persistence
- Overall PASSED/FAILED status banner
- Summary cards (Total, Passed, Failed, Skipped, Pass Rate, Duration)
- CSS conic-gradient donut chart
- Suite breakdown table with progress bars
- Detailed test results with search/filter/collapse by run_id
- Skip classification badges (expected / unexpected / framework)
- Sensitive data redaction (IPs, passwords, secrets, paths)
- Pipeline-aware report naming (date_time_pipelineId_domain_report)
- Multiple test run segregation by run_id (collapsible sections)

The JSON report also includes:
- Playbook execution logs (when playbooks are run from pipeline)
- Playbook failure details (via `record_playbook_failure()`)
- Log issue counts (CRITICAL/WARNING occurrences)

Reports are organized **by server IP** so you can run tests against
multiple servers and all results accumulate in the same report file.

---

## `build_report_name(domain_name, base_name="")`

Build a pipeline-aware report filename.

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `domain_name` | `str` | **Yes** | Domain identifier. | `"repo_manager"` |
| `base_name` | `str` | No | Fallback name for local runs. | `"repo_manager_fvt"` |

**Returns:** Report base filename without extension.

### Naming logic

| Context | Format | Example |
|---------|--------|---------|
| GitLab CI (`CI_PIPELINE_ID` set) | `YYYYMMDD_HHMMSS_<pipeline_id>_<domain>_report` | `20260909_143022_12345_repo_manager_report` |
| Local run (with `base_name`) | `<base_name>` | `repo_manager_fvt` |
| Local run (without `base_name`) | `<domain>_report` | `repo_manager_report` |

Same `pipeline_id` overwrites its report; different pipeline IDs create
separate files.

### Usage in conftest.py

```python
from omnia_auto import build_report_name, TestReport, set_current_report

report_name = build_report_name(
    domain_name="repo_manager",
    base_name=config.get("report_name", "repo_manager_fvt"),
)
report = TestReport(
    module_name=module_name,
    report_path=report_path,
    report_name=report_name,
    server_ip=oim_ip,
    report_id=report_id,
)
set_current_report(report)
```

---

## `TestReport(module_name, report_path, report_name, server_ip, ...)`

### Constructor parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `module_name` | `str` | **Yes** | A name for the scenario or module being tested. This appears as a label in the report. | `"build"` or `"validate"` |
| `report_path` | `str` | **Yes** | Absolute path to the directory where JSON and HTML files will be saved. The directory is created automatically if it doesn't exist. | `"/opt/omnia/reports"` |
| `report_name` | `str` | **Yes** | Base filename for the report (without extension). Two files are created: `<report_name>.json` and `<report_name>.html`. | `"image_test_report"` |
| `server_ip` | `str` | **Yes** | The IP address of the target server. Results in the report are grouped by this IP. | `"10.20.0.100"` |
| `report_id` | `str` | No | A unique identifier for this test run. If not given, an auto-generated timestamp is used (e.g., `"20260730120000"`). Pass a shared `report_id` across multiple modules to group them in the same run. | `"20260730120000"` |
| `server_hostname` | `str` | No | The hostname of the target server. If not given, it is resolved from `server_ip` automatically. | `"image-builder"` |
| `suite` | `str` | No | Suite label shown in the report (informational). Defaults to the `OMNIA_SUITE` environment variable or `"all"`. | `"build"` |
| `marker` | `str` | No | Marker label shown in the report (informational). Defaults to `OMNIA_MARKER` env var. | `"sanity"` |
| `exec_command` | `str` | No | Command label shown in the report (informational). Defaults to `OMNIA_COMMAND_TYPE` env var. | `"test"` |

### Methods

| Method | What it does |
|--------|-------------|
| `report.add_result(...)` | Add a single test result to the report. See below. |
| `report.save() -> str` | Write the JSON and HTML files. Returns the HTML file path. |
| `report.results` | List of all accumulated result dicts (read-only access). |

---

## `report.add_result(...)` — adding test results

There are two ways to add results:

### Way 1: Pass a dict

```python
report.add_result({
    "tc_id": "IMGBM_FVT_BUILD_V006",
    "test_name": "test_s3_images_x86_64",
    "status": "PASSED",           # "PASSED", "FAILED", or "SKIPPED"
    "duration": 1.58,             # seconds (also accepts "duration_seconds")
    "details": "All 2 images found in S3",
    "error": "",                  # empty for passed tests
    "markers": ["sanity"],        # optional — for marker breakdown in report
})
```

### Way 2: Pass keyword arguments

```python
report.add_result(
    tc_id="IMGBM_FVT_BUILD_V006",
    test_name="test_s3_images_x86_64",
    status="PASSED",
    duration=1.58,
    details="All 2 images found in S3",
)
```

### `add_result` parameters (keyword form)

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `tc_id` | `str` | No | Stable test-case ID stored in JSON and shown with the HTML test name. | `"IMGBM_FVT_BUILD_V006"` |
| `test_name` | `str` | **Yes** | Name of the test. | `"test_s3_images_x86_64"` |
| `passed` | `bool` | No | `True` for pass, `False` for fail. Only used if `status` is not given. | `True` |
| `status` | `str` | No | `"PASSED"`, `"FAILED"`, or `"SKIPPED"`. Overrides `passed`. | `"PASSED"` |
| `duration` | `float` | No | Duration in seconds. Default: `0.0`. | `1.58` |
| `details` | `str` | No | Multi-line output from the test (shown in expandable section). | `"PASS: All images found"` |
| `error` | `str` | No | Error message (shown in red box in the report). | `"AssertionError: ..."` |

### Skip classification

When a test is skipped (`status="SKIPPED"`), the report automatically classifies
the skip reason into one of three categories:

| Classification | Meaning | Examples |
|---------------|---------|---------|
| `expected` | Feature not enabled/configured, known skip | "not enabled", "not configured", "requires X" |
| `unexpected` | No clear reason found | Empty skip reason, unrecognized message |
| `framework` | Test infrastructure issue | "fixture error", "import error", "conftest" |

The classification appears as a colored badge next to the SKIP status in the
HTML report.

---

## `report.save() -> str`

Writes two files:
- `<report_path>/<report_name>.json` — structured JSON with all results
- `<report_path>/<report_name>.html` — interactive HTML report

**Returns:** the path to the HTML file.

**Important:** If a report file already exists, new results are **merged** into it.
Multiple runs and multiple modules accumulate in the same report, organized by
server IP and report ID.

### Sensitive data redaction

When generating the HTML report, the following data is automatically redacted:
- **IP addresses** — replaced with `***REDACTED_IP***`
- **Passwords/secrets/keys/tokens** — field values replaced with `***REDACTED***`
- **NFS share paths** — replaced with `***REDACTED***`
- **Hostnames/domain names** — field values replaced with `***REDACTED***`

This ensures no sensitive infrastructure information leaks into shared reports.

### Playbook log analysis

If playbook execution logs are available (via `OMNIA_LOG_FILE` environment
variable), they are included in the report with:
- CRITICAL occurrences highlighted in red
- WARNING occurrences highlighted in amber
- Count badges showing total CRITICAL/WARNING counts per suite

### Terminal output when `save()` is called

```
┌────────────────────────────────────────────────────────────────────┐
│  REPORT SAVED                                                     │
├────────────────────────────────────────────────────────────────────┤
│  Server:        10.20.0.100                                        │
│  Report ID:     20260730120000                                     │
│  Duration:      5.48s                                               │
│  Results:       4 passed, 0 failed, 1 skipped                      │
├────────────────────────────────────────────────────────────────────┤
│  JSON: /opt/omnia/reports/image_test_report.json                    │
│  HTML: /opt/omnia/reports/image_test_report.html                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## `set_current_report(report)` / `get_current_report() -> TestReport`

These are global getter/setter functions.  They let you set a "current"
report object so that hooks like `pytest_runtest_makereport` can access
it without passing it around.

### `set_current_report(report)`

| Parameter | Type | Required? | What to give |
|-----------|------|-----------|--------------|
| `report` | `TestReport` | **Yes** | The report instance to set as active. |

### `get_current_report() -> TestReport or None`

Returns the current active report, or `None` if none was set.

---

## `record_playbook_failure(...)`

Records a playbook/domain execution failure in the test report when the
playbook fails **before** pytest/verify runs. This ensures playbook failures
appear in the report even when no test results exist.

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `module_name` | `str` | **Yes** | Domain name. | `"repo_manager"` |
| `report_path` | `str` | **Yes** | Directory for JSON/HTML output. | `"/opt/omnia/reports"` |
| `report_name` | `str` | **Yes** | Base filename without extension. | `"repo_manager_fvt"` |
| `server_ip` | `str` | **Yes** | Target server IP address. | `"localhost"` |
| `report_id` | `str` | **Yes** | Shared report ID (e.g., CI_PIPELINE_ID). | `"12345"` |
| `log_file` | `str` | No | Path to playbook log file. | `"/tmp/deploy.log"` |
| `command_type` | `str` | No | Command that failed. Default: `"deploy"`. | `"deploy"` |

### Usage in GitLab CI pipeline

```yaml
- |
  if [ "$STAGE_RC" -ne 0 ]; then
    echo "ERROR: repo_manager playbook failed"
    $SSH_CMD $TARGET "
      cd $OMNIA_INSTALL_PATH/test/repo_manager
      source .venv/bin/activate 2>/dev/null || true
      python3 -c '
from omnia_auto.functions.report_func import record_playbook_failure
record_playbook_failure(
    module_name=\"repo_manager\",
    report_path=\"/opt/omnia/reports\",
    report_name=\"repo_manager_fvt\",
    server_ip=\"localhost\",
    report_id=\"${CI_PIPELINE_ID:-manual}\",
    command_type=\"deploy\",
)
'
    "
    exit 1
  fi
```

### Behavior

- Checks if this module already has test results — skips if so
- Creates a `TestReport` with the given parameters
- Reads the log file (if provided) and extracts failure context
- Adds a single FAILED result with playbook failure details
- Saves the JSON and HTML report

---

## Full example in `conftest.py`

```python
import os, pytest
from omnia_auto import (
    TestReport, set_current_report, get_current_report,
    build_report_name, load_test_config, get_test_output,
    get_last_tc_id, add_session_result, print_summary_table,
)

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def pytest_sessionstart(session):
    config = load_test_config()

    # Build pipeline-aware report name
    report_name = build_report_name(
        domain_name="build",
        base_name=config.get("report_name", "image_test_report"),
    )

    # Create the report
    report = TestReport(
        module_name="build",
        report_path=config.get("report_path", "/opt/omnia/reports"),
        report_name=report_name,
        server_ip=config.get("oim_server_ip", "localhost"),
    )
    set_current_report(report)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()

    if result.when == "call":
        tc_id = get_last_tc_id()
        # Determine status
        if result.passed:
            status = "PASSED"
        elif result.skipped:
            status = "SKIPPED"
        else:
            status = "FAILED"

        # Add to report
        report = get_current_report()
        if report:
            report.add_result({
                "tc_id": tc_id,
                "test_name": item.name,
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
        )


def pytest_sessionfinish(session, exitstatus):
    # Save the report
    report = get_current_report()
    if report and report.results:
        report.save()

    # Print summary table
    print_summary_table()
```

---

## Using Playbook Failure Data in Email Notifications

When a pipeline stage fails (e.g., `repo_manager` deploy fails), the failure
details are captured in the JSON report via `record_playbook_failure()`. You can
extract this information for email notifications:

### JSON Report Structure

```json
{
  "servers": {
    "10.20.0.100": {
      "runs": [
        {
          "report_id": "20260909_143022_12345_repo_manager_report",
          "modules": [
            {
              "module": "repo_manager",
              "command_type": "deploy",
              "playbook_logs": "... full playbook output ...",
              "log_issues": {
                "critical": 2,
                "warning": 5
              },
              "results": [
                {
                  "test_name": "playbook_deploy_repo_manager",
                  "status": "FAILED",
                  "details": "... failure context ...",
                  "error": "fatal: [host]: FAILED! => {...}"
                }
              ]
            }
          ]
        }
      ]
    }
  }
}
```

### Email Template Example

```python
import json

with open("/opt/omnia/reports/repo_manager_fvt.json") as f:
    report = json.load(f)

for server_ip, server_data in report["servers"].items():
    for run in server_data["runs"]:
        for module in run["modules"]:
            if module["results"] and module["results"][0]["status"] == "FAILED":
                # Extract failure details
                stage = module["module"]
                command = module.get("command_type", "unknown")
                error = module["results"][0].get("error", "No error details")
                critical_count = module.get("log_issues", {}).get("critical", 0)
                warning_count = module.get("log_issues", {}).get("warning", 0)
                
                # Build email body
                email_body = f"""
                Stage: {stage}
                Command: {command}
                Status: FAILED
                
                Critical Issues: {critical_count}
                Warnings: {warning_count}
                
                Error Details:
                {error}
                """
```

---

## Prerequisite summary

| Function | What you need first |
|----------|-------------------|
| `build_report_name(...)` | Nothing — just pass domain_name |
| `TestReport(...)` | Nothing — just pass the required parameters |
| `report.add_result(...)` | A `TestReport` instance |
| `report.save()` | A `TestReport` instance with at least one result |
| `set_current_report()` | A `TestReport` instance |
| `get_current_report()` | `set_current_report()` called earlier |
| `record_playbook_failure(...)` | Nothing — standalone function |
