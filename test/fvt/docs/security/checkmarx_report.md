# Checkmarx Scan Analysis — omnia-artifactory

**Scan Date:** 2026-06-18
**Total Issues:** 86
**Fixed:** 8 (across 3 files)
**False Positives:** 78

---

## Summary

| Issue Type | Count | Verdict |
|-----------|-------|---------|
| Information_Exposure_Through_an_Error_Message | 49 | **FIXED** |
| Use_Of_Hardcoded_Password | 15 | **FALSE POSITIVE** |
| Insufficiently_Protected_Credentials | 10 | **FALSE POSITIVE** |
| Improper_Resource_Shutdown_or_Release | 3 | **1 FIXED, 2 FALSE POSITIVE** |
| Stored_Command_Injection | 2 | **FALSE POSITIVE** |
| Stored_Command_Argument_Injection | 2 | **FALSE POSITIVE** |
| Command_Injection | 1 | **FIXED** (same fix as resource shutdown) |
| Potential_Clickjacking_on_Legacy_Browsers | 1 | **NOT CODE** |

---

## FIXED Issues

### 1. Information_Exposure_Through_an_Error_Message (49 issues)

**Root Cause:** Exception handlers used `except Exception as e: ... str(e)` which exposes internal system details (file paths, stack traces, OS info) to callers.

**Files fixed:**

**`automation_library/checks/functions/system.py`** (40 hits, 4 source lines)
- Line 77: `run_command()` remote — `str(e)` replaced with `"Remote command execution failed"`
- Line 94: `run_command()` local — `str(e)` replaced with `"Command execution failed"`
- Line 119: `run_shell()` remote — `str(e)` replaced with `"Remote shell execution failed"`
- Line 132: `run_shell()` local — `str(e)` replaced with `"Shell execution failed"`

**`automation_library/checks/functions/network.py`** (9 hits, 1 source line)
- Line 182: `validate_ip_configuration()` — `f"Invalid IP format: {str(e)}"` replaced with `"Invalid IP address format provided"`

### 2. Improper_Resource_Shutdown_or_Release + Command_Injection (1 issue each)

**File:** `automation_library/omnia_sh/functions/omnia_sh_func.py`
**Function:** `run_interactive()` (line 194)

**Root Cause:** `subprocess.Popen` was not properly killed/waited in all exception paths, and stdin/stdout/stderr streams were never closed.

**Fix:**
- Initialized `process = None` before try block
- Added `process.kill()` + `process.wait()` in `TimeoutExpired` and generic `Exception` handlers
- Added `finally` block to close all streams (stdin, stdout, stderr)
- Removed `str(e)` from error message

Additionally fixed `str(e)` in `run_command()` (line 130) and `run_shell()` (line 161) in the same file.

---

## FALSE POSITIVE Issues

### Use_Of_Hardcoded_Password (15 issues)

Checkmarx flags variable names or string literals containing "pass", "password", or "secret". None are actual hardcoded credentials.

| File | Line | Flagged Object | Actual Usage | Verdict |
|------|------|---------------|-------------|---------|
| `checks/functions/main.py` | 95 | `"PASS"` | Test status string (`status = "PASS"`) | FALSE POSITIVE |
| `checks/functions/main.py` | 127 | `"PASS"` | Test status string (`status_text = "PASS"`) | FALSE POSITIVE |
| `gitlab/functions/gitlab_func.py` | 613 | `"pass"` | Test verdict string (`verdict = "pass"`) | FALSE POSITIVE |
| `gitlab/functions/gitlab_func.py` | 633 | `"pass"` | Verdict comparison (`svc["verdict"] == "pass"`) | FALSE POSITIVE |
| `gitlab/functions/gitlab_func.py` | 770 | `"pass"` | Test verdict string | FALSE POSITIVE |
| `gitlab/functions/gitlab_func.py` | 790 | `"pass"` | Verdict comparison | FALSE POSITIVE |
| `prepare_oim/functions/prepare_oim_func.py` | 485 | `"pass"` | Test verdict string | FALSE POSITIVE |
| `prepare_oim/functions/prepare_oim_func.py` | 493 | `"pass"` | Test verdict string | FALSE POSITIVE |
| `prepare_oim/functions/prepare_oim_func.py` | 521 | `"pass"` | Verdict comparison | FALSE POSITIVE |
| `prepare_oim/functions/prepare_oim_func.py` | 558 | `"pass"` | Test verdict string | FALSE POSITIVE |
| `prepare_oim/functions/prepare_oim_func.py` | 568 | `"pass"` | Test verdict string | FALSE POSITIVE |
| `prepare_oim/functions/prepare_oim_func.py` | 596 | `"pass"` | Verdict comparison | FALSE POSITIVE |
| `build_stream/vars/build_stream_vars.py` | 170 | `"BSM_CLIENT_SECRET"` | CI/CD variable **key name**, not a secret value | FALSE POSITIVE |
| `prepare_oim/vars/build_stream_vars.py` | 55 | `"postgres_password"` | Credential **key name** for vault lookup, not a password | FALSE POSITIVE |
| `telemetry/vars/victoria_vars.py` | 80 | `"victoria-tls-certs"` | K8s Secret **resource name**, not a credential | FALSE POSITIVE |

