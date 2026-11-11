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

"""Unit contracts for Orchestrator NFT configuration and recap parsing."""

import pytest
from library.functions.nft_func import (
    persistent_changed_count,
    resolve_nft_thresholds,
)


def _threshold_config(**overrides):
    values = {
        "precheck": 60,
        "prepare": 300,
        "provision": 1800,
        "cleanup": 180,
    }
    values.update(overrides)
    return {"nft_performance_threshold_seconds": values}


def test_nft_thresholds_accept_complete_positive_integer_mapping():
    """ORCH_UT_030: Complete positive lifecycle thresholds are accepted."""
    assert resolve_nft_thresholds(_threshold_config())["provision"] == 1800


def test_nft_thresholds_reject_missing_lifecycle():
    """ORCH_UT_031: Missing lifecycle thresholds fail closed."""
    config = _threshold_config()
    del config["nft_performance_threshold_seconds"]["cleanup"]

    with pytest.raises(ValueError, match="missing: cleanup"):
        resolve_nft_thresholds(config)


@pytest.mark.parametrize("invalid", [True, 0, -1, 2.5, "60"])
def test_nft_thresholds_reject_invalid_values(invalid):
    """ORCH_UT_032: Non-positive or non-integer thresholds are rejected."""
    with pytest.raises(TypeError, match="precheck must be a positive integer"):
        resolve_nft_thresholds(_threshold_config(precheck=invalid))


def test_persistent_change_count_excludes_inventory_only_change():
    """ORCH_UT_033: In-memory inventory updates are excluded from the recap."""
    output = """
TASK [orchestrator_setup : Create OIM host group] *****************************
changed: [localhost]
TASK [prepare : Inspect state] ************************************************
ok: [localhost]
localhost : ok=2 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
oim : ok=1 changed=0 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
"""
    assert persistent_changed_count(output) == 0


def test_persistent_change_count_requires_ansible_recap():
    """ORCH_UT_034: Missing recap evidence cannot prove idempotency."""
    with pytest.raises(ValueError, match="no changed= recap"):
        persistent_changed_count("playbook output unavailable")
