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


"""Constants of the pipeline summary email (library/functions/email_func.py)."""

# An attached report larger than this is gzip-compressed.
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024

# Seconds allowed for the SMTP conversation.
SMTP_TIMEOUT = 60

# The attachments of one mail together stay below this size (most mail servers refuse more); the
# largest ones are left out and named in the mail, they stay in the job artifacts.
MAX_MESSAGE_BYTES = 20 * 1024 * 1024

# Status of a job (GitLab CI_JOB_STATUS): (label, colour).
STATUS_STYLES = {
    "success": ("PASSED", "#198754"),
    "failed": ("FAILED", "#dc3545"),
    "canceled": ("CANCELED", "#6c757d"),
    "skipped": ("NOT RUN", "#6c757d"),
    "running": ("RUNNING", "#0d6efd"),
}
UNKNOWN_STYLE = ("NOT RUN", "#6c757d")

# Verdict -> banner colour.
# GitLab job statuses that make the verdict FAILED (a timeout is a failed job with a failure reason).
FAILED_STATUSES = ("failed", "canceled", "canceling")
VERDICT_COLORS = {"PASSED": "#198754", "FAILED": "#dc3545", "UNKNOWN": "#6c757d"}
