#!/usr/bin/env python3
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

"""Create or update the GitLab project that runs the SVT of one theme on one or more clusters.

Uses the GitLab client of test/pipeline/setup_gitlab_project.py and the theme
data of test/system_test (stages, credential domains), so a new theme needs
no change here::

    ./setup_svt_project.py --render [--config svt_pipeline_config.yml]   # print the CI files
    ./setup_svt_project.py --create --gitlab-url https://gitlab.example.com
    ./setup_svt_project.py --update --gitlab-url ... [--update-inputs] [--set-password]
                           [--scan-host-keys] [--bao-cacert ca.pem]
    ./setup_svt_project.py --set-variables --gitlab-url ...              # only the CI/CD variables
    ./setup_svt_project.py --validate --gitlab-url ...                   # GitLab CI lint

The GitLab token comes from GITLAB_TOKEN or a prompt, each cluster's OIM SSH
password from <CLUSTER>_SVT_TARGET_PASS or a prompt (--create, --set-password);
none is printed, stored in a file or passed as an argument.

--scan-host-keys stores each cluster's OIM host key (ssh-keyscan, run from this
machine) as the File variable <CLUSTER>_SVT_SSH_KNOWN_HOSTS that the jobs require, and
prints its fingerprint: compare it with the OIM's
(ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub). --bao-cacert FILE stores the
OpenBao CA certificate as the File variable BAO_CACERT. Both only change the variable
they name and can be repeated.

Files committed: .gitlab-ci.yml (one trigger job per cluster, each holding the
cluster's resource group), .gitlab-ci-svt-<theme>.yml (the jobs: the theme's stages
and the configured timeouts), svt_ci.py, the config (reference copy) and, per
cluster, clusters/<name>/svt/user_inputs.yml and <theme>_test_config.yml (and the
reference secret.yaml and values.yaml of the PowerScale CSI, which are never replaced: the user
edits them for the array)
(copied from test/system_test on --create, or with --update-inputs; edit
them in GitLab). The pipeline never starts on a push: run it from CI/CD >
Pipelines, the API or a schedule.
"""

import argparse
import getpass
import os
import re
import subprocess  # nosec B404  # ssh-keyscan and ssh-keygen, fixed argument lists
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

HERE = Path(__file__).resolve().parent
SVT_ROOT = HERE.parent
TEST_ROOT = SVT_ROOT.parent
sys.path.insert(0, str(TEST_ROOT / "pipeline"))
sys.path.insert(0, str(SVT_ROOT))

# pylint: disable=wrong-import-position
from setup_gitlab_project import (  # noqa: E402  # test/pipeline, the shared GitLab client
    GitLabClient,
    _validate_namespace,
    _validate_project_name,
    _validate_token,
    _validate_url,
)
from library.vars.catalog_vars import (  # noqa: E402
    CATALOG_STAGE_PREFIX,
    catalog_soft_stages,
    catalog_stage_info,
    catalog_stages,
)
from library.vars.common_vars import INPUTS_FILE  # noqa: E402
from library.vars.theme_vars import (  # noqa: E402
    THEMES,
    default_clean_reinstall,
    default_skip_stages,
    soft_stages,
    stage_info,
    starts_clean,
    theme_title,
)

DEFAULT_CONFIG = HERE / "svt_pipeline_config.yml"
PIPELINE_FILES = (("svt_ci.py", "svt_ci.py"), ("svt_report_page.py", "svt_report_page.py"))
PLACEHOLDER_INPUTS = ("secret.yaml", "values.yaml")
POWERSCALE_EXAMPLES = (TEST_ROOT.parent / "src" / "orchestrator" / "examples"
                       / "powerscale_reference_files" / "CSI_driver")
FIRST_STAGE, LAST_STAGE = "initialization", "summary"
THEME_RESULT = "theme_result"
# First job of a theme that starts from scratch: the shared cleanup and omnia.sh -s again.
CLEAN_INSTALL = "clean_install"
# A theme job without its own timeouts_hours entry takes the entry of this job.
TIMEOUT_ALIASES = {THEME_RESULT: "summary", CLEAN_INSTALL: FIRST_STAGE}
OIM_LOGIN_VAR = "SVT_TARGET_PASS"
CLUSTER_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
# Global keys: config section.key -> CI/CD variable.
GLOBAL_VARIABLES = {
    ("openbao", "auth_role"): "BAO_AUTH_ROLE",
    ("email", "recipients"): "EMAIL_RECIPIENTS",
    ("email", "sender"): "EMAIL_SENDER",
    ("email", "smtp_server"): "SMTP_SERVER",
    ("email", "smtp_port"): "SMTP_PORT",
    ("email", "required"): "SVT_EMAIL_REQUIRED",
    ("svt", "poll_seconds"): "SVT_POLL_SECONDS",
    ("svt", "log_limit_kb"): "SVT_LOG_LIMIT_KB",
}
# Where OpenBao is: ONE place, the openbao block of user_inputs.yml (also what
# ./setup_env.sh --domain-creds-from-openbao reads). Its keys -> CI/CD variable.
THEME_OPENBAO_VARIABLES = {
    "server_url": "BAO_SERVER_URL",
    "secret_path": "BAO_DATA_PATH",
    "tls_skip_verify": "BAO_TLS_SKIP_VERIFY",
}
# Cluster keys: section.key of clusters.<name> -> variable <PREFIX>_<name>.
CLUSTER_VARIABLES = {
    ("target", "ip"): "SVT_TARGET_IP",
    ("target", "user"): "SVT_TARGET_USER",
    ("target", "ssh_skip_host_key"): "SVT_SSH_SKIP_HOST_KEY",
    ("omnia", "repo"): "SVT_OMNIA_REPO",
    ("omnia", "branch"): "SVT_OMNIA_BRANCH",
    ("omnia", "install_path"): "SVT_OMNIA_INSTALL_PATH",
    ("omnia", "checkout_mode"): "SVT_CHECKOUT_MODE",
    ("svt", "clean_reinstall"): "SVT_CLEAN_REINSTALL",
    ("svt", "skip_stages"): "SVT_SKIP_STAGES",
    ("svt", "user_inputs"): "SVT_USER_INPUTS",
    ("", "themes"): "SVT_THEMES",
    ("", "secret_path"): "BAO_DATA_PATH",
}


