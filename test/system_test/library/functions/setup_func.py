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
5. ``files``      only when enable_powerscale_csi is true: the PowerScale CSI
                  secret.yaml and values.yaml of test/system_test go to the paths of
                  omnia_config.yml (by default the orchestrator's project input folder,
                  which the cleanup deletes and the install creates, so after the install)

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

from . import openbao_func, run_func
from .config_func import (
    ConfigError,
    apply_cleanup_flags,
    apply_fvt_settings,
    apply_report_settings,
    load_openbao_settings,
)
from .fvt_func import domain_dir
from .omnia_func import (
    domain_input_dir,
    missing_credentials,
    omnia_env,
    setup_problems,
)
from .process_func import interactive_command, stream_command, tee_command
from .readiness_func import (
    configure_problem,
    load_setup_record,
    omnia_venv_path,
    outdated_requirements,
    read_json,
    requirements_checksum,
    sha256,
)
from ..messages.svt_msgs import RUN_MSGS, SETUP_MSGS, STAGE_MSGS
from ..vars.common_vars import (
    CATALOG_LINE_RE,
    CATALOG_REPLACE_ANSWER,
    CREDS_STDIN_FLAG,
    DOMAIN_INIT,
    DOMAIN_INIT_FORCE_ARG,
    FVT_SETUP,
    GENERATOR,
    INPUTS_CATALOG_KEY,
    INPUTS_FILE,
    MAX_CREDS_STDIN_BYTES,
    MODULE_ROOT,
    OPENBAO_CREDS_FLAG,
    OMNIA_ENV_FILE,
    OMNIA_FORCE_DEPS_ARG,
    OMNIA_FORCE_ENV_ARG,
    OMNIA_LIST_CATALOGS_ARG,
    OMNIA_SELECT_CATALOG_ARG,
    OMNIA_SETUP_ARGS,
    OMNIA_SH,
    OMNIA_SH_DIR,
    POWERSCALE_ENABLE_KEY,
    POWERSCALE_EXAMPLES_DIR,
    POWERSCALE_FILES,
    REPO_ROOT,
    REQUIREMENTS_MARKER,
    SETUP_RECORD,
    SETUP_REPORT_DIR,
    SRC_OMNIA_CONFIG,
    SRC_OMNIA_ENV_FILE,
    STAGED_FILE_MODE,
    VIRTUAL_ENV_KEY,
)
from ..vars.theme_vars import THEMES, creds_suite_of

Emit = Callable[[str], None]


# --------------------------------------------------------------- setup record
def setup_dir() -> str:
    """Return (and create, mode 0750) reports/setup."""
    os.makedirs(SETUP_REPORT_DIR, mode=0o750, exist_ok=True)
    return SETUP_REPORT_DIR


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


def record_action(action: str, outcome: Dict[str, Any]) -> None:
    """Store the outcome of a setup step in reports/setup/setup.json, with its run id.

    The installation outlives a run, so the record is kept across runs; the
    run id tells which run a step belongs to (--status shows "earlier run").
    """
    record = load_setup_record()
    record[action] = {**outcome, "run_id": run_func.load_run().get("run_id", "")}
    _write_json(os.path.join(setup_dir(), SETUP_RECORD), record)


def generated_inputs_sha256(theme: str) -> str:
    """Return one checksum of the src inputs the theme's generator profile writes.

    install compares this, not user_inputs.yml: a comment or a value that the
    generator leaves unchanged needs no new installation.
    """
    profile_path = os.path.join(os.path.dirname(GENERATOR), "profiles",
                                f"{THEMES[theme]['profile']}.yml")
    try:
        with open(profile_path, "r", encoding="utf-8") as stream:
            targets = (yaml.safe_load(stream) or {}).get("targets") or []
    except (OSError, yaml.YAMLError):
        return ""
    parts = [f"{target['file']}={sha256(os.path.join(REPO_ROOT, target['file']))}"
             for target in targets if isinstance(target, dict) and target.get("file")]
    return hashlib.sha256("|".join(sorted(parts)).encode()).hexdigest()


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
            "fvt": result.get("fvt") or {}, "results": result.get("results") or []}


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
def venv_env(venv: str) -> Dict[str, str]:
    """Return the environment of the activated Omnia venv (what activate-omnia.sh sets)."""
    return {**omnia_env(), VIRTUAL_ENV_KEY: venv,
            "PATH": f"{venv}/bin:{os.environ.get('PATH', '')}"}


