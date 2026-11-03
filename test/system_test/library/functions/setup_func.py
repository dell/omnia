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

"""./setup_env.sh steps: configure, cleanup, install, credentials (and the setup record).

``./setup_env.sh`` with no action runs every step in order (``all``):

1. ``configure``  user_inputs.yml -> src/<domain>/input and src/main/omnia.env
                  (dataset generator, theme profile); the cleanup flags of
                  test_config.yml -> each suite's test_config.yml
2. ``cleanup``    only with --force (or alone with --cleanup), destructive: each
                  suite's cleanup FVT, then omnia.sh --cleanup
3. ``install``    omnia.sh -s (venv, every domain-init.sh, catalog, omnia-cli),
                  then omnia.sh --select-catalog when user_inputs.yml sets
                  main.catalog, then the test requirements of the theme suites in the Omnia
                  venv (only the suites whose requirements changed)
4. ``creds``      the missing domain credential stores, written by
                  test/build_stream/setup_env.sh with the Omnia venv activated

Every value about the installation (venv, data path, project, domain data
paths) is read from the installed /etc/omnia/omnia.env. ``assume_yes``
(--yes) answers every confirmation, so the steps can run unattended.
Every step returns ``{"status": passed|skipped|failed, "error": str, ...}``;
the driver (_setup.py) stores it in reports/setup/setup.json.
"""

import hashlib
import json
import os
import subprocess  # nosec B404  # fixed argument lists, no shell
import sys
import tempfile
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from . import run_func
from .config_func import (
    apply_cleanup_flags,
    apply_fvt_settings,
    apply_report_settings,
    theme_config_path,
)
from .fvt_func import domain_dir
from .omnia_func import (
    credential_path,
    domain_input_dir,
    missing_credentials,
    omnia_env,
    setup_problems,
)
from .process_func import interactive_command, stream_command, tee_command
from ..messages.svt_msgs import RUN_MSGS, SETUP_MSGS, STAGE_MSGS
from ..vars.common_vars import (
    CATALOG_LINE_RE,
    CATALOG_REPLACE_ANSWER,
    CREDS_STDIN_FLAG,
    DOMAIN_INIT,
    DOMAIN_INIT_FORCE_ARG,
    FVT_REQUIREMENTS,
    FVT_SETUP,
    GENERATOR,
    INPUTS_CATALOG_KEY,
    INPUTS_FILE,
    MAX_CREDS_STDIN_BYTES,
    OMNIA_AUTO_WHEEL,
    OMNIA_ENV_FILE,
    OMNIA_FORCE_DEPS_ARG,
    OMNIA_FORCE_ENV_ARG,
    OMNIA_LIST_CATALOGS_ARG,
    OMNIA_SELECT_CATALOG_ARG,
    OMNIA_SETUP_ARGS,
    OMNIA_SH,
    OMNIA_SH_DIR,
    OMNIA_VENV_KEY,
    REPO_ROOT,
    DEFAULT_THEME,
    REQUIREMENTS_MARKER,
    SETUP_RECORD,
    SETUP_REPORT_DIR,
    SRC_OMNIA_ENV_FILE,
    VIRTUAL_ENV_KEY,
)
from ..vars.theme_vars import CREDS_SUITE, THEMES

Emit = Callable[[str], None]
Check = Tuple[str, bool, str]


# --------------------------------------------------------------- setup record
def sha256(path: str) -> str:
    """Return the SHA-256 of a file ("" when it is absent)."""
    try:
        with open(path, "rb") as stream:
            return hashlib.sha256(stream.read()).hexdigest()
    except OSError:
        return ""


def setup_dir() -> str:
    """Return (and create, mode 0750) reports/setup."""
    os.makedirs(SETUP_REPORT_DIR, mode=0o750, exist_ok=True)
    return SETUP_REPORT_DIR


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: str, data: Dict[str, Any]) -> None:
    """Write JSON atomically next to ``path``."""
    handle, temp = tempfile.mkstemp(prefix=".tmp.", dir=os.path.dirname(path))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def load_setup_record() -> Dict[str, Any]:
    """Return reports/setup/setup.json ({} before the first step)."""
    return _read_json(os.path.join(SETUP_REPORT_DIR, SETUP_RECORD))


