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

"""RUN steps: the product command ``src/main/omnia.sh`` run as a customer runs it.

An SVT test with ``run`` (test_case_vars.py) runs ``./omnia.sh --prepare-base`` or
``./omnia.sh -r <domain> [--tags <tag>]`` instead of an FVT step; the checks that follow
are FVT steps. The arguments are checked against theme_vars.OMNIA_RUN_TAGS and the
theme's ``run_domains`` (no free text reaches the command line), the command runs without
a shell and with an empty stdin (a prompt fails instead of waiting), and its output streams
into the stage log. The result has the shape of fvt_func.run_fvt_step (no FVT results).
"""

from typing import Any, Dict, Sequence, Tuple

from .process_func import stream_command
from ..vars.common_vars import OMNIA_RUN_ARG, OMNIA_SH, OMNIA_SH_DIR, OMNIA_TAGS_ARG
from ..vars.theme_vars import OMNIA_PREPARE_BASE, OMNIA_RUN_TAGS, THEMES


def check_run_args(theme: str, arguments: Sequence[str]) -> Tuple[str, ...]:
    """Return ``arguments`` when ``theme`` may run them with omnia.sh, else raise ValueError."""
    args = tuple(str(arg) for arg in arguments)
    if args == OMNIA_PREPARE_BASE:
        return args
    domains = THEMES[theme].get("run_domains") or ()
    if len(args) >= 2 and args[0] == OMNIA_RUN_ARG and args[1] in domains:
        if len(args) == 2:
            return args
        if (len(args) == 4 and args[2] == OMNIA_TAGS_ARG
                and args[3] in OMNIA_RUN_TAGS.get(args[1], ())):
            return args
    raise ValueError(f"omnia.sh {' '.join(args)!r} is not a RUN step of theme {theme!r} "
                     f"(allowed: {' '.join(OMNIA_PREPARE_BASE)}, or {OMNIA_RUN_ARG} <domain of "
                     f"{list(domains)}> [{OMNIA_TAGS_ARG} <tag of theme_vars.OMNIA_RUN_TAGS>])")


def describe_run(arguments: Sequence[str]) -> str:
    """Return the command of a RUN step as text, e.g. ``./omnia.sh -r telemetry``."""
    return " ".join(["./omnia.sh", *arguments])


def run_info(arguments: Sequence[str]) -> Dict[str, Any]:
    """Return what a RUN step runs (the report's header chips): suite, tag, action, options."""
    args = tuple(arguments)
    if args == OMNIA_PREPARE_BASE:
        return {"suite": "src/main/omnia.sh", "domain": "main", "tag": "prepare-base",
                "action": "run", "options": ""}
    tag = args[3] if len(args) == 4 else "default flow"
    return {"suite": "src/main/omnia.sh", "domain": args[1], "tag": tag, "action": "run",
            "options": ""}


def run_omnia_step(theme: str, arguments: Sequence[str]) -> Dict[str, Any]:
    """Run ``./omnia.sh <arguments>`` in src/main and stream its output.

    Returns:
        Dict with keys: success, rc, duration, command, output, step (label), fvt (run_info),
        results (always empty: a RUN step has no FVT results).
    """
    args = check_run_args(theme, arguments)
    result: Dict[str, Any] = dict(stream_command(["bash", OMNIA_SH, *args], cwd=OMNIA_SH_DIR))
    result["step"] = describe_run(args)
    result["fvt"] = run_info(args)
    result["results"] = []
    return result
