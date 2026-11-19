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

"""Unit tests of the catalog_build theme (no command runs, nothing outside tmp is written).

Run from test/system_test: .venv/bin/python -m pytest ut -q -p no:cacheprovider -o addopts=""
"""

# pylint: disable=protected-access,import-error,wrong-import-position

import json
import os
import sys
from unittest import mock

import pytest
import yaml

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MODULE_ROOT)

from library.functions import catalog_func, readiness_func, svt_report_func, test_func  # noqa: E402
from library.functions.catalog_settings import (  # noqa: E402
    CatalogSettingsError,
    domain_fvt_tags,
    load_catalog_settings,
)
from library.functions.config_func import load_svt_config  # noqa: E402
from library.functions.fvt_func import describe_step  # noqa: E402
from library.vars import catalog_vars  # noqa: E402
from library.vars.catalog_vars import CATALOG_DEFAULT_STEPS  # noqa: E402
from library.vars.theme_vars import THEMES  # noqa: E402

PATH = "catalog_build_test_config.yml"
LISTED = {"1": "default", "2": "rhel/10.2/slurm_x86_64_no_vast.json",
          "3": "rhel/10.2/slurm_aarch64.json"}


def _settings(**block):
    return load_catalog_settings(block, PATH)


# ---------------------------------------------------------------- settings
def test_defaults_are_filled():
    """An empty block gives every default (force_rebuild true)."""
    settings = _settings()
    assert settings["catalogs"] == "all"
    assert settings["repo_config"] == "partial"
    assert settings["caching_policy"] is True
    assert settings["force_rebuild"] is True
    assert settings["include_aarch64"] is False
    assert settings["continue_on_failure"] is True
    assert settings["cleanup_between"] == "none"
    assert settings["steps"] == CATALOG_DEFAULT_STEPS


@pytest.mark.parametrize("block, fragment", [
    ({"unknown": 1}, "unknown key"),
    ({"repo_config": "never"}, "repo_config"),
    ({"force_rebuild": "true"}, "force_rebuild"),
    ({"cleanup_between": "all"}, "cleanup_between"),
    ({"catalogs": []}, "catalogs"),
    ({"catalogs": ["a.json", "a.json"]}, "twice"),
    ({"catalogs": ["../x.json"]}, "invalid catalog"),
    ({"repo_policies": {"epel": {"policy": "always"}}}, "<version>/<arch>/<repo>"),
    ({"repo_policies": {"10.2/x86_64/epel": {"policy": "sometimes"}}}, "policy"),
    ({"repo_policies": {"10.2/x86_64/epel": {"caching": "no"}}}, "caching"),
    ({"steps": [["orchestrator", "deploy"]]}, "domain"),
    ({"steps": [["repo_manager", "no_such_tag"]]}, "no FVT tag"),
])
def test_invalid_values_are_rejected(block, fragment):
    """Every invalid value names the key to fix."""
    with pytest.raises(CatalogSettingsError, match=fragment):
        load_catalog_settings(block, PATH)


def test_step_tags_come_from_the_suites():
    """The FVT tags are read from each suite's domain_vars.py."""
    assert {"precheck", "prepare", "execute", "status"} <= set(domain_fvt_tags("repo_manager"))
    assert {"precheck", "validate", "prepare", "build"} <= set(
        domain_fvt_tags("image_build_manager"))
    assert domain_fvt_tags("no_such_suite") == []


def test_shipped_theme_config_loads():
    """catalog_build_test_config.yml is valid and the theme mirrors build_stream's entry."""
    config = load_svt_config("catalog_build")
    assert config["catalog"]["catalogs"] == "all"
    assert config["catalog"]["force_rebuild"] is True
    assert config["fvt_settings"] == {}
    theme, base = THEMES["catalog_build"], THEMES["build_stream"]
    assert theme["credential_domains"] == ("repo_manager", "image_build_manager")
    for key in ("cleanup_steps", "fvt_domains", "creds_suite", "cleanup_requires",
                "cleanup_when_deployed"):
        assert theme[key] == base[key], key