def record_action(action: str, outcome: Dict[str, Any]) -> None:
    """Store the outcome of a setup step in reports/setup/setup.json."""
    record = load_setup_record()
    record[action] = outcome
    _write_json(os.path.join(setup_dir(), SETUP_RECORD), record)


def _passed(**detail: Any) -> Dict[str, Any]:
    return {"status": "passed", "error": "", **detail}


def _failed(error: str, **detail: Any) -> Dict[str, Any]:
    return {"status": "failed", "error": error, **detail}


def _skipped(reason: str, **detail: Any) -> Dict[str, Any]:
    return {"status": "skipped", "error": reason, **detail}


def _problems(items: List[str]) -> str:
    return "\n  - " + "\n  - ".join(items)


def row(name: str, status: str, duration: float = 0.0, details: str = "",
        error: str = "") -> Dict[str, Any]:
    """Return one report row (status PASSED, FAILED or SKIPPED)."""
    return {"name": name, "status": status, "duration": round(float(duration), 3),
            "details": details, "error": error}


def result_row(name: str, result: Dict[str, Any], details: str = "") -> Dict[str, Any]:
    """Return the report row of a finished command: its command line, screen output and
    the FVT results it added (FVT steps)."""
    return {**row(name, "PASSED" if result["success"] else "FAILED",
                  float(result.get("duration") or 0.0), details or f"rc={result.get('rc')}",
                  "" if result["success"] else f"rc={result['rc']}"),
            "command": result.get("command", ""), "output": result.get("output", ""),
            "results": result.get("results") or []}


def current_run(config: Dict[str, Any]) -> Dict[str, str]:
    """Return the report settings of the current run (started by configure).

    Raises:
        RunError: No run was started, or it is of another theme, or the theme's
            test_config changed its report settings since (see run_func.active_run).
    """
    return run_func.active_run(config, allow_failed=True)


def unattended(assume_yes: bool) -> bool:
    """Return whether no question may be asked (--yes, or no terminal on stdin)."""
    return assume_yes or not sys.stdin.isatty()


# ------------------------------------------------------------ Omnia venv helpers
def omnia_venv_path() -> str:
    """Return OMNIA_VENV_PATH of the installed omnia.env ("" before omnia.sh -s)."""
    return omnia_env().get(OMNIA_VENV_KEY, "")


def venv_env(venv: str) -> Dict[str, str]:
    """Return the environment of the activated Omnia venv (what activate-omnia.sh sets)."""
    return {**omnia_env(), VIRTUAL_ENV_KEY: venv,
            "PATH": f"{venv}/bin:{os.environ.get('PATH', '')}"}


def _omnia_venv_ready() -> str:
    """Return the Omnia venv path when its interpreter exists ("" otherwise)."""
    venv = omnia_venv_path()
    return venv if venv and os.access(os.path.join(venv, "bin", "python"), os.X_OK) else ""


def _requirements_checksum(domain: str) -> str:
    """Return one checksum of what a suite's setup_env.sh installs."""
    suite = domain_dir(domain)
    parts = [sha256(os.path.join(suite, FVT_REQUIREMENTS)), sha256(os.path.join(suite, FVT_SETUP)),
             sha256(OMNIA_AUTO_WHEEL)]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def outdated_requirements(theme: str, venv: str) -> List[str]:
    """Return the theme suites whose test requirements are not (or no longer) in ``venv``."""
    marker = _read_json(os.path.join(venv, REQUIREMENTS_MARKER)) if venv else {}
    return [domain for domain in THEMES[theme]["fvt_domains"]
            if marker.get(domain) != _requirements_checksum(domain)]


