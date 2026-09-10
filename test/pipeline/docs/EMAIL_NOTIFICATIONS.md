# Email Notifications with Test Report Attachments

## Overview

The `send_email.py` script sends automated email notifications with pipeline execution summaries and test reports attached. It integrates with GitLab CI/CD to notify stakeholders of pipeline results.

## Features

- **Test Report Attachments** - HTML and JSON test reports with detailed results
- **Test Summary in Email Body** - Quick overview of pass/fail/skip counts
- **SMTP Retry Logic** - Automatic retry with exponential backoff for reliability
- **Multiple Recipients** - Support for comma-separated email addresses
- **Flexible Configuration** - All settings via environment variables

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `EMAIL_RECIPIENTS` | Comma-separated list of recipients | `user1@example.com,user2@example.com` |
| `EMAIL_SENDER` | From address for the email | `pipeline@example.com` |
| `SMTP_SERVER` | SMTP relay host | `smtp.example.com` |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SMTP_PORT` | SMTP relay port | `25` |
| `SMTP_USER` | SMTP authentication username | (none) |
| `SMTP_PASSWORD` | SMTP authentication password | (none) |
| `TEST_REPORTS_PATH` | Directory containing test reports | `/opt/omnia/reports` |
| `PIPELINE_TRIGGER_TIME` | Pipeline trigger timestamp | (read from `pipeline_time.env`) |
| `CI_PIPELINE_URL` | GitLab pipeline URL | (auto-set by GitLab) |

## Usage in GitLab CI/CD

### Basic Example

```yaml
send_notification:
  stage: notify
  script:
    - python3 test/pipeline/send_email.py
  variables:
    EMAIL_RECIPIENTS: "team@example.com"
    EMAIL_SENDER: "pipeline@example.com"
    SMTP_SERVER: "smtp.example.com"
  only:
    - branches
  when: always
```

### With SMTP Authentication

```yaml
send_notification:
  stage: notify
  script:
    - python3 test/pipeline/send_email.py
  variables:
    EMAIL_RECIPIENTS: "team@example.com"
    EMAIL_SENDER: "pipeline@example.com"
    SMTP_SERVER: "smtp.example.com"
    SMTP_PORT: "587"
    SMTP_USER: "username"
    SMTP_PASSWORD: $SMTP_PASSWORD  # Use GitLab CI/CD secret variable
  only:
    - branches
  when: always
```

### With Custom Test Reports Path

```yaml
send_notification:
  stage: notify
  script:
    - python3 test/pipeline/send_email.py
  variables:
    EMAIL_RECIPIENTS: "team@example.com,manager@example.com"
    EMAIL_SENDER: "pipeline@example.com"
    SMTP_SERVER: "smtp.example.com"
    TEST_REPORTS_PATH: "/opt/omnia/reports"  # Optional, defaults to this
  artifacts:
    paths:
      - /opt/omnia/reports/*.html
      - /opt/omnia/reports/*.json
    expire_in: 30 days
  only:
    - branches
  when: always
```

## Email Content

### Email Subject
```
Omnia Pipeline Execution Report - 2026-09-09 18:39:04
```

### Email Body

The email includes:

1. **Pipeline Information**
   - Trigger time
   - Pipeline URL (clickable link)

2. **Test Execution Summary** (if test reports exist)
   - Total passed tests
   - Total failed tests
   - Total skipped tests

3. **Attachments**
   - `*.html` - Interactive HTML test reports (one per domain)
   - `*.json` - Structured JSON test data (one per domain)

### Example Email Body

```
Omnia Pipeline Execution Report

Pipeline Trigger Time: 2026-09-09 18:39:04
Pipeline URL: https://gitlab.example.com/project/-/pipelines/12345

Test Execution Summary
Passed: 120
Failed: 15
Skipped: 20

Detailed test reports are attached to this email.

Please find the detailed test reports attached.

This is an automated email from GitLab CI/CD pipeline.
```

## Test Report Attachments

### HTML Report
- **Filename**: `repo_manager_fvt.html` (or other domain names)
- **Content**: Interactive HTML with:
  - Dark/light theme toggle
  - Test results grouped by run_id
  - Search and filter capabilities
  - Expandable test details with logs
  - Summary statistics and charts

### JSON Report
- **Filename**: `repo_manager_fvt.json` (or other domain names)
- **Content**: Structured data with:
  - Complete test results
  - Playbook failure details (if applicable)
  - Log issue counts (CRITICAL/WARNING)
  - Server and run information

## Extracting Data from JSON Reports

To programmatically extract failure details from the JSON report:

```python
import json

with open("/opt/omnia/reports/repo_manager_fvt.json") as f:
    report = json.load(f)

for server_ip, server_data in report["servers"].items():
    for run in server_data["runs"]:
        for module in run["modules"]:
            if module["results"] and module["results"][0]["status"] == "FAILED":
                stage = module["module"]
                command = module.get("command_type", "unknown")
                error = module["results"][0].get("error", "")
                critical = module.get("log_issues", {}).get("critical", 0)
                warning = module.get("log_issues", {}).get("warning", 0)
                
                print(f"Stage: {stage}")
                print(f"Command: {command}")
                print(f"Status: FAILED")
                print(f"Critical Issues: {critical}")
                print(f"Warnings: {warning}")
                print(f"Error: {error}")
```

## Troubleshooting

### Email Not Sending

1. **Check SMTP connectivity**
   ```bash
   telnet smtp.example.com 25
   ```

2. **Verify environment variables**
   ```bash
   echo $EMAIL_RECIPIENTS
   echo $SMTP_SERVER
   ```

3. **Check script output**
   - Look for "Email sent successfully" message
   - Check for SMTP error messages

### Reports Not Attached

1. **Verify test reports exist**
   ```bash
   ls -la /opt/omnia/reports/
   ```

2. **Check TEST_REPORTS_PATH is set**
   ```bash
   echo $TEST_REPORTS_PATH
   ```

3. **Verify file permissions**
   - Reports must be readable by the script user

### SMTP Authentication Failures

1. **Verify credentials**
   - Check SMTP_USER and SMTP_PASSWORD are correct
   - Ensure password doesn't contain special characters that need escaping

2. **Check SMTP port**
   - Port 25: No authentication (open relay)
   - Port 587: TLS authentication
   - Port 465: SSL authentication

## Performance Considerations

- **Large Reports**: HTML reports can be large (>1MB). Consider email size limits.
- **Multiple Recipients**: Email is sent to all recipients in a single message.
- **Retry Logic**: Failed sends are retried up to 3 times with 5-second delays.
- **File I/O**: Reports are read entirely into memory before sending.

## Security Considerations

- **Sensitive Data**: Reports may contain sensitive information (IPs, hostnames, etc.)
  - Ensure email recipients are authorized
  - Consider using encryption for sensitive environments
  
- **Credentials**: Use GitLab CI/CD secret variables for SMTP credentials
  - Never commit passwords to the repository
  - Use `$VARIABLE_NAME` syntax in CI/CD configuration

- **Email Headers**: The script includes standard email headers for traceability

## Examples

### Send to Multiple Teams

```yaml
variables:
  EMAIL_RECIPIENTS: "team-a@example.com,team-b@example.com,manager@example.com"
```

### Send Only on Failure

```yaml
send_notification:
  when: on_failure  # Only send if pipeline fails
```

### Send with Custom Subject

Modify the script to customize the subject line:

```python
msg["Subject"] = f"[FAILED] Omnia Pipeline - {trigger_time}"
```

### Archive Reports

```yaml
artifacts:
  paths:
    - /opt/omnia/reports/
  expire_in: 90 days
  when: always
```
