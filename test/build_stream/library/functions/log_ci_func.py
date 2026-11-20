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

"""GitLab CI console log integration (ER-BSM-003 TC-FVT-021, TC-FVT-022).

The after_script of .gitlab-ci-build.yml and the deploy child template
previews the last ``BSM_LOG_TAIL_LINES`` lines of the stage's execution log
(playbook stages only) and prints curl templates with ``<TOKEN>``,
``<CLIENT_ID>`` and ``<CLIENT_SECRET>`` placeholders.

The GitLab jobs of the target BuildStream job are found from the pipelines
this session ran for it, else by scanning the newest pipelines and their
child pipelines for a job whose trace names ``/api/v1/jobs/<job_id>/logs``
(only the after_script prints it). Traces are compared with secrets held in
memory; a finding names the leak type, never the value.
"""

from typing import Any, Callable, Dict, List, Optional, Set

from . import gitlab_api_func
from .log_query_func import (
    SESSION, add_check, blocked_result, finish, new_result, session_pipeline_ids, target)
from ..messages.execute_msgs import STEP_MSGS
from ..vars.execute_vars import (
    ANSI_ESCAPE_RE,
    LOG_CI_FINISHED,
    LOG_CI_JOB_MARKER,
    LOG_CI_NON_PLAYBOOK_STAGES,
    LOG_CI_PREVIEW_BANNER,
    LOG_CI_PREVIEW_NOTICE,
    LOG_CI_PREVIEW_RULE,
    LOG_CI_PREVIEW_VARIABLE,
    LOG_CI_SCAN_DEPTH,
    LOG_CI_SCAN_PIPELINES,
    LOG_CI_SECRET_LEAKS,
    LOG_CI_SECRET_VARIABLES,
    LOG_CI_STAGE_MAP,
    LOG_CI_STAGE_TEMPLATE,
    LOG_CI_TEMPLATES,
)

Emit = Callable[[str], None]
_BANNER_PREFIX = LOG_CI_PREVIEW_BANNER.split("{", 1)[0]


def _trace(context: Dict[str, Any], job_id: int) -> str:
    """Return a GitLab job trace without ANSI escapes and carriage returns."""
    return ANSI_ESCAPE_RE.sub("", gitlab_api_func.job_trace(context, job_id))


