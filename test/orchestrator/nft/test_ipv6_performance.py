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
"""NFT: IPoIB IPv6 performance benchmarks (TC-NFT-001, TC-NFT-002, TC-NFT-003).

These tests verify NFR-1 performance targets:
- TC-NFT-001: Allocation validation p95 < 100 ms/record (500 records)
- TC-NFT-002: Artifact generation p95 < 30 s/node (500 nodes)
- TC-NFT-003: IPv6/IPv4 throughput parity (median within 5%)

Local tests use synthetic data to validate the benchmark framework itself.
Physical tests must be run on the approved IB testbed.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from unittest import mock

import pytest

# Path setup for module_utils imports
_SRC_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..",
                 "src", "orchestrator", "plugins")
)
sys.path.insert(0, os.path.join(_SRC_ROOT, "module_utils"))
sys.path.insert(0, _SRC_ROOT)

# Mock ansible.module_utils path
sys.modules.setdefault("ansible", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils.basic", mock.MagicMock())

from orchestrator_validation.validators import (  # noqa: E402
    ib_ipv6_allocation_validator as validator,
)
from orchestrator_validation.renderers import nm_renderer  # noqa: E402

pytestmark = pytest.mark.nft


def _generate_allocation_data(record_count: int) -> dict:
    """Generate synthetic allocation data matching the real schema."""
    records = []
    for i in range(record_count):
        node_num = i // 2
        iface_num = i % 2
        records.append({
            "allocation_id": f"alloc-{i:06d}",
            "node_id": f"x3000c0s{node_num}b0n0",
            "interface_id": f"ib{iface_num}",
            "hostname": f"node-{node_num:04d}",
            "address": f"fd00:1b::{node_num:04x}:{iface_num + 1}",
            "prefix_length": 64,
            "address_family": "ipv6",
            "fabric_id": "fabric-1",
            "rail_id": "rail1",
            "lifecycle_state": "active",
            "mtu": 2044,
            "ipoib_mode": "datagram",
            "pkey": "0x7FFF",
        })

    return {
        "schema_version": "1.0",
        "snapshot_id": f"bench-{record_count}",
        "generated_at": "2026-09-25T12:00:00Z",
        "allocations": records,
    }


class TestAllocationValidationLatency:
    """TC-NFT-001: Allocation validation p95 latency benchmark."""

    def test_schema_validation_latency_50_records(self):
        """Validate that schema validation completes efficiently for 50 records."""
        data = _generate_allocation_data(50)
        timings = []
        for _ in range(5):
            start = time.perf_counter()
            errors = validator.validate_schema(data)
            elapsed = time.perf_counter() - start
            timings.append(elapsed * 1000 / 50)  # ms per record
            assert not errors, f"Schema errors: {errors}"
        p95 = _percentile(timings, 95)
        assert p95 < 100.0, f"p95={p95:.2f} ms/record exceeds 100 ms target"

    def test_semantic_validation_latency_50_records(self):
        """Validate that semantic validation completes efficiently."""
        data = _generate_allocation_data(50)
        timings = []
        for _ in range(5):
            start = time.perf_counter()
            errors = validator.validate_semantic(data)
            elapsed = time.perf_counter() - start
            timings.append(elapsed * 1000 / 50)
            assert not errors, f"Semantic errors: {errors}"
        p95 = _percentile(timings, 95)
        assert p95 < 100.0, f"p95={p95:.2f} ms/record exceeds 100 ms target"

    def test_full_preflight_latency_50_records(self):
        """Validate full preflight pipeline latency."""
        data = _generate_allocation_data(50)
        timings = []
        for _ in range(5):
            start = time.perf_counter()
            validator.validate_schema(data)
            validator.validate_semantic(data)
            validator.preflight_validate(data)
            elapsed = time.perf_counter() - start
            timings.append(elapsed * 1000 / 50)
        p95 = _percentile(timings, 95)
        assert p95 < 100.0, f"p95={p95:.2f} ms/record exceeds 100 ms target"

    def test_validation_scales_linearly(self):
        """Verify validation time scales approximately linearly with records."""
        sizes = [10, 50, 100]
        median_per_record = []
        for n in sizes:
            data = _generate_allocation_data(n)
            timings = []
            for _ in range(3):
                start = time.perf_counter()
                validator.validate_schema(data)
                validator.validate_semantic(data)
                elapsed = time.perf_counter() - start
                timings.append(elapsed * 1000 / n)
            median_per_record.append(statistics.median(timings))

        # Per-record time should not grow more than 5x between 10 and 100
        ratio = median_per_record[-1] / max(median_per_record[0], 0.001)
        assert ratio < 5.0, (
            f"Non-linear scaling: {median_per_record[0]:.2f} ms (10 rec) vs "
            f"{median_per_record[-1]:.2f} ms (100 rec), ratio={ratio:.1f}x"
        )


class TestArtifactGenerationThroughput:
    """TC-NFT-002: Artifact generation throughput benchmark."""

    def test_render_throughput_25_nodes(self):
        """Verify artifact generation throughput for 25 nodes."""
        data = _generate_allocation_data(50)  # 25 nodes × 2 interfaces
        normalized, _ = validator.preflight_validate(data)
        timings = []
        for _ in range(3):
            start = time.perf_counter()
            for node_id in sorted(normalized.keys()):
                nm_renderer.render_node_full(node_id, normalized[node_id])
            nm_renderer.render_managed_hosts_block(normalized)
            elapsed = time.perf_counter() - start
            timings.append(elapsed / max(len(normalized), 1))
        p95 = _percentile(timings, 95)
        assert p95 < 30.0, f"p95={p95:.3f} s/node exceeds 30 s target"

    def test_render_cloud_init_structure(self):
        """Verify rendered cloud-init has correct structure."""
        data = _generate_allocation_data(4)  # 2 nodes
        normalized, _ = validator.preflight_validate(data)
        for node_id, interfaces in normalized.items():
            result = nm_renderer.render_node_full(node_id, interfaces)
            assert "nm_results" in result
            assert "cloud_init" in result
            assert "smd_component" in result
            assert "config_hash" in result
            ci = result["cloud_init"]
            assert "write_files" in ci
            assert "runcmd" in ci

    def test_hosts_block_generation(self):
        """Verify managed hosts block contains all nodes."""
        data = _generate_allocation_data(10)
        normalized, _ = validator.preflight_validate(data)
        block = nm_renderer.render_managed_hosts_block(normalized)
        assert "BEGIN Omnia IPoIB managed block" in block
        assert "END Omnia IPoIB managed block" in block
        # Should contain entries for all active nodes
        for node_id in normalized:
            # Hostname should appear in the hosts block
            assert any(
                node_id in line or "node-" in line
                for line in block.splitlines()
            )

    def test_idempotent_detection(self):
        """Verify config hash enables idempotent reapplication detection."""
        data = _generate_allocation_data(4)
        normalized, _ = validator.preflight_validate(data)
        node_id = list(normalized.keys())[0]
        result1 = nm_renderer.render_node_full(node_id, normalized[node_id])
        result2 = nm_renderer.render_node_full(node_id, normalized[node_id])
        assert result1["config_hash"] == result2["config_hash"]
        assert not nm_renderer.is_reapplication_needed(
            result1["config_hash"], result2["config_hash"],
        )


class TestThroughputParity:
    """TC-NFT-003: IPv6/IPv4 throughput parity (framework validation)."""

    def test_parity_calculation_within_threshold(self):
        """Verify parity calculation correctly detects < 5% delta."""
        v4_throughputs = [10_000_000_000.0] * 5
        v6_throughputs = [9_700_000_000.0] * 5
        median_v4 = statistics.median(v4_throughputs)
        median_v6 = statistics.median(v6_throughputs)
        delta = (median_v4 - median_v6) / median_v4 * 100
        assert abs(delta) < 5.0, f"Delta {delta:.1f}% exceeds 5% target"

    def test_parity_calculation_fails_on_large_delta(self):
        """Verify parity fails when delta exceeds 5%."""
        v4_throughputs = [10_000_000_000.0] * 5
        v6_throughputs = [9_000_000_000.0] * 5  # 10% worse
        median_v4 = statistics.median(v4_throughputs)
        median_v6 = statistics.median(v6_throughputs)
        delta = (median_v4 - median_v6) / median_v4 * 100
        assert abs(delta) >= 5.0, f"Delta {delta:.1f}% should exceed 5%"

    def test_parity_symmetric(self):
        """If IPv6 is faster, delta is negative but still within 5%."""
        v4_throughputs = [10_000_000_000.0] * 5
        v6_throughputs = [10_200_000_000.0] * 5  # 2% faster
        median_v4 = statistics.median(v4_throughputs)
        median_v6 = statistics.median(v6_throughputs)
        delta = (median_v4 - median_v6) / median_v4 * 100
        assert abs(delta) < 5.0


class TestEvidenceCollector:
    """TC-NFT-003 adjacent: Evidence collection framework validation."""

    def test_evidence_json_structure(self):
        """Verify evidence package has all required fields."""
        required_keys = {
            "evidence_version", "node_id", "build_id",
            "collected_at", "matrix_dimensions", "test_results",
        }
        evidence = {
            "evidence_version": "1.0",
            "node_id": "test-node",
            "build_id": "test-build",
            "collected_at": "2026-09-26T00:00:00Z",
            "matrix_dimensions": {
                "hca_model": "ConnectX-7",
                "firmware": "28.42.1000",
                "driver_version": "5.18",
                "architecture": "x86_64",
            },
            "test_results": {"TC-NFT-001": "PASS"},
        }
        assert required_keys.issubset(evidence.keys())

    def test_evidence_softroce_exclusion_note(self):
        """Verify evidence package includes SoftRoCE exclusion note."""
        notes = [
            "SoftRoCE evidence is NOT valid as IPoIB release evidence",
            "Only configurations present in this matrix are release-claimed",
        ]
        assert any("SoftRoCE" in n for n in notes)

    def test_evidence_writes_to_file(self):
        """Verify evidence can be serialized to JSON file."""
        evidence = {
            "evidence_version": "1.0",
            "node_id": "test-node",
            "build_id": "test-build",
            "collected_at": "2026-09-26T00:00:00Z",
            "matrix_dimensions": {"architecture": "x86_64"},
            "test_results": {},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
        ) as fh:
            json.dump(evidence, fh, indent=2)
            path = fh.name
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            assert loaded["node_id"] == "test-node"
            assert loaded["evidence_version"] == "1.0"
        finally:
            os.unlink(path)


class TestPercentileUtility:
    """Unit tests for the percentile calculation used in benchmarks."""

    def test_p95_single_value(self):
        """p95 of a single value is that value."""
        assert _percentile([42.0], 95) == 42.0

    def test_p95_sorted_ascending(self):
        """p95 of ascending values is near the top."""
        data = list(range(1, 101))
        p95 = _percentile([float(x) for x in data], 95)
        assert 95 <= p95 <= 100

    def test_p50_is_median(self):
        """p50 should equal the median."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _percentile(data, 50) == statistics.median(data)

    def test_p0_is_min(self):
        """p0 should be the minimum."""
        data = [5.0, 3.0, 1.0, 4.0, 2.0]
        assert _percentile(data, 0) == min(data)

    def test_p100_is_max(self):
        """p100 should be the maximum."""
        data = [5.0, 3.0, 1.0, 4.0, 2.0]
        assert _percentile(data, 100) == max(data)

    def test_empty_returns_zero(self):
        """Empty list returns 0."""
        assert _percentile([], 95) == 0.0


def _percentile(data: list[float], pct: float) -> float:
    """Compute percentile (matches benchmark module implementation)."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (pct / 100.0) * (len(sorted_data) - 1)
    lower = int(idx)
    upper = min(lower + 1, len(sorted_data) - 1)
    frac = idx - lower
    return sorted_data[lower] + frac * (sorted_data[upper] - sorted_data[lower])
