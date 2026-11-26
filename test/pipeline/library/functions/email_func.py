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


"""The pipeline summary email, in the layout of the SVT email: a verdict banner, a run details
table with links to the repository, branch, commit and pipeline, what failed and what did not
run, one row per job with a link to its log, and the test reports attached.

``build_message`` is a pure function (testable); ``send_message`` does the SMTP part (SSL on
465, STARTTLS on 587, login only when a user and a password are set).
"""

import gzip
import html
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Sequence, Tuple

from ..vars.email_vars import (
    FAILED_STATUSES,
    MAX_ATTACHMENT_BYTES,
    MAX_MESSAGE_BYTES,
    SMTP_TIMEOUT,
    STATUS_STYLES,
    UNKNOWN_STYLE,
    VERDICT_COLORS,
)

Job = Tuple[str, str, str]
CELL = "padding:6px 10px;border:1px solid #dee2e6;font-size:13px"
HEAD = f"{CELL};background:#f1f3f5;text-align:left"


def web_base(repo: str) -> str:
    """Return the https web address of a git remote ("" when it cannot be derived)."""
    if repo.startswith("git@") and ":" in repo:
        host, path = repo[4:].split(":", 1)
        repo = f"https://{host}/{path}"
    if not repo.startswith("https://") and not repo.startswith("http://"):
        return ""
    return repo[:-4] if repo.endswith(".git") else repo.rstrip("/")


def anchor(url: str, text: str) -> str:
    """Return a link, or the escaped text when the url is not an http(s) address."""
    if not url.startswith(("https://", "http://")):
        return html.escape(text)
    return f"<a href='{html.escape(url, quote=True)}' style='color:#0b5ed7'>{html.escape(text)}</a>"


def button(url: str, text: str, color: str = "#0b5ed7") -> str:
    if not url.startswith(("https://", "http://")):
        return ""
    return (f"<a href='{html.escape(url, quote=True)}' style='display:inline-block;margin:0 8px "
            f"8px 0;padding:8px 14px;background:{color};color:#fff;text-decoration:none;"
            f"border-radius:4px;font-size:13px'>{html.escape(text)}</a>")


def status_cell(status: str) -> str:
    label, color = STATUS_STYLES.get(status, UNKNOWN_STYLE)
    return f"<b style='color:{color}'>{label}</b>"


def verdict_of(jobs: Sequence[Job]) -> str:
    if not jobs:
        return "UNKNOWN"
    return "FAILED" if any(status in FAILED_STATUSES for _, status, _ in jobs) else "PASSED"


def not_run(order: Sequence[str], jobs: Sequence[Job]) -> List[str]:
    """Jobs that did not run: GitLab skipped them, or (no status at all) they follow the first
    failed job of the order."""
    seen = {name: status for name, status, _ in jobs}
    failed = [i for i, name in enumerate(order) if seen.get(name) == "failed"]
    after = order[failed[0] + 1:] if failed else []
    return [name for name in order if seen.get(name) == "skipped"
            or (name in after and name not in seen)]


def fit_attachments(attachments: Sequence[Tuple[str, bytes]], limit: int = MAX_MESSAGE_BYTES
                    ) -> Tuple[List[Tuple[str, bytes]], List[str]]:
    """Return (attachments that fit, names left out): the largest go first until the mail fits.

    The size is what travels: a part over MAX_ATTACHMENT_BYTES is gzip-compressed, and base64
    makes everything a third bigger.
    """
    def weight(item: Tuple[str, bytes]) -> int:
        size = len(gzip.compress(item[1])) if len(item[1]) > MAX_ATTACHMENT_BYTES else len(item[1])
        return size * 4 // 3

    kept = list(attachments)
    dropped: List[str] = []
    while kept and sum(weight(item) for item in kept) > limit:
        largest = max(kept, key=weight)
        kept.remove(largest)
        dropped.append(largest[0])
    return kept, dropped