def test_build_stream_theme_is_unchanged():
    """build_stream still loads its FVT settings and has no catalog block."""
    config = load_svt_config("build_stream")
    assert "catalog" not in config
    assert "catalog" in config["fvt_settings"]
    assert not THEMES["build_stream"].get("catalog_plan")


# -------------------------------------------------------------------- plan
def test_aarch64_detection_on_bundled_catalogs():
    """aarch64 is read from the functional layers of the real catalog files."""
    assert catalog_func.aarch64_layers(
        catalog_func.catalog_file("rhel/10.2/slurm_x86_64_no_vast.json")) == []
    assert catalog_func.aarch64_layers(catalog_func.catalog_file("rhel/10.2/slurm_aarch64.json"))
    assert catalog_func.aarch64_layers(catalog_func.catalog_file("default"))


def test_plan_all_skips_aarch64_by_default():
    """'all' follows the --list-catalogs order; aarch64 catalogs are skipped with a reason."""
    with mock.patch.object(catalog_func, "bundled_catalogs", return_value=(LISTED, "")):
        entries = catalog_func.plan(_settings())
    assert [entry["catalog"] for entry in entries] == list(LISTED.values())
    assert [entry["run"] for entry in entries] == [False, True, False]
    assert [entry["stage"] for entry in entries] == ["catalog_01", "catalog_02", "catalog_03"]
    assert "aarch64" in entries[0]["reason"]


def test_plan_aarch64_needs_the_build_host():
    """include_aarch64 without aarch64_inventory_host_ip stops the plan."""
    with mock.patch.object(catalog_func, "_aarch64_host", return_value=""):
        with pytest.raises(ValueError, match="aarch64_inventory_host_ip"):
            catalog_func.plan(_settings(include_aarch64=True))


def test_plan_list_keeps_the_given_order():
    """An explicit list runs in its own order; an unknown catalog is reported."""
    names = {"b": "rhel/10.2/slurm_aarch64.json", "a": "rhel/10.2/slurm_x86_64_no_vast.json"}
    with mock.patch.object(catalog_func, "resolve_catalog",
                           side_effect=lambda selection: (names.get(selection, ""),
                                                          "" if selection in names else "x")):
        entries = catalog_func.plan(_settings(catalogs=["a", "b"]))
        assert [entry["catalog"] for entry in entries] == [names["a"], names["b"]]
        with pytest.raises(ValueError, match="not in ./omnia.sh --list-catalogs"):
            catalog_func.plan(_settings(catalogs=["zzz"]))


@pytest.fixture(name="plan_file")
def _plan_file(tmp_path):
    """A plan written by write_plan for run svt-1 (catalog 1 runs, catalog 2 is aarch64)."""
    path = str(tmp_path / "catalog_build_plan.json")
    with mock.patch.object(catalog_func, "bundled_catalogs", return_value=(
            {"1": "rhel/10.2/slurm_x86_64_no_vast.json", "2": "rhel/10.2/slurm_aarch64.json"},
            "")):
        rows, error = catalog_func.write_plan(_settings(cleanup_between="images"), "svt-1",
                                              lambda _: None, path=path)
    assert not error and rows[0]["status"] == "PASSED"
    return path


def test_write_plan_stores_the_run(plan_file):
    """The plan file holds the run id, the JSON-ready settings and the entries."""
    with open(plan_file, encoding="utf-8") as stream:
        data = json.load(stream)
    assert data["run_id"] == "svt-1"
    assert data["settings"]["steps"][0] == ["repo_manager", "precheck"]
    assert [entry["run"] for entry in data["entries"]] == [True, False]


