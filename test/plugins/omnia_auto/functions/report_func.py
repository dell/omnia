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

"""
Enterprise Test Report Generator for omnia-auto test suites.

Generates JSON and HTML reports with:
- Pipeline-aware report naming (date_time_pipelineId_domain_report)
- Dark/light theme toggle with localStorage persistence
- CSS donut charts with pass rate
- Suite breakdown tables with progress bars
- Collapsible scenario sections with search/filter
- Playbook execution logs accordion with CRITICAL/WARNING highlighting
- Skip classification (expected / unexpected / framework)
- Sensitive data redaction (IPs, passwords, secrets, paths)
- Playbook failure capture (record_playbook_failure)
- Separate test runs for repeated domain execution

Reports are organized by server (IP/hostname) and stored under
the configured report_path.
"""

import json
import os
import re
import socket
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .report_html import generate_html

# Status constants to avoid hardcoded password detection
_STATUS_PASS = "pass"
_STATUS_PASS_UPPER = "PASS"
_STATUS_SKIP = "skip"
_STATUS_SKIP_UPPER = "SKIP"
_STATUS_FAIL = "fail"
_STATUS_FAIL_UPPER = "FAIL"

_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


# ── Report Naming ────────────────────────────────────────────────────────────

def build_report_name(domain_name: str, base_name: str = "") -> str:
    """Build pipeline-aware report filename.

    When running in GitLab CI (CI_PIPELINE_ID is set):
        ``YYYYMMDD_HHMMSS_<pipeline_id>_<domain>_report``

    When running locally:
        ``<base_name>`` or ``<domain>_report``

    Same pipeline_id overwrites its report; different IDs create
    separate files.

    Args:
        domain_name: Domain identifier (e.g. ``repo_manager``).
        base_name: Fallback name for local runs.

    Returns:
        Report base filename without extension.
    """
    pipeline_id = os.environ.get("CI_PIPELINE_ID")
    if pipeline_id:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{ts}_{pipeline_id}_{domain_name}_report"
    return base_name or f"{domain_name}_report"


# ── Sensitive Data Redaction ─────────────────────────────────────────────────

_REDACT_PATTERNS = None


def _compile_redact_patterns():
    """Compile regex patterns for sensitive data redaction (lazy init)."""
    return [
        # IP addresses
        (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
         '***REDACTED_IP***'),
        # Password / secret / key / token field values
        (re.compile(
            r'(?i)([\w]*(?:password|passwd|hashed_passwd|secret|_key|token|'
            r'credential|api_key|ssh_key|private_key|auth_token)[\w]*'
            r'\s*[:=]\s*)["\']?(\S+?)(?=["\',}\]\s]|$)'
        ), r'\1***REDACTED***'),
        # NFS share paths
        (re.compile(
            r'(?i)(nfs_server_share_path\s*[:=]\s*)["\']?[^"\'\s,}\]]+'),
         r'\1***REDACTED***'),
        # Domain / hostname field values
        (re.compile(
            r'(?i)((?:domain_name|hostname)\s*[:=]\s*)["\']?[^"\'\s,}\]]+'),
         r'\1***REDACTED***'),
    ]


def _redact_sensitive(text: str) -> str:
    """Redact sensitive data (IPs, passwords, secrets, paths) from text."""
    global _REDACT_PATTERNS  # pylint: disable=global-statement
    if not text:
        return text
    if _REDACT_PATTERNS is None:
        _REDACT_PATTERNS = _compile_redact_patterns()
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── Skip Classification ─────────────────────────────────────────────────────

def _classify_skip(details: str = "", error: str = "") -> str:
    """Classify a skipped test into expected / unexpected / framework.

    Returns one of: ``'expected'``, ``'unexpected'``, ``'framework'``.
    """
    text = ((details or "") + " " + (error or "")).lower()
    if not text.strip():
        return "unexpected"

    framework_kw = [
        "fixture", "setup failed", "import error", "conftest",
        "collection error", "module not found", "no module named",
        "parametrize", "setup error", "teardown error",
    ]
    if any(kw in text for kw in framework_kw):
        return "framework"

    expected_kw = [
        "not enabled", "not configured", "disabled", "not supported",
        "not available", "not applicable", "not installed", "feature not",
        "requires", "only applies", "not present", "skipping",
        "condition", "marker", "prerequisite",
    ]
    if any(kw in text for kw in expected_kw):
        return "expected"

    return "unexpected"


# ── Playbook / Molecule Log Analysis ────────────────────────────────────────