def build_message(*, sender: str, recipients: Sequence[str], info: Dict[str, str],
                  jobs: Sequence[Job], order: Sequence[str],
                  attachments: Sequence[Tuple[str, bytes]] = (),
                  reasons: Optional[Dict[str, str]] = None) -> MIMEMultipart:
    """Build the summary email.

    Args:
        info: cluster, mode, domains, repo, branch, commit, pipeline_url, job_url, trigger_time.
        jobs: (job name, status, job url) of every job that left a status.
        order: the job names in pipeline order (rows of the table).
        attachments: (file name, content) of the test reports.
        reasons: {job: why it failed}, shown under the failed job.
    """
    reasons = reasons or {}
    attachments, left_out = fit_attachments(attachments)
    esc = html.escape
    verdict = verdict_of(jobs)
    color = VERDICT_COLORS[verdict]
    failed = [(n, u) for n, s, u in jobs if s == "failed"]
    skipped = not_run(order, jobs)
    by_name = {n: (s, u) for n, s, u in jobs}
    repo, branch, commit = info.get("repo", ""), info.get("branch", ""), info.get("commit", "")
    base = web_base(repo)
    branch_url = f"{base}/tree/{branch}" if base and branch else ""
    commit_url = f"{base}/commit/{commit}" if base and commit else ""
    pipeline_url = info.get("pipeline_url", "")
    cluster = info.get("cluster", "")
    rows = [("Cluster", esc(cluster or "-")), ("Mode", esc(info.get("mode", "-"))),
            ("Domains", esc(info.get("domains", "-"))),
            ("Repository", anchor(base, base or repo or "-")),
            ("Branch", anchor(branch_url, branch or "-")),
            ("Commit", anchor(commit_url, commit[:12]) if commit else "not checked out"),
            ("Started", esc(info.get("trigger_time", "-") or "-")),
            ("Pipeline", anchor(pipeline_url, pipeline_url or "-"))]
    info_rows = "".join(f"<tr><td style='{HEAD};width:110px'><b>{name}</b></td>"
                        f"<td style='{CELL}'>{value}</td></tr>" for name, value in rows)
    why = ""
    if failed:
        items = "".join(
            f"<li style='margin-bottom:6px'>{anchor(url, name)}"
            + (f"<br><span style='color:#842029'>{esc(reasons[name])}</span>"
               if reasons.get(name) else "") + "</li>" for name, url in failed)
        why = ("<div style='border-left:4px solid #dc3545;background:#fdf1f2;padding:10px 14px;"
               f"margin:16px 0'><b>Failed:</b><ul style='margin:6px 0 0 18px;padding:0'>{items}"
               "</ul>" + (f"<b>Did not run:</b> {len(skipped)} job(s), listed in the table below"
                          if skipped else "") + "</div>")
    table = "".join(
        f"<tr><td style='{CELL}'>{anchor(by_name[name][1], name)}</td>"
        f"<td style='{CELL}'>{status_cell(by_name[name][0])}</td></tr>"
        for name in order if name in by_name)
    buttons = button(pipeline_url, "Open the pipeline") + button(
        f"{info['job_url']}/artifacts/download" if info.get("job_url") else "",
        "Download all artifacts", "#6c757d")
    footer = ("The test reports are attached (open them in a browser)." if attachments
              else "No test report was attached: none was produced or it could not be fetched.")
    if left_out:
        footer += (" Too large for the mail, see the job artifacts: " + ", ".join(left_out) + ".")
    body = (
        "<html><body style='margin:0;padding:16px;background:#f8f9fa;"
        "font-family:Arial,Helvetica,sans-serif;color:#212529'>"
        "<table role='presentation' width='680' cellpadding='0' cellspacing='0' "
        "style='max-width:680px;margin:0 auto;background:#fff;border:1px solid #dee2e6'>"
        f"<tr><td style='background:{color};color:#fff;padding:16px 20px'>"
        "<div style='font-size:12px;opacity:.85'>Omnia FVT Pipeline</div>"
        f"<div style='font-size:20px;font-weight:bold'>{esc(cluster or 'cluster')}: {verdict}"
        "</div></td></tr><tr><td style='padding:16px 20px'>"
        f"<table cellpadding='0' cellspacing='0' style='border-collapse:collapse;width:100%'>"
        f"{info_rows}</table>{why}<p style='margin:16px 0 8px'>{buttons}</p>"
        "<h3 style='margin:18px 0 6px;font-size:15px'>Pipeline jobs</h3>"
        "<table cellpadding='0' cellspacing='0' style='border-collapse:collapse;width:100%'>"
        f"<tr><th style='{HEAD}'>Job</th><th style='{HEAD}'>Status</th></tr>{table}</table>"
        f"<p style='margin:16px 0 0;font-size:12px;color:#6c757d'>{footer}</p>"
        "</td></tr></table></body></html>")
    text = "\n".join([
        f"Omnia FVT Pipeline [{cluster}] {info.get('mode', '')}: {verdict}", "",
        f"Repository: {base or repo or '-'}", f"Branch:     {branch or '-'}  {branch_url}".rstrip(),
        f"Commit:     {commit[:12] or 'not checked out'}  {commit_url}".rstrip(),
        f"Pipeline:   {pipeline_url}", "",
        *([("Failed: " + ", ".join(n for n, _ in failed))] if failed else []),
        *[f"  {n}: {reasons[n]}" for n, _ in failed if reasons.get(n)],
        *([f"Did not run: {len(skipped)} job(s)"] if skipped else []), "", "Pipeline jobs:",
        *(f"  {name:<28} {'not run' if by_name[name][0] == 'skipped' else by_name[name][0]}"
          for name in order if name in by_name)])
    message = MIMEMultipart("mixed")
    message["From"], message["To"] = sender, ", ".join(recipients)
    names = f" ({', '.join(n for n, _ in failed)})" if failed else ""
    message["Subject"] = (f"Omnia FVT Pipeline [{cluster}] {info.get('mode', '')} - {verdict}{names}")
    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(text, "plain", "utf-8"))
    alternative.attach(MIMEText(body, "html", "utf-8"))
    message.attach(alternative)
    for name, content in attachments:
        if len(content) > MAX_ATTACHMENT_BYTES:
            part = MIMEApplication(gzip.compress(content), "gzip")
            name += ".gz"
        else:
            part = MIMEText(content.decode("utf-8", errors="replace"),
                            "html" if name.endswith(".html") else "plain", "utf-8")
        part.add_header("Content-Disposition", "attachment", filename=name)
        message.attach(part)
    return message


def send_message(message: MIMEMultipart, server: str, port: int, user: str = "",
                 password: Optional[str] = None) -> None:
    """Send the message; raises OSError or smtplib.SMTPException when it cannot be sent."""
    smtp_class = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
    with smtp_class(server, port, timeout=SMTP_TIMEOUT) as smtp:
        if port == 587:
            smtp.starttls(context=ssl.create_default_context())
        if user and password:
            smtp.login(user, password)
        smtp.send_message(message)