def _omnia_venv_ready() -> str:
    """Return the Omnia venv path when its interpreter exists ("" otherwise)."""
    venv = omnia_venv_path()
    return venv if venv and os.access(os.path.join(venv, "bin", "python"), os.X_OK) else ""


def install_requirements(theme: str, venv: str, emit: Emit, force: bool) -> Dict[str, Any]:
    """Install the theme suites' test requirements into the Omnia venv, in order.

    A suite whose requirements did not change since its last install into this
    venv is skipped, unless ``force``.
    """
    marker_path = os.path.join(venv, REQUIREMENTS_MARKER)
    marker = read_json(marker_path)
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
        marker[domain] = requirements_checksum(domain)
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


def bundled_catalogs() -> Tuple[Dict[str, str], str]:
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
    catalogs, error = bundled_catalogs()
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


def select_catalog(name: str, emit: Emit, rows: List[Dict[str, Any]]) -> str:
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
                   generated_sha256=generated_inputs_sha256(theme),
                   test_config_sha256=sha256(config["path"]), flags_changed=len(changes),
                   run_id=settings["run_id"], rows=rows)


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


def _omnia_setup_command(force: bool, emit: Emit) -> List[str]:
    """Return the omnia.sh -s command line for this OIM."""
    arguments = ["bash", OMNIA_SH, *OMNIA_SETUP_ARGS]
    if force:
        arguments.append(OMNIA_FORCE_DEPS_ARG)
    if os.path.isfile(OMNIA_ENV_FILE) and sha256(SRC_OMNIA_ENV_FILE) != sha256(OMNIA_ENV_FILE):
        arguments.append(OMNIA_FORCE_ENV_ARG)
        emit(SETUP_MSGS["force_env"].format(src=SRC_OMNIA_ENV_FILE, path=OMNIA_ENV_FILE))
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
    arguments = _omnia_setup_command(force, emit)
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
        error = select_catalog(catalog, emit, rows)
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
                   inputs_sha256=record["configure"]["inputs_sha256"],
                   generated_sha256=generated_inputs_sha256(theme),
                   catalog_selected=record["configure"].get("catalog", ""), rows=rows)


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


def _run_creds_suite(theme: str, arguments: List[str], venv: str, emit: Emit,
                     payload: Optional[bytes] = None, suite: str = "") -> Dict[str, Any]:
    """Run test/<suite>/setup_env.sh (default: the theme's creds_suite) in the activated Omnia
    venv (prompts not logged)."""
    suite = suite or THEMES[theme]["creds_suite"]
    emit(SETUP_MSGS["creds_run"].format(suite=suite, command=" ".join(arguments)))
    return interactive_command(["bash", FVT_SETUP, *arguments], cwd=domain_dir(suite),
                               env=venv_env(venv), input_bytes=payload)


def _split_suites(theme: str) -> bool:
    """Return whether some store of ``theme`` is written by another suite than creds_suite."""
    return bool(THEMES[theme].get("creds_suites"))


def _suite_args(theme: str, flag: str, domain: str) -> Tuple[str, List[str]]:
    """Return (suite, arguments) of a prompt flag for one store.

    The creds_suite writes several stores and takes ``--domain``; a suite of creds_suites
    owns one store and has no ``--domain`` option.
    """
    suite = creds_suite_of(theme, domain)
    own = suite != THEMES[theme]["creds_suite"]
    return suite, [flag] if own else [flag, "--domain", domain]


