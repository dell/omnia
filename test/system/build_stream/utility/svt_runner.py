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

"""BuildStream SVT validation runner.

Wraps the shared ``omnia_auto`` ValidationRunner for a suite that has a
single category (``svt_build_stream``) whose scenarios live under ``svt/``.
The shared runner's FVT/NFT/UT categories do not exist here, so help, list,
banner and batch output are rewritten for SVT. Pytest invocation, option
parsing and suite/marker validation are reused unchanged.

continue_on_failure (test_config.yml) decides what happens after a failure:
    false  the run stops at the first failed scenario step
    true   the next scenarios still run; a scenario whose execution (exec)
           failed never runs its verification, because it depends on it
"""

import os
import tempfile
from typing import Dict, List

import yaml

from omnia_auto.functions.formatting_func import Colors
from omnia_auto.functions.validation_runner import (
    ValidationRunner,
    _banner_step,
    _canonical_choice,
    _count_test_files,
    _err,
    _fail,
    _fail_tag,
    _generate_random_id,
    _green,
    _info,
    _list_subdirs,
    _ok,
    _pass,
    _scenario_is_enabled,
    _separator,
    _skip,
    _validate_config_value,
    _warn,
    _yellow,
)
from omnia_auto.vars.validation_vars import COMMANDS

from library.vars.test_case_vars import TEST_CASES

_COMMAND_HELP = (
    ("exec", "Run the scenario entry points only: precheck (E001) and playbook (E002)"),
    ("verify", "Run the verification cases only (V...); exec must have run before"),
    ("test", "Run exec, then verify (full flow for the scenario)"),
)
_OPTION_HELP = (
    ("--suite <name>", "Run one suite (sub-folder) of a scenario, e.g. --suite cadence"),
    ("--marker <expr>", "Filter by marker; '+' = AND, ',' = OR (e.g. --marker cadence)"),
    ("-v, --verbose", "More pytest output"),
    ("--debug", "Full pytest debug output (-vvs)"),
)


def _read_flag(script_dir: str, name: str) -> bool:
    """Return a boolean flag from test_config.yml (False when unset/unreadable)."""
    try:
        with open(os.path.join(script_dir, "test_config.yml"), encoding="utf-8") as stream:
            return (yaml.safe_load(stream) or {}).get(name) is True
    except (OSError, yaml.YAMLError, AttributeError):
        return False


