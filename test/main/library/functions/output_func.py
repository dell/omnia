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

"""Consistent, concise detail fields for Omnia Main test output."""

from typing import Any, Dict, Mapping, Optional

from omnia_auto import TestLogger as _BaseTestLogger


def _compact(value: Any, limit: int = 180) -> str:
    """Collapse multiline diagnostic text and keep terminal output readable."""
    rendered = " ".join(str(value).split())
    return rendered if len(rendered) <= limit else f"{rendered[:limit - 3]}..."


def command_result_fields(
    result: Mapping[str, Any],
    expected: str = "",
    context: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build ordered CLI/report fields without dumping long command output."""
    expected_result = expected or (
        "non-zero return code" if result.get("expected_error")
        else "return code 0"
    )
    fields: Dict[str, Any] = {
        "Command": _compact(result.get("command", "not recorded")),
        "Expected": expected_result,
        "Return code": result.get("rc", "unknown"),
    }
    if context:
        fields.update(context)
    if result.get("duration") is not None:
        fields["Duration"] = f"{result['duration']:.1f}s"
    if result.get("error"):
        fields["Error"] = _compact(result["error"])
    return fields


class TestLogger(_BaseTestLogger):
    """Test logger that can render a bound verification result consistently."""

    def __init__(self, test_name: str, tc_id: str = ""):
        super().__init__(test_name, tc_id)
        self._bound_result: Optional[Mapping[str, Any]] = None

    def bind_result(self, result: Mapping[str, Any]) -> None:
        """Bind the result used by the next PASS or FAIL output."""
        self._bound_result = result

    def _bound_fields(self) -> Dict[str, Any]:
        result = self._bound_result or {}
        if "command" in result or "rc" in result:
            return command_result_fields(result)

        fields: Dict[str, Any] = {}
        if result.get("details"):
            fields["Observed"] = _compact(result["details"])
        if result.get("found"):
            fields["Verified"] = ", ".join(map(str, result["found"]))
        if "missing" in result:
            fields["Missing"] = (
                ", ".join(map(str, result["missing"])) or "none"
            )
        if "missing_sections" in result:
            fields["Missing sections"] = (
                ", ".join(map(str, result["missing_sections"])) or "none"
            )
        if result.get("file_count") is not None:
            fields["Files found"] = result["file_count"]
        if result.get("error"):
            fields["Error"] = _compact(result["error"])
        return fields

    def passed(self, message: str, details: str = None) -> None:
        """Render a pass with bound structured fields when available."""
        fields = self._bound_fields() if details is None else {}
        if fields:
            _BaseTestLogger.passed(self, message)
            self._add_fields(fields)
        else:
            super().passed(message, details)

    def failed(self, message: str, details: str = None) -> None:
        """Render a failure with bound structured fields when available."""
        fields = self._bound_fields() if details is None else {}
        if fields:
            _BaseTestLogger.failed(self, message)
            self._add_fields(fields)
        else:
            super().failed(message, details)

    def passed_fields(self, message: str, fields) -> None:
        """Render explicit structured pass fields without recursive dispatch."""
        _BaseTestLogger.passed(self, message)
        self._add_fields(fields)

    def failed_fields(self, message: str, fields) -> None:
        """Render explicit structured failure fields without recursive dispatch."""
        _BaseTestLogger.failed(self, message)
        self._add_fields(fields)