def _write_payload(theme: str, venv: str, emit: Emit, data: Any,
                   domains: List[str]) -> Dict[str, Any]:
    """Give each suite the stores of ``domains`` it writes, from JSON keyed by domain.

    The creds_suite gets ``{domain: fields}`` of its domains; a suite of creds_suites gets the
    flat ``fields`` of its one domain. The values stay in memory (stdin of the suite).
    """
    if not isinstance(data, dict) or not all(isinstance(value, dict) for value in data.values()):
        return _failed(SETUP_MSGS["creds_stdin_invalid"])
    default = THEMES[theme]["creds_suite"]
    groups: Dict[str, List[str]] = {}
    for domain in domains:
        groups.setdefault(creds_suite_of(theme, domain), []).append(domain)
    for suite, owned in groups.items():
        body: Any = ({domain: data[domain] for domain in owned if domain in data}
                     if suite == default else data.get(owned[0]))
        if not body:
            continue
        result = _run_creds_suite(theme, [CREDS_STDIN_FLAG], venv, emit,
                                  payload=json.dumps(body).encode("utf-8"), suite=suite)
        if not result["success"]:
            return _failed(SETUP_MSGS["creds_failed"].format(rc=result["rc"]),
                           domains=_creds_report(theme, emit))
    return _passed()


def _read_stdin_payload() -> Tuple[bytes, str]:
    """Return (the JSON read once from stdin, error)."""
    payload = b"" if sys.stdin.isatty() else sys.stdin.buffer.read(MAX_CREDS_STDIN_BYTES + 1)
    if len(payload) > MAX_CREDS_STDIN_BYTES:
        return b"", SETUP_MSGS["creds_stdin_too_large"].format(limit=MAX_CREDS_STDIN_BYTES)
    return payload, ""


def _write_stdin(theme: str, venv: str, emit: Emit, payload: bytes,
                 domains: List[str]) -> Dict[str, Any]:
    """Write the stores from the stdin JSON: split per suite when the theme has creds_suites,
    else the payload goes unchanged to the creds_suite."""
    if _split_suites(theme):
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return _failed(SETUP_MSGS["creds_stdin_invalid"])
        return _write_payload(theme, venv, emit, data, domains)
    result = _run_creds_suite(theme, [CREDS_STDIN_FLAG], venv, emit, payload=payload)
    if not result["success"]:
        return _failed(SETUP_MSGS["creds_failed"].format(rc=result["rc"]),
                       domains=_creds_report(theme, emit))
    return _passed()


def _creds_next(theme: str, emit: Emit) -> None:
    """Say what comes after the credentials: the FVT suite's own hints are not for the SVT."""
    emit(SETUP_MSGS["creds_next"].format(suite=THEMES[theme]["creds_suite"], theme=theme))


def _creds_openbao(config: Dict[str, Any], venv: str, domains: List[str],
                   emit: Emit) -> Dict[str, Any]:
    """Read ``domains`` from OpenBao and give them to the suite's --domain-creds-stdin.

    The values stay in memory (the JSON goes to the suite's stdin); only field names are
    printed.
    """
    theme = config["theme"]
    try:
        settings = load_openbao_settings()
    except ConfigError as exc:
        return _failed(str(exc))
    emit(SETUP_MSGS["creds_openbao"].format(domains=", ".join(domains),
                                            server=settings["server_url"] or "(not set)",
                                            path=settings["secret_path"] or "(not set)"))
    try:
        found = openbao_func.read_domains(settings, domains, openbao_func.token(), emit)
    except openbao_func.OpenBaoError as exc:
        return _failed(SETUP_MSGS["creds_openbao_failed"].format(error=exc))
    if _split_suites(theme):
        return _write_payload(theme, venv, emit, found, domains)
    result = _run_creds_suite(theme, [CREDS_STDIN_FLAG], venv, emit,
                              payload=json.dumps(found).encode("utf-8"))
    if not result["success"]:
        return _failed(SETUP_MSGS["creds_failed"].format(rc=result["rc"]),
                       domains=_creds_report(theme, emit))
    return _passed()


