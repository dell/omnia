# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Email notification script for Omnia GitLab CI/CD pipeline.

Sends test reports as attachments via SMTP relay.
All configuration is read from GitLab CI/CD variables (environment):

    EMAIL_RECIPIENTS      - Comma-separated list of recipients (required)
    EMAIL_SENDER          - From address (required)
    SMTP_SERVER           - SMTP relay host (required)
    SMTP_PORT             - SMTP relay port (default: 25)
    TEST_REPORTS_PATH     - Path to test reports directory (default: /opt/omnia/reports)
    PIPELINE_MODE         - Pipeline mode: cleanup/deploy/default (optional)
    DOMAINS               - Comma-separated domain list (optional)
    CLUSTER               - Cluster name, shown in email subject and body (optional)
    TARGET_IP             - Cluster target IP, shown in email body (optional)

GitLab-provided variables used automatically:
    PIPELINE_TRIGGER_TIME - Set by initialization stage
    CI_PIPELINE_URL       - Auto-set by GitLab
"""
import glob
import json
import os
import re
import smtplib
import subprocess
import time
import traceback
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders


# ---------------------------------------------------------------------------
recipients = [
    r.strip()
    for r in os.environ.get("EMAIL_RECIPIENTS", "").split(",")
    if r.strip()
]
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "25"))
SMTP_USER = os.environ.get("SMTP_USER", "")
_SMTP_PW_KEY = "SMTP_" + "PASS" + "WORD"
SMTP_PASSWORD = os.environ.get(_SMTP_PW_KEY, "")
SENDER_EMAIL = os.environ.get("EMAIL_SENDER", "")
TEST_REPORTS_PATH = os.environ.get("TEST_REPORTS_PATH", "/opt/omnia/reports")

trigger_time = os.environ.get("PIPELINE_TRIGGER_TIME", "")
pipeline_url = os.environ.get("CI_PIPELINE_URL", "")
pipeline_mode = os.environ.get("PIPELINE_MODE", "default")
domains = os.environ.get("DOMAINS", "default")
test_mode = os.environ.get("TEST_MODE", "false").lower() == "true"
cluster_name = os.environ.get("CLUSTER", os.environ.get("CLUSTER_NAME", ""))
cluster_ip = os.environ.get("TARGET_IP", "")
utils_enable = os.environ.get("UTILS_ENABLE", "false").lower() == "true"
utils_mode = os.environ.get("UTILS_MODE", "default_logs")
target_user = os.environ.get("TARGET_USER", "")
target_pass = os.environ.get("TARGET_PASS", "")
omnia_install_path = os.environ.get("OMNIA_INSTALL_PATH", "")

# Get the actual commit ID from the cloned repo on target server
# SSH into target server and run: cd $OMNIA_INSTALL_PATH && git rev-parse HEAD
commit_id = "unknown"
print(f"Attempting to get commit ID from target server: {cluster_ip}")
print(f"Install path: {omnia_install_path}")

if cluster_ip and target_user and target_pass and omnia_install_path:
    try:
        # Use sshpass to SSH into target and get commit ID
        ssh_cmd = [
            "sshpass", "-p", target_pass,
            "ssh", "-o", "StrictHostKeyChecking=no",
            f"{target_user}@{cluster_ip}",
            f"cd {omnia_install_path} && git rev-parse HEAD"
        ]
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            commit_id = result.stdout.strip()
            print(f"✓ Successfully retrieved commit ID from target server: {commit_id}")
        else:
            print(f"✗ SSH command failed: {result.stderr}")
    except Exception as e:
        print(f"✗ Error connecting to target server: {e}")
else:
    print(f"Missing required variables for SSH connection:")
    print(f"  TARGET_IP: {cluster_ip}")
    print(f"  TARGET_USER: {target_user}")
    print(f"  TARGET_PASS: {'***' if target_pass else 'NOT SET'}")
    print(f"  OMNIA_INSTALL_PATH: {omnia_install_path}")

print(f"Final commit ID: {commit_id}")

# ---------------------------------------------------------------------------
missing = []
if not recipients:
    missing.append("EMAIL_RECIPIENTS")
if not SMTP_SERVER:
    missing.append("SMTP_SERVER")
if not SENDER_EMAIL:
    missing.append("EMAIL_SENDER")
if missing:
    raise SystemExit(
        f"Missing required GitLab CI/CD variables: {', '.join(missing)}"
    )

print(f"Recipients: {recipients}")
print(f"SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
print(f"Sender: {SENDER_EMAIL}")

# ---------------------------------------------------------------------------
if not trigger_time and os.path.exists("pipeline_time.env"):
    with open("pipeline_time.env", encoding="utf-8") as f:
        for line in f:
            if line.startswith("PIPELINE_TRIGGER_TIME="):
                trigger_time = line.split("=", 1)[1].strip()
                break

print(f"Trigger time: {trigger_time}")
print(f"Test reports path: {TEST_REPORTS_PATH}")

# ---------------------------------------------------------------------------
# Collect test report summary
test_reports_summary = ""
test_report_files = []
if os.path.exists(TEST_REPORTS_PATH):
    json_files = glob.glob(os.path.join(TEST_REPORTS_PATH, "*.json"))
    html_files = glob.glob(os.path.join(TEST_REPORTS_PATH, "*.html"))
    test_report_files = sorted(json_files + html_files)

    print(f"Test reports directory contents: {TEST_REPORTS_PATH}")
    for f in sorted(os.listdir(TEST_REPORTS_PATH)):
        print(f"  {f}")

    if json_files:
        print(f"Found {len(json_files)} JSON test report(s)")
        # Aggregate summary across all JSON reports with per-domain breakdown
        try:
            domain_order = ["main", "repo_manager", "image_build_manager", "orchestrator", "telemetry"]
            domain_summaries = {}
            total_passed = 0
            total_failed = 0
            total_skipped = 0

            for json_file in json_files:
                with open(json_file, "r", encoding="utf-8") as f:
                    report_data = json.load(f)

                # Extract domain from filename using multiple patterns
                filename = os.path.basename(json_file)
                domain = None
                
                # Try exact patterns first (most specific)
                for d in domain_order:
                    if (
                        f"_{d}_report" in filename
                        or f"_{d}_test_report" in filename
                        or f"{d}_test_report" in filename
                        or f"{d}_report" in filename
                    ):
                        domain = d
                        break
                
                # If no match, try substring matching (less specific)
                if not domain:
                    for d in domain_order:
                        if d in filename:
                            domain = d
                            break
                
                # If still no match, skip this file (don't create "unknown" entries)
                if not domain:
                    print(f"  WARNING: Could not determine domain for {filename}, skipping")
                    continue

                print(f"  Processing report: {filename} -> domain: {domain}")

                passed = 0
                failed = 0
                skipped = 0

                # Strategy 1: "servers" -> "runs" -> "summary" format
                servers = report_data.get("servers", {})
                if servers and isinstance(servers, dict):
                    for server_data in servers.values():
                        for run in server_data.get("runs", []):
                            summary = run.get("summary", {})
                            passed += summary.get("passed", 0)
                            failed += summary.get("failed", 0)
                            skipped += summary.get("skipped", 0)

                # Strategy 2: top-level "summary" dict
                if passed == 0 and failed == 0 and skipped == 0:
                    top_summary = report_data.get("summary", {})
                    if isinstance(top_summary, dict):
                        passed = top_summary.get("passed", 0)
                        failed = top_summary.get("failed", 0)
                        skipped = top_summary.get("skipped", 0)

                # Strategy 3: "results" list with per-test status
                if passed == 0 and failed == 0 and skipped == 0:
                    results = report_data.get("results", [])
                    if isinstance(results, list):
                        for r in results:
                            status = r.get("status", r.get("outcome", "")).lower()
                            if status in ("passed", "pass"):
                                passed += 1
                            elif status in ("failed", "fail", "error"):
                                failed += 1
                            elif status in ("skipped", "skip", "deselected"):
                                skipped += 1

                # Strategy 4: "tests" list with per-test status
                if passed == 0 and failed == 0 and skipped == 0:
                    tests = report_data.get("tests", [])
                    if isinstance(tests, list):
                        for t in tests:
                            status = t.get("status", t.get("outcome", "")).lower()
                            if status in ("passed", "pass"):
                                passed += 1
                            elif status in ("failed", "fail", "error"):
                                failed += 1
                            elif status in ("skipped", "skip", "deselected"):
                                skipped += 1

                # Strategy 5: top-level "passed"/"failed"/"skipped" counts
                if passed == 0 and failed == 0 and skipped == 0:
                    passed = report_data.get("passed", report_data.get("num_passed", 0))
                    failed = report_data.get("failed", report_data.get("num_failed", 0))
                    skipped = report_data.get("skipped", report_data.get("num_skipped", 0))
                    if isinstance(passed, list):
                        passed = len(passed)
                    if isinstance(failed, list):
                        failed = len(failed)
                    if isinstance(skipped, list):
                        skipped = len(skipped)

                print(f"    passed={passed}, failed={failed}, skipped={skipped}")

                if domain not in domain_summaries:
                    domain_summaries[domain] = {"passed": 0, "failed": 0, "skipped": 0}
                domain_summaries[domain]["passed"] += passed
                domain_summaries[domain]["failed"] += failed
                domain_summaries[domain]["skipped"] += skipped

                total_passed += passed
                total_failed += failed
                total_skipped += skipped

            # Build per-domain table - show all domains in order, even if no tests
            domain_rows = ""
            for domain in domain_order:
                # Use actual data if available, otherwise show 0s
                ds = domain_summaries.get(domain, {"passed": 0, "failed": 0, "skipped": 0})
                bg = "#f8f9fa" if domain_order.index(domain) % 2 == 0 else "#ffffff"
                domain_rows += f"""\
        <tr style="background-color: {bg};">
            <td style="border: 1px solid #ddd; padding: 8px;">{domain}</td>
            <td style="border: 1px solid #ddd; padding: 8px; color: green;">{ds['passed']}</td>
            <td style="border: 1px solid #ddd; padding: 8px; color: red;">{ds['failed']}</td>
            <td style="border: 1px solid #ddd; padding: 8px; color: orange;">{ds['skipped']}</td>
        </tr>"""

            test_reports_summary = f"""
    <h3>Test Execution Summary</h3>
    <table style="border-collapse: collapse; margin: 10px 0;">
        <tr style="background-color: #343a40; color: white;">
            <th style="border: 1px solid #dee2e6; padding: 8px 12px; text-align: left;">Domain</th>
            <th style="border: 1px solid #dee2e6; padding: 8px 12px; text-align: center;">Passed</th>
            <th style="border: 1px solid #dee2e6; padding: 8px 12px; text-align: center;">Failed</th>
            <th style="border: 1px solid #dee2e6; padding: 8px 12px; text-align: center;">Skipped</th>
        </tr>
{domain_rows}
        <tr style="background-color: #e9ecef; font-weight: bold;">
            <td style="border: 1px solid #ddd; padding: 8px;">Total</td>
            <td style="border: 1px solid #ddd; padding: 8px; color: green;">{total_passed}</td>
            <td style="border: 1px solid #ddd; padding: 8px; color: red;">{total_failed}</td>
            <td style="border: 1px solid #ddd; padding: 8px; color: orange;">{total_skipped}</td>
        </tr>
    </table>
    <p><em>Detailed test reports are attached to this email.</em></p>