def install_requirements(theme: str, venv: str, emit: Emit, force: bool) -> Dict[str, Any]:
    """Install the theme suites' test requirements into the Omnia venv, in order.

    A suite whose requirements did not change since its last install into this
    venv is skipped, unless ``force``.
    """
    marker_path = os.path.join(venv, REQUIREMENTS_MARKER)
    marker = _read_json(marker_path)
    outdated = THEMES[theme]["fvt_domains"] if force else outdated_requirements(theme, venv)
    installed, rows = [], []
    for domain in THEMES[theme]["fvt_domains"]:
        label = f"test requirements: {domain}"
        if domain not in outdated:
            emit(SETUP_MSGS["requirements_current"].format(domain=domain, venv=venv))
            rows.append(row(label, "SKIPPED", details="unchanged since the last install"))
            continue
        emit(SETUP_MSGS["requirements"].format(domain=domain, venv=venv))
        result = stream_command(["bash", FVT_SETUP], cwd=domain_dir(domain), env=venv_env(venv))
        rows.append(result_row(label, result, details=f"test/{domain}/{FVT_SETUP} in {venv}"))
        if not result["success"]:
            return _failed(STAGE_MSGS["step_failed"].format(label=f"{domain} {FVT_SETUP}",
                                                            rc=result["rc"]), rows=rows)
        marker[domain] = _requirements_checksum(domain)
        _write_json(marker_path, marker)
        installed.append(domain)
    return _passed(installed=installed, rows=rows)


# ---------------------------------------------------------------- configure
def _catalog_selection() -> str:
    """Return user_inputs.yml main.catalog as text ("" when not set)."""
    try:
        with open(INPUTS_FILE, "r", encoding="utf-8") as stream:
            node: Any = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError):
        return ""
    for key in INPUTS_CATALOG_KEY:
        node = node.get(key) if isinstance(node, dict) else None
    return "" if node is None else str(node).strip()


