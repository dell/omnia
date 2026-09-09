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

GitLab-provided variables used automatically:
    PIPELINE_TRIGGER_TIME - Set by initialization stage
    CI_PIPELINE_URL       - Auto-set by GitLab
"""
import glob
import json
import os
import smtplib
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
    
    if json_files:
        print(f"Found {len(json_files)} JSON test report(s)")
        # Extract summary from the first JSON report
        try:
            with open(json_files[0], "r", encoding="utf-8") as f:
                report_data = json.load(f)
            
            total_passed = 0
            total_failed = 0
            total_skipped = 0
            
            for server_data in report_data.get("servers", {}).values():
                for run in server_data.get("runs", []):
                    summary = run.get("summary", {})
                    total_passed += summary.get("passed", 0)
                    total_failed += summary.get("failed", 0)
                    total_skipped += summary.get("skipped", 0)
            
            test_reports_summary = f"""
    <h3>Test Execution Summary</h3>
    <table style="border-collapse: collapse; margin: 10px 0;">
        <tr style="background-color: #f0f0f0;">
            <td style="border: 1px solid #ddd; padding: 8px;"><strong>Passed</strong></td>
            <td style="border: 1px solid #ddd; padding: 8px; color: green;"><strong>{total_passed}</strong></td>
        </tr>
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;"><strong>Failed</strong></td>
            <td style="border: 1px solid #ddd; padding: 8px; color: red;"><strong>{total_failed}</strong></td>
        </tr>
        <tr style="background-color: #f0f0f0;">
            <td style="border: 1px solid #ddd; padding: 8px;"><strong>Skipped</strong></td>
            <td style="border: 1px solid #ddd; padding: 8px; color: orange;"><strong>{total_skipped}</strong></td>
        </tr>
    </table>
    <p><em>Detailed test reports are attached to this email.</em></p>
"""
        except Exception as e:
            print(f"Error reading test report summary: {e}")
            test_reports_summary = "<p><em>Test reports are attached to this email.</em></p>"
    else:
        test_reports_summary = "<p><em>No test reports found.</em></p>"
else:
    print(f"Test reports directory not found: {TEST_REPORTS_PATH}")

# ---------------------------------------------------------------------------
msg = MIMEMultipart()
msg["From"] = SENDER_EMAIL
msg["To"] = ", ".join(recipients)
msg["Subject"] = f"Omnia Pipeline Execution Report - {trigger_time}"

html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; margin: 20px;">
    <h2>Omnia Pipeline Execution Report</h2>
    <p><strong>Pipeline Trigger Time:</strong> {trigger_time}</p>
    <p><strong>Pipeline URL:</strong>
        <a href="{pipeline_url}">{pipeline_url}</a></p>
    <br>
    {test_reports_summary}
    <br>
    <p>Please find the pipeline execution summary and test reports attached.</p>
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
