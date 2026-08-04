# Report — `TestReport`, `get_current_report()`, `set_current_report()`

**Source file:** `src/omnia_auto/functions/report_func.py`

## What is this?

A test report generator that produces **JSON** and **HTML** report files.
The HTML report includes:

- Dark/light theme toggle
- SVG donut charts showing pass rate
- Scenario bar charts with hover tooltips
- Trend sparklines across runs
- Duration charts for slowest scenarios
- Expandable test items with output details
- Playbook log viewer

Reports are organized **by server IP** so you can run tests against
multiple servers and all results accumulate in the same report file.

---

## `TestReport(module_name, report_path, report_name, server_ip, ...)`

### Constructor parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `module_name` | `str` | **Yes** | A name for the scenario or module being tested. This appears as a label in the report. | `"build"` or `"validate"` |
| `report_path` | `str` | **Yes** | Absolute path to the directory where JSON and HTML files will be saved. The directory is created automatically if it doesn't exist. | `"/opt/omnia/reports"` |
| `report_name` | `str` | **Yes** | Base filename for the report (without extension). Two files are created: `<report_name>.json` and `<report_name>.html`. | `"image_test_report"` |
| `server_ip` | `str` | **Yes** | The IP address of the target server. Results in the report are grouped by this IP. | `"100.10.0.84"` |
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
    test_name="test_s3_images_x86_64",
    status="PASSED",
    duration=1.58,
    details="All 2 images found in S3",
)
```

### `add_result` parameters (keyword form)

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `test_name` | `str` | **Yes** | Name of the test. | `"test_s3_images_x86_64"` |
| `passed` | `bool` | No | `True` for pass, `False` for fail. Only used if `status` is not given. | `True` |
| `status` | `str` | No | `"PASSED"`, `"FAILED"`, or `"SKIPPED"`. Overrides `passed`. | `"PASSED"` |
| `duration` | `float` | No | Duration in seconds. Default: `0.0`. | `1.58` |
| `details` | `str` | No | Multi-line output from the test (shown in expandable section). | `"✔ PASS: All images found"` |
| `error` | `str` | No | Error message (shown in red box in the report). | `"AssertionError: ..."` |

---

## `report.save() -> str`

Writes two files:
- `<report_path>/<report_name>.json` — structured JSON with all results
- `<report_path>/<report_name>.html` — interactive HTML report

**Returns:** the path to the HTML file.

**Important:** If a report file already exists, new results are **merged** into it.
Multiple runs and multiple modules accumulate in the same report, organized by
server IP and report ID.

### Terminal output when `save()` is called

```
┌────────────────────────────────────────────────────────────────────┐
│  REPORT SAVED                                                     │
├────────────────────────────────────────────────────────────────────┤
│  Server:        100.10.0.84                                        │
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

## Full example in `conftest.py`

```python
import os, pytest
from omnia_auto import (
    TestReport, set_current_report, get_current_report,
    load_test_config, get_test_output,
    add_session_result, print_summary_table,
)

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def pytest_sessionstart(session):
    config = load_test_config()

    # Create the report
    report = TestReport(
        module_name="build",
        report_path=config.get("report_path", "/opt/omnia/reports"),
        report_name=config.get("report_name", "image_test_report"),
        server_ip=config.get("oim_server_ip", "localhost"),
    )
    set_current_report(report)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()

    if result.when == "call":
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

## Prerequisite summary

| Function | What you need first |
|----------|-------------------|
| `TestReport(...)` | Nothing — just pass the required parameters |
| `report.add_result(...)` | A `TestReport` instance |
| `report.save()` | A `TestReport` instance with at least one result |
| `set_current_report()` | A `TestReport` instance |
| `get_current_report()` | `set_current_report()` called earlier |
