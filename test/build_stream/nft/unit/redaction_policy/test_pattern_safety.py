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

"""Pattern-safety check against the shared vectors (TC-UT-018)."""

from pathlib import Path

import pytest
import yaml

from core.logs.redaction_policy import check_pattern_safety

pytestmark = pytest.mark.unit

VECTORS_PATH = Path(__file__).with_name("pattern_safety_vectors.yml")
with VECTORS_PATH.open(encoding="utf-8") as handle:
    VECTORS = yaml.safe_load(handle)


@pytest.mark.parametrize("case", VECTORS["accepted"], ids=lambda case: case["pattern"][:40])
def test_accepted_vectors_pass(case):
    """Accepted vectors return no reason."""
    assert check_pattern_safety(case["pattern"], case.get("allow_nested", False)) is None


@pytest.mark.parametrize("case", VECTORS["rejected"], ids=lambda case: case["pattern"][:40])
def test_rejected_vectors_return_their_reason(case):
    """Rejected vectors return exactly the expected reason."""
    assert check_pattern_safety(case["pattern"], case.get("allow_nested", False)) == case["reason"]


@pytest.mark.parametrize("value", [None, 5, ["a"]])
def test_non_string_is_empty(value):
    """Non-string input is refused as empty rather than raising."""
    assert check_pattern_safety(value) == "empty"
