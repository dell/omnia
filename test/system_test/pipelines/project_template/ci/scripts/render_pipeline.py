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

"""Validate the clusters and write the child pipeline of one SVT run.

    python3 ci/scripts/render_pipeline.py --theme build_stream --clusters all \
        --start-stage initialization --out generated/pipeline.yml [--check-only]

One job chain per selected cluster (jobs named <cluster>:<stage>), all in one
child pipeline so clusters run in parallel; every job of a cluster shares the
resource group svt-<cluster>, so two runs never use the same OIM at once.
On a push, --clusters all selects only the clusters whose files changed.
"""

import argparse
import json
import os
import subprocess  # nosec B404  # fixed git argument list
import sys
from typing import Any, Dict, List

from svt_ci import STAGES, ConfigError, list_clusters, load_cluster, load_theme

ARTIFACT_DIR = "svt-reports"
ARTIFACT_EXPIRY = "30 days"
SCRIPT = "ci/scripts/remote_stage.sh"


def changed_clusters(before: str, current: str) -> List[str]:
    """Return clusters with changed files between two commits ([] when unknown)."""
    if not before or set(before) == {"0"}:
        return []
    try:
        result = subprocess.run(  # nosec B603 B607  # fixed git argument list
            ["git", "diff", "--name-only", before, current, "--", "clusters"],
            capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return sorted({line.split("/")[1] for line in result.stdout.splitlines()
                   if line.count("/") >= 2})


def select_clusters(requested: str) -> List[str]:
    """Return the cluster names to run."""
    available = list_clusters()
    if requested != "all":
        names = [name.strip() for name in requested.split(",") if name.strip()]
        unknown = [name for name in names if name not in available]
        if unknown:
            raise ConfigError(f"unknown cluster(s) {', '.join(unknown)}; "
                              f"available: {', '.join(available) or 'none'}")
        return names
    if os.environ.get("CI_PIPELINE_SOURCE") == "push":
        changed = changed_clusters(os.environ.get("CI_COMMIT_BEFORE_SHA", ""),
                                   os.environ.get("CI_COMMIT_SHA", "HEAD"))
        if changed:
            return [name for name in changed if name in available]
    return available


def _job(cluster: Dict[str, Any], stage: str, timeout: str, run_id: str, theme: str,
         extra: Dict[str, str], tag: str) -> Dict[str, Any]:
    name = cluster["name"]
    report_dir = f"{ARTIFACT_DIR}/{name}"
    job: Dict[str, Any] = {
        "stage": stage,
        "resource_group": f"svt-{name}",
        "timeout": timeout,
        "variables": {"SVT_CLUSTER": name, "SVT_STAGE": stage, "SVT_THEME": theme,
                      "SVT_RUN_ID": run_id, **extra},
        "id_tokens": {"SVT_ID_TOKEN": {"aud": cluster["openbao_audience"]}},
        "script": [f"bash {SCRIPT}"],
        "after_script": [f"bash {SCRIPT} --stop"],
        "artifacts": {"when": "always", "expire_in": ARTIFACT_EXPIRY,
                      "paths": [f"{report_dir}/"],
                      "reports": {"junit": f"{report_dir}/*.xml"}},
    }
    if tag:
        job["tags"] = [tag]
    return job


def render(theme_name: str, clusters: List[str], start_stage: str,
           pipeline_id: str) -> Dict[str, Any]:
    """Return the child pipeline definition."""
    theme = load_theme(theme_name)
    first = STAGES.index(start_stage)
    pipeline: Dict[str, Any] = {"stages": list(STAGES)}
    for name in clusters:
        cluster = load_cluster(name)
        timeouts = {**theme["timeouts"], **cluster["timeouts"]}
        run_id = f"svt-{pipeline_id}-{name}"
        resume = {"SVT_RESUME": "true"} if first > 0 else {}
        tag, log_tag = cluster["runner_tag"], cluster["full_log_runner_tag"] or cluster["runner_tag"]
        previous = ""
        for stage in STAGES[first:-1]:
            if stage == "system_verification":
                for case in theme["cases"]:
                    job_name = f"{name}:svt:{case}"
                    job = _job(cluster, stage, timeouts[stage], run_id, theme_name,
                               {"SVT_CASE": case, "SVT_FULL_LOG": "true", **resume}, log_tag)
                    if previous:
                        job["needs"] = [previous]
                    pipeline[job_name], previous = job, job_name
                continue
            job_name = f"{name}:{stage}"
            extra = {"SVT_CREDENTIAL_MODULES": " ".join(theme.get("credential_modules") or [])} \
                if stage == "environment_setup" else {}
            job = _job(cluster, stage, timeouts[stage], run_id, theme_name,
                       {**extra, **resume}, tag)
            if previous:
                job["needs"] = [previous]
            pipeline[job_name], previous = job, job_name
        summary = _job(cluster, "summary", timeouts["summary"], run_id, theme_name, {}, tag)
        summary["when"] = "always"
        summary["needs"] = [{"job": previous, "optional": True}] if previous else []
        pipeline[f"{name}:summary"] = summary
    return pipeline


def main(argv: List[str]) -> int:
    """Parse the arguments, validate and write the pipeline."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("--theme", required=True)
    parser.add_argument("--clusters", default="all")
    parser.add_argument("--start-stage", choices=STAGES[:-1], default=STAGES[0])
    parser.add_argument("--out", default="generated/pipeline.yml")
    parser.add_argument("--check-only", action="store_true",
                        help="validate every cluster and theme, write nothing")
    args = parser.parse_args(argv)
    try:
        clusters = select_clusters(args.clusters)
        if not clusters:
            raise ConfigError("no cluster selected: add clusters/<name>/ "
                              "(cluster.yml, user_inputs.yml, test_config.yml)")
        pipeline = render(args.theme, clusters, args.start_stage,
                          os.environ.get("CI_PIPELINE_ID", "local"))
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"theme {args.theme}, start {args.start_stage}, clusters: {', '.join(clusters)}")
    if not args.check_only:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as stream:
            json.dump(pipeline, stream, indent=2)
        print(f"child pipeline written: {args.out} ({len(pipeline) - 1} jobs)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
