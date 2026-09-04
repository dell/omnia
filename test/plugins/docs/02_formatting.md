# Formatting & Logging — `Colors`, `Symbols`, `TestLogger`, `log()`, session summary

**Source file:** `src/omnia_auto/functions/formatting_func.py`

## What is this?

This module gives you terminal colors, status symbols, structured test logging,
and an end-of-session summary table.  Use it to make your test output clean
and readable — every test prints a structured pass/fail/skip line, and at the
end of the run you get a summary table.

---

## `Colors` — ANSI color constants

A class with string attributes for terminal coloring.  Colors are
automatically disabled when output is piped to a file (override with
the `FORCE_COLOR=1` environment variable).

### Available colors

| Attribute | What it looks like | Use for |
|-----------|--------------------|---------|
| `Colors.RESET` | *(resets all formatting)* | End of any colored text |
| `Colors.BOLD` | **bold text** | Emphasis |
| `Colors.DIM` | dim text | De-emphasis |
| `Colors.RED` | red | Errors |
| `Colors.GREEN` | green | Success |
| `Colors.YELLOW` | yellow | Warnings, skips |
| `Colors.BLUE` | blue | Info |
| `Colors.CYAN` | cyan | Headers |
| `Colors.GRAY` | gray | Detail lines |
| `Colors.BRIGHT_RED` | bright red | Critical failures |
| `Colors.BRIGHT_GREEN` | bright green | Pass markers |
| `Colors.BRIGHT_YELLOW` | bright yellow | Warning markers |
| `Colors.BRIGHT_BLUE` | bright blue | Info markers |
| `Colors.BRIGHT_CYAN` | bright cyan | Test headers |

### Example

```python
from omnia_auto import Colors

print(f"{Colors.BRIGHT_GREEN}PASS{Colors.RESET} — All containers running")
print(f"{Colors.BRIGHT_RED}FAIL{Colors.RESET} — Registry unreachable")
```

---

## `Symbols` — Unicode status indicators

A class with string attributes for status symbols.

| Attribute | Character | Meaning |
|-----------|-----------|---------|
| `Symbols.CHECK` | ✔ | Passed / OK |
| `Symbols.CROSS` | ✘ | Failed / Error |
| `Symbols.ARROW` | → | Step / transition |
| `Symbols.SKIP` | ↷ | Skipped |
| `Symbols.TRIANGLE` | ▶ | Test header |
| `Symbols.PIPE` | │ | Detail indent line |

### Example

```python
from omnia_auto import Symbols

print(f"  {Symbols.CHECK} All images found in S3")
print(f"  {Symbols.CROSS} Registry check failed")
print(f"  {Symbols.SKIP} No aarch64 groups — skipping")
```

---

## `log(message, level="INFO")`

Print a timestamped, color-coded log line.

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `message` | `str` | **Yes** | The message to print. | `"Syncing input files"` |
| `level` | `str` | No | One of: `"INFO"`, `"DEBUG"`, `"WARN"`, `"ERROR"`, `"OK"`. Default is `"INFO"`. | `"OK"` |

### Prerequisite

None — works standalone.

**Note:** `DEBUG` messages are hidden by default.  Call `set_debug_mode(True)` to show them.

### Output format

```
[14:30:00] [INFO] Syncing input files
[14:30:01] [OK]   Sync complete
[14:30:02] [WARN] Retrying connection
[14:30:03] [ERROR] Connection refused
```

### Example

```python
from omnia_auto import log

log("Starting file sync", "INFO")
log("Sync complete", "OK")
log("Retrying in 5s", "WARN")
log("Connection refused", "ERROR")
log("Variable dump: x=42", "DEBUG")  # hidden unless debug mode is on
```

---

## `set_debug_mode(enabled: bool)`

Enable or disable `DEBUG` level output globally.

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `enabled` | `bool` | **Yes** | `True` to show DEBUG messages, `False` to hide them. | `True` |

### Prerequisite

None.

### Example

```python
from omnia_auto import set_debug_mode, log

set_debug_mode(True)
log("This will now be visible", "DEBUG")

set_debug_mode(False)
log("This will be hidden", "DEBUG")
```

---

## `TestLogger(test_name, tc_id="")`

Structured test output logger.  Each test creates a `TestLogger` instance
that prints a formatted header and provides methods for pass/fail/skip
results with optional detail lines.

This is the main way your test functions produce output.

### Constructor parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `test_name` | `str` | **Yes** | A human-readable name for the test. This is displayed as the test header. | `"Verify containers running"` |
| `tc_id` | `str` | No | A test case ID like `IMGBM_FVT_BUILD_V006`. If provided, it appears in brackets before the test name. | `"IMGBM_FVT_BUILD_V006"` |

### Methods

| Method | What it does | When to use |
|--------|-------------|-------------|
| `tl.check(message)` | Prints a yellow arrow line → | Before performing a check ("Checking S3 bucket...") |
| `tl.info(message)` | Prints a blue arrow line → | For informational messages during the test |
| `tl.passed(message, details=None)` | Prints a green ✔ PASS line | When a check passes. `details` is an optional multi-line string shown below the pass line. |
| `tl.failed(message, details=None)` | Prints a red ✘ FAIL line | When a check fails. `details` is optional. |
| `tl.skipped(message, details=None)` | Prints a yellow ↷ SKIP line | When a check is skipped. `details` is optional. |
| `tl.passed_fields(message, fields)` | Prints a green ✔ PASS line followed by colored key/value fields | When named values make the result easier to understand. |
| `tl.failed_fields(message, fields)` | Prints a red ✘ FAIL line followed by colored key/value fields | When a failure needs named diagnostic values. |
| `tl.skipped_fields(message, fields)` | Prints a yellow ↷ SKIP line followed by colored key/value fields | When a skip needs its prerequisites or current configuration shown. |
| `tl.get_output()` | Returns all captured output as a single string | When you need to store the output (e.g., for the test report) |

