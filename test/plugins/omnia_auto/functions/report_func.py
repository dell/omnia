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
Test Report Generator for omnia-auto test suites.

Generates JSON and HTML reports with:
- Dark/light theme toggle
- SVG donut charts with pass rate
- Scenario bar charts with hover tooltips
- Deploy/Verify section split
- Expandable test items with output and error details
- Server setup panel
- KPI cards

Reports are organized by server (IP/hostname) and stored under
the configured report_path.
"""

import json
import os
import re
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional

from .report_html import generate_html

_ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def _resolve_report_dir(report_path: str) -> str:
    """Ensure the report directory exists and return its absolute path."""
    os.makedirs(report_path, exist_ok=True)
    return report_path


def _load_report(report_dir: str, report_name: str) -> Dict[str, Any]:
    """Load existing report JSON if present."""
    report_file = os.path.join(report_dir, f"{report_name}.json")
    if os.path.exists(report_file):
        try:
            with open(report_file, 'r', encoding='utf-8') as fh:
                return json.load(fh)
        except (json.JSONDecodeError, IOError):
            return {"servers": {}}
    return {"servers": {}}


def _save_json(data: Dict[str, Any], report_dir: str, report_name: str):
    """Save report data as JSON."""
    path = os.path.join(report_dir, f"{report_name}.json")
    with open(path, "w", encoding='utf-8') as fh:
        json.dump(data, fh, indent=2, default=str)


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences (color codes) from text."""
    return _ANSI_RE.sub('', text)


