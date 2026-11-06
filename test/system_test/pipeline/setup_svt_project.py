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
cluster's resource group), .gitlab-ci-svt.yml (the jobs: the theme's stages
and the configured timeouts), svt_ci.py, the config (reference copy) and, per
cluster, clusters/<name>/svt/user_inputs.yml and <theme>_test_config.yml
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
from library.vars.theme_vars import THEMES, stage_info, theme_title  # noqa: E402

DEFAULT_CONFIG = HERE / "svt_pipeline_config.yml"
PIPELINE_FILES = (("svt_ci.py", "svt_ci.py"),)
FIRST_STAGE, LAST_STAGE = "initialization", "summary"
PASSWORD_VAR = "SVT_TARGET_PASS"
CLUSTER_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
# Global keys: config section.key -> CI/CD variable.
GLOBAL_VARIABLES = {
    ("openbao", "server_url"): "BAO_SERVER_URL",
    ("openbao", "auth_role"): "BAO_AUTH_ROLE",
    ("openbao", "secret_path"): "BAO_DATA_PATH",
    ("openbao", "tls_skip_verify"): "BAO_TLS_SKIP_VERIFY",
    ("email", "recipients"): "EMAIL_RECIPIENTS",
    ("email", "sender"): "EMAIL_SENDER",
    ("email", "smtp_server"): "SMTP_SERVER",
    ("email", "smtp_port"): "SMTP_PORT",
    ("email", "required"): "SVT_EMAIL_REQUIRED",
    ("svt", "poll_seconds"): "SVT_POLL_SECONDS",
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
    ("", "secret_path"): "BAO_DATA_PATH",
}


# ------------------------------------------------------------------ config
def prefix(cluster: str) -> str:
    """Return the CI/CD variable prefix of a cluster (cluster-1 -> CLUSTER_1)."""
    return re.sub(r"[^A-Z0-9]", "_", cluster.upper())


