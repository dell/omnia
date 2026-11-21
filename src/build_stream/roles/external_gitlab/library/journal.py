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
"""Ansible module: external GitLab setup journal (ER-BSM-003 FR-3).

The journal records only resource identifiers (IDs, names, keys), never secret
values. Writes are atomic (tmp + fsync + rename), serialised with flock on a
sibling lock file, and the file is root:0600.
"""

import errno
import fcntl
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: journal
short_description: Manage the external GitLab setup journal
description:
  - Reads and updates C(external_gitlab_journal.json) with atomic, locked writes.
  - Stores resource identifiers only; secret-looking keys are rejected.
options:
  path:
    description: Journal file path.
    type: str
    required: true
  action:
    description: Operation to perform.
    type: str
    required: true
    choices: [read, init, record, remove, delete, rollback_plan]
  run_id:
    description: Identifier of the current execution (required for init, record, rollback_plan).
    type: str
  header:
    description: Top-level fields to set on init (omnia_project, gitlab_url, project_id).
    type: dict
    default: {}
  resource:
    description: Resource entry to record or remove (type plus id, name or key).
    type: dict
    default: {}
  resources:
    description: Several resource entries to record in one atomic write.
    type: list
    elements: dict
    default: []
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Record the project
  journal:
    path: "{{ _egl_journal_path }}"
    action: record
    run_id: "{{ _egl_run_id }}"
    resource: {type: project, id: "42", action: created, state: applied}
'''

RETURN = r'''
journal:
  description: Journal content after the operation.
  returned: always
  type: dict
degraded:
  description: True when the journal could not be used (corrupt or unsupported schema).
  returned: always
  type: bool
corrupt_backup:
  description: Path the corrupt journal was moved to, if any.
  returned: when corruption was detected
  type: str
plan:
  description: Resources created in this run in reverse (rollback) order.
  returned: when action is rollback_plan
  type: list
