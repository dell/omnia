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

# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-LOGGING-001.2, CG-SECRETS-001.7, CG-INPUT-001.9, CG-LOGGING-001.1
# ****

"""Ansible-side pattern-safety check against the shared vectors (TC-UT-018)."""

import importlib.util
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parents[5] / "src" / "build_stream"
CHECK_PATH = (
    SRC / "plugins" / "module_utils" / "input_validation" / "validators"
    / "redaction_pattern_check.py"
)
VECTORS_PATH = (
    Path(__file__).resolve().parents[1] / "redaction_policy" / "pattern_safety_vectors.yml"
)


def _load_check():
    """Load the Ansible-side check module from its file."""
    spec = importlib.util.spec_from_file_location("redaction_pattern_check", CHECK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _vectors() -> dict:
    """Load the shared vectors file."""
    with VECTORS_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


CHECK = _load_check()


@pytest.mark.parametrize("case", _vectors()["accepted"], ids=lambda case: case["pattern"][:40])
def test_accepted_vectors_pass(case):
    """GIVEN a shared accepted vector THEN the Ansible check returns no reason."""
    assert CHECK.check_pattern_safety(case["pattern"], case.get("allow_nested", False)) is None


@pytest.mark.parametrize("case", _vectors()["rejected"], ids=lambda case: case["pattern"][:40])
def test_rejected_vectors_return_their_reason(case):
    """GIVEN a shared rejected vector THEN the Ansible check returns the same reason."""
    reason = CHECK.check_pattern_safety(case["pattern"], case.get("allow_nested", False))
    assert reason == case["reason"]


def test_reserved_rule_ids_match_baseline_and_built_in_rules():
    """The reserved ids are the baseline pattern ids plus the built-in rule ids."""
    assert CHECK.RESERVED_RULE_IDS == frozenset({
        "private-key", "key-value", "gitlab-token", "jwt", "bearer", "url-credentials",
        "ipv4", "ipv6", "email",
    })


def test_length_limit_is_inclusive_at_256():
    """A pattern of exactly 256 characters is accepted; 257 is too long."""
    assert CHECK.check_pattern_safety("a" * 256) is None
    assert CHECK.check_pattern_safety("a" * 257) == "too-long"