def load_config(path: Path) -> Dict[str, Any]:
    """Return the checked pipeline config."""
    with open(path, "r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream) or {}
    theme = str((config.get("svt") or {}).get("theme") or "")
    if theme not in THEMES:
        raise SystemExit(f"svt.theme {theme!r} is not a theme of test/system_test "
                         f"(known: {', '.join(THEMES)})")
    clusters = config.get("clusters") or {}
    if not isinstance(clusters, dict) or not clusters:
        raise SystemExit("clusters: add at least one cluster block (see the comments)")
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
    variables["SVT_CLUSTERS"] = ",".join(config["clusters"])
    for cluster, block in config["clusters"].items():
        for (section, key), name in CLUSTER_VARIABLES.items():
            value = _value(block or {}, section, key)
            if value not in (None, ""):
                variables[f"{prefix(cluster)}_{name}"] = str(value)
            elif name != "BAO_DATA_PATH":
                variables[f"{prefix(cluster)}_{name}"] = ""
    return variables


def jobs_of(theme: str) -> List[str]:
    """Return the pipeline jobs in order: preflight, checkout, the SVT stages, summary."""
    return ["preflight", "checkout", FIRST_STAGE, *THEMES[theme]["stages"], LAST_STAGE]


def _timeout(config: Dict[str, Any], job: str) -> Tuple[str, int]:
    hours = (config.get("svt") or {}).get("timeouts_hours") or {}
    value = float(hours.get(job, hours.get("default_hours", 6)))
    minutes = max(10, int(round(value * 60)))
    return f"{minutes}m", minutes * 60


# ------------------------------------------------------------------ render
HEADER = ("# Generated by test/system_test/pipeline/setup_svt_project.py - do not edit here:\n"
          "# change svt_pipeline_config.yml, then ./setup_svt_project.py --update.\n")


def resource_group(cluster: str) -> str:
    """Return the resource group of a cluster's OIM: one SVT pipeline at a time per OIM."""
    return f"svt-{cluster}"


def render_parent(config: Dict[str, Any]) -> str:
    """Return .gitlab-ci.yml: one trigger job per cluster, each holding its resource group.

    Each cluster's SVT is a child pipeline (.gitlab-ci-svt.yml) with
    SVT_CLUSTER set; the clusters run at the same time, and a second pipeline
    for the same OIM waits until the first one ends. SVT_CLUSTERS (default:
    every cluster) picks the clusters of a run.
    """
    theme = config["svt"]["theme"]
    lines = [
        HEADER.rstrip("\n"),
        f"# SVT theme {theme}: {theme_title(theme)}. The jobs are in .gitlab-ci-svt.yml.",
        f"# Clusters: {', '.join(config['clusters'])}",
        "workflow:",
        "  rules:",
        "    - if: '$CI_PIPELINE_SOURCE =~ /^(web|api|schedule|trigger|pipeline)$/'",
        "",
        "stages:",
        "  - svt",
        "",
    ]
    for cluster in config["clusters"]:
        lines += [
            f"svt_{cluster}:",
            "  stage: svt",
            f'  resource_group: "{resource_group(cluster)}"',
            "  rules:",
            f"    - if: '$SVT_CLUSTERS =~ /(^|,) *{cluster} *(,|$)/'",
            "  variables:",
            f'    SVT_CLUSTER: "{cluster}"',
            f'    SVT_SKIP_STAGES: "${prefix(cluster)}_SVT_SKIP_STAGES"',
            "  trigger:",
            "    include:",
            "      - local: .gitlab-ci-svt.yml",
            "    strategy: depend",
            "    forward:",
            "      yaml_variables: true",
            "      pipeline_variables: true",
            "",
        ]
    return "\n".join(lines)


def render_ci(config: Dict[str, Any]) -> Tuple[str, int]:
    """Return (.gitlab-ci-svt.yml text, longest job timeout in seconds)."""
    theme = config["svt"]["theme"]
    jobs = jobs_of(theme)
    bao = bool((config.get("openbao") or {}).get("server_url"))
    longest = max(_timeout(config, job)[1] for job in jobs)
    lines = [
        HEADER.rstrip("\n"),
        f"# SVT theme {theme}: {theme_title(theme)} (child of .gitlab-ci.yml)",
        "# Jobs: " + " -> ".join(jobs),
        "workflow:",
        "  rules:",
        "    - if: '$CI_PIPELINE_SOURCE == \"parent_pipeline\"'",
        "",
        "variables:",
        f'  SVT_THEME: "{theme}"',
        f'  SVT_JOB_ORDER: "{",".join(jobs)}"',
        f'  SVT_CREDENTIAL_DOMAINS: "{",".join(THEMES[theme]["credential_domains"])}"',
        '  GIT_DEPTH: "1"',
        "",
        "stages:",
        *[f"  - {job}" for job in jobs],
        "",
        "default:",
        "  after_script:",
        "    - python3 svt_ci.py after-job || true",
        "  artifacts:",
        "    when: always",
        "    paths:",
        "      - pipeline_job_status/",
        "      - svt_ci/",
        "",
    ]
    for job in jobs:
        timeout = _timeout(config, job)[0]
        title, description = stage_info(theme, job) if job not in ("preflight", "checkout") \
            else (job.title(), {"preflight": "SSH to the OIM, OpenBao reachable",
                                "checkout": "Omnia checkout on the OIM, svt/ inputs copied"}[job])
        lines += [f"# {title}: {description}", f"{job}:", f"  stage: {job}",
                  f"  timeout: {timeout}"]
        if job == FIRST_STAGE and bao:
            lines += ["  id_tokens:", "    VAULT_ID_TOKEN:", "      aud: $BAO_SERVER_URL"]
        if job in THEMES[theme]["stages"]:
            lines += ["  rules:",
                      f"    - if: '$SVT_SKIP_STAGES =~ /(^|,) *{job} *(,|$)/'",
                      "      when: never",
                      "    - when: on_success",
                      "  script:", f"    - python3 svt_ci.py stage {job}"]
        elif job == LAST_STAGE:
            lines += ["  when: always", "  artifacts:", "    when: always",
                      "    expire_in: 30 days", "    paths:", "      - svt_report/",
                      "      - svt_ci/", "      - pipeline_job_status/",
                      "    reports:", "      junit: svt_report/junit/*.xml",
                      "  script:", "    - python3 svt_ci.py summary"]
        else:
            lines += ["  script:", f"    - python3 svt_ci.py {job}"]
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
             (".gitlab-ci-svt.yml", render_ci(config)[0]),
             ("svt_pipeline_config.yml", config_path.read_text(encoding="utf-8"))]
    return files + [(repo, (HERE / local).read_text(encoding="utf-8"))
                    for local, repo in PIPELINE_FILES]


def _input_files(config: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return (repo path, content) of every cluster's SVT inputs, from test/system_test."""
    names = ("user_inputs.yml", f"{config['svt']['theme']}_test_config.yml")
    return [(f"clusters/{cluster}/svt/{name}", (SVT_ROOT / name).read_text(encoding="utf-8"))
            for cluster in config["clusters"] for name in names]


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
    key = f"{prefix(cluster)}_{PASSWORD_VAR}"
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
    _, longest = render_ci(config)
    _commit(client, project_id, branch, _files(config, config_path))
    if args.create or args.update_inputs:
        _commit(client, project_id, branch, _input_files(config),
                only_missing=not args.update_inputs)
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
          f"user_inputs.yml and {config['svt']['theme']}_test_config.yml in the project, "
          f"then CI/CD > Pipelines > Run pipeline (branch {branch}).")
    return 0


def validate(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    """Lint the rendered .gitlab-ci.yml with the project's CI lint API."""
    client = _client(args)
    project = _project(client, config, create=False)
    valid = True
    for name, text in ((".gitlab-ci.yml", render_parent(config)),
                       (".gitlab-ci-svt.yml", render_ci(config)[0])):
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
        print(f"# ===== .gitlab-ci.yml\n{render_parent(config)}\n"
              f"# ===== .gitlab-ci-svt.yml\n{render_ci(config)[0]}")
        return 0
    if not args.gitlab_url:
        parser.error("--gitlab-url is required")
    if (args.scan_host_keys or args.bao_cacert) and not (args.create or args.update):
        parser.error("--scan-host-keys and --bao-cacert go with --create or --update")
    if args.bao_cacert and not Path(args.bao_cacert).is_file():
        parser.error(f"--bao-cacert: {args.bao_cacert} is not a file")
    return validate(args, config) if args.validate else apply(args, config, config_path)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
