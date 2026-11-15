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

# pylint: disable=redefined-outer-name

"""TC-FVT-021/022/023: CI console log preview and CLI templates (ER-BSM-003).

These exercise the ``default.after_script`` block embedded in the GitLab CI
templates (AC-006/AC-007/AC-008). The real shell block is extracted from each
template and executed with POSIX ``sh`` against a mock BSM log API, so the
console output, graceful failure handling, and credential-free CLI templates
are verified without a live cluster.
"""

import http.server
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_FILES = (
    Path(__file__).parents[5]
    / "src" / "build_stream" / "roles" / "hosted_gitlab" / "files"
)
TEMPLATES = {
    "build": _FILES / ".gitlab-ci-build.yml",
    "cadence": _FILES / ".gitlab-ci-cadence.yml",
    "deploy_child": _FILES / ".gitlab-ci-deploy-child-template.yml",
}
# A playbook stage for each template, used to drive the inline preview path.
PLAYBOOK_STAGE = {
    "build": "build-images",
    "cadence": "deploy",
    "deploy_child": "restart",
}


def _after_script(path: Path) -> str:
    """Return the single shell script string from a template's default.after_script."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    block = data["default"]["after_script"]
    assert len(block) == 1, "after_script is expected to be one shell block"
    return block[0]


class _LogHandler(http.server.BaseHTTPRequestHandler):
    """Mock BSM log API returning a configurable response."""

    status = 200
    payload = {
        "job_id": "job-1",
        "stages": [
            {
                "stage_name": "build-image",
                "has_log": True,
                "log_content": "TASK [build] ok: [oim] 10.0.0.5\nPLAY RECAP ok=3",
                "unavailable_reason": None,
            }
        ],
    }

    valid_token = None
    token_requests = 0
    issued_token = "fresh-token"

    def do_POST(self):  # noqa: N802
        """Mock /api/v1/auth/token issuing ``issued_token``."""
        type(self).token_requests += 1
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"access_token": self.issued_token}).encode("utf-8"))

    def do_GET(self):  # noqa: N802
        """Serve the configured JSON payload and status (401 for a stale token)."""
        if self.valid_token and self.headers.get("Authorization") != f"Bearer {self.valid_token}":
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "token_expired"}')
            return
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(self.payload).encode("utf-8"))

    def log_message(self, *_args):
        """Silence the default stderr access log."""


DEFAULT_PAYLOAD = dict(_LogHandler.payload)


@pytest.fixture
def bsm_server():
    """Start a mock BSM API; return a controller to set status/payload and URL."""
    server = http.server.HTTPServer(("127.0.0.1", 0), _LogHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    class _Ctl:
        url = f"http://{host}:{port}"

        @staticmethod
        def set(status=200, payload=None, valid_token=None):
            _LogHandler.status = status
            _LogHandler.valid_token = valid_token
            _LogHandler.token_requests = 0
            if payload is not None:
                _LogHandler.payload = payload

    _Ctl.set(200, DEFAULT_PAYLOAD)
    yield _Ctl
    server.shutdown()


def _run(tmp_path, template_key, env):
    """Execute a template's after_script under /bin/sh with the given environment."""
    script = tmp_path / f"after_{template_key}.sh"
    script.write_text(_after_script(TEMPLATES[template_key]), encoding="utf-8")
    base = {"BSM_CERT_FILE": "/nonexistent/ca.crt", "ACCESS_TOKEN": "preview-token"}
    base.update(env)
    return subprocess.run(
        ["sh", str(script)], capture_output=True, text=True, env=base, check=False
    )


def test_tail_preview_printed_on_success(tmp_path, bsm_server):
    """TC-FVT-021: the console shows the labelled execution-log tail on 200."""
    proc = _run(tmp_path, "build", {
        "CI_JOB_STAGE": "build-images",
        "JOB_ID": "job-1",
        "BSM_API_URL": bsm_server.url,
    })
    assert proc.returncode == 0
    assert "Execution Log (last 50 lines) - stage build-image" in proc.stdout
    assert "PLAY RECAP ok=3" in proc.stdout
    assert "10.0.0.5" in proc.stdout  # operational data preserved


