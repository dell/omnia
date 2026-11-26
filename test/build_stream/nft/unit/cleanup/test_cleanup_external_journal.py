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

"""Regression tests for external GitLab cleanup ownership (journal-driven variable deletion).

The real role task file ``cleanup_external.yml`` is run with ansible-playbook against a
local fake GitLab API, so the assertions are on the HTTP calls actually issued.
"""

import json
import os
import re
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[5] / "src" / "build_stream"
ROLES = SRC / "roles"
ANSIBLE = shutil.which("ansible-playbook")
CREATED_BSM_CLIENT_KEYS = {"BSM_CLIENT_ID", "BSM_CLIENT_SECRET"}
OMNIA_MARKER = "Omnia BuildStream catalog (managed-by:omnia-buildstream)."

pytestmark = pytest.mark.skipif(ANSIBLE is None, reason="ansible-playbook is not installed")

PLAYBOOK = """---
- name: Run the external GitLab cleanup tasks
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: Include cleanup tasks
      ansible.builtin.include_role:
        name: cleanup_gitlab
        tasks_from: cleanup_external
"""


class FakeGitLab:
    """Minimal GitLab API recording every request; behaviour is configurable per test."""

    def __init__(self, fail_variable_delete=False, project_description="", project_delete_status=202):
        self.requests = []
        self.raw_requests = []
        self.fail_variable_delete = fail_variable_delete
        self.project_description = project_description
        self.project_delete_status = project_delete_status
        self.project_scheduled = False
        self.project_deleted = False
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                return

            def _reply(self, status, body=None):
                payload = json.dumps(body if body is not None else {}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if self.command != "HEAD" and status != 204:
                    self.wfile.write(payload)

            def _handle(self):
                outer.requests.append((self.command, self.path.split("?")[0]))
                outer.raw_requests.append((self.command, self.path))
                path = self.path.split("?")[0]
                if self.command == "GET" and path.endswith("/access_tokens"):
                    return self._reply(200, [{"id": 7, "name": "customer-token"}])
                if self.command == "GET" and path.endswith("/triggers"):
                    return self._reply(200, [{"id": 9, "description": "customer trigger"}])
                if re.match(r".*/projects/\d+$", path):
                    if self.command == "GET":
                        if outer.project_deleted:
                            return self._reply(404)
                        if outer.project_scheduled:
                            return self._reply(200, {
                                "id": 1,
                                "description": outer.project_description,
                                "marked_for_deletion_on": "2026-11-26",
                                "path_with_namespace": "infra/omnia-catalog-deletion_scheduled-1",
                            })
                        return self._reply(200, {"id": 1, "description": outer.project_description})
                    if self.command == "DELETE" and "permanently_remove=true" in self.path:
                        outer.project_deleted = True
                        return self._reply(204)
                    if self.command == "DELETE":
                        if outer.project_delete_status in (200, 202, 204):
                            outer.project_scheduled = True
                        return self._reply(outer.project_delete_status)
                if self.command == "DELETE" and "/variables/" in path:
                    return self._reply(500 if outer.fail_variable_delete else 204)
                return self._reply(204 if self.command == "DELETE" else 200)

            do_GET = do_DELETE = do_POST = do_PUT = _handle

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        self.server.shutdown()
        self.server.server_close()

    def deleted_variables(self):
        return {p.rsplit("/", 1)[1] for m, p in self.requests if m == "DELETE" and "/variables/" in p}

    def deleted_other(self):
        return [p for m, p in self.requests if m == "DELETE" and "/variables/" not in p]


def variable(key, action):
    return {"type": "variable", "key": key, "action": action, "run_id": "r1"}


def project(action, pid="1"):
    return {"type": "project", "id": pid, "action": action, "run_id": "r1"}


def run_cleanup(tmp_path, gitlab, journal=None, raw_journal=None):
    """Run cleanup_external.yml; returns (result, stdout, journal_path)."""
    out_dir = tmp_path / "output"
    in_dir = tmp_path / "input"
    out_dir.mkdir()
    in_dir.mkdir()
    journal_path = out_dir / "external_gitlab_journal.json"
    if raw_journal is not None:
        journal_path.write_text(raw_journal, encoding="utf-8")
    elif journal is not None:
        journal_path.write_text(json.dumps(journal), encoding="utf-8")
    playbook = tmp_path / "cleanup.yml"
    playbook.write_text(PLAYBOOK, encoding="utf-8")
    extra = {
        "output_project_dir": str(out_dir),
        "input_project_dir": str(in_dir),
        "gitlab_external_url": gitlab.url,
        "gitlab_project_namespace": "infra",
        "gitlab_api_token": "glpat-test-token",
        "gitlab_project_id": "1",
        "cleanup_credentials": "false",
    }
    env = dict(
        os.environ,
        ANSIBLE_ROLES_PATH=str(ROLES),
        ANSIBLE_LIBRARY=str(SRC / "plugins" / "modules"),
        ANSIBLE_MODULE_UTILS=str(SRC / "plugins" / "module_utils"),
        ANSIBLE_NOCOLOR="1",
        ANSIBLE_HOME=str(tmp_path / ".ansible"),
        ANSIBLE_LOCALHOST_WARNING="False",
    )
    result = subprocess.run(
        [ANSIBLE, str(playbook), "-i", "localhost,", "-e", json.dumps(extra)],
        capture_output=True, text=True, env=env, cwd=tmp_path, check=False, timeout=180,
    )
    return result, result.stdout + result.stderr, journal_path


def valid_journal(*variables, project_id="1"):
    return {"schema_version": 1, "project_id": project_id, "resources": list(variables)}


class TestJournalOwnership:
    """GIVEN a setup journal WHEN cleanup runs THEN only Omnia-created variables are deleted."""

    def test_created_variable_is_deleted(self, tmp_path):
        with FakeGitLab() as gitlab:
            result, _out, _ = run_cleanup(tmp_path, gitlab, valid_journal(variable("BSM_API_URL", "created")))
            assert result.returncode == 0, result.stdout
            assert "BSM_API_URL" in gitlab.deleted_variables()

    def test_adopted_variable_is_preserved(self, tmp_path):
        with FakeGitLab() as gitlab:
            result, _out, _ = run_cleanup(tmp_path, gitlab, valid_journal(variable("BSM_API_URL", "adopted")))
            assert result.returncode == 0, result.stdout
            assert "BSM_API_URL" not in gitlab.deleted_variables()

    def test_mixed_created_and_adopted_deletes_only_created(self, tmp_path):
        journal = valid_journal(variable("BSM_API_URL", "adopted"), variable("BSM_API_USERNAME", "created"),
                                variable("GITLAB_API_TOKEN", "adopted"), variable("BSM_API_CERT", "created"))
        with FakeGitLab() as gitlab:
            result, _out, _ = run_cleanup(tmp_path, gitlab, journal)
            assert result.returncode == 0, result.stdout
            assert gitlab.deleted_variables() == {"BSM_API_USERNAME", "BSM_API_CERT"} | CREATED_BSM_CLIENT_KEYS

    def test_customer_token_and_trigger_are_untouched(self, tmp_path):
        with FakeGitLab() as gitlab:
            run_cleanup(tmp_path, gitlab, valid_journal(variable("BSM_API_URL", "created")))
            assert gitlab.deleted_other() == []


class TestProjectOwnership:
    """GIVEN a project in the journal WHEN cleanup runs THEN it is deleted only if Omnia created it."""

    def test_created_project_is_deleted_outright(self, tmp_path):
        # When Omnia created the project, deleting it removes its files,
        # variables, token and trigger in one call — no per-resource deletes.
        journal = valid_journal(project("created"), variable("BSM_API_URL", "created"))
        with FakeGitLab() as gitlab:
            result, out, journal_path = run_cleanup(tmp_path, gitlab, journal)
            assert result.returncode == 0, out
            assert gitlab.requests.count(("DELETE", "/api/v4/projects/1")) == 2
            assert any("permanently_remove=true" in path and "full_path=" in path
                       for method, path in gitlab.raw_requests if method == "DELETE")
            assert gitlab.project_deleted
            assert gitlab.deleted_variables() == set(), "project delete must replace per-variable deletes"
            assert "project permanently deleted" in out
            assert "PERMANENTLY DELETED (Omnia-owned catalog project)" in out
            assert not journal_path.exists(), "ownership evidence is removed after a clean project delete"

    def test_maintainer_falls_back_to_owned_resource_cleanup(self, tmp_path):
        journal = valid_journal(project("created"), variable("BSM_API_URL", "created"))
        with FakeGitLab(project_delete_status=403) as gitlab:
            result, out, journal_path = run_cleanup(tmp_path, gitlab, journal)
            assert result.returncode == 0, out
            assert gitlab.requests.count(("DELETE", "/api/v4/projects/1")) == 1
            assert not gitlab.project_deleted
            assert "BSM_API_URL" in gitlab.deleted_variables()
            assert "falling back to Omnia resource cleanup (HTTP 403)" in out
            assert "PRESERVED (delete unavailable; Omnia resources removed)" in out
            assert not journal_path.exists()

    def test_adopted_project_without_marker_is_never_deleted(self, tmp_path):
        # An adopted project whose live description carries no Omnia marker is
        # preserved; only Omnia-created resources inside it are removed.
        journal = valid_journal(project("adopted"), variable("BSM_API_URL", "created"))
        with FakeGitLab(project_description="a customer project") as gitlab:
            result, out, _ = run_cleanup(tmp_path, gitlab, journal)
            assert result.returncode == 0, out
            assert ("DELETE", "/api/v4/projects/1") not in gitlab.requests
            assert "BSM_API_URL" in gitlab.deleted_variables()
            assert "PRESERVED (customer-owned" in out

    def test_created_project_with_marker_is_deleted(self, tmp_path):
        journal = valid_journal(project("created"), variable("BSM_API_URL", "created"))
        with FakeGitLab(project_description=OMNIA_MARKER) as gitlab:
            result, out, _ = run_cleanup(tmp_path, gitlab, journal)
            assert result.returncode == 0, out
            assert gitlab.requests.count(("DELETE", "/api/v4/projects/1")) == 2
            assert gitlab.project_deleted
            assert "PERMANENTLY DELETED (Omnia-owned catalog project)" in out

    def test_adopted_project_with_marker_is_never_deleted(self, tmp_path):
        # The normal adoption state: the customer project already carries the
        # Omnia marker (adoption requires it) and the journal records "adopted".
        journal = valid_journal(project("adopted"), variable("BSM_API_URL", "created"))
        with FakeGitLab(project_description=OMNIA_MARKER) as gitlab:
            result, out, journal_path = run_cleanup(tmp_path, gitlab, journal)
            assert result.returncode == 0, out
            assert not [r for r in gitlab.requests if r[0] == "DELETE" and r[1] == "/api/v4/projects/1"]
            assert not gitlab.project_deleted
            assert gitlab.deleted_variables() >= {"BSM_API_URL"}
            assert "PRESERVED (customer-owned" in out
            assert not journal_path.exists()

    @pytest.mark.parametrize("raw_journal", [None, "{broken"])
    def test_marked_project_without_reliable_journal_is_preserved(self, tmp_path, raw_journal):
        # The marker alone never authorizes deleting the project: with a missing
        # or corrupt journal nothing is deleted and ownership evidence is kept.
        with FakeGitLab(project_description=OMNIA_MARKER) as gitlab:
            result, out, journal_path = run_cleanup(tmp_path, gitlab, raw_journal=raw_journal)
            assert result.returncode == 0, out
            assert not [r for r in gitlab.requests if r[0] == "DELETE"]
            assert not gitlab.project_deleted
            assert "Remote cleanup complete: False" in out
            assert journal_path.exists() == (raw_journal is not None)


class TestUnreliableJournal:
    """GIVEN no reliable ownership evidence WHEN cleanup runs THEN no remote variable is deleted."""

    @pytest.mark.parametrize("name,kwargs", [
        ("missing", {}),
        ("malformed", {"raw_journal": "{not json"}),
        ("not-a-document", {"raw_journal": "[1, 2, 3]"}),
        ("unsupported-schema", {"journal": {"schema_version": 99, "resources": [variable("BSM_API_URL", "created")]}}),
        ("resources-not-a-list", {"journal": {"schema_version": 1, "resources": "BSM_API_URL"}}),
    ])
    def test_no_variables_deleted_and_warning_emitted(self, tmp_path, name, kwargs):
        with FakeGitLab() as gitlab:
            result, out, journal_path = run_cleanup(tmp_path, gitlab, **kwargs)
            assert result.returncode == 0, out
            assert gitlab.deleted_variables() == set(), name
            assert "NO remote CI/CD variables will be deleted" in out
            for key in ("GITLAB_API_TOKEN", "BSM_API_PASSWORD", "BSM_CLIENT_SECRET"):
                assert key in out
            assert "Remote cleanup complete: False" in out
            if kwargs:
                assert journal_path.exists(), "ownership evidence must be preserved"

    def test_project_and_customer_resources_are_preserved(self, tmp_path):
        with FakeGitLab() as gitlab:
            run_cleanup(tmp_path, gitlab)
            assert gitlab.deleted_other() == []
            assert ("DELETE", "/api/v4/projects/1") not in gitlab.requests

    def test_unreliable_journal_is_not_reported_as_removed(self, tmp_path):
        with FakeGitLab() as gitlab:
            _result, out, _ = run_cleanup(tmp_path, gitlab, raw_journal="{broken")
            assert "variables removed: 0" in out


class TestApiFailure:
    """GIVEN a GitLab API failure WHEN cleanup runs THEN failure is reported and evidence is kept."""

    def test_failure_reported_and_local_state_kept(self, tmp_path):
        with FakeGitLab(fail_variable_delete=True) as gitlab:
            result, out, journal_path = run_cleanup(
                tmp_path, gitlab, valid_journal(variable("BSM_API_URL", "created")))
            assert result.returncode == 0, out
            assert "GitLab API cleanup call(s) failed" in out
            assert "variables removed: 0" in out
            assert "Remote cleanup complete: False" in out
            assert journal_path.exists()
            assert gitlab.deleted_other() == []

    def test_success_removes_local_journal(self, tmp_path):
        with FakeGitLab() as gitlab:
            result, out, journal_path = run_cleanup(
                tmp_path, gitlab, valid_journal(variable("BSM_API_URL", "created")))
            assert result.returncode == 0, out
            assert "Remote cleanup complete: True" in out
            assert not journal_path.exists()
