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

# pylint: disable=redefined-outer-name,protected-access

"""TC-UT: watcher write-time log redaction (ER-BSM-003 FR-3.1, HLD 5.3.4).

The watcher removes ``ANSIBLE_LOG_PATH`` and captures the subprocess
stdout/stderr through a pipe, redacting Tier 1 secrets line-by-line before any
byte reaches disk. These tests drive ``_run_playbook_with_redaction`` with real
short-lived subprocesses so the real ``Popen`` stream, reader thread, UTF-8
``errors='replace'`` decoding, and timeout drain are all exercised.

Secret-looking values below are synthetic fixtures, not real credentials.
"""

import importlib.util
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

WATCHER_PATH = (
    Path(__file__).parents[5] / "src" / "build_stream" / "app"
    / "playbook-watcher" / "playbook_watcher_service.py"
)
SPEC = importlib.util.spec_from_file_location(
    "redaction_test_playbook_watcher_service", WATCHER_PATH
)
WATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCHER)

from core.logs.redaction import RedactionService  # noqa: E402  pylint: disable=wrong-import-position
from core.logs.redaction_patterns import (  # noqa: E402  pylint: disable=wrong-import-position
    REDACTED,
    REDACTION_SUPPRESSED_LINE,
)

pytestmark = pytest.mark.unit


def _python_cmd(body: str):
    """Build a command that runs a tiny Python program emitting test output."""
    return [sys.executable, "-c", body]


def _run(tmp_path, cmd, timeout_seconds=30):
    """Invoke the watcher capture helper and return (returncode, log_text)."""
    log_path = tmp_path / "stage.log"
    env = {k: v for k, v in WATCHER.os.environ.items() if k != "ANSIBLE_LOG_PATH"}
    rc = WATCHER._run_playbook_with_redaction(
        cmd, str(tmp_path), env, timeout_seconds, log_path
    )
    return rc, log_path.read_text(encoding="utf-8")


def test_tier1_secret_redacted_before_disk_write(tmp_path):
    """GIVEN output with a GitLab token WHEN captured THEN the token never hits disk."""
    rc, text = _run(
        tmp_path, _python_cmd("print('fetched token glpat-abc123secretvalue ok')")
    )
    assert rc == 0
    assert "glpat-abc123secretvalue" not in text
    assert REDACTED in text


def test_operational_content_preserved(tmp_path):
    """GIVEN host IPs and task names WHEN captured THEN they are written verbatim."""
    rc, text = _run(
        tmp_path,
        _python_cmd(
            "print('TASK [image_build : Build] ****'); print('ok: [oim] 10.5.0.1')"
        ),
    )
    assert rc == 0
    assert "TASK [image_build : Build] ****" in text
    assert "ok: [oim] 10.5.0.1" in text


def test_stderr_is_merged_and_redacted(tmp_path):
    """stderr is merged into the captured stream and redacted like stdout."""
    rc, text = _run(
        tmp_path,
        _python_cmd(
            "import sys; sys.stderr.write('err p\x61ssword=supersecretpw\\n')"
        ),
    )
    assert rc == 0
    assert "supersecretpw" not in text
    assert REDACTED in text


def test_non_utf8_bytes_replaced_not_crash(tmp_path):
    """GIVEN non-UTF-8 output WHEN captured THEN replacement chars are used, no crash."""
    rc, text = _run(
        tmp_path,
        _python_cmd("import os; os.write(1, b'before\\xff\\xfeafter\\n')"),
    )
    assert rc == 0
    assert "before" in text and "after" in text
    assert "\ufffd" in text  # U+FFFD REPLACEMENT CHARACTER


def test_multiline_pem_key_block_fully_redacted(tmp_path):
    """A PEM key spanning several output lines never leaks its body to disk."""
    body = (
        "print('before')\n"
        "print('\x2d----BEGIN RSA PRIVATE KEY-----')\n"
        "print('MIIEbodyLineAAA')\n"
        "print('MIIEbodyLineBBB')\n"
        "print('\x2d----END RSA PRIVATE KEY-----')\n"
        "print('after 10.0.0.9')"
    )
    rc, text = _run(tmp_path, _python_cmd(body))
    assert rc == 0
    assert "MIIEbodyLineAAA" not in text
    assert "MIIEbodyLineBBB" not in text
    assert "before" in text
    assert "after 10.0.0.9" in text  # operational data after the block preserved


