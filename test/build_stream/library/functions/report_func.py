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


"""Report one check or tag playbook result through TestLogger.

These helpers only log (and build the failure message); the calling test
asserts the result.
"""

from typing import Any, Dict

from .probe_func import result_fields
from ..messages.build_stream_msgs import TEST_ASSERT_MSGS as ASSERT
from ..messages.build_stream_msgs import TEST_LOG_MSGS as LOG


def report_check(tl: Any, result: Dict[str, Any]) -> None:
    """Log every checked item of ``result`` as a field, as passed or failed."""
    fields = result_fields(result)
    if result["success"]:
        tl.passed_fields(LOG["result_passed"], fields)
    else:
        tl.failed_fields(
            LOG["result_failed"],
            [*fields, ("Error", result.get("error") or LOG["result_no_error"])],
        )


def report_tag_playbook(tl: Any, tag: str, result: Dict[str, Any],
                        arguments: str = "") -> str:
    """Log the ``build_stream.yml --tags <tag>`` run in ``result``.

    Returns:
        The assertion message for a failed run.
    """
    command = f"ansible-playbook build_stream.yml --tags {tag} {arguments}".rstrip()
    fields = [
        ("Command", command),
        ("Return code", result["rc"]),
        ("Duration seconds", f"{result['duration']:.1f}"),
    ]
    if result["success"]:
        tl.passed_fields(
            LOG["tag_playbook_ok"].format(tag=tag, duration=result["duration"]), fields,
        )
    else:
        tl.failed_fields(
            LOG["tag_playbook_failed"].format(
                tag=tag, rc=result["rc"], duration=result["duration"]),
            [*fields, ("Error", result.get("error") or LOG["result_no_error"])],
        )
    return ASSERT["tag_playbook_failed"].format(
        tag=tag, rc=result["rc"], duration=result["duration"], error=result.get("error"),
    )
