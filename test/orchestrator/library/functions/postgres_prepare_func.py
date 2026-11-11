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

"""PostgreSQL postcondition helpers for the prepare lifecycle."""

from typing import Any

from omnia_auto import run_on_host

from ..vars.prepare_vars import (
    POSTGRES_CONTAINER,
    POSTGRES_READINESS_SCRIPT,
    POSTGRES_REQUIRED_DATABASE,
    POSTGRES_REQUIRED_ROLE,
    PREPARE_COMMANDS,
)
from ._prepare_helpers import prepare_result


def check_prepare_postgresql_readiness(host) -> dict[str, Any]:
    """Verify PostgreSQL accepts queries and contains the SMD database role."""
    probe = run_on_host(
        host,
        PREPARE_COMMANDS["postgres_readiness"],
        POSTGRES_READINESS_SCRIPT,
    )
    observed = {}
    for line in probe.stdout.splitlines():
        key, separator, value = line.strip().partition("|")
        if separator and key in {"READY", "DATABASE", "ROLE", "QUERY"}:
            observed[key] = value

    states = {
        "READY": ("PostgreSQL readiness", "ready"),
        "DATABASE": (
            f"Database {POSTGRES_REQUIRED_DATABASE}",
            "present",
        ),
        "ROLE": (f"Role {POSTGRES_REQUIRED_ROLE}", "present"),
        "QUERY": (
            f"Read-only query on {POSTGRES_REQUIRED_DATABASE}",
            "passed",
        ),
    }
    fields = [("Container", POSTGRES_CONTAINER)]
    failures = []
    for key, (label, expected) in states.items():
        actual = observed.get(key, "not checked")
        fields.append((label, actual))
        if actual != expected:
            failures.append(f"{label}={actual}")
    if probe.rc != 0 and not failures:
        failures.append(f"PostgreSQL probe rc={probe.rc}")

    return prepare_result(
        not failures,
        "PostgreSQL and SMD database readiness checked",
        fields,
        "; ".join(failures),
    )
