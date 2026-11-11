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

"""Check, clean or delete the GitLab project that runs the SVT.

The project is the one named in svt_pipeline_config.yml (gitlab.namespace and
gitlab.project_name), the same one setup_svt_project.py creates::

    ./cleanup_svt_project.py --status        --gitlab-url https://gitlab.example.com
    ./cleanup_svt_project.py --clean         --gitlab-url ... [--dry-run] [--yes]
    ./cleanup_svt_project.py --delete        --gitlab-url ... [--dry-run] [--yes]
    ./cleanup_svt_project.py --verify-gone   --gitlab-url ...

--status      read-only: the project, its pipelines, jobs, artifact size and variables.
--clean       keep the project, its files and variables; delete every pipeline of it
              (running ones are cancelled first), which removes their jobs, logs and
              artifacts, then delete the remaining job artifacts. Then it checks that
              nothing is left.
--delete      delete the whole project (pipelines, artifacts, files, variables),
              permanently (GitLab first only schedules the deletion; the script then
              removes it for good), then check that it is gone. Create it again with
              ./setup_svt_project.py --create.
--verify-gone exit 0 only when the project does not exist at all (a project that GitLab
              only scheduled for deletion still exists); use it after --delete, or to
              prove an environment is clean.
--dry-run     with --clean or --delete: list what would be removed, remove nothing.

--clean and --delete ask you to type the project path (<namespace>/<project>) unless
--yes is given; without --yes and without a terminal they refuse. The GitLab token
comes from GITLAB_TOKEN or a prompt and is never printed or stored.

Only GitLab is touched. The OIM (the checkout folder, /opt/omnia, the SVT reports) is
cleaned on the OIM: ./setup_env.sh --cleanup (see docs/SETUP.md). A runner enabled on the
project is not deleted; it is only released when the project is deleted.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from setup_svt_project import (  # noqa: E402  # same folder; also loads the shared GitLab client
    DEFAULT_CONFIG,
    GitLabClient,
    _client,
    _validate_namespace,
    _validate_project_name,
    load_config,
)

ACTIVE = ("running", "pending", "created", "waiting_for_resource", "preparing", "scheduled")
WAIT_SECONDS, POLL_SECONDS = 120, 3


def project_path(config: Dict[str, Any]) -> str:
    """Return <namespace>/<project> of the config."""
    gitlab = config.get("gitlab") or {}
    name = _validate_project_name(str(gitlab.get("project_name") or "omnia-svt"))
    namespace = _validate_namespace(str(gitlab.get("namespace") or "root"))
    return f"{namespace}/{name}"


def _pages(client: GitLabClient, path: str, **params: Any) -> List[Dict[str, Any]]:
    """Return every item of a paginated GitLab list."""
    items: List[Dict[str, Any]] = []
    page: Optional[str] = "1"
    while page:
        # pylint: disable-next=protected-access
        response = client._get(path, params={"per_page": 100, "page": page, **params})
        if response.status_code != 200:
            raise SystemExit(f"GitLab {path}: HTTP {response.status_code}")
        items.extend(response.json())
        page = response.headers.get("X-Next-Page") or None
    return items


def _size(value: Any) -> str:
    size = float(value or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return "0 B"


def find(client: GitLabClient, path: str) -> Optional[Dict[str, Any]]:
    """Return the project (with statistics) or None when it does not exist."""
    # pylint: disable-next=protected-access
    response = client._get(f"/projects/{quote(path, safe='')}", params={"statistics": "true"})
    return response.json() if response.status_code == 200 else None


def state(client: GitLabClient, project: Dict[str, Any]) -> Dict[str, Any]:
    """Return what the project holds: pipelines, jobs, job artifacts, variables, runners."""
    pid = project["id"]
    jobs = _pages(client, f"/projects/{pid}/jobs")
    with_artifacts = [job for job in jobs
                      if any(a.get("file_type") != "trace" for a in job.get("artifacts") or [])]
    return {
        "pipelines": _pages(client, f"/projects/{pid}/pipelines"),
        "jobs": len(jobs),
        "jobs_with_artifacts": len(with_artifacts),
        "artifact_size": (project.get("statistics") or {}).get("job_artifacts_size", 0),
        "variables": len(client.list_variables(pid) or []),
        "runners": len(_pages(client, f"/projects/{pid}/runners")),
    }


def show(path: str, project: Dict[str, Any], held: Dict[str, Any]) -> None:
    """Print the state of the project."""
    pending = " (scheduled for deletion)" if project.get("marked_for_deletion_on") else ""
    print(f"project   : {path}{pending}  id {project['id']}  {project.get('web_url', '')}")
    print(f"pipelines : {len(held['pipelines'])}"
          + (f"  ({sum(1 for p in held['pipelines'] if p['status'] in ACTIVE)} active)"
             if held["pipelines"] else ""))
    print(f"jobs      : {held['jobs']}  ({held['jobs_with_artifacts']} with artifacts, "
          f"{_size(held['artifact_size'])} of job artifacts)")
    print(f"variables : {held['variables']}   runners enabled: {held['runners']}")


def confirm(path: str, what: str, yes: bool) -> bool:
    """Ask the user to type the project path; --yes skips the question."""
    if yes:
        return True
    if not sys.stdin.isatty():
        print(f"ERROR: {what} needs --yes when there is no terminal", file=sys.stderr)
        return False
    typed = input(f"This will {what} {path}. Type the project path to continue: ").strip()
    if typed != path:
        print("not confirmed: nothing was removed")
        return False
    return True


def clean(client: GitLabClient, project: Dict[str, Any], dry_run: bool) -> None:
    """Cancel and delete every pipeline, then the remaining job artifacts."""
    pid = project["id"]
    pipelines = _pages(client, f"/projects/{pid}/pipelines")
    print(f"{len(pipelines)} pipeline(s) {'would be ' if dry_run else ''}deleted")
    if dry_run:
        for pipeline in pipelines:
            print(f"  pipeline {pipeline['id']}  {pipeline['status']:<10} {pipeline.get('ref', '')}")
        return
    for pipeline in pipelines:
        if pipeline["status"] in ACTIVE:
            # pylint: disable-next=protected-access
            client._post(f"/projects/{pid}/pipelines/{pipeline['id']}/cancel")
    for pipeline in pipelines:
        # pylint: disable-next=protected-access
        response = client._delete(f"/projects/{pid}/pipelines/{pipeline['id']}")
        mark = "ok" if response.status_code in (200, 202, 204, 404) else f"HTTP {response.status_code}"
        print(f"  pipeline {pipeline['id']}: {mark}")
    # pylint: disable-next=protected-access
    response = client._delete(f"/projects/{pid}/artifacts")
    print(f"  remaining job artifacts: HTTP {response.status_code}")


def by_id(client: GitLabClient, pid: int) -> Optional[Dict[str, Any]]:
    """Return the project with this id, or None when it does not exist any more."""
    # pylint: disable-next=protected-access
    response = client._get(f"/projects/{pid}")
    return response.json() if response.status_code == 200 else None


def delete(client: GitLabClient, project: Dict[str, Any], path: str) -> None:
    """Delete the project. GitLab first only schedules the deletion and renames the project
    (<path>-deletion_scheduled-<id>); the second call, with that new path, removes it."""
    pid = project["id"]
    if not project.get("marked_for_deletion_on"):
        # pylint: disable-next=protected-access
        response = client._delete(f"/projects/{pid}")
        print(f"  delete project: HTTP {response.status_code}")
        if response.status_code not in (200, 202, 204):
            raise SystemExit(f"could not delete {path}: {response.text[:200]}")
    held = by_id(client, pid)
    if held and held.get("marked_for_deletion_on"):
        # pylint: disable-next=protected-access
        response = client._delete(f"/projects/{pid}", params={
            "permanently_remove": "true", "full_path": held["path_with_namespace"]})
        print(f"  permanent removal of {held['path_with_namespace']}: HTTP {response.status_code}")


def wait_until(check, label: str) -> bool:
    """Poll ``check`` until it is true (GitLab removes things in the background)."""
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(POLL_SECONDS)
    print(f"  still not done after {WAIT_SECONDS}s: {label}")
    return check()


def gone(client: GitLabClient, path: str, pid: Optional[int] = None) -> bool:
    """Return whether the project does not exist at all (a project that is only scheduled
    for deletion still exists)."""
    return (by_id(client, pid) if pid else find(client, path)) is None


def verify_clean(client: GitLabClient, path: str) -> bool:
    """Check that the project holds no pipeline, job or artifact; print the result."""
    project = find(client, path)
    if project is None:
        print("verify: the project does not exist")
        return False
    def empty() -> bool:
        held = state(client, find(client, path) or project)
        return not held["pipelines"] and not held["jobs"] and not held["jobs_with_artifacts"]
    ok = wait_until(empty, "pipelines, jobs and artifacts")
    held = state(client, find(client, path) or project)
    print(f"verify: pipelines {len(held['pipelines'])}, jobs {held['jobs']}, "
          f"jobs with artifacts {held['jobs_with_artifacts']}, "
          f"job artifacts {_size(held['artifact_size'])} -> {'CLEAN' if ok else 'NOT CLEAN'}")
    return ok


def main(argv: List[str]) -> int:
    """Parse the arguments and run the command."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument("--status", action="store_true", help="show what the project holds")
    command.add_argument("--clean", action="store_true",
                         help="delete every pipeline, job log and artifact; keep the project")
    command.add_argument("--delete", action="store_true", help="delete the whole project")
    command.add_argument("--verify-gone", action="store_true",
                         help="exit 0 only when the project does not exist")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--gitlab-url", required=True, help="GitLab URL")
    parser.add_argument("--dry-run", action="store_true",
                        help="with --clean or --delete: list what would be removed")
    parser.add_argument("--yes", action="store_true",
                        help="do not ask to type the project path")
    parser.add_argument("--no-verify-ssl", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run and not (args.clean or args.delete):
        parser.error("--dry-run goes with --clean or --delete")
    path = project_path(load_config(Path(args.config).resolve()))
    client = _client(args)
    project = find(client, path)
    if args.verify_gone:
        if project is None:
            print(f"{path}: gone")
            return 0
        print(f"{path}: STILL THERE" + (" (only scheduled for deletion: run --delete --yes "
                                        "to remove it permanently)"
                                        if project.get("marked_for_deletion_on") else ""))
        return 1
    if project is None:
        print(f"{path}: the project does not exist")
        return 0 if args.delete else 1
    show(path, project, state(client, project))
    if args.status:
        return 0
    if args.dry_run:
        if args.clean:
            clean(client, project, dry_run=True)
        else:
            print(f"the project {path} would be deleted with everything in it")
        return 0
    if not confirm(path, "delete the pipelines and artifacts of" if args.clean
                   else "DELETE the whole project", args.yes):
        return 1
    if args.clean:
        clean(client, project, dry_run=False)
        return 0 if verify_clean(client, path) else 1
    delete(client, project, path)
    ok = wait_until(lambda: gone(client, path, project["id"]), "the project to disappear")
    print(f"verify: {path} -> {'GONE' if ok else 'STILL THERE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
