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

"""Log information is printed only for stages that run a playbook (ER-BSM-003).

parse-catalog is a synchronous API call with no playbook, so it must not print a
stage log box, and the pipeline summaries list logs only for playbook stages.
"""

import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_FILES = (
    Path(__file__).parents[5]
    / "src" / "build_stream" / "roles" / "hosted_gitlab" / "files"
)
TEMPLATES = sorted(_FILES.glob(".gitlab-ci-*.yml"))
PLAYBOOK_STAGE_JOBS = {
    ".gitlab-ci-build.yml": ("configure-local-repository", "build-images"),
    ".gitlab-ci-cadence.yml": (
        "configure-local-repository", "build-images", "deploy", "restart", "validate"),
    ".gitlab-ci-deploy-child-template.yml": ("deploy", "restart", "validate"),
}


def _script(job: dict) -> str:
    """Join a job's script lines into one shell text."""
    return "\n".join(str(line) for line in job.get("script", []))


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.name)
def test_api_stage_log_box_is_gone(path):
    """The API-only stage log box helper and its callers are removed everywhere."""
    assert "print_api_stage_log_info" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", [".gitlab-ci-build.yml", ".gitlab-ci-cadence.yml"])
def test_parse_catalog_prints_no_log_information(name):
    """GIVEN the parse-catalog job WHEN its script runs THEN it names no log file."""
    job = _load(_FILES / name)["parse-catalog"]
    text = _script(job)
    assert "Log File Path" not in text
    assert "print_stage_log_info" not in text
    assert "execution logs" not in text
    assert "[OK] Catalog parsed" in text  # the result line is still printed


@pytest.mark.parametrize("name", PLAYBOOK_STAGE_JOBS)
def test_summary_lists_logs_only_for_playbook_stages(name):
    """The summary 'Stage Logs' list names only stages that ran a playbook."""
    text = _script(_load(_FILES / name)["summary"])
    assert "Stage Logs:" in text or name == ".gitlab-ci-deploy-child-template.yml"
    assert 'print_stage_log_info "parse-catalog"' not in text
    assert "for _SUMMARY_STAGE in" in text
    loop = text[text.index("for _SUMMARY_STAGE in"):].split(";")[0]
    assert "parse-catalog" not in loop


@pytest.mark.parametrize("name,stages", PLAYBOOK_STAGE_JOBS.items())
def test_playbook_stages_still_report_their_log(name, stages):
    """The playbook stages keep their stage log reporting."""
    data = _load(_FILES / name)
    for stage in stages:
        assert "print_stage_log_info" in _script(data[stage]), stage


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.name)
def test_all_job_scripts_are_valid_shell(path, tmp_path):
    """Every job script block and the after_script parse as POSIX shell."""
    data = _load(path)
    blocks = []
    for key, job in data.items():
        if isinstance(job, dict):
            for field in ("before_script", "script", "after_script"):
                if job.get(field):
                    blocks.append((key, field, "\n".join(str(x) for x in job[field])))
    assert blocks
    for key, field, text in blocks:
        script = tmp_path / "check.sh"
        script.write_text(text, encoding="utf-8")
        proc = subprocess.run(["sh", "-n", str(script)], capture_output=True, text=True,
                              check=False)
        assert proc.returncode == 0, f"{path.name} {key}.{field}: {proc.stderr}"
