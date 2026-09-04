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
ValidationRunner — core logic for omnia test execution.

Handles argument parsing, pytest invocation, config-driven batch
execution, test listing, and result summarization.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

import yaml

from .formatting_func import Colors, _render_summary
from ..vars.validation_vars import COMMANDS

# Regex for safe identifiers from config YAML (no shell metacharacters)
_SAFE_IDENT_RE = re.compile(r"^[a-zA-Z0-9_\-./]+$")
_SAFE_MARKER_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:[+,][A-Za-z_][A-Za-z0-9_]*)*$"
)


def _validate_config_value(value: str, label: str) -> str:
    """Validate that a config-derived value is a safe identifier.

    Rejects values containing shell metacharacters or whitespace to
    prevent command injection when config values are passed as
    subprocess arguments.

    Args:
        value: The string to validate.
        label: Descriptive label for error messages.

    Returns:
        The validated value (unchanged).

    Raises:
        ValueError: If the value contains unsafe characters.
    """
    if value and not _SAFE_IDENT_RE.match(value):
        raise ValueError(
            f"Unsafe {label} value in config: {value!r}"
        )
    return value


def _validate_marker_value(value: str) -> str:
    """Validate a safe Single, AND, or OR marker expression.

    Marker names follow pytest's identifier style. A compound expression
    may use ``+`` for AND or ``,`` for OR, but not both operators.
    """
    if not isinstance(value, str):
        raise ValueError("Marker expression must be a string")
    if value and (
        ("+" in value and "," in value)
        or not _SAFE_MARKER_RE.fullmatch(value)
    ):
        raise ValueError(
            "Unsafe marker expression: marker names must be joined "
            "using only '+' (AND) or ',' (OR)"
        )
    return value


def _canonical_choice(
    value: str, choices: Sequence[str], label: str,
) -> str:
    """Return the trusted allowlist member equal to *value*.

    Returning the object from ``choices`` prevents untrusted configuration
    text from flowing directly into an execution argument.
    """
    for choice in choices:
        if value == choice:
            return choice
    raise ValueError(
        f"Unsupported {label} value {value!r}; expected one of: "
        f"{', '.join(choices)}"
    )


# =====================================================================
# OUTPUT HELPERS
# =====================================================================

def _separator() -> None:
    """Print a blue separator line."""
    print(
        f"{Colors.BLUE}{'=' * 65}{Colors.RESET}",
        flush=True,
    )


def _banner_step(text: str) -> None:
    """Print a yellow step banner."""
    print(
        f"\n{Colors.YELLOW}{'=' * 65}{Colors.RESET}\n"
        f"{Colors.YELLOW}  {text}{Colors.RESET}\n"
        f"{Colors.YELLOW}{'=' * 65}{Colors.RESET}\n",
        flush=True,
    )


def _info(msg: str) -> None:
    """Print an informational message in blue."""
    print(f"{Colors.BLUE}{msg}{Colors.RESET}", flush=True)


def _ok(msg: str) -> None:
    """Print a success message in green."""
    print(f"{Colors.GREEN}{msg}{Colors.RESET}", flush=True)


def _warn(msg: str) -> None:
    """Print a warning message in yellow."""
    print(
        f"{Colors.YELLOW}{msg}{Colors.RESET}", flush=True,
    )


def _err(msg: str) -> None:
    """Print an error message in red to stderr."""
    print(
        f"{Colors.RED}Error: {msg}{Colors.RESET}",
        file=sys.stderr, flush=True,
    )


def _green(msg: str, end: str = "\n") -> None:
    """Print text in green."""
    print(
        f"{Colors.GREEN}{msg}{Colors.RESET}",
        end=end, flush=True,
    )


def _yellow(msg: str) -> None:
    """Print text in yellow."""
    print(
        f"{Colors.YELLOW}{msg}{Colors.RESET}", flush=True,
    )


def _cyan(msg: str) -> None:
    """Print text in cyan."""
    print(f"{Colors.CYAN}{msg}{Colors.RESET}", flush=True)


def _fail(msg: str) -> None:
    """Print a failure message in red."""
    print(f"{Colors.RED}{msg}{Colors.RESET}", flush=True)


def _pass(tag: str) -> None:
    """Print PASS tag."""
    print(
        f"  {Colors.GREEN}PASS{Colors.RESET}  {tag}",
        flush=True,
    )