class SvtRunner(ValidationRunner):
    """ValidationRunner for the single-category BuildStream SVT suite."""

    def __init__(self, domain: str, script_dir: str, domain_config: Dict,
                 category: str, tag_root: str) -> None:
        super().__init__(domain=domain, script_dir=script_dir, domain_config=domain_config)
        self.fvt_dir = os.path.join(script_dir, tag_root)
        self.cat_fvt = category
        self.categories = (category,)
        self.tag_root = tag_root

    # -----------------------------------------------------------------
    # Dispatch: one category only
    # -----------------------------------------------------------------

    def main(self, args: List[str]) -> int:
        if not args or args[0] in ("help", "--help", "-h"):
            self._print_help()
            return 0
        if args[0] == "--config":
            return self._cmd_config()
        if args[0] == self.cat_fvt:
            return self._dispatch_fvt(args[1:])
        _err(f"Unknown category '{args[0]}'. This suite has one category: {self.cat_fvt}")
        _warn(f"  Try: ./run_validation.sh {self.cat_fvt} list   or   ./run_validation.sh --help")
        return 1

    @property
    def _continue_on_failure(self) -> bool:
        return _read_flag(self.script_dir, "continue_on_failure")

    # -----------------------------------------------------------------
    # Full flow: exec + verify per scenario, honouring continue_on_failure
    # -----------------------------------------------------------------

    def _run_test(self, tag: str, suite: str, marker: str, verbose: str) -> int:
        """Run exec then verify for one scenario, or every scenario in order."""
        fd, results_file = tempfile.mkstemp(prefix="omnia_results_", suffix=".json")
        os.close(fd)
        os.environ["OMNIA_SUPPRESS_SUMMARY"] = "true"
        os.environ["OMNIA_RESULTS_FILE"] = results_file
        keep_going = self._continue_on_failure
        scenarios = [tag] if tag else list(self._all_exec_tags)
        scenario_marker = marker or ("" if tag else self._all_exec_marker)
        failed: List[str] = []
        total = len(scenarios) * 2
        for index, scenario in enumerate(scenarios):
            _banner_step(f"Step {index * 2 + 1}/{total}: Execute {scenario} "
                         "(precheck + entry point)")
            if self._run_exec(scenario, suite if tag else "", scenario_marker, verbose):
                failed.append(f"{scenario} exec")
                _warn(f"  {scenario}: execution failed, so its verification is skipped "
                      "(it depends on the execution).")
                if not keep_going:
                    _warn("  Stopping: continue_on_failure is false in test_config.yml.")
                    break
                _warn("  continue_on_failure is true: moving on to the next scenario.")
                continue
            _banner_step(f"Step {index * 2 + 2}/{total}: Verify {scenario}")
            if self._run_verify(scenario, suite if tag else "", scenario_marker, verbose):
                failed.append(f"{scenario} verify")
                if not keep_going:
                    _warn("  Stopping: continue_on_failure is false in test_config.yml.")
                    break
                _warn("  continue_on_failure is true: moving on to the next scenario.")

        self._print_combined_summary(results_file)
        print()
        _separator()
        label = f"{self.cat_fvt} {tag or 'full flow'}"
        if failed:
            _fail(f"  {label}: FAILED ({', '.join(failed)})")
        else:
            _ok(f"  {label}: EXEC + VERIFY PASSED")
        _separator()
        for key in ("OMNIA_SUPPRESS_SUMMARY", "OMNIA_RESULTS_FILE"):
            os.environ.pop(key, None)
        return 1 if failed else 0

    # -----------------------------------------------------------------
    # Batch: test_run_config.yml
    # -----------------------------------------------------------------

    def _cmd_config(self) -> int:  # pylint: disable=too-many-branches
        """Run the scenarios enabled in test_run_config.yml, top to bottom."""
        try:
            with open(self.config_file, encoding="utf-8") as stream:
                cfg = yaml.safe_load(stream) or {}
            scenarios = cfg.get(self.cat_fvt)
            if not isinstance(scenarios, dict) or not scenarios:
                raise ValueError(f"'{self.cat_fvt}:' with at least one scenario is required")
        except (OSError, yaml.YAMLError, ValueError) as exc:
            _err(f"Invalid {os.path.basename(self.config_file)}: {exc}")
            return 2

        os.environ["RUN_ID"] = run_id = _generate_random_id()
        fd, results_file = tempfile.mkstemp(prefix="omnia_results_", suffix=".json")
        os.close(fd)
        os.environ["OMNIA_SUPPRESS_SUMMARY"] = "true"
        os.environ["OMNIA_RESULTS_FILE"] = results_file
        keep_going = self._continue_on_failure
        _separator()
        _info("  BuildStream SVT — batch run from test_run_config.yml")
        _info(f"  Report ID           : {run_id}")
        _info(f"  continue_on_failure : {str(keep_going).lower()} (test_config.yml)")
        _separator()
        counts = {"passed": 0, "failed": 0, "skipped": 0}
        for name, scenario in scenarios.items():
            try:
                name = _canonical_choice(_validate_config_value(str(name), "scenario"),
                                         self._get_fvt_tags(), "scenario")
                if not isinstance(scenario, dict):
                    raise ValueError("must be a mapping")
                if not _scenario_is_enabled(scenario, name):
                    _skip(f"{name} (run: false)")
                    counts["skipped"] += 1
                    continue
                command = _canonical_choice(str(scenario.get("command", "test")),
                                            COMMANDS, "command")
                extra = self._build_config_extra(scenario, name)
            except ValueError as exc:
                _err(f"Scenario '{name}': {exc}")
                counts["failed"] += 1
                if not keep_going:
                    break
                continue
            rc = self._run_config_command([self.cat_fvt, name, command, *extra])
            if rc == 0:
                _pass(f"{name} {command}")
                counts["passed"] += 1
                continue
            _fail_tag(f"{name} {command}")
            counts["failed"] += 1
            if not keep_going:
                _warn("  Stopping the batch: continue_on_failure is false in test_config.yml.")
                break

        self._print_combined_summary(results_file)
        print()
        _separator()
        print(f"  Scenarios  {Colors.GREEN}Passed: {counts['passed']}{Colors.RESET}  "
              f"{Colors.RED}Failed: {counts['failed']}{Colors.RESET}  "
              f"{Colors.YELLOW}Skipped: {counts['skipped']}{Colors.RESET}")
        _separator()
        for key in ("OMNIA_SUPPRESS_SUMMARY", "OMNIA_RESULTS_FILE"):
            os.environ.pop(key, None)
        return 1 if counts["failed"] else 0

    # -----------------------------------------------------------------
    # Output: banner, help, list
    # -----------------------------------------------------------------

    def _print_banner(self, category: str, tag: str, command: str, suite: str,  # pylint: disable=too-many-arguments,too-many-positional-arguments
                      marker: str, run_id: str) -> None:
        del category
        _separator()
        _info("  BuildStream System Verification Test (SVT)")
        _separator()
        _green(f"  Category            : {self.cat_fvt}")
        _green(f"  Scenario            : {tag or 'full flow (' + ' -> '.join(self._all_exec_tags) + ')'}")
        _green(f"  Command             : {command}")
        _green(f"  Suite               : {suite or 'all'}")
        _green(f"  Marker              : {marker or 'none (every test)'}")
        _green(f"  continue_on_failure : {str(self._continue_on_failure).lower()}")
        _green(f"  debug_mode          : {str(_read_flag(self.script_dir, 'debug_mode')).lower()}")
        _green(f"  Report ID           : {run_id}")
        _separator()
        print()

    def _scenario_cases(self, tag: str) -> List[tuple]:
        """Return (id, test name, title) for every registered case of ``tag``."""
        prefix = f"BSM_SVT_{tag.upper()}_"
        return [(tc["id"], f"test_{key}", tc["title"])
                for key, tc in TEST_CASES.items() if tc["id"].startswith(prefix)]

    def _print_help(self) -> None:
        c = self.cat_fvt
        _separator()
        _info("  BuildStream System Verification Test (SVT) — Validation Runner")
        _separator()
        print()
        _yellow("USAGE")
        print(f"  ./run_validation.sh {c} <command> [options]             full flow")
        print(f"  ./run_validation.sh {c} <scenario> <command> [options]  one scenario")
        print(f"  ./run_validation.sh {c} list                            scenarios and test cases")
        print(f"  ./run_validation.sh {'--config':<{len(c) + 33}}batch from test_run_config.yml")
        print()
        _yellow("COMMANDS")
        for name, text in _COMMAND_HELP:
            print(f"  {name:<10} {text}")
        print()
        _yellow("SCENARIOS (run in this order)")
        for tag in self._get_fvt_tags():
            suites = _list_subdirs(os.path.join(self.fvt_dir, tag))
            print(f"  {tag:<14} suites: {', '.join(suites) or '-'}")
        print()
        _yellow("FULL FLOW (no scenario given)")
        print(f"  {' -> '.join(self._all_exec_tags)}   (every test)")
        _warn("  The last scenario, cleanup, removes the domains enabled under 'cleanup' "
              "in test_config.yml.")
        print()
        _yellow("OPTIONS")
        for name, text in _OPTION_HELP:
            print(f"  {name:<17} {text}")
        print()
        _yellow("MARKERS")
        print(f"  {', '.join(self._domain_markers)}")
        print()
        _yellow("FAILURE HANDLING (test_config.yml)")
        print("  continue_on_failure: false  stop at the first failure (default)")
        print("  continue_on_failure: true   keep running independent tests; dependent ones")
        print("                              (verify after a failed exec, deploy after a failed")
        print("                              build) are skipped with the reason")
        print()
        _yellow("EXAMPLES")
        print(f"  ./run_validation.sh {c} list")
        print(f"  ./run_validation.sh {c} test                                      # full flow")
        print(f"  ./run_validation.sh {c} prepare_base test")
        print(f"  ./run_validation.sh {c} installation test")
        print(f"  ./run_validation.sh {c} installation verify --marker cadence      # cadence only")
        print(f"  ./run_validation.sh {c} installation verify --suite build")
        print(f"  ./run_validation.sh {c} auto_cleanup test")
        print(f"  ./run_validation.sh {c} cleanup test                              # destructive")
        print("  ./run_validation.sh --config")
        print()

    _print_fvt_help = _print_help

    def _cmd_list(self, category: str) -> int:
        del category
        _separator()
        _info("  BuildStream SVT — scenarios and test cases")
        _separator()
        print()
        _yellow(f"Full flow: {' -> '.join(self._all_exec_tags)}")
        print()
        for tag in self._get_fvt_tags():
            tag_dir = os.path.join(self.fvt_dir, tag)
            suites = _list_subdirs(tag_dir)
            _green(f"  {tag}", end="")
            print(f"  ({_count_test_files(tag_dir)} test files; "
                  f"suites: {', '.join(suites) or '-'})")
            for tc_id, name, title in self._scenario_cases(tag):
                print(f"    {tc_id:<28} {name}")
                print(f"    {'':<28} {Colors.CYAN}{title}{Colors.RESET}")
            print()
        print(f"  Test case table: {self.tag_root}/README.md")
        print()
        return 0