def test_write_plan_failure_is_a_failed_row():
    """An unknown catalog fails the plan with a FAILED row and no file."""
    with mock.patch.object(catalog_func, "resolve_catalog", return_value=("", "unknown")):
        rows, error = catalog_func.write_plan(_settings(catalogs=["zzz"]), "svt-1",
                                              lambda _: None, path="/nonexistent/plan.json")
    assert "zzz" in error and rows[0]["status"] == "FAILED"


def test_plan_becomes_theme_data(plan_file):
    """Stages, soft stages, stage titles and TEST_CASES come from the plan."""
    plan = catalog_vars.load_plan(plan_file)
    assert catalog_vars.catalog_stages(plan) == ("catalog_01", "catalog_02")
    assert catalog_vars.catalog_soft_stages(plan) == ("catalog_01", "catalog_02")
    info = catalog_vars.catalog_stage_info(plan)
    assert info["catalog_01"][0] == "Catalog 1: rhel/10.2/slurm_x86_64_no_vast.json"
    assert "aarch64" in info["catalog_02"][1]
    cases = catalog_vars.catalog_test_cases(plan)
    first = [key for key, case in cases.items() if case["stage"] == "catalog_01"]
    assert first[0] == "catalog_build_01_select"
    assert first[1:3] == ["catalog_build_01_repo_manager_precheck_exec",
                          "catalog_build_01_repo_manager_precheck_verify"]
    assert len(first) == 1 + 2 * len(CATALOG_DEFAULT_STEPS) + 1
    assert cases["catalog_build_01_select"]["id"] == "SVT_CATALOG_BUILD_0100"
    assert cases["catalog_build_01_repo_manager_precheck_exec"]["step"] == (
        "repo_manager", ("precheck", "exec"))
    assert cases["catalog_build_01_repo_manager_precheck_exec"]["stop_leftovers"] is True
    assert cases["catalog_build_01_repo_manager_precheck_verify"]["stop_leftovers"] is False
    cleanup = cases["catalog_build_01_cleanup_image_build_manager_cleanup_images"]
    assert cleanup["always"] is True
    assert list(key for key, case in cases.items() if case["stage"] == "catalog_02") == [
        "catalog_build_02_skip"]
    ids = [case["id"] for case in cases.values()]
    orders = [case["order"] for case in cases.values()]
    assert len(set(ids)) == len(ids) and orders == sorted(orders)


def test_continue_on_failure_false_has_no_soft_stage(plan_file):
    """continue_on_failure false: every catalog stage is hard (stops the run)."""
    plan = catalog_vars.load_plan(plan_file)
    plan["settings"]["continue_on_failure"] = False
    assert catalog_vars.catalog_soft_stages(plan) == ()


def test_no_plan_is_no_stage(tmp_path):
    """Without a plan the theme has no catalog stage and no test."""
    plan = catalog_vars.load_plan(str(tmp_path / "missing.json"))
    assert plan == {}
    assert not catalog_vars.catalog_stages(plan) and not catalog_vars.catalog_test_cases(plan)


def test_readiness_needs_the_plan_of_this_run(plan_file, tmp_path):
    """The plan must exist and belong to the current run."""
    run_file = tmp_path / "current_run.json"
    run_file.write_text(json.dumps({"run_id": "svt-1"}))
    assert readiness_func.catalog_plan_problem(plan_file, str(run_file)) == ""
    run_file.write_text(json.dumps({"run_id": "svt-2"}))
    assert "belongs to run svt-1" in readiness_func.catalog_plan_problem(plan_file, str(run_file))
    assert "no catalog plan" in readiness_func.catalog_plan_problem(
        str(tmp_path / "none.json"), str(run_file))


# ------------------------------------------------------------ input writes
REPO_YAML = """---
repo_config: "partial"  # Options: always | partial
caching_policy: true
repositories:
  "10.2":
    x86_64:
      baseos: {}
      epel:
        url: "https://mirror/epel"
      user_repos:
        slurm_custom:
          url: "https://mirror/slurm"
"""
IMAGE_YAML = """---
build_image:
  max_parallel: 0
  force_rebuild: false
functional_groups_source: "config"
"""