def creds(config: Dict[str, Any], flag: str, domain: Optional[str], emit: Emit) -> Dict[str, Any]:
    """Write the domain credential stores (--set/--update-domain-creds, --domain-creds-stdin,
    --domain-creds-from-openbao)."""
    theme = config["theme"]
    venv, error = _creds_ready(theme)
    if error:
        return _failed(error)
    domains = THEMES[theme]["credential_domains"]
    if domain and domain not in domains:
        return _failed(SETUP_MSGS["unknown_domain"].format(domain=domain, known=", ".join(domains)))
    if flag == OPENBAO_CREDS_FLAG:
        written = _creds_openbao(config, venv, [domain] if domain else list(domains), emit)
        if written["status"] == "failed":
            return written
        _creds_next(theme, emit)
        return _passed(domains=_creds_report(theme, emit))
    if _split_suites(theme):
        written = _creds_split(theme, venv, flag, [domain] if domain else list(domains), emit)
        if written["status"] == "failed":
            return written
        _creds_next(theme, emit)
        return _passed(domains=_creds_report(theme, emit))
    result = _run_creds_suite(theme, [flag, *(["--domain", domain] if domain else [])], venv, emit)
    stored = _creds_report(theme, emit)
    if not result["success"]:
        return _failed(SETUP_MSGS["creds_failed"].format(rc=result["rc"]), domains=stored)
    _creds_next(theme, emit)
    return _passed(domains=stored)


def _creds_split(theme: str, venv: str, flag: str, domains: List[str],
                 emit: Emit) -> Dict[str, Any]:
    """A theme with creds_suites: --domain-creds-stdin split per suite, a prompt flag per store."""
    if flag == CREDS_STDIN_FLAG:
        payload, error = _read_stdin_payload()
        if error:
            return _failed(error)
        if not payload.strip():
            return _failed(SETUP_MSGS["creds_need_stdin"].format(domains=", ".join(domains)))
        return _write_stdin(theme, venv, emit, payload, domains)
    for domain in domains:
        suite, arguments = _suite_args(theme, flag, domain)
        result = _run_creds_suite(theme, arguments, venv, emit, suite=suite)
        if not result["success"]:
            return _failed(SETUP_MSGS["creds_failed"].format(rc=result["rc"]),
                           domains=_creds_report(theme, emit))
    return _passed()


def _creds_prompts(theme: str, venv: str, missing: List[str], emit: Emit) -> Dict[str, Any]:
    """Prompt each missing store on the terminal."""
    for domain in missing:
        suite, arguments = _suite_args(theme, "--set-domain-creds", domain)
        result = _run_creds_suite(theme, arguments, venv, emit, suite=suite)
        if not result["success"]:
            return _failed(SETUP_MSGS["creds_failed"].format(rc=result["rc"]),
                           domains=_creds_report(theme, emit))
    return _passed()


def _creds_stdin(theme: str, venv: str, missing: List[str], emit: Emit) -> Dict[str, Any]:
    """Unattended: give the JSON on stdin (read once, kept in memory) to --domain-creds-stdin."""
    payload, error = _read_stdin_payload()
    if error:
        return _failed(error)
    if not payload.strip():
        return _failed(SETUP_MSGS["creds_need_stdin"].format(domains=", ".join(missing)))
    return _write_stdin(theme, venv, emit, payload, missing)


def auto_creds(config: Dict[str, Any], emit: Emit, assume_yes: bool,
               from_openbao: bool = False) -> Dict[str, Any]:
    """Write only the missing stores: from OpenBao (``from_openbao``), else prompts on a
    terminal, else JSON read from stdin."""
    theme = config["theme"]
    venv, error = _creds_ready(theme)
    if error:
        return _failed(error)
    missing = missing_credentials(theme)
    if not missing:
        _creds_report(theme, emit)
        return _skipped(SETUP_MSGS["creds_all_set"],
                        domains=list(THEMES[theme]["credential_domains"]))
    if from_openbao:
        written = _creds_openbao(config, venv, missing, emit)
    else:
        writer = _creds_stdin if unattended(assume_yes) else _creds_prompts
        written = writer(theme, venv, missing, emit)
    if written["status"] == "failed":
        return written
    stored = _creds_report(theme, emit)
    still = missing_credentials(theme)
    if still:
        return _failed(SETUP_MSGS["creds_incomplete"].format(domains=", ".join(still)),
                       domains=stored)
    _creds_next(theme, emit)
    return _passed(domains=stored)


# -------------------------------------------------------------------- files
def _is_reference_example(path: str, name: str) -> bool:
    """Return whether ``path`` is still the product's reference ``name`` (never edited)."""
    try:
        with open(path, "rb") as staged, open(os.path.join(POWERSCALE_EXAMPLES_DIR, name),
                                              "rb") as example:
            return staged.read().strip() == example.read().strip()
    except OSError:
        return False