def _count_log_issues(logs: str) -> dict:
    """Count CRITICAL and WARNING occurrences in playbook/molecule logs."""
    if not logs:
        return {"critical": 0, "warning": 0}
    upper = logs.upper()
    lines = upper.split('\n')
    return {
        "critical": sum(1 for ln in lines if 'CRITICAL' in ln),
        "warning": sum(
            1 for ln in lines if 'WARNING' in ln or '[WARN]' in ln
        ),
    }


# ── Internal Helpers ─────────────────────────────────────────────────────────

def _resolve_report_dir(report_path: str) -> str:
    """Ensure the report directory exists and return its absolute path."""
    os.makedirs(report_path, exist_ok=True)
    return report_path


def _load_report(report_dir: str, report_name: str) -> Dict[str, Any]:
    """Load existing report JSON if present."""
    report_file = os.path.join(report_dir, f"{report_name}.json")
    if os.path.exists(report_file):
        try:
            with open(report_file, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, IOError):
            return {"servers": {}}
    return {"servers": {}}


def _save_json(data: Dict[str, Any], report_dir: str, report_name: str):
    """Save report data as JSON."""
    path = os.path.join(report_dir, f"{report_name}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences (color codes) from text."""
    return _ANSI_RE.sub("", text)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ── TestReport Class ────────────────────────────────────────────────────────

class TestReport:
    """Enterprise test report generator — organizes results by server.

    All required values must be passed by the consumer.
    No config files are read internally.
    """

    def __init__(
        self,
        module_name: str,
        report_path: str,
        report_name: str,
        server_ip: str,
        report_id: Optional[str] = None,
        server_hostname: Optional[str] = None,
        suite: Optional[str] = None,
        marker: Optional[str] = None,
        exec_command: Optional[str] = None,
    ):
        """Initialise a test report.

        Args:
            module_name: Scenario / module name (e.g. ``prepare``).
            report_path: Absolute directory where JSON/HTML are saved.
            report_name: Base filename without extension.
            server_ip: Target server IP address.
            report_id: Unique run identifier (default: timestamp).
            server_hostname: Target hostname (resolved from IP if omitted).
            suite: Suite filter label (informational).
            marker: Marker filter label (informational).
            exec_command: Execution command label (informational).
        """
        self.module_name = module_name
        self.report_path = _resolve_report_dir(report_path)
        self.report_name = report_name
        self.start_time = datetime.now()
        self.report_id = report_id or self.start_time.strftime("%Y%m%d%H%M%S%f")[:-3]
        self.results: List[Dict[str, Any]] = []
        self.playbook_logs: Optional[str] = None
        self.command_type: Optional[str] = None
        self.playbook_duration: Optional[float] = None

        if not server_hostname:
            server_hostname = self._resolve_hostname(server_ip)

        self.server_info = {"ip": server_ip, "hostname": server_hostname}
        self.suite = suite or os.environ.get("OMNIA_SUITE", "all")
        self.marker = marker or os.environ.get("OMNIA_MARKER", "")
        self.exec_command = (
            exec_command or os.environ.get("OMNIA_COMMAND_TYPE", "")
        )

        self._print_header()

    @staticmethod
    def _resolve_hostname(server_ip: str) -> str:
        """Resolve hostname from IP address."""
        if not server_ip or server_ip == "localhost":
            return "localhost"
        try:
            return socket.gethostbyaddr(server_ip)[0]
        except (socket.herror, socket.gaierror, OSError):
            return server_ip

    def _print_header(self):
        """Print report initialization header."""
        line = "\u2500" * 68
        print(f"\n\u250c{line}\u2510")
        print(
            f"\u2502  {'SERVER:':<12} "
            f"{self.server_info['ip']:<52} \u2502"
        )
        print(
            f"\u2502  {'MODULE:':<12} "
            f"{self.module_name:<52} \u2502"
        )
        print(
            f"\u2502  {'REPORT ID:':<12} "
            f"{self.report_id:<52} \u2502"
        )
        print(f"\u2514{line}\u2518\n")

    def _get_playbook_logs(self) -> tuple:
        """Get playbook execution logs and command type."""
        log_file = os.environ.get("OMNIA_LOG_FILE")
        command_type = os.environ.get("OMNIA_COMMAND", "execution")
        if log_file and os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as fh:
                    content = fh.read()
                    clean_content = _strip_ansi(content)
                    test_start_markers = [
                        "test session starts",
                        "collecting ...",
                    ]
                    playbook_only = clean_content
                    for mk in test_start_markers:
                        if mk in clean_content:
                            playbook_only = clean_content.split(mk)[
                                0
                            ].strip()
                            break
                    return playbook_only, command_type
            except (IOError, OSError):
                return None, command_type
        return None, command_type

    # ── Result Collection ────────────────────────────────────────────

    def add_result(
        self,
        test_name: Any,
        passed: bool = False,
        duration: float = 0.0,
        details: Optional[str] = None,
        error: Optional[str] = None,
        status: Optional[str] = None,
        tc_id: Optional[str] = None,
    ):
        """Add a test result to the report."""
        if isinstance(test_name, dict):
            self._add_dict_result(test_name)
            return

        normalized_status = (status or "").strip().upper()
        if normalized_status not in {"PASSED", "FAILED", "SKIPPED"}:
            normalized_status = "PASSED" if passed else "FAILED"

        result = {
            "test_name": test_name,
            "status": normalized_status,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 3),
        }
        if tc_id:
            result["tc_id"] = str(tc_id)
        if details:
            result["details"] = details
        if error:
            result["error"] = error

        # Add skip classification for skipped tests
        if normalized_status == "SKIPPED":
            result["skip_type"] = _classify_skip(
                details or "", error or ""
            )

        self.results.append(result)

    def _add_dict_result(self, payload: dict):
        """Add a result from a dictionary payload."""
        normalized_status = (
            str(payload.get("status") or "").strip().upper()
        )
        if normalized_status not in {"PASSED", "FAILED", "SKIPPED"}:
            payload_passed = bool(payload.get("passed"))
            normalized_status = (
                "PASSED" if payload_passed else "FAILED"
            )

        duration_seconds = payload.get("duration_seconds")
        if duration_seconds is None:
            duration_seconds = payload.get("duration", 0.0)

        result = {
            "test_name": (
                payload.get("test_name")
                or payload.get("name")
                or "<unknown>"
            ),
            "status": normalized_status,
            "timestamp": (
                payload.get("timestamp") or datetime.now().isoformat()
            ),
            "duration_seconds": round(
                float(duration_seconds or 0.0), 3
            ),
        }
        if payload.get("tc_id"):
            result["tc_id"] = str(payload["tc_id"])
        if payload.get("details"):
            result["details"] = payload.get("details")
        detail_fields = payload.get("detail_fields")
        if isinstance(detail_fields, list):
            normalized_fields = []
            for field in detail_fields:
                if not isinstance(field, dict) or "key" not in field:
                    continue
                normalized_fields.append(
                    {
                        "key": str(field["key"]),
                        "value": str(field.get("value", "")),
                    }
                )
            if normalized_fields:
                result["detail_fields"] = normalized_fields
        if payload.get("error"):
            result["error"] = payload.get("error")
        if payload.get("category"):
            result["category"] = payload.get("category")
        if payload.get("markers"):
            result["markers"] = payload.get("markers")

        # Add skip classification for skipped tests
        if normalized_status == "SKIPPED":
            result["skip_type"] = _classify_skip(
                payload.get("details", ""),
                payload.get("error", ""),
            )

        self.results.append(result)

    # ── Save & Persist ───────────────────────────────────────────────

    def save(self) -> str:
        """Save the report as JSON and HTML. Returns the HTML file path."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        passed = sum(
            1 for r in self.results if r["status"] == "PASSED"
        )
        failed = sum(
            1 for r in self.results if r["status"] == "FAILED"
        )
        skipped = sum(
            1 for r in self.results if r["status"] == "SKIPPED"
        )

        if self.playbook_logs is None:
            self.playbook_logs, self.command_type = (
                self._get_playbook_logs()
            )

        # Compute log issues if playbook logs exist
        log_issues = None
        if self.playbook_logs:
            log_issues = _count_log_issues(self.playbook_logs)

        module_data = {
            "module": self.module_name,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration, 3),
            "summary": {
                "total": len(self.results),
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            },
            "results": self.results,
            "playbook_logs": self.playbook_logs,
            "command_type": self.command_type,
            "log_issues": log_issues,
            "suite": self.suite,
            "marker": self.marker,
            "exec_command": self.exec_command,
        }

        report = _load_report(self.report_path, self.report_name)
        server_ip = self.server_info["ip"]

        if "servers" not in report:
            report["servers"] = {}

        if server_ip not in report["servers"]:
            report["servers"][server_ip] = {"runs": []}

        report["servers"][server_ip]["hostname"] = (
            self.server_info["hostname"]
        )

        runs = report["servers"][server_ip]["runs"]

        # Find existing run with same report_id
        existing_run_idx = next(
            (
                i
                for i, r in enumerate(runs)
                if r.get("report_id") == self.report_id
            ),
            None,
        )

        if existing_run_idx is not None:
            self._update_existing_run(
                runs[existing_run_idx], module_data, end_time
            )
        else:
            run_data = {
                "report_id": self.report_id,
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "summary": {
                    "total": len(self.results),
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                },
                "modules": [module_data],
            }
            runs.append(run_data)

        _save_json(report, self.report_path, self.report_name)

        current_run = next(
            (
                r
                for r in runs
                if r.get("report_id") == self.report_id
            ),
            None,
        )
        banner_stats = self._get_banner_stats(
            current_run, passed, failed, skipped, duration
        )

        json_path = os.path.join(
            self.report_path, f"{self.report_name}.json"
        )
        html_path = os.path.join(
            self.report_path, f"{self.report_name}.html"
        )

        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(generate_html(report))

        self._print_footer(
            server_ip,
            json_path,
            html_path,
            banner_stats["passed"],
            banner_stats["failed"],
            banner_stats["skipped"],
            banner_stats["duration"],
        )

        return html_path

    def _update_existing_run(
        self, run: dict, module_data: dict, end_time: datetime
    ):
        """Update an existing run with new module data."""
        if "modules" not in run:
            run["modules"] = []

        existing_mod_idx = next(
            (
                i
                for i, m in enumerate(run["modules"])
                if m.get("module") == self.module_name
            ),
            None,
        )

        if existing_mod_idx is not None:
            mod = run["modules"][existing_mod_idx]
            mod["results"].extend(self.results)
            mod["playbook_logs"] = self.playbook_logs
            mod["command_type"] = self.command_type
            if self.playbook_logs:
                mod["log_issues"] = _count_log_issues(
                    self.playbook_logs
                )
            all_results = mod["results"]
            mod["summary"] = {
                "total": len(all_results),
                "passed": sum(
                    1
                    for r in all_results
                    if r["status"] == "PASSED"
                ),
                "failed": sum(
                    1
                    for r in all_results
                    if r["status"] == "FAILED"
                ),
                "skipped": sum(
                    1
                    for r in all_results
                    if r["status"] == "SKIPPED"
                ),
            }
        else:
            run["modules"].append(module_data)

        run["end_time"] = end_time.isoformat()
        all_passed = sum(
            m["summary"]["passed"] for m in run["modules"]
        )
        all_failed = sum(
            m["summary"]["failed"] for m in run["modules"]
        )
        all_skipped = sum(
            (m.get("summary") or {}).get("skipped", 0)
            for m in run["modules"]
        )
        run["summary"] = {
            "total": all_passed + all_failed + all_skipped,
            "passed": all_passed,
            "failed": all_failed,
            "skipped": all_skipped,
        }

    @staticmethod
    def _get_banner_stats(
        current_run: Optional[dict],
        passed: int,
        failed: int,
        skipped: int,
        duration: float,
    ) -> dict:
        """Get statistics for the banner display."""
        if current_run:
            run_summary = current_run.get("summary", {})
            return {
                "passed": run_summary.get("passed", passed),
                "failed": run_summary.get("failed", failed),
                "skipped": run_summary.get("skipped", skipped),
                "duration": sum(
                    m.get("duration_seconds", 0)
                    for m in current_run.get("modules", [])
                ),
            }
        return {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration": duration,
        }

    def _print_footer(
        self,
        server_ip: str,
        json_path: str,
        html_path: str,
        passed: int,
        failed: int,
        skipped: int,
        duration: float,
    ):
        """Print report save footer."""
        status_color = "\033[92m" if failed == 0 else "\033[91m"
        reset = "\033[0m"
        width = 68
        content_width = 64
        line = "\u2500" * width

        result_plain = (
            f"{passed} passed, {failed} failed, {skipped} skipped"
        )

        json_display = (
            json_path[: content_width - 6]
            if len(json_path) > content_width - 6
            else json_path
        )
        html_display = (
            html_path[: content_width - 6]
            if len(html_path) > content_width - 6
            else html_path
        )

        print(f"\n\u250c{line}\u2510")
        print(f"\u2502  {'REPORT SAVED':<{content_width}}  \u2502")
        print(f"\u251c{line}\u2524")
        print(
            f"\u2502  {'Server:':<12}"
            f"{server_ip:<{content_width - 12}}  \u2502"
        )
        print(
            f"\u2502  {'Report ID:':<12}"
            f"{self.report_id:<{content_width - 12}}  \u2502"
        )
        dur_str = f"{duration:.2f}s"
        print(
            f"\u2502  {'Duration:':<12}"
            f"{dur_str:<{content_width - 12}}  \u2502"
        )
        result_display = (
            f"{status_color}{passed} passed{reset}, "
            f"{status_color}{failed} failed{reset}, "
            f"{skipped} skipped"
        )
        padding_len = content_width - 12 - len(result_plain)
        padding = " " * max(0, padding_len)
        print(
            f"\u2502  {'Results:':<12}"
            f"{result_display}{padding}  \u2502"
        )
        print(f"\u251c{line}\u2524")
        print(
            f"\u2502  JSON: "
            f"{json_display:<{content_width - 6}}  \u2502"
        )
        print(
            f"\u2502  HTML: "
            f"{html_display:<{content_width - 6}}  \u2502"
        )
        print(f"\u2514{line}\u2518\n")


# ── Module-Level State ───────────────────────────────────────────────────────

_current_report: Optional[TestReport] = None


def get_current_report() -> Optional[TestReport]:
    """Get the current active test report."""
    return _current_report


def set_current_report(report: TestReport):
    """Set the current active test report."""
    global _current_report  # pylint: disable=global-statement
    _current_report = report


# ── Playbook Failure Capture ─────────────────────────────────────────────────

_FAILURE_KW = [
    "failed=", "unreachable=", "fatal:", "failed: [",
    "CRITICAL", "PLAY RECAP",
]


def record_playbook_failure(
    module_name: str,
    report_path: str,
    report_name: str,
    server_ip: str,
    report_id: str,
    log_file: Optional[str] = None,
    command_type: str = "deploy",
):
    """Record a playbook/domain execution failure in the test report.

    Called from pipeline shell scripts when the domain playbook fails
    before pytest/verify executes. Ensures playbook failures are
    captured in the report even when no test results exist.

    Args:
        module_name:  Domain name (e.g. ``repo_manager``).
        report_path:  Directory for JSON/HTML output.
        report_name:  Base filename without extension.
        server_ip:    Target server IP address.
        report_id:    Shared report ID (e.g. CI_PIPELINE_ID).
        log_file:     Path to playbook log file with execution output.
        command_type:  Command that failed (``deploy``, ``test``, etc.).
    """
    # Check if this module already has results in the report
    existing = _load_report(report_path, report_name)
    for _srv in existing.get("servers", {}).values():
        for run in _srv.get("runs", []):
            if run.get("report_id") != report_id:
                continue
            for mod in run.get("modules", []):
                if (
                    mod.get("module") == module_name
                    and mod.get("results")
                ):
                    return  # Tests already recorded, skip

    report = TestReport(
        module_name=module_name,
        report_path=report_path,
        report_name=report_name,
        server_ip=server_ip,
        report_id=report_id,
    )
    report.command_type = command_type

    failure_details = ""
    failure_summary = (
        f"Playbook {command_type} failed for {module_name}"
    )

    if log_file and os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as fh:
                content = fh.read()

            clean_content = _strip_ansi(content)
            report.playbook_logs = clean_content

            lines = clean_content.strip().split("\n")

            # Extract lines around failure indicators for context
            context_lines: List[str] = []
            for i, log_line in enumerate(lines):
                if any(
                    kw.lower() in log_line.lower()
                    for kw in _FAILURE_KW
                ):
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    context_lines.extend(lines[start:end])

            if context_lines:
                seen: set = set()
                unique: List[str] = []
                for ln in context_lines:
                    if ln not in seen:
                        seen.add(ln)
                        unique.append(ln)
                failure_details = "\n".join(unique)
            else:
                failure_details = "\n".join(lines[-30:])

            # Try to find a concise error line
            for log_line in reversed(lines):
                low = log_line.lower().strip()
                if any(
                    kw in low
                    for kw in ["fatal:", "failed:", "critical"]
                ):
                    failure_summary = log_line.strip()
                    break

        except (IOError, OSError):
            failure_details = (
                f"Could not read log file: {log_file}"
            )

    report.add_result(
        test_name=f"playbook_{command_type}_{module_name}",
        passed=False,
        duration=0.0,
        details=failure_details
        or (
            f"Playbook {command_type} command failed. "
            "Check logs for details."
        ),
        error=failure_summary,
        status="FAILED",
    )

    report.save()