# ------------------------------------------------------------------ config
def prefix(cluster: str) -> str:
    """Return the CI/CD variable prefix of a cluster (cluster-1 -> CLUSTER_1)."""
    return re.sub(r"[^A-Z0-9]", "_", cluster.upper())


def openbao_variables() -> Dict[str, str]:
    """Return the OpenBao settings of user_inputs.yml (block ``openbao``) as CI/CD values."""
    try:
        with open(INPUTS_FILE, "r", encoding="utf-8") as stream:
            block = (yaml.safe_load(stream) or {}).get("openbao") or {}
    except (OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"cannot read {INPUTS_FILE}: {exc}") from exc
    values = {}
    for key, name in THEME_OPENBAO_VARIABLES.items():
        value = block.get(key)
        text = "" if value is None else str(value).strip()
        values[name] = text.lower() if isinstance(value, bool) else text.strip("/")
    return values


def cluster_themes(config: Dict[str, Any], cluster: str) -> List[str]:
    """Return the SVT themes of a cluster in run order (``clusters.<name>.themes``: a comma
    separated string or a list)."""
    block = (config.get("clusters") or {}).get(cluster) or {}
    raw = block.get("themes")
    items = raw if isinstance(raw, list) else str(raw or "").split(",")
    return [str(item).strip() for item in items if str(item).strip()]


def check_theme_order(cluster: str, themes: List[str]) -> None:
    """Refuse a theme that starts from scratch (build_stream) anywhere but last.

    The other themes share one initialization. A theme that cleans and installs Omnia again in
    its own first job would destroy what the themes after it run on, so it must be the last.
    """
    for index, theme in enumerate(themes):
        if starts_clean(theme) and index != len(themes) - 1:
            others = ",".join(t for t in themes if t != theme)
            raise SystemExit(
                f"clusters.{cluster}.themes: {theme} must be the last theme, not "
                f"{'first' if index == 0 else 'in the middle'} ({', '.join(themes)}). {theme} "
                f"cleans and installs Omnia again in its own clean_install job, so every other "
                f"theme runs before it, for example \"{others},{theme}\"")


def theme_slots(themes: List[str]) -> Tuple[List[str], List[str]]:
    """Return (shared, last) themes of a cluster pipeline: the themes that share the one
    initialization, and the theme that starts from scratch (it is the last one) or none."""
    last = themes[-1:] if starts_clean(themes[-1]) else []
    return [t for t in themes if t not in last], last


def cluster_enabled(config: Dict[str, Any], cluster: str) -> bool:
    """Return whether a cluster is in the default selection (``enabled: false`` leaves it out)."""
    block = (config.get("clusters") or {}).get(cluster) or {}
    return str(block.get("enabled", True)).strip().lower() not in ("false", "no", "0", "off")


def trigger_job(cluster: str) -> str:
    """Return the name of the trigger job of a cluster (one per cluster, all its themes)."""
    return f"svt_{cluster}"


def cluster_ci_file(cluster: str) -> str:
    """Return the cluster pipeline file: preflight, initialization, one trigger per theme,
    summary."""
    return f".gitlab-ci-svt-cluster-{cluster}.yml"


def disabled_stages(theme: str) -> List[str]:
    """Return the optional stages <theme>_test_config.yml turns off (stages: <name>: false)."""
    try:
        with open(SVT_ROOT / f"{theme}_test_config.yml", "r", encoding="utf-8") as stream:
            block = (yaml.safe_load(stream) or {}).get("stages") or {}
    except (OSError, yaml.YAMLError):
        block = {}
    return [name for name in THEMES[theme].get("optional_stages") or () if not block.get(name)]


def ci_file(theme: str) -> str:
    """Return the child pipeline file of a theme (its setup, stages and result jobs)."""
    return f".gitlab-ci-svt-{theme}.yml"