class TestReport:
    """Test report generator — organizes results by server.

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
        self.report_id = report_id or datetime.now().strftime("%Y%m%d%H%M%S")
        self.start_time = datetime.now()
        self.results: List[Dict[str, Any]] = []
        self.playbook_logs: Optional[str] = None
        self.command_type: Optional[str] = None
        self.playbook_duration: Optional[float] = None

        if not server_hostname:
            server_hostname = self._resolve_hostname(server_ip)

        self.server_info = {"ip": server_ip, "hostname": server_hostname}
        self.suite = suite or os.environ.get("OMNIA_SUITE", "all")
        self.marker = marker or os.environ.get("OMNIA_MARKER", "")
        self.exec_command = exec_command or os.environ.get("OMNIA_COMMAND_TYPE", "")

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
        print(f"\u2502  {'SERVER:':<12} {self.server_info['ip']:<52} \u2502")
        print(f"\u2502  {'MODULE:':<12} {self.module_name:<52} \u2502")
        print(f"\u2502  {'REPORT ID:':<12} {self.report_id:<52} \u2502")
        print(f"\u2514{line}\u2518\n")

    def _get_playbook_logs(self) -> tuple:
        """Get playbook execution logs and command type."""
        log_file = os.environ.get('OMNIA_LOG_FILE')
        command_type = os.environ.get('OMNIA_COMMAND', 'execution')
        if log_file and os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                    clean_content = _strip_ansi(content)
                    test_start_markers = [
                        "test session starts",
                        "collecting ...",
                    ]
                    playbook_only = clean_content
                    for mk in test_start_markers:
                        if mk in clean_content:
                            playbook_only = clean_content.split(mk)[0].strip()
                            break
                    return playbook_only, command_type
            except (IOError, OSError):
                return None, command_type
        return None, command_type

    def add_result(
        self,
        test_name: Any,
        passed: bool = False,
        duration: float = 0.0,
        details: Optional[str] = None,
        error: Optional[str] = None,
        status: Optional[str] = None,
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
        if details:
            result["details"] = details
        if error:
            result["error"] = error
        self.results.append(result)

    def _add_dict_result(self, payload: dict):
        """Add a result from a dictionary payload."""
        normalized_status = str(payload.get("status") or "").strip().upper()
        if normalized_status not in {"PASSED", "FAILED", "SKIPPED"}:
            payload_passed = bool(payload.get("passed"))
            normalized_status = "PASSED" if payload_passed else "FAILED"

        duration_seconds = payload.get("duration_seconds")
        if duration_seconds is None:
            duration_seconds = payload.get("duration", 0.0)

        result = {
            "test_name": payload.get("test_name") or payload.get("name") or "<unknown>",
            "status": normalized_status,
            "timestamp": payload.get("timestamp") or datetime.now().isoformat(),
            "duration_seconds": round(float(duration_seconds or 0.0), 3),
        }
        if payload.get("details"):
            result["details"] = payload.get("details")
        if payload.get("error"):
            result["error"] = payload.get("error")
        if payload.get("category"):
            result["category"] = payload.get("category")
        if payload.get("markers"):
            result["markers"] = payload.get("markers")
        self.results.append(result)

    def save(self) -> str:
        """Save the report as JSON and HTML. Returns the HTML file path."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        passed = sum(1 for r in self.results if r["status"] == "PASSED")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        skipped = sum(1 for r in self.results if r["status"] == "SKIPPED")

        if self.playbook_logs is None:
            self.playbook_logs, self.command_type = self._get_playbook_logs()

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

        report["servers"][server_ip]["hostname"] = self.server_info["hostname"]

        runs = report["servers"][server_ip]["runs"]
        existing_run_idx = next(
            (i for i, r in enumerate(runs) if r.get("report_id") == self.report_id),
            None
        )

        if existing_run_idx is not None:
            self._update_existing_run(runs[existing_run_idx], module_data, end_time)
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
            (r for r in runs if r.get("report_id") == self.report_id),
            None,
        )
        banner_stats = self._get_banner_stats(
            current_run, passed, failed, skipped, duration
        )

        json_path = os.path.join(self.report_path, f"{self.report_name}.json")
        html_path = os.path.join(self.report_path, f"{self.report_name}.html")

        with open(html_path, 'w', encoding='utf-8') as fh:
            fh.write(generate_html(report))

        self._print_footer(
            server_ip, json_path, html_path,
            banner_stats["passed"], banner_stats["failed"],
            banner_stats["skipped"], banner_stats["duration"]
        )

        return html_path

    def _update_existing_run(self, run: dict, module_data: dict, end_time: datetime):
        """Update an existing run with new module data."""
        if "modules" not in run:
            run["modules"] = []

        existing_mod_idx = next(
            (i for i, m in enumerate(run["modules"])
             if m.get("module") == self.module_name),
            None
        )

        if existing_mod_idx is not None:
            mod = run["modules"][existing_mod_idx]
            mod["results"].extend(self.results)
            mod["playbook_logs"] = self.playbook_logs
            mod["command_type"] = self.command_type
            all_results = mod["results"]
            mod["summary"] = {
                "total": len(all_results),
                "passed": sum(1 for r in all_results if r["status"] == "PASSED"),
                "failed": sum(1 for r in all_results if r["status"] == "FAILED"),
                "skipped": sum(1 for r in all_results if r["status"] == "SKIPPED"),
            }
        else:
            run["modules"].append(module_data)

        run["end_time"] = end_time.isoformat()
        all_passed = sum(m["summary"]["passed"] for m in run["modules"])
        all_failed = sum(m["summary"]["failed"] for m in run["modules"])
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
        # Box width: 70 chars total (68 dashes + 2 corners)
        # Content: │ + 2 spaces + content (64 chars) + 2 spaces + │ = 70
        width = 68
        content_width = 64
        line = "\u2500" * width

        # Build result string without colors first for width calculation
        result_plain = f"{passed} passed, {failed} failed, {skipped} skipped"

        # Truncate paths if too long
        json_display = json_path[:content_width - 6] if len(json_path) > content_width - 6 else json_path
        html_display = html_path[:content_width - 6] if len(html_path) > content_width - 6 else html_path

        print(f"\n\u250c{line}\u2510")
        print(f"\u2502  {'REPORT SAVED':<{content_width}}  \u2502")
        print(f"\u251c{line}\u2524")
        print(f"\u2502  {'Server:':<12}{server_ip:<{content_width - 12}}  \u2502")
        print(f"\u2502  {'Report ID:':<12}{self.report_id:<{content_width - 12}}  \u2502")
        print(f"\u2502  {'Duration:':<12}{duration:.2f}s{'':<{content_width - 12 - len(f'{duration:.2f}s')}}  \u2502")
        # Use colored version but with pre-calculated padding
        result_display = (
            f"{status_color}{passed} passed{reset}, "
            f"{status_color}{failed} failed{reset}, "
            f"{skipped} skipped"
        )
        # Calculate visible length and add padding
        padding_len = content_width - 12 - len(result_plain)
        padding = " " * max(0, padding_len)
        print(f"\u2502  {'Results:':<12}{result_display}{padding}  \u2502")
        print(f"\u251c{line}\u2524")
        print(f"\u2502  JSON: {json_display:<{content_width - 6}}  \u2502")
        print(f"\u2502  HTML: {html_display:<{content_width - 6}}  \u2502")
        print(f"\u2514{line}\u2518\n")


_current_report: Optional[TestReport] = None


def get_current_report() -> Optional[TestReport]:
    """Get the current active test report."""
    return _current_report


def set_current_report(report: TestReport):
    """Set the current active test report."""
    global _current_report  # pylint: disable=global-statement
    _current_report = report