def _relevant(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return finished jobs of stages whose after_script prints the log hook."""
    stages = (*LOG_CI_STAGE_MAP, *LOG_CI_NON_PLAYBOOK_STAGES)
    return [job for job in jobs
            if job.get("stage") in stages and job.get("status") in LOG_CI_FINISHED]


def discover_ci_jobs(context: Dict[str, Any], job_id: str, needed: List[str],
                     emit: Emit) -> List[Dict[str, Any]]:
    """Return the GitLab jobs (with trace) whose after_script served ``job_id``.

    Session pipelines are visited first, then the newest pipelines; each is
    followed into its child pipelines up to LOG_CI_SCAN_DEPTH. The scan
    stops once a job of every ``needed`` CI stage was found.
    """
    marker = LOG_CI_JOB_MARKER.format(job_id=job_id)
    queue = [(pid, 0) for pid in session_pipeline_ids(job_id)]
    queue += [(int(p["id"]), 0)
              for p in gitlab_api_func.list_pipelines(context, per_page=LOG_CI_SCAN_PIPELINES)]
    seen, found = set(), []
    while queue and not set(needed) <= {job["stage"] for job in found}:
        pipeline_id, depth = queue.pop(0)
        if pipeline_id in seen:
            continue
        seen.add(pipeline_id)
        relevant = _relevant(gitlab_api_func.pipeline_jobs(context, pipeline_id))
        if relevant:
            # Probe a playbook job: its after_script always names the BSM job.
            relevant.sort(key=lambda item: item["stage"] not in LOG_CI_STAGE_MAP)
            first = _trace(context, relevant[0]["id"])
            if marker in first:
                emit(f"GitLab pipeline #{pipeline_id} previews job {job_id}")
                traced = [{**relevant[0], "trace": first}]
                traced.extend({**job, "trace": _trace(context, job["id"])}
                              for job in relevant[1:])
                # A non-playbook job without a BSM job ID (initialization) prints a
                # skip notice only; playbook jobs are always kept.
                found.extend(job for job in traced
                             if job["stage"] in LOG_CI_STAGE_MAP or marker in job["trace"])
        if depth < LOG_CI_SCAN_DEPTH:
            for bridge in gitlab_api_func.pipeline_bridges(context, pipeline_id):
                child = (bridge.get("downstream_pipeline") or {}).get("id")
                if child:
                    queue.insert(0, (int(child), depth + 1))
    return found


def _ci_jobs(api: Dict[str, Any], job: Dict[str, Any], emit: Emit) -> Optional[List[Dict]]:
    """Return (and cache) the CI jobs of the target job; None when none was found."""
    if "ci" not in SESSION:
        needed = [ci for ci, bsm in LOG_CI_STAGE_MAP.items() if bsm in job["logged"]]
        SESSION["ci"] = discover_ci_jobs(api["context"], job["job_id"], needed, emit)
    return SESSION["ci"] or None


def _preview_lines(trace: str, banner: str) -> Optional[int]:
    """Return how many log lines follow ``banner`` up to its closing rule (None: no banner)."""
    lines = trace.splitlines()
    start = next((index for index, line in enumerate(lines) if banner in line), None)
    if start is None:
        return None
    rules = [index for index in range(start + 1, len(lines))
             if lines[index].rstrip().endswith(LOG_CI_PREVIEW_RULE)]
    return rules[1] - rules[0] - 1 if len(rules) >= 2 else 0


def _notice(trace: str) -> str:
    """Return the after_script notice line, if any."""
    return next((line.strip() for line in trace.splitlines()
                 if LOG_CI_PREVIEW_NOTICE in line), "no preview banner")


def verify_ci_log_preview(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """TC-FVT-021: playbook-stage CI jobs preview the last N execution-log lines.

    N is the BSM_LOG_TAIL_LINES project variable, which must equal
    ``log_ci_preview_lines`` of build_stream_config.yml. Failed jobs must
    preview too; non-playbook jobs must not.
    """
    del host, settings
    job = target()
    api = SESSION.get("client")
    if not job or not api:
        return blocked_result(STEP_MSGS["log_no_target"])
    result = new_result()
    variable = gitlab_api_func.ci_variable_value(api["context"], LOG_CI_PREVIEW_VARIABLE)
    lines = variable["value"].strip() if variable["success"] else ""
    expected = str(api["settings"]["ci_preview"])
    add_check(result, lines == expected, f"{LOG_CI_PREVIEW_VARIABLE}",
              f"{lines or variable['error']} (log_ci_preview_lines {expected})")
    ci_jobs = _ci_jobs(api, job, emit)
    if not ci_jobs:
        result["failures"].append(STEP_MSGS["log_ci_not_found"].format(
            count=LOG_CI_SCAN_PIPELINES, job_id=job["job_id"]))
        return finish(result)
    preview = int(lines) if lines.isdigit() else int(expected)
    failed_seen = False
    logged = set(job["logged"])
    for ci_job in ci_jobs:
        failed_seen = _check_preview(result, ci_job, preview, logged) or failed_seen
    result["fields"].append(("  Failure path", "covered by a failed job" if failed_seen
                             else "no failed playbook job with a log (manual evidence)"))
    return finish(result)


def _check_preview(result: Dict[str, Any], ci_job: Dict[str, Any], preview: int,
                   logged: Set[str]) -> bool:
    """Check one CI job's console output for its stage's log state.

    A stage with a published log must print the preview. A playbook stage
    without one (for example a request rejected before the playbook ran) must
    print the "not yet available" notice instead, and no preview. Returns True
    for a failed job whose preview was checked.
    """
    label = f"{ci_job['stage']} job #{ci_job['id']} ({ci_job['status']})"
    stage = LOG_CI_STAGE_MAP.get(ci_job["stage"])
    if stage is None:
        banner_found = _BANNER_PREFIX in ci_job["trace"]
        add_check(result, not banner_found, f"{label}: no preview",
                  "templates only" if not banner_found else "preview printed")
        return False
    if stage not in logged:
        notice = f"{LOG_CI_PREVIEW_NOTICE} Execution log not yet available for stage {stage}"
        found = notice in ci_job["trace"] and _BANNER_PREFIX not in ci_job["trace"]
        add_check(result, found, f"{label}: no log yet",
                  f"notice printed for stage {stage}" if found else _notice(ci_job["trace"]),
                  STEP_MSGS["log_ci_no_log_notice"].format(label=label, stage=stage))
        return False
    count = _preview_lines(ci_job["trace"],
                           LOG_CI_PREVIEW_BANNER.format(lines=preview, stage=stage))
    add_check(result, count is not None and 1 <= count <= preview, f"{label}: preview",
              f"{count} of at most {preview} lines" if count is not None
              else _notice(ci_job["trace"]))
    return ci_job["status"] == "failed"


def verify_ci_log_templates(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """TC-FVT-022: CI jobs print curl templates with placeholders and no credential."""
    del host, settings
    job = target()
    api = SESSION.get("client")
    if not job or not api:
        return blocked_result(STEP_MSGS["log_no_target"])
    result = new_result()
    ci_jobs = _ci_jobs(api, job, emit)
    if not ci_jobs:
        result["failures"].append(STEP_MSGS["log_ci_not_found"].format(
            count=LOG_CI_SCAN_PIPELINES, job_id=job["job_id"]))
        return finish(result)
    secrets = [api["token"]]
    for key in LOG_CI_SECRET_VARIABLES:
        variable = gitlab_api_func.ci_variable_value(api["context"], key)
        if variable["success"] and variable["value"]:
            secrets.append(variable["value"])
    for ci_job in ci_jobs:
        _check_templates(result, ci_job, job["job_id"], secrets)
    return finish(result)


def _check_templates(result: Dict[str, Any], ci_job: Dict[str, Any], job_id: str,
                     secrets: List[str]) -> None:
    """Check one CI job prints every curl template and no credential."""
    label = f"{ci_job['stage']} job #{ci_job['id']}"
    trace = ci_job["trace"]
    wanted = {name: text.format(job_id=job_id) for name, text in LOG_CI_TEMPLATES.items()}
    stage = LOG_CI_STAGE_MAP.get(ci_job["stage"])
    if stage:
        wanted["stage command"] = LOG_CI_STAGE_TEMPLATE.format(job_id=job_id, stage=stage)
    missing = [name for name, text in wanted.items() if text not in trace]
    add_check(result, not missing, f"{label}: templates",
              f"{len(wanted)} present" if not missing else f"missing {', '.join(missing)}")
    leaks = [name for name, pattern in LOG_CI_SECRET_LEAKS.items() if pattern.search(trace)]
    leaks += ["credential value"] * sum(1 for value in secrets if value in trace)
    add_check(result, not leaks, f"{label}: no credential",
              "none found" if not leaks else ", ".join(sorted(set(leaks))))