def _bundled_catalogs() -> Tuple[Dict[str, str], str]:
    """Return ({number: name} of ./omnia.sh --list-catalogs, error)."""
    try:
        listed = subprocess.run(  # nosec B603  # fixed argument list, no shell
            ["bash", OMNIA_SH, OMNIA_LIST_CATALOGS_ARG], cwd=OMNIA_SH_DIR, check=False,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return {}, SETUP_MSGS["catalog_list_failed"].format(rc="not run")
    if listed.returncode != 0:
        return {}, SETUP_MSGS["catalog_list_failed"].format(rc=listed.returncode)
    return {match.group(1): match.group(2)
            for match in map(CATALOG_LINE_RE.match, listed.stdout.splitlines()) if match}, ""


def resolve_catalog(selection: str) -> Tuple[str, str]:
    """Return (catalog name, error) for a number or name of ./omnia.sh --list-catalogs.

    The name is what --select-catalog gets, so the choice does not depend on
    the order of the list at install time.
    """
    catalogs, error = _bundled_catalogs()
    if error:
        return "", error
    wanted = selection
    if wanted.startswith(("10.0/", "10.2/")):
        wanted = f"rhel/{wanted}"
    if wanted in catalogs:
        return catalogs[wanted], ""
    names = [name for name in catalogs.values()
             if wanted in (name, os.path.basename(name))]
    if len(names) == 1:
        return names[0], ""
    return "", SETUP_MSGS["catalog_unknown"].format(selection=selection, count=len(catalogs))


def _configure_catalog(emit: Emit, rows: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Check user_inputs.yml main.catalog; return (catalog name or "", error)."""
    selection = _catalog_selection()
    if not selection:
        emit(SETUP_MSGS["catalog_default"])
        rows.append(row("catalog (user_inputs.yml main.catalog)", "PASSED",
                        details="default catalog (omnia.sh -s)"))
        return "", ""
    name, error = resolve_catalog(selection)
    if error:
        rows.append(row("catalog (user_inputs.yml main.catalog)", "FAILED", error=error))
        return "", error
    emit(SETUP_MSGS["catalog_resolved"].format(selection=selection, name=name))
    rows.append(row("catalog (user_inputs.yml main.catalog)", "PASSED",
                    details=f"{selection} = {name}"))
    return name, ""


def _select_catalog(name: str, emit: Emit, rows: List[Dict[str, Any]]) -> str:
    """Run ./omnia.sh --select-catalog ``name`` (replaces the active catalog); return an error."""
    emit(SETUP_MSGS["catalog_select"].format(name=name))
    result = tee_command(["bash", OMNIA_SH, OMNIA_SELECT_CATALOG_ARG, name], cwd=OMNIA_SH_DIR,
                         drop_venv=True, input_bytes=CATALOG_REPLACE_ANSWER)
    rows.append(result_row(f"./omnia.sh {OMNIA_SELECT_CATALOG_ARG} {name}", result,
                           details="copied to CATALOG_FILE_PATH of omnia.env"))
    if not result["success"]:
        return SETUP_MSGS["catalog_select_failed"].format(name=name, rc=result["rc"])
    return ""


def configure(config: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Fill the src inputs from user_inputs.yml and write the cleanup flags into the suites."""
    theme = config["theme"]
    if not os.path.isfile(OMNIA_SH):
        return _failed(STAGE_MSGS["repo_missing"].format(path=OMNIA_SH))
    try:
        run = run_func.start_run(config)
    except run_func.RunError as exc:
        return _failed(str(exc))
    settings = run_func.settings_of(run)
    emit(RUN_MSGS["started"].format(run_id=run["run_id"], theme=theme,
                                    report_path=run["report_path"]))
    run_rows = [row(f"run {run['run_id']} started", "PASSED",
                    details=RUN_MSGS["started"].format(run_id=run["run_id"], theme=theme,
                                                       report_path=run["report_path"]))]
    previous = run.get("previous") or {}
    if previous:
        emit(RUN_MSGS["previous"].format(**previous))
        run_rows.append(row("previous run", "PASSED",
                            details=RUN_MSGS["previous"].format(**previous)))
    profile = THEMES[theme]["profile"]
    emit(SETUP_MSGS["configure_inputs"].format(inputs=INPUTS_FILE, profile=profile))
    generated = tee_command([sys.executable, GENERATOR, "--inputs", INPUTS_FILE,
                             "--profile", profile], cwd=os.path.dirname(GENERATOR),
                            no_input=True)
    rows = [*run_rows, result_row("user_inputs.yml -> src/<domain>/input, src/main/omnia.env",
                                  generated, details=f"dataset generator, profile {profile}")]
    if not generated["success"]:
        return _failed(SETUP_MSGS["generator_failed"].format(rc=generated["rc"]), rows=rows)
    catalog, error = _configure_catalog(emit, rows)
    if error:
        return _failed(error, rows=rows)
    emit(SETUP_MSGS["configure_flags"].format(config=config["path"]))
    changes = apply_cleanup_flags(config, emit)
    changes += apply_fvt_settings(config, emit)
    rows.append(row("cleanup flags -> each suite's test_config.yml", "PASSED",
                    details=f"{len(changes)} value(s) changed"))
    emit(SETUP_MSGS["configure_report"].format(**settings))
    report_changes = apply_report_settings(settings, emit)
    rows.append(row("report settings -> each suite's test_config.yml", "PASSED",
                    details=f"run {settings['run_id']}, {settings['report_path']}/"
                            f"{settings['report_name']} ({len(report_changes)} value(s) changed)"))
    return _passed(theme=theme, profile=profile, catalog=catalog,
                   inputs_sha256=sha256(INPUTS_FILE),
                   test_config_sha256=sha256(config["path"]), flags_changed=len(changes),
                   run_id=settings["run_id"], rows=rows)


def configure_problem(record: Dict[str, Any]) -> str:
    """Return why the inputs must be configured (again) ("" when current)."""
    configured = record.get("configure") or {}
    if configured.get("status") != "passed":
        return SETUP_MSGS["configure_first"]
    if configured.get("inputs_sha256") != sha256(INPUTS_FILE):
        return SETUP_MSGS["inputs_changed"].format(path=INPUTS_FILE)
    theme_config = theme_config_path(configured.get("theme") or DEFAULT_THEME)
    if configured.get("test_config_sha256") != sha256(theme_config):
        return SETUP_MSGS["inputs_changed"].format(path=theme_config)
    return ""


# ------------------------------------------------------------------ install
def stale_inputs(theme: str) -> List[Tuple[str, str]]:
    """Return (domain, runtime file) for every src input whose runtime copy differs."""
    env = omnia_env()
    stale = []
    if sha256(SRC_OMNIA_ENV_FILE) != sha256(OMNIA_ENV_FILE):
        stale.append(("main", OMNIA_ENV_FILE))
    for domain in THEMES[theme]["credential_domains"]:
        source = os.path.join(REPO_ROOT, "src", domain, "input")
        target = domain_input_dir(env, domain)
        for name in sorted(os.listdir(source)) if os.path.isdir(source) else []:
            if name.startswith(".") or not os.path.isfile(os.path.join(source, name)):
                continue
            if sha256(os.path.join(source, name)) != sha256(os.path.join(target, name)):
                stale.append((domain, os.path.join(target, name)))
    return stale


def _refresh_inputs(theme: str, venv: str, emit: Emit,
                    rows: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    """Unattended: re-stage the stale domains (domain-init.sh --force); return what stays stale."""
    stale = stale_inputs(theme)
    for domain in dict.fromkeys(domain for domain, _ in stale if domain != "main"):
        emit(SETUP_MSGS["refresh_inputs"].format(domain=domain))
        script = DOMAIN_INIT.format(domain=domain)
        result = tee_command(["bash", script, DOMAIN_INIT_FORCE_ARG], cwd=os.path.dirname(script),
                             env=venv_env(venv), no_input=True)
        rows.append(result_row(f"domain-init.sh --force: {domain}", result,
                               details="runtime inputs differed from src"))
    return stale_inputs(theme)


def _omnia_setup_command(config: Dict[str, Any], force: bool, emit: Emit) -> List[str]:
    """Return the omnia.sh -s command line for this OIM."""
    arguments = ["bash", OMNIA_SH, *OMNIA_SETUP_ARGS]
    if force:
        arguments.append(OMNIA_FORCE_DEPS_ARG)
    if os.path.isfile(OMNIA_ENV_FILE) and sha256(SRC_OMNIA_ENV_FILE) != sha256(OMNIA_ENV_FILE):
        if config["omnia_force_env"]:
            arguments.append(OMNIA_FORCE_ENV_ARG)
            emit(SETUP_MSGS["force_env"].format(src=SRC_OMNIA_ENV_FILE, path=OMNIA_ENV_FILE))
        else:
            emit(SETUP_MSGS["keep_env"].format(src=SRC_OMNIA_ENV_FILE, path=OMNIA_ENV_FILE))
    return arguments


def install(config: Dict[str, Any], emit: Emit, force: bool = False,
            assume_yes: bool = False) -> Dict[str, Any]:
    """Run omnia.sh -s, then install the theme suites' test requirements into the Omnia venv."""
    theme = config["theme"]
    record = load_setup_record()
    problem = configure_problem(record)
    if problem:
        return _failed(problem)
    if os.path.isfile(OMNIA_ENV_FILE) and not force:
        emit(SETUP_MSGS["previous_setup"].format(path=OMNIA_ENV_FILE))
    arguments = _omnia_setup_command(config, force, emit)
    no_input = unattended(assume_yes)
    emit(SETUP_MSGS["omnia_setup"].format(command=" ".join(arguments[1:])))
    result = tee_command(arguments, cwd=OMNIA_SH_DIR, drop_venv=True, no_input=no_input)
    rows = [result_row(f"./omnia.sh {' '.join(arguments[2:])}", result,
                       details="venv, every domain-init.sh, catalog, omnia-cli")]
    if not result["success"]:
        return _failed(SETUP_MSGS["omnia_setup_failed"].format(rc=result["rc"]), rows=rows)
    problems = setup_problems(theme)
    rows.append(row("Omnia setup complete (omnia.env, data path, venv, domain inputs)",
                    "FAILED" if problems else "PASSED", error="; ".join(problems)))
    if problems:
        return _failed(SETUP_MSGS["setup_incomplete"] + _problems(problems), rows=rows)
    catalog = record["configure"].get("catalog", "")
    if catalog:
        error = _select_catalog(catalog, emit, rows)
        if error:
            return _failed(error, rows=rows)
    venv = omnia_venv_path()
    stale = _check_inputs(theme, venv, no_input, emit, rows)
    installed = install_requirements(theme, venv, emit, force)
    rows.extend(installed.pop("rows", []))
    if installed["status"] == "failed":
        return {**installed, "rows": rows}
    return _passed(omnia_venv=venv, force=force, force_env=OMNIA_FORCE_ENV_ARG in arguments,
                   catalog=catalog or "default",
                   installed=installed["installed"], stale_inputs=stale,
                   inputs_sha256=record["configure"]["inputs_sha256"], rows=rows)


def _check_inputs(theme: str, venv: str, no_input: bool, emit: Emit,
                  rows: List[Dict[str, Any]]) -> List[str]:
    """Re-stage stale inputs when unattended; report the runtime files that still differ."""
    stale = _refresh_inputs(theme, venv, emit, rows) if no_input else stale_inputs(theme)
    for _, path in stale:
        emit(SETUP_MSGS["stale_input"].format(path=path))
    rows.append(row("runtime inputs match src", "SKIPPED" if stale else "PASSED",
                    details=", ".join(path for _, path in stale)))
    return [path for _, path in stale]


# -------------------------------------------------------------- credentials
def _creds_ready(theme: str) -> Tuple[str, str]:
    """Return (Omnia venv, error): the setup must exist before a store is written."""
    problems = setup_problems(theme)
    if problems:
        return "", SETUP_MSGS["setup_missing"] + _problems(problems)
    return omnia_venv_path(), ""


def _creds_report(theme: str, emit: Emit) -> List[str]:
    """Print every store's state; return the stored domains."""
    missing = missing_credentials(theme)
    for name in THEMES[theme]["credential_domains"]:
        state = "missing" if name in missing else "encrypted"
        emit(SETUP_MSGS["creds_state"].format(domain=name, state=state))
    return [name for name in THEMES[theme]["credential_domains"] if name not in missing]


def _run_creds_suite(arguments: List[str], venv: str, emit: Emit,
                     payload: Optional[bytes] = None) -> Dict[str, Any]:
    """Run test/build_stream/setup_env.sh in the activated Omnia venv (prompts not logged)."""
    emit(SETUP_MSGS["creds_run"].format(suite=CREDS_SUITE, command=" ".join(arguments)))
    return interactive_command(["bash", FVT_SETUP, *arguments], cwd=domain_dir(CREDS_SUITE),
                               env=venv_env(venv), input_bytes=payload)


def creds(config: Dict[str, Any], flag: str, domain: Optional[str], emit: Emit) -> Dict[str, Any]:
    """Write the domain credential stores (--set/--update-domain-creds, --domain-creds-stdin)."""
    theme = config["theme"]
    venv, error = _creds_ready(theme)
    if error:
        return _failed(error)
    domains = THEMES[theme]["credential_domains"]
    if domain and domain not in domains:
        return _failed(SETUP_MSGS["unknown_domain"].format(domain=domain, known=", ".join(domains)))
    result = _run_creds_suite([flag, *(["--domain", domain] if domain else [])], venv, emit)
    stored = _creds_report(theme, emit)
    if not result["success"]:
        return _failed(SETUP_MSGS["creds_failed"].format(rc=result["rc"]), domains=stored)
    return _passed(domains=stored)


def _creds_prompts(theme: str, venv: str, missing: List[str], emit: Emit) -> Dict[str, Any]:
    """Prompt each missing store on the terminal."""
    for domain in missing:
        result = _run_creds_suite(["--set-domain-creds", "--domain", domain], venv, emit)
        if not result["success"]:
            return _failed(SETUP_MSGS["creds_failed"].format(rc=result["rc"]),
                           domains=_creds_report(theme, emit))
    return _passed()


def _creds_stdin(theme: str, venv: str, missing: List[str], emit: Emit) -> Dict[str, Any]:
    """Unattended: give the JSON on stdin (read once, kept in memory) to --domain-creds-stdin."""
    payload = b"" if sys.stdin.isatty() else sys.stdin.buffer.read(MAX_CREDS_STDIN_BYTES + 1)
    if not payload.strip():
        return _failed(SETUP_MSGS["creds_need_stdin"].format(domains=", ".join(missing)))
    if len(payload) > MAX_CREDS_STDIN_BYTES:
        return _failed(SETUP_MSGS["creds_stdin_too_large"].format(limit=MAX_CREDS_STDIN_BYTES))
    result = _run_creds_suite([CREDS_STDIN_FLAG], venv, emit, payload=payload)
    if not result["success"]:
        return _failed(SETUP_MSGS["creds_failed"].format(rc=result["rc"]),
                       domains=_creds_report(theme, emit))
    return _passed()


def auto_creds(config: Dict[str, Any], emit: Emit, assume_yes: bool) -> Dict[str, Any]:
    """Write only the missing stores: prompts on a terminal, else JSON read from stdin."""
    theme = config["theme"]
    venv, error = _creds_ready(theme)
    if error:
        return _failed(error)
    missing = missing_credentials(theme)
    if not missing:
        _creds_report(theme, emit)
        return _skipped(SETUP_MSGS["creds_all_set"],
                        domains=list(THEMES[theme]["credential_domains"]))
    writer = _creds_stdin if unattended(assume_yes) else _creds_prompts
    written = writer(theme, venv, missing, emit)
    if written["status"] == "failed":
        return written
    stored = _creds_report(theme, emit)
    still = missing_credentials(theme)
    if still:
        return _failed(SETUP_MSGS["creds_incomplete"].format(domains=", ".join(still)),
                       domains=stored)
    return _passed(domains=stored)


# ---------------------------------------------------------------- readiness
def readiness_checks(theme: str) -> List[Check]:
    """Return (label, ok, how to fix) for everything ./run_validation.sh needs."""
    record = load_setup_record()
    checks: List[Check] = []
    problem = configure_problem(record)
    checks.append((f"Inputs configured (user_inputs.yml, {theme}_test_config.yml)",
                   not problem, problem))
    setup = setup_problems(theme)
    checks.append(("Omnia installed (omnia.sh -s: omnia.env, data path, venv, domain inputs)",
                   not setup, "; ".join(setup)))
    installed = record.get("install") or {}
    if installed.get("status") == "failed":
        detail = SETUP_MSGS["install_failed"].format(
            error=(installed.get("error") or "").splitlines()[0] if installed.get("error") else "")
    elif installed.get("status") != "passed":
        detail = SETUP_MSGS["install_first"]
    elif installed.get("inputs_sha256") != (record.get("configure") or {}).get("inputs_sha256"):
        detail = SETUP_MSGS["install_again"]
    else:
        detail = ""
    checks.append(("Installed after the last configure", not detail, detail))
    if setup:
        checks.append(("Test requirements in the Omnia venv", False, SETUP_MSGS["install_first"]))
        checks.append(("Domain credentials", False, SETUP_MSGS["creds_after_install"]))
        return checks
    outdated = outdated_requirements(theme, omnia_venv_path())
    detail = (SETUP_MSGS["requirements_outdated"].format(domains=", ".join(outdated))
              if outdated else "")
    label = f"Test requirements in the Omnia venv ({len(THEMES[theme]['fvt_domains'])} suites)"
    checks.append((label, not outdated, detail))
    missing = missing_credentials(theme)
    env = omnia_env()
    for domain in THEMES[theme]["credential_domains"]:
        detail = SETUP_MSGS["creds_missing"].format(
            domain=domain, path=credential_path(env, domain)) if domain in missing else ""
        checks.append((f"Credentials: {domain}", not detail, detail))
    return checks


def readiness_problems(theme: str) -> List[str]:
    """Return how to fix everything that blocks the SVT stages ([] when ready)."""
    return [detail for _, ok, detail in readiness_checks(theme) if not ok]
