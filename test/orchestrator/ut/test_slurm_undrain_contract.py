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

"""Contract tests: Slurm undrain must pass node names as argv, never via a shell.

The previous task ran a ``for ... $(sinfo ...)`` loop through
``ansible.builtin.command``, which has no shell. The loop never executed
(rc=2, hidden by ``failed_when: false``), so drained nodes were never resumed.
The replacement lists nodes with ``sinfo`` and resumes each one with an argv
``scontrol`` call after an allowlist check.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

SLURM_ROLE = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "orchestrator"
    / "roles"
    / "slurm_config"
)
TASKS_FILE = SLURM_ROLE / "tasks" / "check_ctld_running.yml"
VARS_FILE = SLURM_ROLE / "vars" / "main.yml"

LIST_TASK = "Get drained or down Slurm nodes"
RESUME_TASK = "Undrain drained or down Slurm nodes"
WARN_TASK = "Warn about Slurm nodes that were not resumed"


def _load_block_tasks():
    tasks = yaml.safe_load(TASKS_FILE.read_text(encoding="utf-8"))
    return next(task for task in tasks if "block" in task)["block"]


def _task(name):
    return next(task for task in _load_block_tasks() if task.get("name") == name)


def test_undrain_does_not_use_shell_loop():
    for task in _load_block_tasks():
        command = task.get("ansible.builtin.command")
        text = command.get("cmd", "") if isinstance(command, dict) else str(command or "")
        assert "$(" not in text and "for " not in text, task.get("name")
        assert "ansible.builtin.shell" not in task, task.get("name")


def test_undrain_uses_argv_with_validated_node_names():
    list_task = _task(LIST_TASK)
    assert list_task["ansible.builtin.command"]["argv"][0] == "sinfo"

    resume_task = _task(RESUME_TASK)
    assert resume_task["ansible.builtin.command"]["argv"] == [
        "scontrol",
        "update",
        "NodeName={{ item }}",
        "State=RESUME",
    ]
    assert "slurm_node_name_pattern" in resume_task["loop"]


def test_node_name_pattern_rejects_shell_metacharacters():
    import re

    pattern = re.compile(yaml.safe_load(VARS_FILE.read_text(encoding="utf-8"))[
        "slurm_node_name_pattern"
    ])
    for good in ("node1", "slurm-node-01", "n1.cluster.local", "a_b"):
        assert pattern.match(good), good
    for bad in ("", "-node", "a;b", "a b", "$(id)", "`id`", "a|b", "a=b", "a\nb"):
        assert not pattern.match(bad), repr(bad)


@pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="ansible CLI not installed"
)
def test_undrain_executes_argv_only_and_reports_failures(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "scontrol.log"
    marker_semicolon = tmp_path / "pwned_semicolon"
    marker_subst = tmp_path / "pwned_subst"

    (bindir / "sinfo").write_text(
        "#!/bin/sh\n"
        "cat <<'EOF'\n"
        "node1\nnode2\nnode1\n\n"
        f"bad;touch {marker_semicolon}\n"
        f"$(touch {marker_subst})\n"
        "node3\n"
        "EOF\n",
        encoding="utf-8",
    )
    (bindir / "scontrol").write_text(
        "#!/bin/sh\n"
        f'echo "CALL:$#" >> {log}\n'
        f'for a in "$@"; do echo "ARG:$a" >> {log}; done\n'
        'for a in "$@"; do [ "$a" = "NodeName=node3" ] && exit 1; done\n'
        "exit 0\n",
        encoding="utf-8",
    )
    for name in ("sinfo", "scontrol"):
        path = bindir / name
        path.chmod(path.stat().st_mode | stat.S_IEXEC)

    pattern = yaml.safe_load(VARS_FILE.read_text(encoding="utf-8"))[
        "slurm_node_name_pattern"
    ]
    play = [
        {
            "hosts": "localhost",
            "gather_facts": False,
            "environment": {"PATH": f"{bindir}:{os.environ['PATH']}"},
            "vars": {
                "ctld": "localhost",
                "ctld_state": {"localhost": True},
                "slurm_node_name_pattern": pattern,
            },
            "tasks": [_task(LIST_TASK), _task(RESUME_TASK), _task(WARN_TASK)],
        }
    ]
    playbook = tmp_path / "undrain.yml"
    playbook.write_text(yaml.safe_dump(play), encoding="utf-8")

    result = subprocess.run(
        ["ansible-playbook", "-i", "localhost,", "-c", "local", str(playbook)],
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    calls = log.read_text(encoding="utf-8").splitlines()
    args = [line[4:] for line in calls if line.startswith("ARG:")]
    assert [a for a in args if a.startswith("NodeName=")] == [
        "NodeName=node1",
        "NodeName=node2",
        "NodeName=node3",
    ]
    assert calls.count("CALL:3") == 3
    assert args.count("update") == 3 and args.count("State=RESUME") == 3
    assert not marker_semicolon.exists()
    assert not marker_subst.exists()
    assert "Slurm node(s) not resumed on localhost: node3" in result.stdout