def test_custom_tail_lines_label(tmp_path, bsm_server):
    """BSM_LOG_TAIL_LINES customises the preview length shown in the console."""
    proc = _run(tmp_path, "build", {
        "CI_JOB_STAGE": "build-images",
        "JOB_ID": "job-1",
        "BSM_API_URL": bsm_server.url,
        "BSM_LOG_TAIL_LINES": "100",
    })
    assert "Execution Log (last 100 lines)" in proc.stdout


def test_cli_templates_have_token_placeholder_no_credentials(tmp_path, bsm_server):
    """TC-FVT-022: CLI templates use <TOKEN> and never echo the real token."""
    proc = _run(tmp_path, "build", {
        "CI_JOB_STAGE": "build-images",
        "JOB_ID": "job-xyz",
        "BSM_API_URL": bsm_server.url,
    })
    assert "<TOKEN>" in proc.stdout
    assert "<CLIENT_ID>" in proc.stdout and "<CLIENT_SECRET>" in proc.stdout
    assert "jobs/job-xyz/logs?full=true" in proc.stdout
    assert "jobs/job-xyz/logs?stage=build-image" in proc.stdout  # per-stage template
    assert "Bearer preview-token" not in proc.stdout  # real token never printed


def test_api_unreachable_is_non_fatal(tmp_path):
    """BSM API unreachable prints a warning and does not change the exit status."""
    proc = _run(tmp_path, "build", {
        "CI_JOB_STAGE": "build-images",
        "JOB_ID": "job-1",
        "BSM_API_URL": "http://127.0.0.1:1",
    })
    assert proc.returncode == 0
    assert "Log preview unavailable" in proc.stdout
    assert "<TOKEN>" in proc.stdout  # templates still printed


def test_log_not_yet_available_returns_graceful_message(tmp_path, bsm_server):
    """A 404 from the API is reported as not-yet-available, not an error."""
    bsm_server.set(status=404, payload={"error": "LOG_NOT_AVAILABLE"})
    proc = _run(tmp_path, "build", {
        "CI_JOB_STAGE": "build-images",
        "JOB_ID": "job-1",
        "BSM_API_URL": bsm_server.url,
    })
    assert proc.returncode == 0
    assert "Execution log not yet available" in proc.stdout


def test_no_job_id_skips_preview(tmp_path, bsm_server):
    """With no BSM job associated, the preview is skipped entirely."""
    proc = _run(tmp_path, "build", {
        "CI_JOB_STAGE": "initialization",
        "BSM_API_URL": bsm_server.url,
    })
    assert proc.returncode == 0
    assert "No BSM job associated" in proc.stdout


def test_non_playbook_stage_prints_templates_without_preview(tmp_path, bsm_server):
    """Non-playbook stages print CLI templates but no inline execution-log preview."""
    proc = _run(tmp_path, "build", {
        "CI_JOB_STAGE": "parse-catalog",
        "JOB_ID": "job-1",
        "BSM_API_URL": bsm_server.url,
    })
    assert proc.returncode == 0
    assert "Execution Log (last" not in proc.stdout  # no playbook stage => no preview
    assert "jobs/job-1/logs?full=true" in proc.stdout  # full-log template still shown
    assert "?stage=" not in proc.stdout  # no per-stage template for a non-playbook stage


@pytest.mark.parametrize("template_key", list(TEMPLATES))
def test_all_templates_share_after_script_parity(tmp_path, bsm_server, template_key):
    """TC-FVT-023 (AC-008): every pipeline template previews logs identically."""
    proc = _run(tmp_path, template_key, {
        "CI_JOB_STAGE": PLAYBOOK_STAGE[template_key],
        "JOB_ID": "job-1",
        "BSM_API_URL": bsm_server.url,
    })
    assert proc.returncode == 0
    assert "Execution Log (last 50 lines)" in proc.stdout
    assert "<TOKEN>" in proc.stdout
    assert "Retrieve complete execution logs through the BSM API" in proc.stdout


