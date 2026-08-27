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
Formatting utilities for omnia-auto test modules.

Contains:
- Colors: ANSI color codes for terminal output
- Symbols: Unicode symbols for status indicators
- log(): Simple timestamped logging
- TestLogger: Structured test output logger
"""

import os
import sys
from datetime import datetime


def _supports_color() -> bool:
    """Check if terminal supports ANSI colors."""
    if os.environ.get("NO_COLOR"):
        return False
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return False
    if os.environ.get("FORCE_COLOR") or os.environ.get("OMNIA_COMMAND_TYPE"):
        return True
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    return True


_USE_COLOR = _supports_color()


# =============================================================================
# ANSI COLOR CODES
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m" if _USE_COLOR else ""
    BOLD = "\033[1m" if _USE_COLOR else ""
    DIM = "\033[2m" if _USE_COLOR else ""

    RED = "\033[31m" if _USE_COLOR else ""
    GREEN = "\033[32m" if _USE_COLOR else ""
    YELLOW = "\033[33m" if _USE_COLOR else ""
    BLUE = "\033[34m" if _USE_COLOR else ""
    CYAN = "\033[36m" if _USE_COLOR else ""
    GRAY = "\033[90m" if _USE_COLOR else ""

    BRIGHT_RED = "\033[91m" if _USE_COLOR else ""
    BRIGHT_GREEN = "\033[92m" if _USE_COLOR else ""
    BRIGHT_YELLOW = "\033[93m" if _USE_COLOR else ""
    BRIGHT_BLUE = "\033[94m" if _USE_COLOR else ""
    BRIGHT_CYAN = "\033[96m" if _USE_COLOR else ""


# =============================================================================
# UNICODE SYMBOLS
# =============================================================================

class Symbols:
    """Unicode symbols for status indicators."""
    CHECK = "\u2714"
    CROSS = "\u2718"
    ARROW = "\u2192"
    SKIP = "\u21b7"
    TRIANGLE = "\u25b6"
    PIPE = "\u2502"


# =============================================================================
# LOGGING
# =============================================================================

_debug_mode = False
_verbose_mode = bool(os.environ.get("OMNIA_VERBOSE", ""))


def set_debug_mode(enabled: bool) -> None:
    """Enable or disable debug mode globally."""
    global _debug_mode
    _debug_mode = enabled


def set_verbose_mode(enabled: bool) -> None:
    """Enable or disable verbose mode globally.

    When verbose is off, INFO-level log messages are suppressed.
    WARN, ERROR, and OK messages always display.
    """
    global _verbose_mode
    _verbose_mode = enabled


def log(message: str, level: str = "INFO") -> None:
    """Print log message with timestamp and color.

    INFO-level messages are suppressed unless verbose mode is on
    (set via ``set_verbose_mode(True)`` or ``OMNIA_VERBOSE`` env var).
    DEBUG messages require debug mode.  WARN, ERROR, and OK always print.
    """
    if level == "DEBUG" and not _debug_mode:
        return
    if level == "INFO" and not _verbose_mode:
        return

    timestamp = datetime.now().strftime("%H:%M:%S")
    level_colors = {
        "INFO": Colors.BRIGHT_BLUE,
        "DEBUG": Colors.GRAY,
        "WARN": Colors.BRIGHT_YELLOW,
        "ERROR": Colors.BRIGHT_RED,
        "OK": Colors.BRIGHT_GREEN,
    }
    color = level_colors.get(level, "")
    print(f"{color}[{timestamp}] [{level}] {message}{Colors.RESET}")


# =============================================================================
# TEST LOGGER
# =============================================================================

_last_output = ""
_last_tc_id = ""

MAX_LINE_WIDTH = 100


def get_test_output(test_name: str = None) -> str:  # pylint: disable=unused-argument
    """Get captured output for the last test."""
    return _last_output


def get_last_tc_id() -> str:
    """Get TC ID set by the most recent TestLogger instance.
    
    Used by pytest hooks to retrieve the test case ID for summary
    table display. The TC ID is set when TestLogger.__init__ is called.
    
    Returns:
        str: Test case ID (e.g., "TC_IB_001") or empty string if none set.
    """
    return _last_tc_id


class TestLogger:
    """
    Structured test output logger for pytest validation tests.

    Usage:
        log = TestLogger("Verify S3 images pushed")
        log.check("Checking bucket...")
        log.passed("All images found", "details here")
    """

    def __init__(self, test_name: str, tc_id: str = ""):
        global _last_output, _last_tc_id  # pylint: disable=global-variable-not-assigned
        self.test_name = test_name
        self.tc_id = tc_id
        _last_tc_id = tc_id
        self._output_lines = []
        self._add_line("")
        id_part = f" [{tc_id}]" if tc_id else ""
        header = (
            f"  {Colors.BRIGHT_CYAN}{Colors.BOLD}"
            f"{Symbols.TRIANGLE}{id_part} {test_name}{Colors.RESET}"
        )
        self._add_line(header)

    def _add_line(self, line: str):
        """Add line to output and print."""
        global _last_output
        self._output_lines.append(line)
        print(line, flush=True)
        _last_output = "\n".join(self._output_lines)

    def check(self, message: str):
        """Log check being performed."""
        self._add_line(
            f"  {Colors.BRIGHT_YELLOW}{Symbols.ARROW}"
            f"{Colors.RESET} {message}"
        )

    def info(self, message: str):
        """Log informational message."""
        self._add_line(
            f"  {Colors.BRIGHT_BLUE}{Symbols.ARROW}"
            f"{Colors.RESET} {message}"
        )

    @staticmethod
    def _truncate(line: str, max_w: int = MAX_LINE_WIDTH) -> str:
        """Truncate a detail line to max width."""
        if len(line) > max_w:
            return line[:max_w - 3] + "..."
        return line

    def passed(self, message: str, details: str = None):
        """Log passed result."""
        self._add_line(
            f"  {Colors.BRIGHT_GREEN}{Symbols.CHECK} PASS:"
            f"{Colors.RESET} {self._truncate(message)}"
        )
        if details:
            for line in details.split('\n'):
                self._add_line(
                    f"    {Colors.GRAY}{Symbols.PIPE}"
                    f"{Colors.RESET} {line}"
                )

    def skipped(self, message: str, details: str = None):
        """Log skipped result."""
        self._add_line(
            f"  {Colors.BRIGHT_YELLOW}{Symbols.SKIP} SKIP:"
            f"{Colors.RESET} {self._truncate(message)}"
        )
        if details:
            for line in details.split('\n'):
                self._add_line(
                    f"    {Colors.GRAY}{Symbols.PIPE}"
                    f"{Colors.RESET} {line}"
                )
        else:
            self._add_line(
                f"    {Colors.GRAY}{Symbols.PIPE}"
                f"{Colors.RESET} {Colors.DIM}Skipped{Colors.RESET}"
            )

    def failed(self, message: str, details: str = None):
        """Log failed result."""
        self._add_line(
            f"  {Colors.BRIGHT_RED}{Symbols.CROSS} FAIL:"
            f"{Colors.RESET} {self._truncate(message)}"
        )
        if details:
            for line in details.split('\n'):
                self._add_line(
                    f"    {Colors.GRAY}{Symbols.PIPE}"
                    f"{Colors.RESET} {line}"
                )

    def get_output(self) -> str:
        """Get all captured output."""
        return "\n".join(self._output_lines)


# =============================================================================
# SESSION RESULTS — shared summary table for all consumer modules
# =============================================================================

_SESSION_RESULTS = []


def add_session_result(
    test_name: str,
    status: str,
    duration: float,
    tc_id: str = "",
) -> None:
    """Append a test result for the session summary table.

    Args:
        test_name: Short test function name.
        status: ``PASSED``, ``FAILED``, or ``SKIPPED``.
        duration: Duration in seconds.
        tc_id: Test case ID (e.g. ``TC_PR_001``).
    """
    _SESSION_RESULTS.append({
        "test_name": test_name,
        "tc_id": tc_id,
        "status": status,
        "duration": duration,
    })


def get_session_results():
    """Return the accumulated session results list."""
    return _SESSION_RESULTS


def clear_session_results():
    """Clear accumulated session results."""
    _SESSION_RESULTS.clear()


def print_summary_table() -> None:
    """Print a formatted test execution summary table.

    Respects environment variables:
    - ``OMNIA_RESULTS_FILE`` — export results to JSON for aggregation
    - ``OMNIA_SUPPRESS_SUMMARY`` — skip printing (shell wrapper prints combined)
    """
    import json as _json

    if not _SESSION_RESULTS:
        return

    results_file = os.environ.get("OMNIA_RESULTS_FILE", "")
    if results_file:
        existing = []
        if os.path.isfile(results_file):
            try:
                with open(results_file, "r", encoding="utf-8") as fh:
                    existing = _json.load(fh)
            except (_json.JSONDecodeError, OSError):
                existing = []
        existing.extend(_SESSION_RESULTS)
        with open(results_file, "w", encoding="utf-8") as fh:
            _json.dump(existing, fh)

    if os.environ.get("OMNIA_SUPPRESS_SUMMARY", ""):
        return

    _render_summary(_SESSION_RESULTS)


def _render_summary(results) -> None:
    """Render the summary table to stdout."""
    if not results:
        return

    passed = [r for r in results if r["status"] == "PASSED"]
    failed = [r for r in results if r["status"] == "FAILED"]
    skipped = [r for r in results if r["status"] == "SKIPPED"]
    total = len(results)

    sep = "=" * 85
    print(f"\n{sep}")
    print("  TEST EXECUTION SUMMARY")
    print(sep)
    print(
        f"  {'TC ID':<12} {'Test Name':<40} "
        f"{'Status':<10} {'Duration':>8}"
    )
    print(
        f"  {'-' * 12} {'-' * 40} "
        f"{'-' * 10} {'-' * 8}"
    )

    for r in results:
        tc_id = r.get("tc_id", "")
        name = r["test_name"]
        if len(name) > 39:
            name = name[:36] + "..."
        status = r["status"]
        dur = f"{r['duration']:.2f}s"
        if status == "PASSED":
            tag = f"{Colors.GREEN}{status}{Colors.RESET}"
        elif status == "FAILED":
            tag = f"{Colors.RED}{status}{Colors.RESET}"
        else:
            tag = f"{Colors.YELLOW}{status}{Colors.RESET}"
        print(
            f"  {Colors.CYAN}{tc_id:<12}{Colors.RESET} "
            f"{Colors.CYAN}{name}{Colors.RESET}"
            f"{' ' * max(1, 40 - len(name))} "
            f"{tag:<19} {dur:>8}"
        )

    print(
        f"  {'-' * 12} {'-' * 40} "
        f"{'-' * 10} {'-' * 8}"
    )
    total_dur = sum(r["duration"] for r in results)
    print(
        f"  {Colors.GREEN}{len(passed)} passed{Colors.RESET}, "
        f"{Colors.RED}{len(failed)} failed{Colors.RESET}, "
        f"{Colors.YELLOW}{len(skipped)} skipped{Colors.RESET} "
        f"/ {total} total "
        f"({total_dur:.2f}s)"
    )
    print(sep)
    print()