def _fail_tag(tag: str) -> None:
    """Print FAIL tag."""
    print(
        f"  {Colors.RED}FAIL{Colors.RESET}  {tag}",
        flush=True,
    )


def _skip(tag: str) -> None:
    """Print SKIP tag."""
    print(
        f"  {Colors.YELLOW}SKIP{Colors.RESET}  {tag}",
        flush=True,
    )


def _timestamp() -> str:
    """ISO-ish timestamp for report IDs."""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _count_test_files(directory: str) -> int:
    """Count ``test_*.py`` files recursively."""
    return sum(
        1 for _ in Path(directory).rglob("test_*.py")
    )


def _list_subdirs(directory: str) -> List[str]:
    """List non-pycache subdirectories."""
    if not os.path.isdir(directory):
        return []
    return sorted(
        d for d in os.listdir(directory)
        if (
            os.path.isdir(os.path.join(directory, d))
            and d != "__pycache__"
        )
    )


# =====================================================================
# VALIDATION RUNNER
# =====================================================================

class ValidationRunner:
    """Reusable validation runner for omnia test modules.

    Args:
        domain: Module domain name (e.g. ``image_build_manager``).
        script_dir: Absolute path to the test module directory.
            Defaults to the caller's working directory.
        domain_config: Domain-specific variables dict with keys:
            ``tags`` (list), ``markers`` (list),
            ``suites`` (dict), ``exclude_tags`` (list).
            When omitted, tags are auto-discovered from
            ``fvt/`` subdirectories.
    """

    def __init__(
        self,
        domain: str,
        script_dir: Optional[str] = None,
        domain_config: Optional[Dict] = None,
    ) -> None:
        self.domain = domain
        self.script_dir = script_dir or os.getcwd()
        self.fvt_dir = os.path.join(self.script_dir, "fvt")
        self.nft_dir = os.path.join(self.script_dir, "nft")
        self.ut_dir = os.path.join(self.script_dir, "ut")
        self.config_file = os.path.join(
            self.script_dir, "test_run_config.yml",
        )
        self.cat_fvt = f"fvt_{domain}"
        self.cat_nft = f"nft_{domain}"
        self.cat_ut = f"ut_{domain}"
        self.categories = (
            self.cat_fvt, self.cat_nft, self.cat_ut,
        )

        # Domain-specific config from library/vars
        cfg = domain_config or {}
        self._domain_markers: List[str] = cfg.get(
            "markers", [],
        )
        self._domain_suites: Dict = cfg.get("suites", {})
        self._exclude_tags: frozenset = frozenset(
            cfg.get("exclude_tags", []),
        )

    # -----------------------------------------------------------------
    # MAIN DISPATCH
    # -----------------------------------------------------------------

    def main(self, args: List[str]) -> int:
        """Parse *args* and dispatch to the handler.

        Returns:
            Exit code (0 = success).
        """
        if not args or args[0] in ("help", "--help", "-h"):
            self._print_help()
            return 0

        if args[0] == "--config":
            return self._cmd_config()

        arg1 = args[0]
        rest = args[1:]

        if arg1 == self.cat_fvt:
            return self._dispatch_fvt(rest)
        if arg1 == self.cat_nft:
            return self._dispatch_simple("nft", rest)
        if arg1 == self.cat_ut:
            return self._dispatch_simple("ut", rest)

        _err(f"Unknown category '{arg1}'")
        _err(f"Expected: {' | '.join(self.categories)}")
        return 1

    # -----------------------------------------------------------------
    # FVT DISPATCH
    # -----------------------------------------------------------------

    def _dispatch_fvt(self, args: List[str]) -> int:
        """Handle ``fvt_<domain> [tag] <command> [options]``."""
        if not args or args[0] in ("help", "--help"):
            self._print_fvt_help()
            return 0

        if args[0] == "list":
            return self._cmd_list("fvt")

        tags = self._get_fvt_tags()

        if args[0] in tags:
            tag = args[0]
            rest = args[1:]
            command = rest[0] if rest else "verify"
            opts = self._parse_options(
                rest[1:] if rest else [],
            )
        elif args[0] in COMMANDS:
            tag = ""
            command = args[0]
            opts = self._parse_options(args[1:])
        else:
            _err(f"Unknown argument '{args[0]}'")
            _err(
                f"Expected a tag ({', '.join(tags)})"
                f" or command ({', '.join(COMMANDS)})"
            )
            return 1

        if command not in COMMANDS:
            _err(f"Invalid command '{command}'")
            _err(f"Supported: {', '.join(COMMANDS)}")
            return 1

        if tag and not os.path.isdir(
            os.path.join(self.fvt_dir, tag),
        ):
            _err(f"Tag '{tag}' not found in fvt/")
            _err(f"Available: {', '.join(tags)}")
            return 1

        return self._run_fvt(tag, command, **opts)

    def _dispatch_simple(
        self, category: str, args: List[str],
    ) -> int:
        """Handle ``nft_<domain>`` or ``ut_<domain>``."""
        if not args:
            args = ["test"]

        if args[0] in ("help", "--help"):
            self._print_category_help(category)
            return 0

        if args[0] == "list":
            return self._cmd_list(category)

        rest = (
            args[1:] if args[0] in COMMANDS else args
        )
        opts = self._parse_options(rest)
        return self._run_simple(category, **opts)

    # -----------------------------------------------------------------
    # OPTION PARSING
    # -----------------------------------------------------------------

    @staticmethod
    def _parse_options(
        args: List[str],
    ) -> Dict[str, str]:
        """Parse ``--suite``, ``--marker``, ``-v``, ``--debug``."""
        opts: Dict[str, str] = {
            "suite": "", "marker": "", "verbose": "",
            "debug": "",
        }
        i = 0
        while i < len(args):
            if args[i] == "--suite" and i + 1 < len(args):
                opts["suite"] = args[i + 1]
                i += 2
            elif (
                args[i] == "--marker"
                and i + 1 < len(args)
            ):
                opts["marker"] = _validate_marker_value(
                    args[i + 1]
                )
                i += 2
            elif args[i] in ("-v", "--verbose"):
                opts["verbose"] = "-v"
                i += 1
            elif args[i] == "--debug":
                opts["debug"] = "true"
                opts["verbose"] = "-vvs"
                i += 1
            else:
                _err(f"Unknown option: {args[i]}")
                return opts
        return opts

    # -----------------------------------------------------------------
    # FVT EXECUTION
    # -----------------------------------------------------------------

    def _run_fvt(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self, tag: str, command: str,
        suite: str = "", marker: str = "",
        verbose: str = "", debug: str = "",
    ) -> int:
        """Execute an FVT scenario."""
        report_id = os.environ.get(
            "REPORT_ID", _timestamp(),
        )
        os.environ["REPORT_ID"] = report_id
        if debug:
            os.environ["OMNIA_DEBUG"] = "true"

        log_dir = os.path.join(
            self.script_dir, "reports", "logs",
        )
        os.makedirs(log_dir, exist_ok=True)
        label = tag or "all"
        os.environ["OMNIA_LOG_FILE"] = os.path.join(
            log_dir, f"{label}_{command}_{report_id}.log",
        )
        os.environ["OMNIA_DEPLOY_TAG"] = tag

        self._print_banner(
            "fvt", tag, command, suite, marker, report_id,
        )

        if command == "exec":
            return self._run_exec(tag, marker, verbose)
        if command == "verify":
            return self._run_verify(
                tag, suite, marker, verbose,
            )
        return self._run_test(
            tag, suite, marker, verbose,
        )

    def _run_exec(
        self, tag: str, marker: str, verbose: str,
    ) -> int:
        """Run playbook execution only."""
        os.environ["OMNIA_COMMAND_TYPE"] = "exec"
        exec_dir = (
            os.path.join(self.fvt_dir, tag) if tag
            else os.path.join(self.fvt_dir, "build")
        )
        marker_args = "-m deploy"
        if marker:
            marker_args += f" --marker {marker}"

        _info(
            f"Executing playbook (tag={tag or 'none'})...",
        )
        rc = self._invoke_pytest_with_summary(
            exec_dir, marker_args, verbose,
        )
        if rc == 0:
            _ok("Playbook execution completed.")
        else:
            _fail("Playbook execution failed.")
        return rc

    def _run_verify(
        self, tag: str, suite: str,
        marker: str, verbose: str,
    ) -> int:
        """Run verification tests only."""
        os.environ["OMNIA_COMMAND_TYPE"] = "verify"
        test_paths = self._build_verify_paths(tag, suite)
        marker_args = "-m 'not deploy'"
        if marker:
            marker_args += f" --marker {marker}"

        label = tag or "all except cleanup"
        _info(
            f"Running verification tests ({label})...",
        )
        rc = self._invoke_pytest_with_summary(
            test_paths, marker_args, verbose,
        )
        if rc == 0:
            _ok("Verification completed.")
        else:
            _fail("Verification failed.")
        return rc

    def _run_test(
        self, tag: str, suite: str,
        marker: str, verbose: str,
    ) -> int:
        """Run exec + verify (full flow)."""
        failed = 0
        fd, results_file = tempfile.mkstemp(
            prefix="omnia_results_", suffix=".json",
        )
        os.close(fd)
        os.environ["OMNIA_SUPPRESS_SUMMARY"] = "true"
        os.environ["OMNIA_RESULTS_FILE"] = results_file

        _banner_step("Step 1/2: Execute Playbook")
        rc = self._run_exec(tag, marker, verbose)
        if rc != 0:
            failed = 1

        if failed == 0:
            _banner_step("Step 2/2: Verify")
            rc = self._run_verify(
                tag, suite, marker, verbose,
            )
            if rc != 0:
                failed = 1
        else:
            _warn("Skipping verification — playbook failed")

        self._print_combined_summary(results_file)

        print()
        _separator()
        label = f"{self.cat_fvt} {tag or 'full'}"
        if failed == 0:
            _ok(f"  {label}: EXEC + VERIFY PASSED")
        else:
            _fail(f"  {label}: FAILED")
        _separator()

        for key in (
            "OMNIA_SUPPRESS_SUMMARY",
            "OMNIA_RESULTS_FILE",
        ):
            os.environ.pop(key, None)
        return failed

    # -----------------------------------------------------------------
    # NFT / UT
    # -----------------------------------------------------------------

    def _run_simple(
        self, category: str,
        marker: str = "", verbose: str = "",
        **_kwargs,
    ) -> int:
        """Run NFT or UT tests."""
        test_dir = (
            self.nft_dir if category == "nft"
            else self.ut_dir
        )
        if not os.path.isdir(test_dir):
            _err(
                f"{category.upper()} directory not found: "
                f"{test_dir}"
            )
            return 1

        cat_upper = category.upper()
        os.environ["OMNIA_COMMAND_TYPE"] = category

        _separator()
        _info(f"  {self.domain} — {cat_upper} Runner")
        _separator()
        print()

        marker_args = ""
        if category == "nft":
            marker_args = "-m nft"
        if marker:
            if marker_args:
                marker_args += f" --marker {marker}"
            else:
                marker_args = f"--marker {marker}"

        _info(f"Running {cat_upper} tests...")
        rc = self._invoke_pytest_with_summary(
            test_dir, marker_args, verbose,
        )
        print()
        if rc == 0:
            _ok(f"{cat_upper} execution completed.")
        else:
            _fail(f"{cat_upper} execution failed.")
        return rc

    # -----------------------------------------------------------------
    # LIST
    # -----------------------------------------------------------------

    def _cmd_list(self, category: str) -> int:
        """List available tests for a category."""
        _separator()
        _info(f"  {self.domain} — Available Tests")
        _separator()
        print()

        if category == "fvt":
            _yellow("FVT Tags:")
            for tag in self._get_fvt_tags():
                tag_dir = os.path.join(self.fvt_dir, tag)
                count = _count_test_files(tag_dir)
                suites = _list_subdirs(tag_dir)
                _green(f"  {tag}", end="")
                print(f"  ({count} test files)")
                if suites:
                    _yellow(
                        f"    suites: {' '.join(suites)}"
                    )
        elif category == "nft":
            if os.path.isdir(self.nft_dir):
                count = _count_test_files(self.nft_dir)
                _yellow("NFT Tests:")
                _green("  nft", end="")
                print(
                    f"  ({count} test files"
                    " — performance, idempotency)"
                )
            else:
                _warn("NFT directory not found")
        elif category == "ut":
            if os.path.isdir(self.ut_dir):
                count = _count_test_files(self.ut_dir)
                _yellow("Unit Tests:")
                _green("  ut", end="")
                print(f"  ({count} test files — unit)")
            else:
                _warn("UT directory not found")

        print()
        return 0

    # -----------------------------------------------------------------
    # CONFIG BATCH
    # -----------------------------------------------------------------

    def _cmd_config(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        self,
    ) -> int:
        """Batch execution from test_run_config.yml."""
        if not os.path.isfile(self.config_file):
            _err(f"Config not found: {self.config_file}")
            return 1

        with open(self.config_file, encoding="utf-8") as cfg_stream:
            cfg = yaml.safe_load(cfg_stream) or {}

        report_id = _timestamp()
        os.environ["REPORT_ID"] = report_id

        fd, results_file = tempfile.mkstemp(
            prefix="omnia_results_", suffix=".json",
        )
        os.close(fd)
        os.environ["OMNIA_SUPPRESS_SUMMARY"] = "true"
        os.environ["OMNIA_RESULTS_FILE"] = results_file

        _separator()
        _info("  Batch Execution from test_run_config.yml")
        _info(f"  Report ID : {report_id}")
        _separator()
        print()

        g_dataset = cfg.get("dataset_override", "")
        g_sync_in = cfg.get("sync_input_override", "")
        g_sync_out = cfg.get("sync_output_override", "")

        total = 0
        passed = 0
        failed = 0
        skipped = 0

        fvt_cfg = cfg.get(self.cat_fvt, {})
        if isinstance(fvt_cfg, dict) and fvt_cfg:
            _yellow("FVT Scenarios:")
            for name, sc in fvt_cfg.items():
                if not isinstance(sc, dict):
                    continue
                total += 1
                try:
                    scenario_name = _validate_config_value(
                        str(name), "scenario name",
                    )
                except ValueError as exc:
                    _err(str(exc))
                    failed += 1
                    continue
                if not sc.get("run", False):
                    _skip(f"fvt/{scenario_name}")
                    skipped += 1
                    continue

                try:
                    scenario_name = _canonical_choice(
                        scenario_name, self._get_fvt_tags(), "scenario",
                    )
                    env = self._build_config_env(
                        sc, g_dataset, g_sync_in, g_sync_out,
                    )
                    extra = self._build_config_extra(
                        sc, scenario_name,
                    )
                    sc_command = _canonical_choice(
                        str(sc.get("command", "test")),
                        COMMANDS,
                        "command",
                    )
                except ValueError as exc:
                    _err(f"Invalid config for {scenario_name}: {exc}")
                    failed += 1
                    continue
                runner_args = [
                    self.cat_fvt,
                    scenario_name,
                    sc_command,
                ] + extra

                rc = self._run_config_command(
                    runner_args, env,
                )
                if rc == 0:
                    _pass(f"fvt/{scenario_name}")
                    passed += 1
                else:
                    _fail_tag(f"fvt/{scenario_name}")
                    failed += 1
            print()

        for cat_key, cat_name in (
            (self.cat_nft, "nft"), (self.cat_ut, "ut"),
        ):
            cat_cfg = cfg.get(cat_key, {})
            if not isinstance(cat_cfg, dict):
                continue
            total += 1
            if cat_cfg.get("run", False):
                try:
                    extra = self._build_config_extra(cat_cfg)
                    cat_command = _canonical_choice(
                        str(cat_cfg.get("command", "test")),
                        COMMANDS,
                        "command",
                    )
                except ValueError as exc:
                    _err(f"Invalid config for {cat_name}: {exc}")
                    failed += 1
                    continue
                runner_args = [
                    cat_key,
                    cat_command,
                ] + extra
                rc = self._run_config_command(runner_args)
                if rc == 0:
                    _pass(cat_name)
                    passed += 1
                else:
                    _fail_tag(cat_name)
                    failed += 1
            else:
                _skip(cat_name)
                skipped += 1

        self._print_combined_summary(results_file)

        print()
        _separator()
        print(
            f"  Total: {total}  "
            f"{Colors.GREEN}Passed: {passed}{Colors.RESET}"
            f"  "
            f"{Colors.RED}Failed: {failed}{Colors.RESET}"
            f"  "
            f"{Colors.YELLOW}Skipped: "
            f"{skipped}{Colors.RESET}"
        )
        _separator()

        for key in (
            "OMNIA_SUPPRESS_SUMMARY",
            "OMNIA_RESULTS_FILE",
        ):
            os.environ.pop(key, None)
        return 1 if failed > 0 else 0

    @staticmethod
    def _build_config_env(
        sc: dict, g_dataset: str,
        g_sync_in: str, g_sync_out: str,
    ) -> dict:
        """Build validated environment overrides for a config scenario."""
        env = {}
        ds = _validate_config_value(
            g_dataset or str(sc.get("dataset", "")), "dataset",
        )
        si = (
            str(g_sync_in).lower() if g_sync_in != ""
            else str(sc.get("sync_input", "")).lower()
        )
        so = (
            str(g_sync_out).lower() if g_sync_out != ""
            else str(sc.get("sync_output", "")).lower()
        )
        if ds:
            env["OMNIA_DATASET_OVERRIDE"] = ds
        if si:
            env["OMNIA_SYNC_INPUT_OVERRIDE"] = si
        if so:
            env["OMNIA_SYNC_OUTPUT_OVERRIDE"] = so
        return env

    def _build_config_extra(
        self, sc: dict, tag: str = "",
    ) -> List[str]:
        """Build allowlisted CLI args from a config scenario."""
        extra: List[str] = []
        marker = self._canonical_marker(
            sc.get("marker", ""),
        )
        if marker:
            extra.extend(["--marker", marker])
        requested_suite = str(sc.get("suite", ""))
        suite = ""
        if requested_suite:
            allowed_suites = (
                _list_subdirs(os.path.join(self.fvt_dir, tag))
                if tag else []
            )
            suite = _canonical_choice(
                requested_suite, allowed_suites, "suite",
            )
        if suite:
            extra.extend(["--suite", suite])
        return extra

    def _canonical_marker(self, value: str) -> str:
        """Accept only the shell-free marker-expression grammar."""
        return _validate_marker_value(value)

    def _run_config_command(
        self, args: List[str], env: Optional[dict] = None,
    ) -> int:
        """Run one batch entry internally with isolated environment changes."""
        original_env = os.environ.copy()
        try:
            if env:
                os.environ.update(env)
            return self.main(args)
        finally:
            os.environ.clear()
            os.environ.update(original_env)

    # -----------------------------------------------------------------
    # PYTEST INVOCATION
    # -----------------------------------------------------------------

    def _invoke_pytest(
        self, test_path,
        marker_args: str = "", verbose: str = "",
    ) -> int:
        """Invoke pytest as a subprocess (raw)."""
        if isinstance(test_path, list):
            test_paths = [str(path) for path in test_path]
        else:
            test_paths = [str(test_path)]

        parts = [
            sys.executable, "-m", "pytest",
            *test_paths,
            "-s", "--tb=short", "--no-header", "-q",
        ]
        if marker_args:
            parts.extend(shlex.split(marker_args))
        if verbose:
            parts.extend(shlex.split(verbose))

        _cyan(f"  Command: {shlex.join(parts)}")
        print(flush=True)
        sys.stdout.flush()

        log_file = os.environ.get("OMNIA_LOG_FILE", "")
        # Disable auto-loaded plugins to avoid conflicts (e.g., pulp_rpm)
        env = os.environ.copy()
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        if log_file:
            try:
                with open(
                    log_file, "a", encoding="utf-8",
                ) as log_stream:
                    with subprocess.Popen(  # nosec B603
                        parts,
                        cwd=self.script_dir,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        shell=False,
                    ) as process:
                        if process.stdout is not None:
                            for output_line in process.stdout:
                                sys.stdout.write(output_line)
                                sys.stdout.flush()
                                log_stream.write(output_line)
                                log_stream.flush()
                        return process.wait()
            except OSError as exc:
                _err(f"Unable to run pytest or write its log: {exc}")
                return 1
        return subprocess.run(
            parts,
            cwd=self.script_dir,
            check=False,
            env=env,
            shell=False,
        ).returncode

    def _invoke_pytest_with_summary(
        self, test_path,
        marker_args: str = "", verbose: str = "",
    ) -> int:
        """Invoke pytest then print summary table after."""
        results_file = os.environ.get(
            "OMNIA_RESULTS_FILE", "",
        )
        own_results = False
        if not results_file:
            fd, results_file = tempfile.mkstemp(
                prefix="omnia_results_", suffix=".json",
            )
            os.close(fd)
            os.environ["OMNIA_RESULTS_FILE"] = results_file
            own_results = True

        was_suppressed = os.environ.get(
            "OMNIA_SUPPRESS_SUMMARY", "",
        )
        os.environ["OMNIA_SUPPRESS_SUMMARY"] = "true"

        rc = self._invoke_pytest(
            test_path, marker_args, verbose,
        )

        if own_results:
            self._print_combined_summary(results_file)
            os.environ.pop("OMNIA_RESULTS_FILE", None)

        if not was_suppressed:
            os.environ.pop("OMNIA_SUPPRESS_SUMMARY", None)
        else:
            os.environ["OMNIA_SUPPRESS_SUMMARY"] = (
                was_suppressed
            )
        return rc

    # -----------------------------------------------------------------
    # HELPERS
    # -----------------------------------------------------------------

    def _get_fvt_tags(self) -> List[str]:
        """Discover FVT tag directories."""
        if not os.path.isdir(self.fvt_dir):
            return []
        return sorted(
            d for d in os.listdir(self.fvt_dir)
            if (
                os.path.isdir(
                    os.path.join(self.fvt_dir, d),
                )
                and d != "__pycache__"
            )
        )

    def _build_verify_paths(
        self, tag: str, suite: str,
    ) -> Union[str, List[str]]:
        """Build test path(s) for verification."""
        if tag:
            base = os.path.join(self.fvt_dir, tag)
            if suite and os.path.isdir(
                os.path.join(base, suite),
            ):
                return os.path.join(base, suite)
            return base
        dirs = []
        for name in self._get_fvt_tags():
            if name in self._exclude_tags:
                continue
            dirs.append(
                os.path.join(self.fvt_dir, name),
            )
        return dirs

    def _print_banner(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self, category: str, tag: str,
        command: str, suite: str,
        marker: str, report_id: str,
    ) -> None:
        """Print execution banner."""
        cat_name = getattr(
            self, f"cat_{category}", category,
        )
        _separator()
        _info(f"  {self.domain} — Validation Runner")
        _separator()
        _green(f"  Category  : {cat_name}")
        if tag:
            _green(f"  Tag       : {tag}")
        else:
            _green("  Tag       : (all except cleanup)")
        _green(f"  Command   : {command}")
        if suite:
            _green(f"  Suite     : {suite}")
        if marker:
            _green(f"  Marker    : {marker}")
        _green(f"  Report ID : {report_id}")
        _separator()
        print()

    @staticmethod
    def _print_combined_summary(
        results_file: str,
    ) -> None:
        """Print combined summary from JSON results."""
        if (
            not results_file
            or not os.path.isfile(results_file)
        ):
            return
        try:
            with open(
                results_file, encoding="utf-8",
            ) as results_fh:
                results = json.load(results_fh)
        except (json.JSONDecodeError, OSError):
            return
        if results:
            _render_summary(results)
        try:
            os.unlink(results_file)
        except OSError:
            pass

    # -----------------------------------------------------------------
    # HELP
    # -----------------------------------------------------------------

    def _print_help(self) -> None:  # pylint: disable=too-many-statements
        """Print top-level help text."""
        d = self.domain
        _separator()
        _info(f"  {d} — Validation Runner")
        _separator()
        print()
        print(
            f"  End-to-end tests for the "
            f"{Colors.GREEN}{d}{Colors.RESET} domain."
        )
        print()
        _yellow("USAGE")
        print(f"  ./run_validation.sh {self.cat_fvt}"
              f" <command> [options]")
        print(f"  ./run_validation.sh {self.cat_fvt}"
              f" <tag> <command> [options]")
        print(f"  ./run_validation.sh {self.cat_fvt} list")
        print(f"  ./run_validation.sh {self.cat_nft}"
              f" <command> [options]")
        print(f"  ./run_validation.sh {self.cat_ut}"
              f" <command> [options]")
        print()
        _yellow("CATEGORIES")
        print(
            f"  {self.cat_fvt:<30}"
            " Functional Verification Tests"
        )
        print(
            f"  {self.cat_nft:<30}"
            " Non-Functional Tests"
        )
        print(
            f"  {self.cat_ut:<30}"
            " Unit Tests"
        )
        print()
        _yellow("COMMANDS")
        print("  exec       Run Ansible playbook only (no tests)")
        print("  verify     Run tests only (no playbook)")
        print("  test       Run playbook + tests (full flow)")
        print()
        _yellow("FVT TAGS")
        for tag in self._get_fvt_tags():
            print(f"  {tag}")
        print()
        _yellow("OPTIONS")
        print("  --suite <name>    Filter by subfolder")
        print("  --marker <expr>   Filter by marker")
        print("  -v, --verbose     Increase verbosity")
        print("  --debug           Full debug (-vvs)")
        print()
        f = self.cat_fvt
        n = self.cat_nft
        u = self.cat_ut
        _yellow("EXAMPLES")
        # Dynamic examples based on domain config
        tags = self._get_fvt_tags()
        ex_tag = tags[0] if tags else "deploy"
        ex_suite = ""
        if ex_tag in self._domain_suites:
            suites = self._domain_suites[ex_tag]
            ex_suite = suites[0] if suites else ""
        ex_marker = (
            self._domain_markers[0]
            if self._domain_markers else "sanity"
        )
        print(f"  ./run_validation.sh {f} verify")
        if ex_suite:
            print(f"  ./run_validation.sh {f} {ex_tag} verify"
                  f" --suite {ex_suite}")
        else:
            print(f"  ./run_validation.sh {f} {ex_tag} verify")
        print(f"  ./run_validation.sh {f} {ex_tag} test"
              f" --marker {ex_marker}")
        print(f"  ./run_validation.sh {f} list")
        print(f"  ./run_validation.sh {n} test")
        print(f"  ./run_validation.sh {u} test")
        print()

    def _print_fvt_help(self) -> None:
        """Print FVT-specific help text."""
        f = self.cat_fvt
        _separator()
        _info(f"  {f} — FVT Help")
        _separator()
        print()
        _yellow("USAGE")
        print(f"  ./run_validation.sh {f} <command> [opts]")
        print(f"  ./run_validation.sh {f} <tag> <command>"
              f" [opts]")
        print(f"  ./run_validation.sh {f} list")
        print()
        _yellow("COMMANDS")
        print("  exec       Run Ansible playbook only (no tests)")
        print("  verify     Run tests only (no playbook)")
        print("  test       Run playbook + tests (full flow)")
        print()
        _yellow("TAGS")
        for tag in self._get_fvt_tags():
            tag_dir = os.path.join(self.fvt_dir, tag)
            count = _count_test_files(tag_dir)
            suites = _list_subdirs(tag_dir)
            suite_str = (
                f"  suites: {', '.join(suites)}"
                if suites else ""
            )
            print(
                f"  {tag:<18} "
                f"({count} test files){suite_str}"
            )
        print()
        _yellow("OPTIONS")
        print("  --suite <name>    Filter by subfolder")
        print("  --marker <expr>   Filter by marker")
        print("  -v, --verbose     Increase verbosity")
        print("  --debug           Full debug (-vvs)")
        print()
        if self._domain_markers:
            _yellow("MARKERS")
            for m in self._domain_markers:
                print(f"  {m}")
            print()
        _yellow("EXAMPLES")
        # Dynamic examples based on domain config
        tags = self._get_fvt_tags()
        ex_tag = tags[0] if tags else "deploy"
        ex_suite = ""
        if ex_tag in self._domain_suites:
            suites = self._domain_suites[ex_tag]
            ex_suite = suites[0] if suites else ""
        ex_marker = (
            self._domain_markers[0]
            if self._domain_markers else "sanity"
        )
        print(f"  ./run_validation.sh {f} {ex_tag} verify")
        if ex_suite:
            print(f"  ./run_validation.sh {f} {ex_tag} verify"
                  f" --suite {ex_suite}")
        print(f"  ./run_validation.sh {f} {ex_tag} test"
              f" --marker {ex_marker}")
        print(f"  ./run_validation.sh {f} list")
        print()

    def _print_category_help(
        self, category: str,
    ) -> None:
        """Print help for NFT or UT category."""
        cat_name = getattr(
            self, f"cat_{category}", category,
        )
        cat_upper = category.upper()
        _separator()
        _info(f"  {cat_name} — {cat_upper} Help")
        _separator()
        print()
        _yellow("USAGE")
        print(f"  ./run_validation.sh {cat_name} <command>"
              f" [options]")
        print(f"  ./run_validation.sh {cat_name} list")
        print()
        _yellow("COMMANDS")
        print("  test       Run playbook + tests (full flow)")
        print("  verify     Run tests only (no playbook)")
        print()
        _yellow("OPTIONS")
        print("  --marker <expr>   Filter by marker")
        print("  -v, --verbose     Increase verbosity")
        print("  --debug           Full debug output")
        print()
        _yellow("EXAMPLES")
        print(f"  ./run_validation.sh {cat_name} test")
        print(f"  ./run_validation.sh {cat_name} test -v")
        print(f"  ./run_validation.sh {cat_name} list")
        print()