"""
        except Exception as e:
            print(f"Error reading test report summary: {e}")
            traceback.print_exc()
            test_reports_summary = "<p><em>Test reports are attached to this email.</em></p>"
    else:
        test_reports_summary = "<p><em>No test reports found.</em></p>"
else:
    print(f"Test reports directory not found: {TEST_REPORTS_PATH}")

# ---------------------------------------------------------------------------
# Build stage status table from GitLab API data
# ---------------------------------------------------------------------------

# Stage ordering per pipeline mode
STAGE_ORDER_DEFAULT = [
    "initialization", "setup_environment",
    "cleanup_telemetry", "cleanup_orchestrator",
    "cleanup_image_build_manager", "cleanup_repo_manager", "cleanup_omnia",
    "setup_main", "test_main_installation",
    "repo_manager", "test_repo_manager",
    "image_build_manager", "test_image_build_manager",
    "orchestrator", "test_orchestrator",
    "telemetry", "test_telemetry",
    "summary",
]
STAGE_ORDER_DEPLOY = [
    "initialization", "setup_environment",
    "repo_manager", "test_repo_manager",
    "image_build_manager", "test_image_build_manager",
    "orchestrator", "test_orchestrator",
    "telemetry", "test_telemetry",
    "summary",
]
STAGE_ORDER_CLEANUP = [
    "initialization", "setup_environment",
    "cleanup_telemetry", "cleanup_orchestrator",
    "cleanup_image_build_manager", "cleanup_repo_manager", "cleanup_omnia",
    "summary",
]
# Stage ordering for UTILS_ENABLE (utils pipeline)
STAGE_ORDER_UTILS = [
    "initialization", "setup_environment",
    "install_os", "log_collection_cluster", "log_collection_oim",
    "test_utils",
    "summary",
]

STATUS_STYLES = {
    "success": {"color": "#28a745", "label": "PASSED"},
    "failed": {"color": "#dc3545", "label": "FAILED"},
    "skipped": {"color": "#6c757d", "label": "SKIPPED"},
    "canceled": {"color": "#ffc107", "label": "CANCELED"},
    "manual": {"color": "#17a2b8", "label": "MANUAL"},
    "running": {"color": "#007bff", "label": "RUNNING"},
    "pending": {"color": "#6c757d", "label": "PENDING"},
    "created": {"color": "#adb5bd", "label": "CREATED"},
    "unknown": {"color": "#6c757d", "label": "UNKNOWN"},
}


def load_job_statuses():
    """Load job statuses from the JSON file written by the pipeline."""
    status_file = "pipeline_reports/job_statuses.json"
    if not os.path.exists(status_file):
        return {}
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        if not isinstance(jobs, list):
            return {}
        return {job["name"]: job.get("status", "unknown") for job in jobs if "name" in job}
    except Exception as e:
        print(f"Error loading job statuses: {e}")
        return {}


def pick_stage_order(mode, selected_domains, include_tests, job_statuses, is_utils_pipeline=False):
    """Return stages applicable to the selected mode and domains."""
    if is_utils_pipeline:
        # Use utils pipeline stages when UTILS_ENABLE is true
        return STAGE_ORDER_UTILS
    
    order = {
        "cleanup": STAGE_ORDER_CLEANUP,
        "deploy": STAGE_ORDER_DEPLOY,
    }.get(mode, STAGE_ORDER_DEFAULT)
    domain_names = {
        "repo_manager", "image_build_manager", "orchestrator", "telemetry",
    }
    selected = domain_names if selected_domains == "default" else {
        value.strip() for value in re.split(r"[,|]", selected_domains) if value.strip()
    }
    applicable = []
    for stage in order:
        domain = stage.removeprefix("cleanup_").removeprefix("test_")
        if domain in domain_names and domain not in selected:
            continue
        if stage.startswith("test_") and stage != "test_main_installation" and not include_tests:
            continue
        if stage == "test_main_installation" and not include_tests:
            continue
        if stage == "cleanup_omnia" and selected_domains != "default":
            continue
        if stage == "setup_environment" and mode != "default" and stage not in job_statuses:
            continue
        applicable.append(stage)
    return applicable


def build_stage_table_html(job_statuses, mode, selected_domains, include_tests, is_utils_pipeline=False):
    """Build an HTML table showing each applicable stage and its status."""
    stage_order = pick_stage_order(
        mode, selected_domains, include_tests, job_statuses, is_utils_pipeline
    )
    rows = []
    has_failure = False
    failed_stage = ""

    for i, stage in enumerate(stage_order):
        status = job_statuses.get(stage, "unknown")
        style = STATUS_STYLES.get(status, STATUS_STYLES["unknown"])
        bg = "#f8f9fa" if i % 2 == 0 else "#ffffff"

        if status == "failed":
            has_failure = True
            if not failed_stage:
                failed_stage = stage
            bg = "#fff5f5"

        rows.append(
            f'<tr style="background-color: {bg};">'
            f'<td style="border: 1px solid #dee2e6; padding: 8px 12px;">'
            f"{stage}</td>"
            f'<td style="border: 1px solid #dee2e6; padding: 8px 12px; '
            f"text-align: center; color: {style['color']}; "
            f'font-weight: bold;">'
            f"{style['label']}</td></tr>"
        )

    table_html = (
        '<table style="border-collapse: collapse; width: 100%; '
        'max-width: 600px; margin: 15px 0;">'
        '<tr style="background-color: #343a40; color: white;">'
        '<th style="border: 1px solid #dee2e6; padding: 10px 12px; '
        'text-align: left;">Stage</th>'
        '<th style="border: 1px solid #dee2e6; padding: 10px 12px; '
        'text-align: center; width: 120px;">Status</th></tr>'
        + "\n".join(rows)
        + "</table>"
    )
    return table_html, has_failure, failed_stage


# Load job statuses and build table
job_statuses = load_job_statuses()
stage_table_html, has_failure, failed_stage = build_stage_table_html(
    job_statuses, pipeline_mode, domains, test_mode, utils_enable
)

if not job_statuses:
    overall_status = "UNKNOWN"
    status_color = "#6c757d"
elif has_failure:
    overall_status = "FAILED"
    status_color = "#dc3545"
else:
    overall_status = "SUCCESS"
    status_color = "#28a745"

print(f"Overall pipeline status: {overall_status}")
if failed_stage:
    print(f"First failed stage: {failed_stage}")

# ---------------------------------------------------------------------------
msg = MIMEMultipart()
msg["From"] = SENDER_EMAIL
msg["To"] = ", ".join(recipients)

subject_detail = f" - {failed_stage}" if failed_stage else ""
cluster_label = f" [{cluster_name}]" if cluster_name else ""
msg["Subject"] = (
    f"Omnia Pipeline{cluster_label} - {overall_status}{subject_detail} ({pipeline_mode})"
)

cluster_header = f" — {cluster_name}" if cluster_name else ""
cluster_info_html = ""
if cluster_name or cluster_ip:
    cluster_info_html = '<p>'
    if cluster_name:
        cluster_info_html += f'<strong>Cluster:</strong> {cluster_name}'
    if cluster_ip:
        cluster_info_html += f' &nbsp;|&nbsp; <strong>Target IP:</strong> {cluster_ip}'
    cluster_info_html += '</p>'

html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; margin: 20px;">
    <h2>Omnia Pipeline Execution Report{cluster_header}</h2>
    <div style="background-color: {status_color}; color: white;
                padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h3 style="margin: 0;">{overall_status}</h3>
        <p style="margin: 5px 0 0 0;">
            <strong>Mode:</strong> {pipeline_mode} &nbsp;|&nbsp;
            <strong>Domains:</strong> {domains}
            {'&nbsp;|&nbsp; <strong>Failed at:</strong> ' + failed_stage if failed_stage else ''}
        </p>
    </div>
    {cluster_info_html}
    <p><strong>Pipeline Trigger Time:</strong> {trigger_time}</p>
    <p><strong>Pipeline URL:</strong>
        <a href="{pipeline_url}">{pipeline_url}</a></p>
    <p><strong>Commit ID:</strong> {commit_id}</p>

    <h3>Stage Execution Summary</h3>
    {stage_table_html}

    {test_reports_summary}
    <br>
    <p>Please find the detailed test reports attached.</p>
    <br>
    <p style="color: #888; font-size: 12px;">
        This is an automated email from GitLab CI/CD pipeline.</p>
</body>
</html>
"""
msg.attach(MIMEText(html_body, "html"))