The `fields` argument accepts a dictionary or an ordered iterable of
`(key, value)` pairs. In the terminal, keys are cyan and values are bright
white when color is supported. Reports store the same fields as structured
data and render them with report-theme colors. Keys and values are escaped
before HTML rendering.

### Prerequisite

None — works standalone.  But typically used inside a `pytest` test function.

### Full example

```python
from omnia_auto import TestLogger

def test_s3_images(host):
    tl = TestLogger("Verify S3 images pushed", "IMGBM_FVT_BUILD_V006")

    tl.check("Checking S3 bucket for images...")
    # ... run some verification logic ...

    images_found = ["slurm_node_x86_64", "slurm_control_node_x86_64"]
    tl.passed(
        f"All images pushed to S3 for {len(images_found)} functional groups",
        "\n".join(f"  - {img}" for img in images_found),
    )

    # Get output for the report
    output = tl.get_output()
```

For named result values, use the structured fields API instead of manually
adding ANSI color codes:

```python
tl.passed_fields(
    "Registry naming is valid",
    {
        "Artifact store": "OCI registry",
        "Architecture": "x86_64",
        "Required suffix": "-imgth",
        "Matching current artifacts": 5,
    },
)
```

### Terminal output

```
  ▶ [IMGBM_FVT_BUILD_V006] Verify S3 images pushed
  → Checking S3 bucket for images...
  ✔ PASS: All images pushed to S3 for 2 functional groups
    │   - slurm_node_x86_64
    │   - slurm_control_node_x86_64
```

---

## `get_test_output(test_name=None) -> str`

Returns the captured output from the **most recent** `TestLogger` instance.

### Parameters

| Parameter | Type | Required? | What to give |
|-----------|------|-----------|--------------|
| `test_name` | `str` | No | Currently unused; reserved for future use. |

### Returns

`str` — the output string from the last `TestLogger`.

### Prerequisite

A `TestLogger` must have been created and used first.

---

## `add_session_result(test_name, status, duration, tc_id="")`

Accumulate a test result for the end-of-session summary table.
You call this from your `pytest_runtest_makereport` hook in `conftest.py`
so that every test result is recorded.

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `test_name` | `str` | **Yes** | The test function name (e.g., `test_s3_images`). | `"test_s3_images_x86_64"` |
| `status` | `str` | **Yes** | One of: `"PASSED"`, `"FAILED"`, `"SKIPPED"`. | `"PASSED"` |
| `duration` | `float` | **Yes** | How long the test took, in seconds. | `1.58` |
| `tc_id` | `str` | No | Test case ID. | `"IMGBM_FVT_BUILD_V006"` |

### Prerequisite

None — but only useful if you also call `print_summary_table()` later.

### Example (in conftest.py)

```python
import pytest
from omnia_auto import add_session_result

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()
    if result.when == "call":
        status = "PASSED" if result.passed else (
            "SKIPPED" if result.skipped else "FAILED"
        )
        add_session_result(
            test_name=item.name,
            status=status,
            duration=getattr(result, "duration", 0),
            tc_id=getattr(item, "_tc_id", ""),
        )
```

---

## `get_session_results() -> list` / `clear_session_results()`

- `get_session_results()` — returns the list of all accumulated results.
- `clear_session_results()` — empties the list.

---

## `print_summary_table()`

Print a formatted summary table of all results that were accumulated via
`add_session_result()`.  Call this from your `pytest_sessionfinish` hook.

If no results were recorded, nothing is printed.

### Prerequisite

- Results must have been added via `add_session_result()`.

### Environment variables it respects

| Variable | Effect |
|----------|--------|
| `OMNIA_RESULTS_FILE` | If set, also writes results to this JSON file (for aggregation across multiple test runs). |
| `OMNIA_SUPPRESS_SUMMARY` | If set, suppresses the table printout (useful when a shell wrapper prints a combined summary). |

### Example (in conftest.py)

```python
from omnia_auto import print_summary_table

def pytest_sessionfinish(session, exitstatus):
    print_summary_table()
```

### Output example

```
=====================================================================================
  TEST EXECUTION SUMMARY
=====================================================================================
  TC ID                  Test Name                                Status     Duration
  ---------------------- ---------------------------------------- ---------- --------
  IMGBM_FVT_BUILD_V006 test_s3_images_x86_64                    PASSED        1.58s
  IMGBM_FVT_BUILD_V007 test_s3_images_aarch64                   SKIPPED       0.85s
  IMGBM_FVT_BUILD_V008 test_registry_images_x86_64              PASSED        1.46s
  IMGBM_FVT_BUILD_V010 test_build_status                        PASSED        0.31s
  ---------------------- ---------------------------------------- ---------- --------
  3 passed, 0 failed, 1 skipped / 4 total (4.20s)
=====================================================================================
```

---

## Prerequisite summary

| Function | Prerequisite |
|----------|-------------|
| `Colors` | None |
| `Symbols` | None |
| `log()` | None |
| `set_debug_mode()` | None |
| `TestLogger()` | None |
| `get_test_output()` | A `TestLogger` must exist |
| `add_session_result()` | None |
| `print_summary_table()` | `add_session_result()` calls |