def load_config(path: Path) -> Dict[str, Any]:
    """Return the checked pipeline config."""
    with open(path, "r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream) or {}
    clusters = config.get("clusters") or {}
    if not isinstance(clusters, dict) or not clusters:
        raise SystemExit("clusters: add at least one cluster block (see the comments)")
    for name, block in clusters.items():
        if "theme" in (block or {}):
            raise SystemExit(f"clusters.{name}.theme is replaced by themes: a comma separated "
                             "list of themes that run one after another, e.g. "
                             "themes: \"catalog_build,build_stream\"")
        themes = cluster_themes(config, name)
        unknown = [theme for theme in themes if theme not in THEMES]
        if not themes or unknown or len(set(themes)) != len(themes):
            problem = (f"{', '.join(unknown)} is not a theme of test/system_test" if unknown
                       else "repeats a theme" if themes else "is missing")
            raise SystemExit(f"clusters.{name}.themes {problem} "
                             f"(a list of: {', '.join(THEMES)})")
        check_theme_order(name, themes)
        clusters[name]["themes"] = ",".join(themes)
    bad = [name for name in clusters if not CLUSTER_NAME.fullmatch(str(name))]
    if bad:
        raise SystemExit(f"invalid cluster name(s) {bad}: letters, digits, _ and -")
    by_prefix: Dict[str, List[str]] = {}
    for name in clusters:
        by_prefix.setdefault(prefix(name), []).append(str(name))
    clash = {key: names for key, names in by_prefix.items() if len(names) > 1}
    if clash:
        raise SystemExit("cluster names that give the same variable prefix (their CI/CD "
                         "variables would collide): " + "; ".join(
                             f"{', '.join(names)} -> {key}" for key, names in clash.items())
                         + ". Rename one of them.")
    return config


def _value(block: Dict[str, Any], section: str, key: str) -> Any:
    return (block if not section else (block.get(section) or {})).get(key)


def ci_variables(config: Dict[str, Any]) -> Dict[str, str]:
    """Return the CI/CD variables of the config (without secrets)."""
    variables = {name: "" if _value(config, section, key) is None
                 else str(_value(config, section, key))
                 for (section, key), name in GLOBAL_VARIABLES.items()}
    variables.update(openbao_variables())
    variables["SVT_CLUSTERS"] = ",".join(name for name in config["clusters"]
                                         if cluster_enabled(config, name))
    for cluster, block in config["clusters"].items():
        for (section, key), name in CLUSTER_VARIABLES.items():
            value = _value(block or {}, section, key)
            if value not in (None, ""):
                variables[f"{prefix(cluster)}_{name}"] = str(value)
            elif name != "BAO_DATA_PATH":
                variables[f"{prefix(cluster)}_{name}"] = ""
    return variables


def catalog_plan(theme: str) -> Dict[str, Any]:
    """Return the catalog plan of a catalog theme, resolved from this checkout ({} otherwise).

    The catalog stages are known only after ./setup_env.sh --configure, so the
    pipeline resolves the same plan here (<theme>_test_config.yml and
    ./omnia.sh --list-catalogs of this checkout): one job per catalog. The
    initialization job fails when the plan --configure wrote on the OIM
    differs (SVT_CATALOG_PLAN).
    """
    if not THEMES[theme].get("catalog_plan"):
        return {}
    # pylint: disable=import-outside-toplevel  # only catalog themes need these
    from library.functions.catalog_func import plan
    from library.functions.config_func import ConfigError, load_svt_config
    try:
        settings = load_svt_config(theme)["catalog"]
        return {"settings": settings, "entries": plan(settings)}
    except (ConfigError, ValueError) as exc:
        raise SystemExit(f"catalog plan of {theme}: {exc}") from exc


def theme_stages(theme: str, plan: Dict[str, Any]) -> Tuple[Tuple[str, ...], Tuple[str, ...],
                                                            Dict[str, Tuple[str, str]]]:
    """Return (stages, soft stages, {stage: (title, description)}) of the theme's jobs."""
    if plan:
        return catalog_stages(plan), catalog_soft_stages(plan), catalog_stage_info(plan)
    return (tuple(THEMES[theme]["stages"]), soft_stages(theme),
            dict(THEMES[theme].get("stage_info") or {}))


def plan_variable(plan: Dict[str, Any]) -> str:
    """Return SVT_CATALOG_PLAN: <stage>=<catalog> of every catalog, comma separated."""
    return ",".join(f"{entry['stage']}={entry['catalog']}" for entry in plan.get("entries") or [])


def jobs_of(theme: str, stages: Tuple[str, ...]) -> List[str]:
    """Return the jobs of a theme pipeline in order: the SVT stages, then theme_result. A theme
    starts directly with its first stage: the initialization of the cluster pipeline did the
    cleanup, the installation and the credentials. A theme that starts from scratch has the job
    clean_install first (cleanup, omnia.sh -s, credentials, readiness)."""
    return [*([CLEAN_INSTALL] if starts_clean(theme) else []), *stages, THEME_RESULT]


def _timeout(config: Dict[str, Any], job: str) -> Tuple[str, int]:
    """Return (GitLab timeout, seconds) of a job: its own entry, else catalog_stage for a
    catalog stage, else default_hours."""
    hours = (config.get("svt") or {}).get("timeouts_hours") or {}
    fallback = hours.get("default_hours", 6)
    if job.startswith(CATALOG_STAGE_PREFIX):
        fallback = hours.get("catalog_stage", fallback)
    value = float(hours.get(job, hours.get(TIMEOUT_ALIASES.get(job, ""), fallback)))
    minutes = max(10, int(round(value * 60)))
    return f"{minutes}m", minutes * 60


# ------------------------------------------------------------------ render
HEADER = ("# Generated by test/system_test/pipeline/setup_svt_project.py - do not edit here:\n"
          "# change svt_pipeline_config.yml, then ./setup_svt_project.py --update.\n")


def resource_group(cluster: str) -> str:
    """Return the resource group of a cluster's OIM: one SVT pipeline at a time per OIM."""
    return f"svt-{cluster}"


def _select_job(config: Dict[str, Any]) -> List[str]:
    """Return the ``select_clusters`` job: it prints the clusters of the run with their themes
    (the variable <PREFIX>_SVT_THEMES, or the themes of the config) and fails on a name of
    SVT_CLUSTERS that is not a cluster of the config, on a theme that is not one of the cluster's
    rendered themes, or when nothing is selected. It needs only a shell."""
    known = " ".join(config["clusters"])
    rendered = " ".join(f"{name}={','.join(cluster_themes(config, name))}"
                        for name in config["clusters"])
    variables = " ".join(f"{name}:{prefix(name)}_SVT_THEMES" for name in config["clusters"])
    return [
        "# Fails fast on a wrong SVT_CLUSTERS or <CLUSTER>_SVT_THEMES and shows the clusters and",
        "# themes of this run.",
        "select_clusters:",
        "  stage: select",
        "  script:",
        "    - |",
        f'      known="{known}"',
        f'      rendered="{rendered}"',
        f'      themevars="{variables}"',
        '      selected=""; bad=""; badtheme=""',
        '      for name in $(printf "%s" "$SVT_CLUSTERS" | tr "," " "); do',
        '        case " $known " in',
        '          *" $name "*) selected="$selected $name" ;;',
        '          *) bad="$bad $name" ;;',
        "        esac",
        "      done",
        '      if [ -n "$bad" ]; then',
        '        echo "ERROR: SVT_CLUSTERS names a cluster that is not in the config:$bad"',
        '        echo "Known clusters: $known"',
        "        exit 1",
        "      fi",
        '      if [ -z "$selected" ]; then',
        '        echo "ERROR: SVT_CLUSTERS selects no cluster [$SVT_CLUSTERS]; known: $known"',
        "        exit 1",
        "      fi",
        '      echo "SVT clusters of this run (themes run in this order):"',
        "      for name in $selected; do",
        '        allowed=""',
        '        for item in $rendered; do',
        '          if [ "${item%%=*}" = "$name" ]; then allowed="${item#*=}"; fi',
        "        done",
        '        chosen="$allowed"',
        '        for item in $themevars; do',
        '          if [ "${item%%:*}" != "$name" ]; then continue; fi',
        '          var="${item#*:}"; value="$(printenv "$var" || true)"',
        '          if [ -n "$value" ]; then chosen="$value"; fi',
        "        done",
        '        for theme in $(printf "%s" "$chosen" | tr "," " "); do',
        '          case ",$allowed," in',
        '            *",$theme,"*) ;;',
        '            *) badtheme="$badtheme $name:$theme" ;;',
        "          esac",
        "        done",
        '        echo "  $name: $chosen"',
        "      done",
        '      if [ -n "$badtheme" ]; then',
        '        echo "ERROR: a themes variable names a theme not rendered here:$badtheme"',
        '        echo "Rendered themes: $rendered (change clusters.<name>.themes, run --update)"',
        "        exit 1",
        "      fi",
        "",
    ]


def render_parent(config: Dict[str, Any]) -> str:
    """Return .gitlab-ci.yml: one trigger job per cluster, each holding its resource group.

    Each cluster's SVT is a child pipeline (.gitlab-ci-svt-cluster-<name>.yml: preflight,
    initialization, one trigger per theme, summary) with SVT_CLUSTER set. The clusters run at
    the same time, and a second pipeline for the same OIM waits until the first one ends.
    SVT_CLUSTERS (default: every enabled cluster) picks the clusters of a run.
    """
    lines = [
        HEADER.rstrip("\n"),
        "# Clusters: " + ", ".join(f"{name} ({', '.join(cluster_themes(config, name))})"
                                   for name in config["clusters"]),
        "workflow:",
        "  rules:",
        "    - if: '$CI_PIPELINE_SOURCE =~ /^(web|api|schedule|trigger|pipeline)$/'",
        "",
        "stages:",
        "  - select",
        "  - svt",
        "",
        *_select_job(config),
    ]
    for cluster in config["clusters"]:
        lines += [
            f"{trigger_job(cluster)}:",
            "  stage: svt",
            f'  resource_group: "{resource_group(cluster)}"',
            "  rules:",
            f"    - if: '$SVT_CLUSTERS =~ /(^|,) *{cluster} *(,|$)/'",
            "  variables:",
            f'    SVT_CLUSTER: "{cluster}"',
            f'    SVT_SKIP_STAGES: "${prefix(cluster)}_SVT_SKIP_STAGES"',
            "  trigger:",
            "    include:",
            f"      - local: {cluster_ci_file(cluster)}",
            "    strategy: depend",
            "    forward:",
            "      yaml_variables: true",
            "      pipeline_variables: true",
            "",
        ]
    return "\n".join(lines)


def _default_block() -> List[str]:
    return ["default:", "  after_script:", "    - python3 svt_ci.py after-job || true",
            "  artifacts:", "    when: always", "    paths:", "      - pipeline_job_status/",
            "      - svt_ci/", ""]


def credential_domains(themes: List[str]) -> List[str]:
    """Return the credential stores the themes need, once each, in theme order (the initialization
    job writes them all: a later theme starts without reading OpenBao again)."""
    domains: List[str] = []
    for theme in themes:
        for domain in THEMES[theme]["credential_domains"]:
            if domain not in domains:
                domains.append(domain)
    return domains


def render_cluster_ci(config: Dict[str, Any], cluster: str) -> Tuple[str, int]:
    """Return (the cluster pipeline text, longest job timeout in seconds).

    preflight (the Omnia checkout) runs once, then one trigger job per theme in the order of
    clusters.<name>.themes (a theme runs whether the one before passed or failed), then the one
    summary with the combined report and email. Each theme trigger opens as its own pipeline.
    The initialization is the complete start of the OIM (cleanup, install, the Omnia environment,
    credentials, readiness), once, for the themes that share it. A theme that starts from scratch
    (build_stream) is the last one and does its own clean_install job.
    """
    themes = cluster_themes(config, cluster)
    shared, last = theme_slots(themes)
    jobs = ["preflight", *([FIRST_STAGE] if shared else []),
            *[f"theme_{t}" for t in shared + last], LAST_STAGE]
    var = f"{prefix(cluster)}_SVT_THEMES"
    longest = max(_timeout(config, job)[1] for job in ("preflight", FIRST_STAGE, LAST_STAGE))
    plans = [(theme, plan_variable(catalog_plan(theme))) for theme in themes]
    lines = [
        HEADER.rstrip("\n"),
        f"# SVT cluster {cluster}: " + " -> ".join(jobs),
        "workflow:",
        f'  name: "SVT {cluster}: {" then ".join(themes)}"',
        "  rules:",
        "    - if: '$CI_PIPELINE_SOURCE == \"parent_pipeline\"'",
        "",
        "variables:",
        f'  SVT_THEME_ORDER: "{",".join(themes)}"',
        f'  SVT_JOB_ORDER: "{",".join(jobs)}"',
        f'  SVT_CREDENTIAL_DOMAINS: "{",".join(credential_domains(themes))}"',
        f'  SVT_CLEAN_INSTALL_THEMES: "{",".join(t for t in themes if starts_clean(t))}"',
        # The initialization job runs once with the first theme of the run (the cluster's
        # <PREFIX>_SVT_THEMES can select a subset): that theme's defaults apply when the cluster's
        # <PREFIX>_SVT_CLEAN_REINSTALL and <PREFIX>_SVT_SKIP_STAGES are empty.
        *[f'  SVT_INIT_DEFAULT_CLEAN_REINSTALL_{theme.upper()}: '
          f'"{str(default_clean_reinstall(theme)).lower()}"' for theme in themes],
        *[f'  SVT_INIT_DEFAULT_SKIP_STAGES_{theme.upper()}: '
          f'"{",".join(default_skip_stages(theme))}"'
          for theme in themes],
        *[f'  SVT_CATALOG_PLAN_{theme.upper()}: "{plan}"' for theme, plan in plans if plan],
        '  GIT_DEPTH: "1"',
        "",
        "stages:",
        *[f"  - {job}" for job in jobs],
        "",
        *_default_block(),
        "# SSH to the OIM, OpenBao reachable, Omnia checkout on the OIM, svt/ inputs copied",
        "preflight:", "  stage: preflight", f"  timeout: {_timeout(config, 'preflight')[0]}",
        "  script:", "    - python3 svt_ci.py preflight", "",
    ]
    init_lines = [
        "# The complete initialization, once: configure, the clean reinstall (shared cleanup of",
        "# user_inputs.yml, then omnia.sh -s and the Omnia environment), OpenBao credentials,",
        "# PowerScale CSI files and the readiness checks. The themes that share it start at their first stage.",
        f"{FIRST_STAGE}:", f"  stage: {FIRST_STAGE}",
        f"  timeout: {_timeout(config, FIRST_STAGE)[0]}",
        "  id_tokens:", "    VAULT_ID_TOKEN:", "      aud: $BAO_SERVER_URL",
        "  script:", "    - python3 svt_ci.py initialization", "",
    ]
    blocks: Dict[str, List[str]] = {}
    for index, theme in enumerate(themes):
        blocks[theme] = [
            f"# Theme {theme}: {theme_title(theme)} (its jobs are in {ci_file(theme)})",
            f"theme_{theme}:", f"  stage: theme_{theme}",
            "  # A failed theme does not stop the next one; the summary still fails the pipeline.",
            "  allow_failure: true",
            "  rules:",
            f"    - if: '$SVT_SKIP_STAGES =~ /(^|,) *theme_{theme} *(,|$)/'",
            "      when: never",
            f"    - if: '${var} == null || ${var} == \"\" || ${var} =~ /(^|,) *{theme} *(,|$)/'",
            "      when: on_success",
            "  variables:",
            f'    SVT_THEME: "{theme}"',
            f'    SVT_THEME_INDEX: "{index}"',
            f'    SVT_THEME_NUMBER: "{index + 1}"',
            f'    SVT_THEME_COUNT: "{len(themes)}"',
            '    SVT_CLUSTER_PIPELINE_ID: "$CI_PIPELINE_ID"',
            '    SVT_CLUSTER_PIPELINE_CREATED_AT: "$CI_PIPELINE_CREATED_AT"',
            "  trigger:", "    include:", f"      - local: {ci_file(theme)}",
            "    strategy: depend", "    forward:", "      yaml_variables: true",
            "      pipeline_variables: true", "",
        ]
    if shared:
        lines += init_lines
    for theme in shared + last:
        lines += blocks[theme]
    lines += [
        "# ONE report (svt_report/svt_report.html: an overview and a page per theme) and one email",
        f"{LAST_STAGE}:", f"  stage: {LAST_STAGE}", f"  timeout: {_timeout(config, LAST_STAGE)[0]}",
        "  when: always", "  artifacts:", "    when: always", "    expire_in: 30 days",
        "    paths:", "      - svt_report/", "      - svt_ci/", "      - pipeline_job_status/",
        "    reports:", "      junit: svt_report/junit/*.xml",
        "  script:", "    - python3 svt_ci.py summary", "",
    ]
    return "\n".join(lines), longest


def render_ci(config: Dict[str, Any], theme: str) -> Tuple[str, int]:
    """Return (the pipeline text of ``theme``, longest job timeout in seconds).

    The jobs of one theme: its stages, then theme_result (the theme's report and verdict). There
    is no setup job: preflight, initialization (cleanup, install, credentials, readiness) and
    summary are in the cluster pipeline, once. The first stage job of a theme after the first
    starts that theme's run (no cleanup) before its stage.
    """
    plan = catalog_plan(theme)
    stages, soft, info = theme_stages(theme, plan)
    jobs = jobs_of(theme, stages)
    longest = max(_timeout(config, job)[1] for job in jobs)
    lines = [
        HEADER.rstrip("\n"),
        f"# SVT theme {theme}: {theme_title(theme)} (child of the cluster pipeline, "
        f"{ci_file(theme)})",
        "# Jobs: " + " -> ".join(jobs),
        "workflow:",
        "  name: 'SVT $SVT_CLUSTER, theme $SVT_THEME_NUMBER of $SVT_THEME_COUNT: $SVT_THEME'",
        "  rules:",
        "    - if: '$CI_PIPELINE_SOURCE == \"parent_pipeline\"'",
        "",
        "variables:",
        f'  SVT_THEME: "{theme}"',
        f'  SVT_JOB_ORDER: "{",".join(jobs)}"',
        f'  SVT_CREDENTIAL_DOMAINS: "{",".join(THEMES[theme]["credential_domains"])}"',
        # Used when the cluster's <PREFIX>_SVT_CLEAN_REINSTALL is empty.
        f'  SVT_DEFAULT_CLEAN_REINSTALL: "{str(default_clean_reinstall(theme)).lower()}"',
        f'  SVT_DEFAULT_SKIP_STAGES: "{",".join(default_skip_stages(theme))}"',
        *([f'  SVT_CATALOG_PLAN: "{plan_variable(plan)}"'] if plan else []),
        '  GIT_DEPTH: "1"',
        "",
        "stages:",
        *[f"  - {job}" for job in jobs],
        "",
        *_default_block(),
    ]
    descriptions = {THEME_RESULT: ("Result", "the theme's SVT summary and verdict, kept for "
                                   "the cluster summary"),
                    CLEAN_INSTALL: ("Clean install", "the shared cleanup, omnia.sh -s, the "
                                    "credentials and the readiness checks again, from scratch")}
    for job in jobs:
        timeout = _timeout(config, job)[0]
        title, description = descriptions.get(job) or info.get(job) or stage_info(theme, job)
        lines += [f"# {title}: {description}", f"{job}:", f"  stage: {job}",
                  f"  timeout: {timeout}"]
        if job in soft:
            lines += ["  # A failure here does not stop the stages after it; the verdict fails.",
                      "  allow_failure: true"]
        if job in stages:
            off = job in disabled_stages(theme)
            lines += ["  rules:"]
            if off:
                # Off in <theme>_test_config.yml stages:, whatever SVT_SKIP_STAGES says.
                lines += ["    - when: never"]
            else:
                lines += [f"    - if: '$SVT_SKIP_STAGES =~ /(^|,) *{job} *(,|$)/'",
                          "      when: never"]
            if job in default_skip_stages(theme) and not off:
                # Left out by default (empty SVT_SKIP_STAGES); "none" or another list runs it.
                lines += ["    - if: '$SVT_SKIP_STAGES == null || $SVT_SKIP_STAGES == \"\"'",
                          "      when: never"]
            lines += ["    - when: on_success",
                      "  script:", f"    - python3 svt_ci.py stage {job}"]
        elif job == CLEAN_INSTALL:
            lines += ["  id_tokens:", "    VAULT_ID_TOKEN:", "      aud: $BAO_SERVER_URL",
                      "  rules:", f"    - if: '$SVT_SKIP_STAGES =~ /(^|,) *{job} *(,|$)/'",
                      "      when: never", "    - when: on_success",
                      "  script:", "    - python3 svt_ci.py clean-install"]
        else:
            lines += ["  when: always", "  script:", "    - python3 svt_ci.py theme-result"]
        lines.append("")
    return "\n".join(lines), longest


# ------------------------------------------------------------------ gitlab
def _client(args: argparse.Namespace) -> GitLabClient:
    token = os.environ.get("GITLAB_TOKEN") or getpass.getpass("GitLab API token: ")
    return GitLabClient(_validate_url(args.gitlab_url), _validate_token(token),
                        verify_ssl=not args.no_verify_ssl)


def _project(client: GitLabClient, config: Dict[str, Any], create: bool) -> Dict[str, Any]:
    gitlab = config.get("gitlab") or {}
    name = _validate_project_name(str(gitlab.get("project_name") or "omnia-svt"))
    namespace = _validate_namespace(str(gitlab.get("namespace") or "root"))
    project = client.find_project(f"{namespace}/{name}")
    if project:
        return project
    if not create:
        raise SystemExit(f"project {namespace}/{name} not found: use --create")
    print(f"creating project {namespace}/{name}")
    return client.create_project(name, namespace)


def _files(config: Dict[str, Any], config_path: Path) -> List[Tuple[str, str]]:
    """Return (repo path, content) of the pipeline files (always committed)."""
    files = [(".gitlab-ci.yml", render_parent(config)),
             *[(cluster_ci_file(cluster), render_cluster_ci(config, cluster)[0])
               for cluster in config["clusters"]],
             *[(ci_file(theme), render_ci(config, theme)[0]) for theme in THEMES],
             ("svt_pipeline_config.yml", config_path.read_text(encoding="utf-8"))]
    return files + [(repo, (HERE / local).read_text(encoding="utf-8"))
                    for local, repo in PIPELINE_FILES]


def _input_files(config: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return (repo path, content) of every cluster's SVT inputs, from test/system_test."""
    names = ["user_inputs.yml", *[f"{theme}_test_config.yml" for theme in THEMES
                                  if (SVT_ROOT / f"{theme}_test_config.yml").is_file()]]
    return [(f"clusters/{cluster}/svt/{name}", (SVT_ROOT / name).read_text(encoding="utf-8"))
            for cluster in config["clusters"] for name in names]


def _placeholder_files(config: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return (repo path, content) of the PowerScale CSI secret.yaml and values.yaml of every
    cluster: the product's reference examples. The user edits them in the project for the
    array, so they are only ever added when missing, never replaced (not even by
    --update-inputs)."""
    return [(f"clusters/{cluster}/svt/{name}", (POWERSCALE_EXAMPLES / name).read_text(
        encoding="utf-8"))
            for cluster in config["clusters"] for name in PLACEHOLDER_INPUTS
            if (POWERSCALE_EXAMPLES / name).is_file()]


def _commit(client: GitLabClient, project_id: int, branch: str,
            files: List[Tuple[str, str]], only_missing: bool = False) -> None:
    """Commit ``files``; with ``only_missing`` a file already in the project is kept."""
    actions = []
    for path, content in files:
        exists = client.file_exists(project_id, path, ref=branch)
        if exists and only_missing:
            print(f"  kept     {path} (already in the project; --update-inputs replaces it)")
            continue
        actions.append({"action": "update" if exists else "create", "file_path": path,
                        "content": content})
    if not actions:
        return
    client.commit_files(project_id, actions, "SVT pipeline files (setup_svt_project.py)",
                        branch=branch)
    for action in actions:
        print(f"  committed {action['file_path']}")


def _set_password(client: GitLabClient, project_id: int, cluster: str) -> None:
    """Store a cluster's OIM SSH password as a masked, protected variable (never printed)."""
    key = f"{prefix(cluster)}_{OIM_LOGIN_VAR}"
    value = os.environ.get(key) or getpass.getpass(f"OIM SSH password of {cluster} ({key}): ")
    if not value:
        print(f"  {key} not set (use {prefix(cluster)}_SVT_SSH_KEY, a file variable, instead)")
        return
    payload = {"key": key, "value": value, "protected": True, "masked": True,
               "variable_type": "env_var"}
    # pylint: disable=protected-access
    exists = client._get(f"/projects/{project_id}/variables/{key}").status_code == 200
    for masked in (True, False):
        payload["masked"] = masked
        response = (client._put(f"/projects/{project_id}/variables/{key}", json=payload)
                    if exists else client._post(f"/projects/{project_id}/variables",
                                                json=payload))
        if response.status_code in (200, 201):
            print(f"  set {key} (protected{', masked' if masked else ''})")
            if not masked:
                print("  WARNING: GitLab could not mask this value (masking rules); it is "
                      "protected and never printed by the pipeline")
            return
    raise SystemExit(f"could not set {key}: HTTP {response.status_code}")


def _scan_host_key(address: str) -> str:
    """Return the ssh-keyscan lines of an OIM ("" when it does not answer)."""
    try:
        done = subprocess.run(  # nosec B603 B607  # fixed list, address from the config
            ["ssh-keyscan", "-T", "10", "-t", "ed25519,ecdsa,rsa", address],
            capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return "\n".join(line for line in done.stdout.splitlines()
                     if line.strip() and not line.startswith("#"))


def _fingerprints(lines: str) -> List[str]:
    """Return the ssh-keygen fingerprint lines of known_hosts text."""
    try:
        done = subprocess.run(  # nosec B603 B607  # fixed list, text on stdin
            ["ssh-keygen", "-lf", "-"], input=lines, capture_output=True, text=True,
            timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [line.strip() for line in done.stdout.splitlines() if line.strip()]


def _set_file_variable(client: GitLabClient, project_id: int, key: str, value: str) -> None:
    """Create or update a protected File variable (its value is never printed)."""
    state = client.set_variable(project_id, key, value, var_type="file", protected=True)
    print(f"  {state} {key} (File, protected)")


def _store_host_keys(client: GitLabClient, project_id: int, config: Dict[str, Any]) -> None:
    """--scan-host-keys: store every cluster's OIM host key as <CLUSTER>_SVT_SSH_KNOWN_HOSTS."""
    for cluster, block in config["clusters"].items():
        address = str(_value(block or {}, "target", "ip") or "")
        if not address:
            print(f"  {cluster}: target.ip is empty, host key not scanned")
            continue
        lines = _scan_host_key(address)
        if not lines:
            print(f"  {cluster}: ssh-keyscan found no host key at {address} (is ssh-keyscan "
                  "installed and port 22 reachable from here?)")
            continue
        _set_file_variable(client, project_id, f"{prefix(cluster)}_SVT_SSH_KNOWN_HOSTS", lines)
        for line in _fingerprints(lines):
            print(f"    {line}")
        print("    compare with the OIM: ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub")


def apply(args: argparse.Namespace, config: Dict[str, Any], config_path: Path) -> int:
    """--create / --update: commit the files, set the variables and the CI timeout."""
    client = _client(args)
    project = _project(client, config, create=args.create)
    project_id = project["id"]
    branch = str((config.get("gitlab") or {}).get("branch") or "main")
    longest = max([render_ci(config, theme)[1] for theme in THEMES]
                  + [render_cluster_ci(config, cluster)[1] for cluster in config["clusters"]])
    _commit(client, project_id, branch, _files(config, config_path))
    _commit(client, project_id, branch, _input_files(config),
            only_missing=not args.update_inputs)
    _commit(client, project_id, branch, _placeholder_files(config), only_missing=True)
    for name, value in sorted(ci_variables(config).items()):
        print(f"  {client.set_variable(project_id, name, value)} {name} = {value}")
    if args.create or args.set_password:
        for cluster in config["clusters"]:
            _set_password(client, project_id, cluster)
    if args.scan_host_keys:
        _store_host_keys(client, project_id, config)
    if args.bao_cacert:
        _set_file_variable(client, project_id, "BAO_CACERT",
                           Path(args.bao_cacert).read_text(encoding="utf-8"))
    # pylint: disable-next=protected-access
    response = client._put(f"/projects/{project_id}", json={"build_timeout": longest})
    print(f"  project CI timeout: {longest // 3600}h{(longest % 3600) // 60:02d}m "
          f"(HTTP {response.status_code})")
    print(f"\nProject: {project.get('web_url', '')}\nNext: edit clusters/<name>/svt/"
          f"user_inputs.yml and the <theme>_test_config.yml of each cluster in the project, "
          f"then CI/CD > Pipelines > Run pipeline (branch {branch}).")
    return 0


def set_variables(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    """--set-variables: rewrite the CI/CD variables of the config; commit nothing else."""
    client = _client(args)
    project = _project(client, config, create=False)
    for name, value in sorted(ci_variables(config).items()):
        print(f"  {client.set_variable(project['id'], name, value)} {name} = {value}")
    print("Only the CI/CD variables changed; --update is for the CI files, timeouts or a theme.")
    return 0


def validate(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    """Lint the rendered .gitlab-ci.yml with the project's CI lint API."""
    client = _client(args)
    project = _project(client, config, create=False)
    valid = True
    for name, text in ((".gitlab-ci.yml", render_parent(config)),
                       *[(cluster_ci_file(cluster), render_cluster_ci(config, cluster)[0])
                         for cluster in config["clusters"]],
                       *[(ci_file(theme), render_ci(config, theme)[0]) for theme in THEMES]):
        result = client.lint_ci(project["id"], text)
        valid = valid and bool(result.get("valid"))
        print(f"{name}: valid {result.get('valid')}")
        for message in (result.get("errors") or []) + (result.get("warnings") or []):
            print(f"  {message}")
    return 0 if valid else 1


def main(argv: List[str]) -> int:
    """Parse the arguments and run the command."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument("--render", action="store_true", help="print the .gitlab-ci.yml")
    command.add_argument("--create", action="store_true", help="create or fill the project")
    command.add_argument("--update", action="store_true", help="update files and variables")
    command.add_argument("--validate", action="store_true", help="GitLab CI lint")
    command.add_argument("--set-variables", action="store_true",
                         help="rewrite only the CI/CD variables of the config (email, polling, "
                              "skip stages, checkout mode, clusters): no file is committed")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--gitlab-url", help="GitLab URL (all commands but --render)")
    parser.add_argument("--update-inputs", action="store_true",
                        help="replace every cluster's clusters/<name>/svt/ inputs with the "
                             "files of test/system_test")
    parser.add_argument("--set-password", action="store_true",
                        help="--update: set every cluster's <CLUSTER>_SVT_TARGET_PASS again")
    parser.add_argument("--scan-host-keys", action="store_true",
                        help="--create/--update: store each cluster's OIM host key (ssh-keyscan) "
                             "as <CLUSTER>_SVT_SSH_KNOWN_HOSTS, which the jobs require")
    parser.add_argument("--bao-cacert", metavar="FILE",
                        help="--create/--update: store this OpenBao CA certificate (PEM) as "
                             "the File variable BAO_CACERT")
    parser.add_argument("--no-verify-ssl", action="store_true")
    args = parser.parse_args(argv)
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    if args.render:
        print(f"# ===== .gitlab-ci.yml\n{render_parent(config)}")
        for cluster in config["clusters"]:
            print(f"\n# ===== {cluster_ci_file(cluster)}\n{render_cluster_ci(config, cluster)[0]}")
        for theme in THEMES:
            print(f"\n# ===== {ci_file(theme)}\n{render_ci(config, theme)[0]}")
        return 0
    if not args.gitlab_url:
        parser.error("--gitlab-url is required")
    if (args.scan_host_keys or args.bao_cacert or args.set_password or args.update_inputs) and not (
            args.create or args.update):
        parser.error("--scan-host-keys, --bao-cacert, --set-password and --update-inputs go "
                     "with --create or --update")
    if args.bao_cacert and not Path(args.bao_cacert).is_file():
        parser.error(f"--bao-cacert: {args.bao_cacert} is not a file")
    if args.validate:
        return validate(args, config)
    return set_variables(args, config) if args.set_variables else apply(args, config, config_path)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
