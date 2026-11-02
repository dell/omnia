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

"""Create or update the GitLab project that runs the Omnia SVT pipeline.

    ./setup_project.py --gitlab-url https://gitlab.example.com \
        --project root/omnia-svt [--cluster cluster1 ...] [--cacert ca.crt]

The GitLab token is read from a hidden prompt (or --token-stdin); it is never
an argument, an environment value or printed. TLS is always verified.
Pushed in one commit ([skip ci]):
  .gitlab-ci.yml, ci/ (themes, scripts)          always updated
  clusters/<cluster>/cluster.yml                 template, kept when present
  clusters/<cluster>/user_inputs.yml             test/system_test/user_inputs.yml
  clusters/<cluster>/test_config.yml             test/build_stream/test_config.yml
Then it reports the GitLab version, raises the project CI timeout, makes sure
the default branch is protected and checks the runners' maximum timeout.
"""

import argparse
import base64
import getpass
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "project_template")
SVT_ROOT = os.path.dirname(HERE)
CLUSTER_SOURCES = {
    "cluster.yml": os.path.join(TEMPLATE, "clusters", "cluster1", "cluster.yml"),
    "user_inputs.yml": os.path.join(SVT_ROOT, "user_inputs.yml"),
    "test_config.yml": os.path.join(os.path.dirname(SVT_ROOT), "build_stream", "test_config.yml"),
}
PROJECT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}(/[A-Za-z0-9][A-Za-z0-9._-]{0,99}){1,3}")
CLUSTER_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}")
PROJECT_TIMEOUT_SECONDS = 86400
LONGEST_STAGE_SECONDS = 43200
MIN_OPTIONS_VERSION = (15, 7)
TIMEOUT = 60


class GitLabError(Exception):
    """A GitLab API call failed (the message never contains the token)."""


class GitLab:
    """Minimal GitLab REST client: verified TLS, token kept in memory."""

    def __init__(self, url: str, token: str, cacert: Optional[str]):
        self.api = f"{url.rstrip('/')}/api/v4"
        self._token = token
        self._tls = ssl.create_default_context(cafile=cacert or None)

    def call(self, method: str, path: str, body: Optional[Dict[str, Any]] = None,
             missing_ok: bool = False) -> Any:
        """Send one request; return decoded JSON (None for 404 when missing_ok)."""
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            f"{self.api}{path}", data=data, method=method,
            headers={"PRIVATE-TOKEN": self._token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, context=self._tls, timeout=TIMEOUT) as response:  # nosec B310
                raw = response.read().decode()
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and missing_ok:
                return None
            detail = exc.read().decode(errors="replace")[:300]
            raise GitLabError(f"{method} {path.split('?')[0]}: HTTP {exc.code} {detail}") from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise GitLabError(f"{method} {path.split('?')[0]}: {exc}") from exc
        return json.loads(raw) if raw.strip() else {}


def _quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def read_token(from_stdin: bool) -> str:
    """Read the GitLab token from stdin or a hidden prompt."""
    token = sys.stdin.readline().strip() if from_stdin else getpass.getpass("GitLab token (api scope): ")
    if not re.fullmatch(r"[A-Za-z0-9._-]{8,256}", token or ""):
        raise GitLabError("the token is empty or has unexpected characters")
    return token


def ensure_project(gitlab: GitLab, path: str, branch: str) -> Dict[str, Any]:
    """Return the project, creating it (private, initialized) when absent."""
    project = gitlab.call("GET", f"/projects/{_quote(path)}", missing_ok=True)
    if project:
        print(f"project {path} exists (id {project['id']})")
        return project
    namespace, name = path.rsplit("/", 1)
    found = gitlab.call("GET", f"/namespaces/{_quote(namespace)}", missing_ok=True)
    if not found:
        raise GitLabError(f"namespace {namespace} not found")
    project = gitlab.call("POST", "/projects", {
        "name": name, "path": name, "namespace_id": found["id"], "visibility": "private",
        "initialize_with_readme": True, "default_branch": branch,
        "description": "Omnia system verification (SVT) pipeline"})
    print(f"project {path} created (id {project['id']})")
    return project


def _template_files() -> List[Tuple[str, str]]:
    """Return (repository path, local path) of the pipeline files (not clusters/)."""
    files = []
    for directory, _, names in os.walk(TEMPLATE):
        relative = os.path.relpath(directory, TEMPLATE)
        if relative.split(os.sep)[0] == "clusters" or "__pycache__" in relative:
            continue
        for name in sorted(names):
            if name.endswith(".pyc"):
                continue
            repo_path = os.path.normpath(os.path.join(relative, name)).replace(os.sep, "/")
            files.append((repo_path, os.path.join(directory, name)))
    return sorted(files)