def test_after_script_overhead_under_two_seconds(tmp_path, bsm_server):
    """TC-NFT-002: the log preview hook adds < 2 seconds to job teardown."""
    start = time.perf_counter()
    proc = _run(tmp_path, "build", {
        "CI_JOB_STAGE": "build-images",
        "JOB_ID": "job-1",
        "BSM_API_URL": bsm_server.url,
    })
    assert proc.returncode == 0
    assert time.perf_counter() - start < 2.0


_REFRESH_ENV = {
    "CI_JOB_STAGE": "build-images",
    "JOB_ID": "job-1",
    "CLIENT_ID": "bsm-client",
    "CLIENT_SECRET": "super-secret-value",
}


def test_expired_token_is_refreshed_and_preview_shown(tmp_path, bsm_server):
    """GIVEN a stale ACCESS_TOKEN WHEN the API answers 401 THEN a fresh token is used."""
    bsm_server.set(valid_token="fresh-token")
    proc = _run(tmp_path, "build", {
        **_REFRESH_ENV, "BSM_API_URL": bsm_server.url, "ACCESS_TOKEN": "stale-token",
    })
    assert proc.returncode == 0
    assert "PLAY RECAP ok=3" in proc.stdout
    assert _LogHandler.token_requests == 1
    assert "super-secret-value" not in proc.stdout + proc.stderr
    assert "fresh-token" not in proc.stdout + proc.stderr


def test_missing_token_is_minted_from_client_credentials(tmp_path, bsm_server):
    """GIVEN no saved token and client credentials THEN the hook obtains one itself."""
    bsm_server.set(valid_token="fresh-token")
    proc = _run(tmp_path, "build", {
        **_REFRESH_ENV, "BSM_API_URL": bsm_server.url, "ACCESS_TOKEN": "",
    })
    assert proc.returncode == 0
    assert "PLAY RECAP ok=3" in proc.stdout


def test_expired_token_without_credentials_is_non_fatal(tmp_path, bsm_server):
    """GIVEN a stale token and no client credentials THEN a warning is printed, job unaffected."""
    bsm_server.set(valid_token="fresh-token")
    proc = _run(tmp_path, "build", {
        "CI_JOB_STAGE": "build-images", "JOB_ID": "job-1",
        "BSM_API_URL": bsm_server.url, "ACCESS_TOKEN": "stale-token",
    })
    assert proc.returncode == 0
    assert "Log preview unavailable (HTTP 401)" in proc.stdout
    assert "curl -H 'Authorization: Bearer <TOKEN>'" in proc.stdout


@pytest.mark.parametrize("template_key", sorted(TEMPLATES))
def test_hook_never_fails_under_errexit(tmp_path, bsm_server, template_key):
    """GIVEN a runner that uses 'sh -e' WHEN the API is unreachable THEN the exit code is 0."""
    script = tmp_path / "errexit.sh"
    script.write_text(_after_script(TEMPLATES[template_key]), encoding="utf-8")
    env = {
        "CI_JOB_STAGE": PLAYBOOK_STAGE[template_key], "JOB_ID": "job-1",
        "BSM_API_URL": "http://127.0.0.1:9", "ACCESS_TOKEN": "", "CURL_MAX_TIME": "2",
        "CURL_CONNECT_TIMEOUT": "1", "PATH": os.environ["PATH"],
    }
    proc = subprocess.run(["sh", "-e", str(script)], capture_output=True, text=True,
                          env=env, check=False)
    assert proc.returncode == 0
    assert "Retrieve complete execution logs" in proc.stdout