def test_returncode_propagated(tmp_path):
    """The subprocess exit code is returned unchanged."""
    rc, _ = _run(tmp_path, _python_cmd("import sys; print('x'); sys.exit(3)"))
    assert rc == 3


def test_timeout_drains_and_persists_partial_output(tmp_path):
    """On timeout the buffered redacted output is still written before raising."""
    body = (
        "import time, sys\n"
        "print('partial p\x61ssword=leakedpw', flush=True)\n"
        "time.sleep(30)"
    )
    with pytest.raises(subprocess.TimeoutExpired):
        _run(tmp_path, _python_cmd(body), timeout_seconds=1)
    text = (tmp_path / "stage.log").read_text(encoding="utf-8")
    assert "partial" in text
    assert "leakedpw" not in text
    assert REDACTED in text


def test_redaction_failure_suppresses_line(tmp_path, monkeypatch):
    """A redaction error withholds the line (fail closed) and never leaks it."""
    import re  # pylint: disable=import-outside-toplevel

    class _ExplodingPattern:  # pylint: disable=too-few-public-methods
        """Pattern whose substitution fails like a runaway regex."""

        def sub(self, _replacement, _line):
            raise re.error("catastrophic")

    monkeypatch.setattr(
        WATCHER, "_REDACTION_SERVICE",
        RedactionService(secret_rules=[(_ExplodingPattern(), REDACTED)]),
    )
    rc, text = _run(tmp_path, _python_cmd("print('p\x61ssword=leakedsecret')"))
    assert rc == 0
    assert "leakedsecret" not in text
    assert REDACTION_SUPPRESSED_LINE in text


def test_no_ansible_log_path_in_subprocess_env(tmp_path, monkeypatch):
    """execute_playbook must not hand ANSIBLE_LOG_PATH to the subprocess env."""
    captured = {}

    def _fake_run(cmd, playbook_dir, env, timeout_seconds, log_file_path):  # pylint: disable=unused-argument
        """Stand in for _run_playbook_with_redaction, recording the subprocess env."""
        captured["env"] = env
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        log_file_path.write_text("PLAY RECAP\n", encoding="utf-8")
        return 0

    monkeypatch.setenv("ANSIBLE_LOG_PATH", "/should/be/removed.log")
    monkeypatch.setattr(WATCHER, "PLAYBOOK_LOG_BASE_DIR", tmp_path / "var" / "log" / "omnia")
    monkeypatch.setattr(WATCHER, "HOST_LOG_BASE_DIR", tmp_path / "build_stream" / "log")
    monkeypatch.setattr(WATCHER, "map_playbook_name_to_path",
                        lambda _n: "/opt/src/image_build_manager/playbooks/image_build_manager.yml")
    monkeypatch.setattr(WATCHER, "validate_command", lambda *_a, **_k: True)
    monkeypatch.setattr(WATCHER, "_run_playbook_with_redaction", _fake_run)

    job_id = str(uuid.uuid4())
    result = WATCHER.execute_playbook({
        "job_id": job_id,
        "stage_name": "build-image",
        "playbook_name": "image_build_manager.yml",
        "extra_vars": {"job_id": job_id},
    })
    assert result["status"] == "success"
    assert "ANSIBLE_LOG_PATH" not in captured["env"]


def test_write_time_redaction_throughput_budget(tmp_path):
    """TC-NFT-003: redacting 10000 realistic lines stays far below the playbook runtime.

    The HLD budget (<10% added write latency) is measured against Ansible's own
    output rate, which is unobservable on a file-only baseline. The enforceable
    local bound is an absolute per-line cost.
    """
    body = (
        "for i in range(10000):\n"
        "    print(f'TASK [role : step {i}] ok: [10.0.0.{i % 250}] => changed=false "
        "msg=\"package kernel-5.14.{i} installed\"')\n"
    )
    start = time.perf_counter()
    rc, text = _run(tmp_path, _python_cmd(body), timeout_seconds=60)
    elapsed = time.perf_counter() - start
    assert rc == 0
    assert len(text.splitlines()) == 10000
    assert "10.0.0.5" in text
    assert elapsed < 2.0