@pytest.fixture(name="runtime")
def _runtime(tmp_path):
    """Two runtime input folders and _runtime_dir pointed at them."""
    for domain, name, text in (("repo_manager", "repo_manager_config.yml", REPO_YAML),
                               ("image_build_manager", "image_build_config.yml", IMAGE_YAML)):
        folder = tmp_path / "runtime" / domain
        folder.mkdir(parents=True)
        (folder / name).write_text(text, encoding="utf-8")
    with mock.patch.object(catalog_func, "_runtime_dir",
                           side_effect=lambda domain: str(tmp_path / "runtime" / domain)):
        yield tmp_path


def _read(runtime, domain, name):
    return yaml.safe_load((runtime / "runtime" / domain / name).read_text(encoding="utf-8"))


def test_write_settings_updates_both_inputs(runtime):
    """Policy, caching, per-repo policies, force_rebuild and catalog mode are written."""
    changes = catalog_func.write_settings(_settings(
        repo_config="always", caching_policy=False, force_rebuild=True,
        repo_policies={"10.2/x86_64/epel": {"policy": "never"},
                       "10.2/x86_64/slurm_custom": {"caching": False},
                       "10.2/x86_64/baseos": {"policy": "partial"}}))
    assert changes
    repo = _read(runtime, "repo_manager", "repo_manager_config.yml")
    assert repo["repo_config"] == "always" and repo["caching_policy"] is False
    x86 = repo["repositories"]["10.2"]["x86_64"]
    assert x86["epel"]["policy"] == "never"
    assert x86["user_repos"]["slurm_custom"]["caching"] is False
    assert x86["baseos"]["policy"] == "partial"
    image = _read(runtime, "image_build_manager", "image_build_config.yml")
    assert image["build_image"]["force_rebuild"] is True
    assert image["functional_groups_source"] == "catalog"
    text = (runtime / "runtime" / "repo_manager" / "repo_manager_config.yml").read_text()
    assert "# Options: always | partial" in text


@pytest.mark.usefixtures("runtime")
def test_write_settings_is_idempotent():
    """A second write with the same settings changes nothing."""
    settings = _settings(force_rebuild=True)
    catalog_func.write_settings(settings)
    assert not catalog_func.write_settings(settings)


@pytest.mark.usefixtures("runtime")
def test_unknown_repository_is_reported():
    """A repo_policies key that is not in repo_manager_config.yml fails clearly."""
    with pytest.raises(ValueError, match="not a repository"):
        catalog_func.write_settings(_settings(
            repo_policies={"10.2/x86_64/nope": {"policy": "always"}}))


def test_overrides_apply_and_restore(runtime, tmp_path):
    """An override replaces one catalog's input; the next catalog gets the shared file back."""
    overrides = tmp_path / "overrides"
    target = overrides / "rhel" / "10.2" / "a.json" / "repo_manager"
    target.mkdir(parents=True)
    (target / "repo_manager_config.yml").write_text("---\nrepo_config: always\n")
    (target / "repo_manager_config_credentials.yml").write_text("secret")
    run_folder = tmp_path / "run"
    with mock.patch.object(catalog_func, "OVERRIDES_DIR", str(overrides)):
        done = catalog_func.restore_and_override(str(run_folder), "rhel/10.2/a.json", print)
        assert done == ["override repo_manager/repo_manager_config.yml"]
        assert _read(runtime, "repo_manager", "repo_manager_config.yml")["repo_config"] == "always"
        catalog_func.restore_and_override(str(run_folder), "rhel/10.2/b.json", print)
    repo = _read(runtime, "repo_manager", "repo_manager_config.yml")
    assert repo["repo_config"] == "partial" and "repositories" in repo
    assert not (runtime / "runtime" / "repo_manager"
                / "repo_manager_config_credentials.yml").exists()