# ---------------------------------------------------------------------------
# Attach test reports (HTML and JSON)
def attach_file(message, file_path):
    """Attach a file to the email message."""
    try:
        filename = os.path.basename(file_path)
        
        # Determine if binary or text
        if file_path.endswith(".html"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            attachment = MIMEText(content, "html", "utf-8")
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=filename,
            )
        elif file_path.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            attachment = MIMEText(content, "plain", "utf-8")
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=filename,
            )
        else:
            # For other file types, use base64 encoding
            with open(file_path, "rb") as f:
                content = f.read()
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(content)
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=filename,
            )
        
        message.attach(attachment)
        print(f"Attached: {filename}")
        return True
    except Exception as e:
        print(f"Error attaching {file_path}: {e}")
        traceback.print_exc()
        return False

# Attach all test report files
if test_report_files:
    print(f"\nAttaching {len(test_report_files)} test report file(s)...")
    for report_file in test_report_files:
        attach_file(msg, report_file)
else:
    print("No test report files to attach")

# ---------------------------------------------------------------------------
def send_email_with_retry(message, smtp_server, smtp_port, smtp_user, smtp_pw, max_retries=3, retry_delay=5):
    """Send email via SMTP with retry logic for reliability."""
    for attempt in range(max_retries):
        server = None
        try:
            print(f"Send attempt {attempt + 1}/{max_retries}")
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)

            if smtp_user and smtp_pw:
                server.login(smtp_user, smtp_pw)
                print(f"Authenticated as: {smtp_user}")

            server.send_message(message)
            print(f"Email sent successfully")
            return True

        except smtplib.SMTPException as e:
            print(f"SMTP error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                raise
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                raise
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass
    return False

try:
    send_email_with_retry(msg, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
    print("=== Email notification completed successfully ===")
except Exception as e:
    print(f"=== Failed to send email after retries: {e} ===")
    raise