def _powerscale_copies(clusters: List[Any]) -> Tuple[Dict[str, str], List[str]]:
    """Return ({target path: source file name}, problems) of the clusters that enable the CSI."""
    copies: Dict[str, str] = {}
    problems: List[str] = []
    for cluster in clusters:
        if not isinstance(cluster, dict) or cluster.get(POWERSCALE_ENABLE_KEY) is not True:
            continue
        name = str(cluster.get("cluster_name", "?"))
        paths: Dict[str, str] = {}
        for key, source in POWERSCALE_FILES.values():
            path = str(cluster.get(key) or "")
            if not path.startswith("/") or ".." in path.split("/"):
                problems.append(SETUP_MSGS["files_bad_path"].format(
                    cluster=name, key=key, value=path, name=source))
            elif not os.path.isdir(os.path.dirname(path)):
                problems.append(SETUP_MSGS["files_no_folder"].format(
                    cluster=name, key=key, folder=os.path.dirname(path)))
            else:
                paths[source] = path
        if len(set(paths.values())) < len(paths):
            problems.append(SETUP_MSGS["files_same_path"].format(
                cluster=name, path=next(iter(paths.values()))))
        copies.update({path: source for source, path in paths.items()})
    return copies, problems


def stage_files(config: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Copy the PowerScale CSI secret.yaml and values.yaml to the paths of omnia_config.yml.

    Runs after the install: the default paths are in the orchestrator's project input
    folder, which the cleanup deletes and the install creates. Only when a Kubernetes cluster
    has enable_powerscale_csi true; then both files must exist in test/system_test (the
    pipeline copies them there from the cluster's folder of the project), have content, be
    valid YAML and differ from the reference examples they were seeded from (an unedited example
    would fail at deployment), and their folders must exist, or the step fails naming what is
    wrong. The copies are plaintext, mode 0600,
    replaced every run: the orchestrator encrypts its copy in place with a key a clean
    reinstall deletes. The array user and password come from the orchestrator credentials.
    """
    del config
    try:
        with open(SRC_OMNIA_CONFIG, "r", encoding="utf-8") as stream:
            clusters = (yaml.safe_load(stream) or {}).get("service_k8s_cluster") or []
    except (OSError, yaml.YAMLError, AttributeError) as exc:
        return _failed(SETUP_MSGS["files_unreadable"].format(error=exc))
    copies, problems = _powerscale_copies(clusters)
    if not copies and not problems:
        return _skipped(SETUP_MSGS["files_not_enabled"])
    for name in sorted(set(copies.values())):
        path = os.path.join(MODULE_ROOT, name)
        if not os.path.isfile(path):
            problems.append(SETUP_MSGS["files_missing"].format(
                path=path, name=name, folder=MODULE_ROOT))
            continue
        try:
            with open(path, "r", encoding="utf-8") as stream:
                content = yaml.safe_load(stream)
        except (OSError, yaml.YAMLError) as exc:
            problems.append(SETUP_MSGS["files_invalid"].format(
                path=path, name=name, error=str(exc).splitlines()[0]))
            continue
        if not content:
            problems.append(SETUP_MSGS["files_empty"].format(
                path=path, name=name, folder=MODULE_ROOT))
        elif _is_reference_example(path, name):
            problems.append(SETUP_MSGS["files_example"].format(
                path=path, name=name, folder=MODULE_ROOT,
                example=os.path.join(POWERSCALE_EXAMPLES_DIR, name)))
    if problems:
        return _failed(_problems(problems))
    for target, name in sorted(copies.items()):
        with open(os.path.join(MODULE_ROOT, name), "rb") as stream:
            content = stream.read()
        descriptor, temp = tempfile.mkstemp(dir=os.path.dirname(target), prefix=".svt-")
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
            os.chmod(temp, STAGED_FILE_MODE)
            os.replace(temp, target)
        except OSError:
            if os.path.exists(temp):
                os.unlink(temp)
            raise
        emit(SETUP_MSGS["files_copied"].format(name=name, target=target))
    return _passed(files=sorted(copies))


# ---------------------------------------------------------------- readiness