# ----------------------------------------------------------------- actions
def test_skip_action_runs_nothing():
    """A skipped catalog returns its reason and runs no command."""
    result = catalog_func.run_action({"action": catalog_vars.ACTION_SKIP, "reason": "aarch64",
                                      "step": ("svt", ("skip", "x.json"))})
    assert result["skipped"] == "aarch64" and result["success"]


def test_select_action_writes_and_selects(plan_file, tmp_path):
    """select: overrides, settings, --select-catalog; a select error fails the action."""
    case = {"action": catalog_vars.ACTION_SELECT, "catalog": "x.json",
            "step": ("svt", ("select", "x.json"))}
    plan = catalog_vars.load_plan(plan_file)

    def selected(name, emit, rows):
        del emit
        rows.append({"command": f"./omnia.sh --select-catalog {name}", "output": "copied"})
        return ""
    with mock.patch.object(catalog_func, "load_plan", return_value=plan), \
            mock.patch.object(catalog_func, "load_run",
                              return_value={"report_path": str(tmp_path)}), \
            mock.patch.object(catalog_func, "restore_and_override", return_value=[]), \
            mock.patch.object(catalog_func, "write_settings", return_value=[1, 2]), \
            mock.patch.object(catalog_func, "select_catalog", side_effect=selected):
        result = catalog_func.run_action(case, lambda _: None)
        assert result["success"] and "2 setting(s) written" in result["output"]
        assert result["command"] == "./omnia.sh --select-catalog x.json"
        with mock.patch.object(catalog_func, "select_catalog", return_value="select failed"):
            assert not catalog_func.run_action(case, lambda _: None)["success"]


def test_svt_action_label():
    """An SVT action is labelled svt <action>, an FVT step fvt_<domain>."""
    assert describe_step(("svt", ("select", "x.json"))) == "svt select x.json"
    assert describe_step(("repo_manager", ("execute", "exec"))) == "fvt_repo_manager execute exec"


# ------------------------------------------------------- run_svt_test hooks
def _fvt(success):
    return {"success": success, "rc": 0 if success else 1, "duration": 1.0, "command": "c",
            "output": "o", "results": [], "fvt": {}}


@pytest.fixture(name="cases")
def _cases():
    """Fake TEST_CASES of one catalog stage; reports and the failure memory are isolated."""
    cases = {
        "catalog_build_01_skip": {"id": "A", "stage": "s", "title": "t", "action": "catalog_skip",
                                  "reason": "aarch64", "step": ("svt", ("skip", "x"))},
        "catalog_build_01_exec": {"id": "B", "stage": "s", "title": "t", "stop_leftovers": True,
                                  "step": ("repo_manager", ("execute", "exec"))},
        "catalog_build_01_verify": {"id": "C", "stage": "s", "title": "t",
                                    "step": ("repo_manager", ("execute", "verify"))},
        "catalog_build_01_cleanup": {"id": "D", "stage": "s", "title": "t", "always": True,
                                     "step": ("image_build_manager", ("cleanup_images", "test"))},
    }
    with mock.patch.dict(test_func.TEST_CASES, cases), \
            mock.patch.object(test_func, "_FAILED", {}), \
            mock.patch.object(test_func, "_report") as report:
        yield report


def test_skip_action_skips_the_test(cases):
    """The skip action reports Skipped and skips the pytest test."""
    with pytest.raises(pytest.skip.Exception, match="aarch64"):
        test_func.run_svt_test("catalog_build", "01_skip")
    assert cases.call_args.args[1]["status"] == "Skipped"


def test_failed_exec_stops_leftovers_and_blocks_the_stage(cases):
    """A failed exec stops its leftovers; verify is skipped; the cleanup still runs."""
    with mock.patch.object(test_func, "run_fvt_step", return_value=_fvt(False)), \
            mock.patch.object(test_func.catalog_func, "stop_leftovers",
                              return_value=[7]) as stop:
        with pytest.raises(AssertionError):
            test_func.run_svt_test("catalog_build", "01_exec")
    stop.assert_called_once()
    assert "pids 7" in cases.call_args.args[1]["note"]
    with pytest.raises(pytest.skip.Exception):
        test_func.run_svt_test("catalog_build", "01_verify")
    with mock.patch.object(test_func, "run_fvt_step", return_value=_fvt(True)) as step:
        test_func.run_svt_test("catalog_build", "01_cleanup")
    step.assert_called_once()


