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

"""Schema parity tests for BuildStream cadence input fields."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator


SCHEMA_PATH = (
    Path(__file__).parents[5]
    / "src"
    / "build_stream"
    / "plugins"
    / "module_utils"
    / "input_validation"
    / "schema"
    / "build_stream_config.json"
)


def _validator() -> Draft7Validator:
    """Return the checked-in BuildStream input-schema validator."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft7Validator(schema)


def _config(cadence: dict) -> dict:
    """Return a minimal document that isolates cadence validation."""
    return {
        "enable_build_stream": False,
        "cadence": cadence,
    }


@pytest.mark.unit
def test_cadence_schema_accepts_supported_boundaries():
    """TC-UT-001-014: Accept every supported cadence field at its limits."""
    document = _config(
        {
            "enabled": True,
            "interval_days": 1,
            "sync_timeout_seconds": 60,
            "sync_poll_interval_seconds": 300,
        }
    )

    assert list(_validator().iter_errors(document)) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "field,value",
    [
        ("enabled", "true"),
        ("interval_days", 0),
        ("interval_days", 0.5),
        ("interval_days", True),
        ("sync_timeout_seconds", 59),
        ("sync_poll_interval_seconds", 0),
        ("sync_poll_interval_seconds", 301),
    ],
)
def test_cadence_schema_rejects_invalid_values(field, value):
    """TC-UT-001-015: Reject invalid cadence types and boundaries."""
    errors = list(_validator().iter_errors(_config({field: value})))

    assert errors, f"Expected schema rejection for cadence.{field}={value!r}"


@pytest.mark.unit
def test_cadence_schema_rejects_unknown_fields():
    """TC-UT-001-016: Reject removed or unsupported cadence settings."""
    errors = list(
        _validator().iter_errors(
            _config({"enabled": True, "catalog_filename": "other.json"})
        )
    )

    assert errors
    assert "Additional properties" in errors[0].message
