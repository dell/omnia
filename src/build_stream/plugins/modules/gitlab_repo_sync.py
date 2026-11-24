#!/usr/bin/python
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

# pylint: disable=import-error,no-name-in-module
"""Ansible module: sync local files into a GitLab repository in one commit (ER-BSM-003).

Creates missing files, updates changed files (unless create_only) and can delete
files, using the Repository Commits API. Unchanged files are skipped by comparing
SHA-256 digests, so repeated runs are idempotent.
"""

import base64
import hashlib
import os
from urllib.parse import quote

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.external_gitlab.gitlab_client import GitLabApiError, GitLabClient

DOCUMENTATION = r'''
---
module: gitlab_repo_sync
short_description: Create, update or delete repository files in a single GitLab commit
options:
  url: {description: GitLab base URL., type: str, required: true}
  token: {description: Token with write access., type: str, required: true, no_log: true}
  project_id: {description: Project ID., type: str, required: true}
  branch: {description: Target branch., type: str, required: true}
  ca_cert_path: {description: Optional PEM CA bundle., type: str, default: ""}
  commit_message: {description: Commit message., type: str, required: true}
  state:
    description: present syncs files; absent deletes the listed paths when they exist.
    type: str
    default: present
    choices: [present, absent]
  files:
    description: List of dicts with path, src (local file, state=present) and create_only (bool).
    type: list
    elements: dict
    required: true
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Push CI files
  gitlab_repo_sync:
    url: https://gitlab.example.com
    token: "{{ _egl_ci_token }}"
    project_id: "42"
    branch: main
    commit_message: Sync Omnia CI files
    files:
      - {path: .gitlab-ci.yml, src: /path/.gitlab-ci.yml}
'''

RETURN = r'''
created:
  description: Repository paths added by this call.
  returned: always
  type: list
updated:
  description: Repository paths modified by this call.
  returned: always
  type: list
deleted:
  description: Repository paths removed by this call.
  returned: always
  type: list
unchanged:
  description: Repository paths already up to date or skipped.
  returned: always
  type: list
'''


def remote_sha256(client, project_id, branch, path):
    """Return the SHA-256 of a repository file, or None when it does not exist."""
    api_path = (
        f"/projects/{project_id}/repository/files/{quote(path, safe='')}"
        f"?ref={quote(branch, safe='')}"
    )
    status, data = client.get(api_path, ok=(200, 404))
    return (data or {}).get("content_sha256") if status == 200 else None


def plan_actions(client, params):
    """Compute commit actions and the created/updated/deleted/unchanged path lists."""
    actions, result = [], {"created": [], "updated": [], "deleted": [], "unchanged": []}
    for entry in params["files"]:
        path = entry["path"]
        remote = remote_sha256(client, params["project_id"], params["branch"], path)
        if params["state"] == "absent":
            if remote is None:
                result["unchanged"].append(path)
            else:
                actions.append({"action": "delete", "file_path": path})
                result["deleted"].append(path)
            continue
        with open(entry["src"], "rb") as handle:
            content = handle.read()
        if remote is not None and (
            remote == hashlib.sha256(content).hexdigest() or entry.get("create_only")
        ):
            result["unchanged"].append(path)
            continue
        actions.append({
            "action": "create" if remote is None else "update",
            "file_path": path,
            "content": base64.b64encode(content).decode("ascii"),
            "encoding": "base64",
        })
        result["created" if remote is None else "updated"].append(path)
    return actions, result


def run_module():
    """Module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(type="str", required=True),
            token=dict(type="str", required=True, no_log=True),
            project_id=dict(type="str", required=True),
            branch=dict(type="str", required=True),
            ca_cert_path=dict(type="str", default=""),
            commit_message=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["present", "absent"]),
            files=dict(type="list", elements="dict", required=True),
        ),
        supports_check_mode=True,
    )
    params = module.params
    if params["state"] == "present":
        for entry in params["files"]:
            if not os.path.isfile(entry.get("src", "")):
                module.fail_json(msg=f"Source file not found for {entry.get('path')}")
    client = GitLabClient(params["url"], params["token"], params["ca_cert_path"] or None)
    try:
        actions, result = plan_actions(client, params)
        if actions and not module.check_mode:
            client.request(
                "POST",
                f"/projects/{params['project_id']}/repository/commits",
                body={
                    "branch": params["branch"],
                    "commit_message": params["commit_message"],
                    "actions": actions,
                },
                ok=(201,),
            )
    except GitLabApiError as exc:
        module.fail_json(msg=f"GitLab repository sync failed: {exc}", status=exc.status)
    module.exit_json(changed=bool(actions), **result)


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