def test_passed_step_stops_nothing(cases):
    """A passed exec never looks for leftovers."""
    del cases
    with mock.patch.object(test_func, "run_fvt_step", return_value=_fvt(True)), \
            mock.patch.object(test_func.catalog_func, "stop_leftovers") as stop:
        test_func.run_svt_test("catalog_build", "01_exec")
    stop.assert_not_called()


# ------------------------------------------------------ leftover processes
PLAYBOOK = "/opt/omnia/venv/bin/ansible-playbook"
PROCS = {
    10: (1, [PLAYBOOK, "repo_manager.yml", "-v", "--tags", "execute"]),   # orphan
    11: (10, ["python3.12"]),                                             # its worker
    12: (11, ["/usr/bin/dnf", "download"]),                               # grandchild
    20: (500, [PLAYBOOK, "repo_manager.yml", "--tags", "precheck"]),      # live step
    30: (1, [PLAYBOOK, "image_build_manager.yml", "--tags", "build"]),    # other domain
    40: (1, ["/usr/bin/python3", "repo_manager.yml"]),                    # not a playbook
}


def test_leftovers_are_the_orphan_and_its_tree():
    """Only an orphaned ansible-playbook of the domain's playbook, with its descendants."""
    assert catalog_func.leftover_playbooks("repo_manager", PROCS) == [10, 11, 12]
    assert catalog_func.leftover_playbooks("image_build_manager", PROCS) == [30]
    assert not catalog_func.leftover_playbooks("repo_manager", {20: PROCS[20]})


def test_processes_reads_proc(tmp_path):
    """ppid and argv come from /proc/<pid>/stat and cmdline (a comm with spaces too)."""
    entry = tmp_path / "77"
    entry.mkdir()
    (entry / "stat").write_text("77 (ansible play) S 1 77 77 0")
    (entry / "cmdline").write_bytes(b"ansible-playbook\0repo_manager.yml\0")
    (tmp_path / "self").mkdir()
    assert catalog_func._processes(str(tmp_path)) == {
        77: (1, ["ansible-playbook", "repo_manager.yml"])}


def test_stop_leftovers_signals_the_tree():
    """SIGTERM, then SIGKILL, to every leftover; nothing is signalled when there is none."""
    with mock.patch.object(catalog_func, "_processes", return_value=PROCS), \
            mock.patch.object(catalog_func.os, "kill") as kill, \
            mock.patch.object(catalog_func.os.path, "exists", return_value=False):
        assert catalog_func.stop_leftovers("repo_manager", lambda _: None, grace=0) == [10, 11, 12]
    assert [call.args for call in kill.call_args_list] == [
        (pid, sig) for sig in (catalog_func.signal.SIGTERM, catalog_func.signal.SIGKILL)
        for pid in (10, 11, 12)]
    with mock.patch.object(catalog_func, "_processes", return_value={}), \
            mock.patch.object(catalog_func.os, "kill") as kill:
        assert not catalog_func.stop_leftovers("repo_manager", lambda _: None, grace=0)
    kill.assert_not_called()


# ------------------------------------------------------------------ report
def test_report_item_of_a_catalog_step():
    """A catalog step becomes a standard report item (the build_stream format)."""
    item = svt_report_func.make_item({"id": "SVT_CATALOG_BUILD_0101", "name": "x: precheck exec",
                                      "status": "PASSED", "command": "fvt_repo_manager precheck "
                                      "exec", "fvt": {"domain": "repo_manager"}})
    assert item["status"] == "Passed" and item["fvt"]["domain"] == "repo_manager"