'''

SCHEMA_VERSION = 1
ALLOWED_RESOURCE_FIELDS = ("type", "id", "name", "key", "token_id", "action", "state", "run_id")
SECRET_FIELD_HINTS = ("token_value", "password", "secret", "value")
IDENT_FIELDS = ("id", "name", "key")


def empty_journal():
    """Return a fresh journal document."""
    return {"schema_version": SCHEMA_VERSION, "resources": []}


def now_iso():
    """UTC timestamp in the journal format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resource_identity(resource):
    """Return the (type, identifier) tuple identifying a resource."""
    ident = next((resource[f] for f in IDENT_FIELDS if resource.get(f) not in (None, "")), "")
    return resource.get("type"), str(ident)


def sanitize_resource(resource):
    """Keep only identifier fields; reject anything that looks like a secret value."""
    for key in resource:
        if key in SECRET_FIELD_HINTS or key not in ALLOWED_RESOURCE_FIELDS:
            raise ValueError(f"field '{key}' is not allowed in a journal resource")
    if not resource.get("type"):
        raise ValueError("resource.type is required")
    if resource_identity(resource)[1] == "" and resource["type"] not in ("runner",):
        raise ValueError("resource needs one of id, name or key")
    return {k: str(v) if k != "type" else v for k, v in resource.items()}


@contextmanager
def locked(path):
    """Hold an exclusive flock on the journal's lock file."""
    directory = os.path.dirname(path)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    fd = os.open(path + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def cleanup_stale_tmp(path):
    """Remove partial temp files left by an interrupted write."""
    directory, base = os.path.split(path)
    prefix = f".{base}.tmp."
    for name in os.listdir(directory):
        if name.startswith(prefix):
            try:
                os.unlink(os.path.join(directory, name))
            except OSError:
                pass


def atomic_write(path, document):
    """Write JSON atomically with mode 0600 (root-owned when running as root)."""
    directory, base = os.path.split(path)
    tmp = os.path.join(directory, f".{base}.tmp.{os.getpid()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if os.geteuid() == 0:
            os.chown(tmp, 0, 0)
        os.rename(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    dir_fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def load(path):
    """Load the journal. Returns (document, degraded, corrupt_backup)."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            document = json.load(handle)
        if not isinstance(document, dict) or not isinstance(document.get("resources", []), list):
            raise ValueError("journal is not a document with a resources list")
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            return empty_journal(), False, None
        raise
    except ValueError:
        backup = os.path.join(os.path.dirname(path), f".journal.corrupt.{int(time.time())}")
        os.rename(path, backup)
        return empty_journal(), False, backup
    if document.get("schema_version") != SCHEMA_VERSION:
        return empty_journal(), True, None
    document.setdefault("resources", [])
    return document, False, None


def find_index(document, resource):
    """Index of *resource* in the journal, or -1."""
    ident = resource_identity(resource)
    for index, existing in enumerate(document["resources"]):
        if resource_identity(existing) == ident:
            return index
    return -1


def apply_action(document, params):
    """Mutate *document* for init/record/remove; returns True when it changed."""
    action = params["action"]
    if action == "init":
        document.update({k: str(v) for k, v in params["header"].items()})
        document["timestamp"] = now_iso()
        return True
    if action == "record":
        batch = params.get("resources") or [params["resource"]]
        for item in batch:
            record_one(document, sanitize_resource(item), params["run_id"])
        document["timestamp"] = now_iso()
        return True
    if action == "remove":
        index = find_index(document, sanitize_resource(params["resource"]))
        if index < 0:
            return False
        document["resources"].pop(index)
        document["timestamp"] = now_iso()
        return True
    return False


def record_one(document, entry, run_id):
    """Insert or replace one sanitized entry, keeping the original 'created' attribution."""
    existing_index = find_index(document, entry)
    if existing_index >= 0:
        previous = document["resources"][existing_index]
        if previous.get("action") == "created" and entry.get("action") != "created":
            entry["action"] = previous["action"]
            entry["run_id"] = previous.get("run_id", entry.get("run_id", ""))
        entry.setdefault("run_id", run_id)
        document["resources"][existing_index] = entry
    else:
        entry.setdefault("run_id", run_id)
        document["resources"].append(entry)


def run_module():
    """Module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            action=dict(type="str", required=True,
                        choices=["read", "init", "record", "remove", "delete", "rollback_plan"]),
            run_id=dict(type="str", default=""),
            header=dict(type="dict", default={}),
            resource=dict(type="dict", default={}),
            resources=dict(type="list", elements="dict", default=[]),
        ),
        supports_check_mode=False,
    )
    params = module.params
    path = params["path"]
    if params["action"] in ("init", "record", "rollback_plan") and not params["run_id"]:
        module.fail_json(msg="run_id is required for this action")
    try:
        with locked(path):
            cleanup_stale_tmp(path)
            if params["action"] == "delete":
                existed = os.path.exists(path)
                if existed:
                    os.unlink(path)
                module.exit_json(changed=existed, journal=empty_journal(), degraded=False)
            document, degraded, backup = load(path)
            result = dict(journal=document, degraded=degraded)
            if backup:
                result["corrupt_backup"] = backup
                module.warn(f"Corrupt journal moved to {backup}; using API reconciliation")
            if degraded:
                module.warn("Unsupported journal schema_version; journal tracking skipped")
            changed = False
            if params["action"] == "rollback_plan":
                result["plan"] = [
                    r for r in reversed(document["resources"])
                    if r.get("run_id") == params["run_id"] and r.get("action") == "created"
                ]
            elif params["action"] != "read" and not degraded:
                changed = apply_action(document, params)
                if changed:
                    atomic_write(path, document)
            module.exit_json(changed=changed, **result)
    except ValueError as exc:
        module.fail_json(msg=str(exc))
    except OSError as exc:
        module.fail_json(msg=f"journal I/O error ({exc.__class__.__name__}): {exc.strerror}")


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
