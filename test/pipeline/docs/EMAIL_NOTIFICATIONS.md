# Email Notifications with Test Report Attachments

## Summary email

In the cluster, utils and build stream pipelines the email is sent by the `summary` job
(`pipeline_ci.py summary`, `library/functions/email_func.py`). It always runs, even after a failure.
It is sent when `EMAIL_RECIPIENTS`, `EMAIL_SENDER` and `SMTP_SERVER` are set; `SMTP_PORT`
(465 uses SSL, 587 uses STARTTLS), `SMTP_USER` and `SMTP_PASSWORD` are optional.

Layout:

- **Banner:** the cluster and the verdict, `PASSED` (green), `FAILED` (red) or `UNKNOWN`.
- **Details table:** cluster, mode, domains, repository, branch and commit (links to the web
  page of the repository), start time and pipeline (link).
- **Failure box** (only after a failure): the failed jobs, each linked to its log, and the jobs
  that did not run after the first failure.
- **Buttons:** open the pipeline, download all artifacts.
- **Pipeline jobs:** one row per job that ran, in pipeline order, with its status and a link.
- **Attachments:** exactly two files: the pipeline's one test report (HTML, written on the OIM in
  `TEST_REPORTS_PATH`, default `/automation`; a report over 5 MB is compressed) and the HTML
  report of the stages with their logs. The JSON of the test report is in the job artifacts. The copy of the stage report in the mail keeps at most
  40,000 characters of each log (the artifact `pipeline_report/` has up to 200,000, and a longer
  log keeps its start and end with a link to the job). The attachments of one mail together stay
  below 20 MB: when they would not, the largest are left out, named in the mail, and stay in the
  job artifacts (`pipeline_reports/`, `pipeline_report/`). A job log is also limited by GitLab
  itself (4 MB by default).
- A plain-text version with the same facts.

Subject: `Omnia FVT Pipeline [<cluster>] <mode> - <VERDICT> (<failed jobs>)`.

A mail that cannot be sent is reported in the job log with an error banner; it does not change the
result of the pipeline.

## HTML report of the stages

The cluster pipeline summary attaches `pipeline_<id>_report.html`: every stage with its status,
duration, failure reason and a scrollable log, in a day and a night theme. See
[CLUSTER_PIPELINE.md](CLUSTER_PIPELINE.md) (Summary, HTML report and email).

---

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

with open("/automation/repo_manager_fvt.json") as f:
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
   ls -la /automation/
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