def build_actions(gitlab: GitLab, project_id: int, branch: str, clusters: List[str],
                  overwrite_clusters: bool) -> List[Dict[str, str]]:
    """Return the commit actions for the pipeline and cluster files."""
    wanted = [(path, local, True) for path, local in _template_files()]
    for cluster in clusters:
        wanted.extend((f"clusters/{cluster}/{name}", source, overwrite_clusters)
                      for name, source in CLUSTER_SOURCES.items())
    actions = []
    for repo_path, local, replace in wanted:
        exists = gitlab.call("GET", f"/projects/{project_id}/repository/files/"
                             f"{_quote(repo_path)}?ref={_quote(branch)}", missing_ok=True)
        if exists and not replace:
            print(f"  keep    {repo_path} (already in the project)")
            continue
        with open(local, "rb") as stream:
            content = base64.b64encode(stream.read()).decode()
        actions.append({"action": "update" if exists else "create", "file_path": repo_path,
                        "content": content, "encoding": "base64"})
        print(f"  {'update' if exists else 'create'}  {repo_path}")
    return actions


def check_settings(gitlab: GitLab, project: Dict[str, Any], branch: str) -> None:
    """Raise the CI timeout, protect the branch and check the runners."""
    project_id = project["id"]
    if int(project.get("build_timeout") or 0) < PROJECT_TIMEOUT_SECONDS:
        gitlab.call("PUT", f"/projects/{project_id}", {"build_timeout": PROJECT_TIMEOUT_SECONDS})
        print(f"project CI timeout set to {PROJECT_TIMEOUT_SECONDS // 3600}h")
    protected = gitlab.call("GET", f"/projects/{project_id}/protected_branches/{_quote(branch)}",
                            missing_ok=True)
    if not protected:
        gitlab.call("POST", f"/projects/{project_id}/protected_branches", {"name": branch})
        print(f"branch {branch} protected (OpenBao releases secrets to protected refs only)")
    runners = gitlab.call("GET", f"/projects/{project_id}/runners?per_page=100") or []
    if not runners:
        print("WARNING: no runner is available to this project; register a shell runner "
              "that reaches the OIMs (SSH) and OpenBao (HTTPS)")
    for runner in runners:
        detail = gitlab.call("GET", f"/runners/{runner['id']}")
        limit = detail.get("maximum_timeout")
        tags = ", ".join(detail.get("tag_list") or []) or "no tags"
        state = (f"maximum job timeout {limit // 3600}h - LOWER than the longest stage "
                 f"({LONGEST_STAGE_SECONDS // 3600}h): raise it or leave it empty"
                 if limit and limit < LONGEST_STAGE_SECONDS else "timeout OK")
        print(f"runner {runner['id']} ({runner.get('description', '')}): {tags}; {state}")


def main(argv: List[str]) -> int:
    """Parse the arguments and set up the project."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("--gitlab-url", required=True, help="https://<gitlab>")
    parser.add_argument("--project", required=True, help="namespace/name, e.g. root/omnia-svt")
    parser.add_argument("--cluster", action="append", default=[], help="cluster folder (repeat)")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--cacert", help="CA file that signed the GitLab certificate")
    parser.add_argument("--token-stdin", action="store_true", help="read the token from stdin")
    parser.add_argument("--overwrite-clusters", action="store_true",
                        help="replace existing cluster files with the templates")
    args = parser.parse_args(argv)
    clusters = args.cluster or ["cluster1"]
    try:
        if not args.gitlab_url.startswith("https://"):
            raise GitLabError("--gitlab-url must be an https:// URL")
        if not PROJECT_RE.fullmatch(args.project):
            raise GitLabError(f"invalid --project {args.project!r}")
        bad = [name for name in clusters if not CLUSTER_RE.fullmatch(name)]
        if bad or not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", args.branch):
            raise GitLabError(f"invalid cluster name(s) {bad} or branch")
        gitlab = GitLab(args.gitlab_url, read_token(args.token_stdin), args.cacert)
        version = str(gitlab.call("GET", "/version").get("version", "0.0"))
        numbers = tuple(int(part) for part in re.findall(r"\d+", version)[:2])
        print(f"GitLab {version}")
        if numbers < MIN_OPTIONS_VERSION:
            print("WARNING: GitLab < 15.7 shows THEME/START_STAGE as free text, not drop-downs")
        project = ensure_project(gitlab, args.project, args.branch)
        actions = build_actions(gitlab, project["id"], args.branch, clusters,
                                args.overwrite_clusters)
        if actions:
            gitlab.call("POST", f"/projects/{project['id']}/repository/commits", {
                "branch": args.branch, "actions": actions,
                "commit_message": "SVT pipeline setup [skip ci]"})
            print(f"committed {len(actions)} file(s) to {args.branch}")
        check_settings(gitlab, project, args.branch)
    except GitLabError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("\nNext steps:")
    print(f"  1. In GitLab, fill clusters/{clusters[0]}/cluster.yml, user_inputs.yml and test_config.yml")
    print(f"  2. Store the secrets: ./openbao_secrets.py --addr <openbao> --cluster {clusters[0]}")
    print(f"  3. Configure the OpenBao JWT role once: ./openbao_secrets.py --print-setup "
          f"--gitlab-url {args.gitlab_url} --project {args.project}")
    print("  4. CI/CD > Pipelines > Run pipeline: choose THEME and CLUSTERS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