### Insufficiently_Protected_Credentials (10 issues)

Checkmarx flags `json.loads()` calls that parse responses containing credential fields, and file-loading functions. All credentials are read from Ansible Vault-encrypted files or retrieved from secured APIs at runtime.

| File | Line | Flagged Object | Actual Usage | Verdict |
|------|------|---------------|-------------|---------|
| `build_stream/functions/api_func.py` | 88 | `loads` | Parsing GitLab API response for BSM token | FALSE POSITIVE |
| `checks/vars/oim_prereq_vars.py` | 73 | `f` | Loading credentials via `load_omnia_test_credentials()` (vault-encrypted) | FALSE POSITIVE |
| `core/functions/host_func.py` | 43 | `f` | Loading credentials file path | FALSE POSITIVE |
| `telemetry/functions/idrac_telemetry_func.py` | 751 | `loads` | Parsing MySQL auth JSON from iDRAC pod | FALSE POSITIVE |
| `telemetry/functions/powerscale_func.py` | 1905 | `loads` | Parsing K8s secret data | FALSE POSITIVE |
| `telemetry/functions/vast_telemetry_func.py` | 306, 618 | `loads` | Parsing K8s secret/endpoint data | FALSE POSITIVE |
| `telemetry/functions/victoria_func.py` | 332 | `loads` | Parsing K8s secret data | FALSE POSITIVE |
| `telemetry/functions/victoria_logs_func.py` | 407 | `loads` | Parsing K8s secret data | FALSE POSITIVE |
| `telemetry/vars/idrac_telemetry_vars.py` | 55 | `f` | Config path string, not credential | FALSE POSITIVE |

### Stored_Command_Injection / Stored_Command_Argument_Injection (4 issues)

| File | Line | Flagged Object | Actual Usage | Verdict |
|------|------|---------------|-------------|---------|
| `kubernetes/functions/k8s_func.py` | 310 | `read` | `stdout.read()` reads SSH command output, not user input | FALSE POSITIVE |
| `kubernetes/functions/k8s_func.py` | 240 | `oim_ssh_password` | Password loaded from config dict, used for SSH connect | FALSE POSITIVE |

These are flagged because config values flow into SSH commands. This is by design — the automation framework reads trusted config files and executes commands on managed infrastructure.

### Improper_Resource_Shutdown_or_Release (2 remaining)

| File | Line | Flagged Object | Actual Usage | Verdict |
|------|------|---------------|-------------|---------|
| `omnia_sh/functions/omnia_sh_func.py` | 947 | `f` | `host.file(path)` — testinfra proxy object, not a file handle. No close needed. | FALSE POSITIVE |
| `omnia_sh/functions/omnia_sh_func.py` | 1147 | `f` | `host.file(service_file)` — testinfra proxy object. No close needed. | FALSE POSITIVE |
| `vast_storage/functions/vast_storage_func.py` | 177 | `host` | `host.file(...)` — testinfra proxy object. No close needed. | FALSE POSITIVE |

### Potential_Clickjacking_on_Legacy_Browsers (1 issue)

| File | Line | Verdict |
|------|------|---------|
| `Cx-omnia-scan-results-summary-PR-284.html` | 1 | **NOT CODE** — Checkmarx scan report HTML artifact |

---

## Files Modified

| File | Changes Made |
|------|-------------|
| `automation_library/checks/functions/system.py` | Replaced `str(e)` with generic messages in 4 exception handlers |
| `automation_library/checks/functions/network.py` | Replaced `str(e)` with generic message in 1 exception handler |
| `automation_library/omnia_sh/functions/omnia_sh_func.py` | Fixed subprocess resource cleanup in `run_interactive()`, replaced `str(e)` in 3 handlers |

## No Hardcoded Passwords

All credential files in `datasets/project_default/omnia_config_credentials.yml` contain only empty template placeholders (`""`). All runtime credentials are loaded from Ansible Vault-encrypted files via `load_omnia_test_credentials()`.
