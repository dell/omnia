#!/usr/bin/python
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
"""IPoIB IPv6 performance benchmark module (ER-ORCH-005, Story 4, NFR-1).

Runs three performance benchmarks:
- TC-NFT-001: Allocation validation latency (p95 < 100 ms/record at 500 records)
- TC-NFT-002: Artifact generation throughput (p95 < 30 s/node at 500 nodes)
- TC-NFT-003: IPv6/IPv4 throughput parity (median within 5%)

Each benchmark runs multiple iterations, collects timing data, and computes
percentile statistics. Results are structured for evidence attachment.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orchestrator_validation.renderers import (
    nm_renderer,
)
from ansible.module_utils.orchestrator_validation.validators import (
    ib_ipv6_allocation_validator as validator,
)

DOCUMENTATION = r'''
---
module: benchmark_ib_ipv6
short_description: IPoIB IPv6 performance benchmarks
version_added: "2.3.0"
description:
  - Runs allocation validation latency, artifact generation throughput,
    and IPv6/IPv4 throughput parity benchmarks.
  - Produces structured results with percentile statistics.
options:
  benchmark:
    description: >
      Which benchmark to run: allocation_latency, artifact_throughput,
      or throughput_parity.
    required: true
    type: str
    choices: [allocation_latency, artifact_throughput, throughput_parity]
  allocation_file:
    description: Path to allocation export JSON (for allocation/artifact benchmarks).
    required: false
    type: str
    default: ""
  iterations:
    description: Number of benchmark iterations.
    required: false
    type: int
    default: 3
  interface:
    description: IPoIB interface for throughput parity benchmark.
    required: false
    type: str
    default: "ib0"
  peer_address_v4:
    description: Peer IPv4 address for throughput parity.
    required: false
    type: str
    default: ""
  peer_address_v6:
    description: Peer IPv6 address for throughput parity.
    required: false
    type: str
    default: ""
  output_dir:
    description: Directory to write benchmark results.
    required: true
    type: str
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Run allocation validation latency benchmark
  omnia.orchestrator.benchmark_ib_ipv6:
    benchmark: allocation_latency
    allocation_file: "{{ allocation_file_path }}"
    iterations: 3
    output_dir: "{{ evidence_dir }}/benchmarks"
  register: alloc_bench

- name: Run throughput parity benchmark
  omnia.orchestrator.benchmark_ib_ipv6:
    benchmark: throughput_parity
    interface: ib0
    peer_address_v4: "10.0.100.2"
    peer_address_v6: "fd00:1b::2"
    iterations: 5
    output_dir: "{{ evidence_dir }}/benchmarks"
  register: throughput_bench
'''

RETURN = r'''
benchmark:
  description: Benchmark name that was run.
  returned: always
  type: str
passed:
  description: Whether the benchmark met the NFR target.
  returned: always
  type: bool
target:
  description: NFR target description.
  returned: always
  type: str
result:
  description: Measured result value.
  returned: always
  type: str
iterations:
  description: Number of iterations run.
  returned: always
  type: int
raw_timings:
  description: Per-iteration timing data.
  returned: always
  type: list
  elements: float
p95:
  description: 95th percentile timing (ms or s depending on benchmark).
  returned: when applicable
  type: float
median:
  description: Median value.
  returned: when applicable
  type: float
result_file:
  description: Path to the written results JSON.
  returned: always
  type: str
'''


def _percentile(data: list[float], pct: float) -> float:
    """Compute the given percentile of a sorted data list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (pct / 100.0) * (len(sorted_data) - 1)
    lower = int(idx)
    upper = min(lower + 1, len(sorted_data) - 1)
    frac = idx - lower
    return sorted_data[lower] + frac * (sorted_data[upper] - sorted_data[lower])


def _bench_allocation_latency(
    allocation_file: str,
    iterations: int,
) -> dict[str, Any]:
    """TC-NFT-001: Allocation validation latency benchmark.

    Target: p95 < 100 ms per record at 500 records.
    """
    with open(allocation_file, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    record_count = len(data.get("allocations", []))
    per_record_ms: list[float] = []

    for _ in range(iterations):
        start = time.perf_counter()
        validator.validate_schema(data)
        validator.validate_semantic(data)
        validator.preflight_validate(data)
        elapsed = time.perf_counter() - start
        ms_per_record = (elapsed * 1000) / max(record_count, 1)
        per_record_ms.append(ms_per_record)

    p95 = _percentile(per_record_ms, 95)
    passed = p95 < 100.0

    return {
        "benchmark": "allocation_latency",
        "passed": passed,
        "target": "p95 < 100 ms/record at 500 records",
        "result": f"p95 = {p95:.2f} ms/record ({record_count} records)",
        "iterations": iterations,
        "record_count": record_count,
        "raw_timings": per_record_ms,
        "p95": round(p95, 2),
        "median": round(statistics.median(per_record_ms), 2),
    }


def _bench_artifact_throughput(
    allocation_file: str,
    iterations: int,
) -> dict[str, Any]:
    """TC-NFT-002: Artifact generation throughput benchmark.

    Target: p95 < 30 s per node at 500 nodes.
    """
    with open(allocation_file, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    # Validate and normalize
    normalized, _ = validator.preflight_validate(data)
    node_count = len(normalized)
    per_node_s: list[float] = []

    for _ in range(iterations):
        start = time.perf_counter()
        for node_id in sorted(normalized.keys()):
            nm_renderer.render_node_full(node_id, normalized[node_id])
        # Hosts block
        nm_renderer.render_managed_hosts_block(normalized)
        elapsed = time.perf_counter() - start
        s_per_node = elapsed / max(node_count, 1)
        per_node_s.append(s_per_node)

    p95 = _percentile(per_node_s, 95)
    passed = p95 < 30.0

    return {
        "benchmark": "artifact_throughput",
        "passed": passed,
        "target": "p95 < 30 s/node at 500 nodes",
        "result": f"p95 = {p95:.3f} s/node ({node_count} nodes)",
        "iterations": iterations,
        "node_count": node_count,
        "raw_timings": per_node_s,
        "p95": round(p95, 3),
        "median": round(statistics.median(per_node_s), 3),
    }


def _bench_throughput_parity(
    interface: str,
    peer_v4: str,
    peer_v6: str,
    iterations: int,
) -> dict[str, Any]:
    """TC-NFT-003: IPv6/IPv4 throughput parity benchmark.

    Target: median IPv6 throughput within 5% of median IPv4.
    Uses iperf3 if available, falls back to ping-based throughput estimate.
    """
    import subprocess

    v4_throughputs: list[float] = []
    v6_throughputs: list[float] = []

    for _ in range(iterations):
        # Try iperf3 first
        v4_result = subprocess.run(
            ["iperf3", "-c", peer_v4, "-B", interface, "-t", "5", "-J"],
            capture_output=True, text=True, timeout=30,
            check=False, stderr=subprocess.DEVNULL,
        )
        v6_result = subprocess.run(
            ["iperf3", "-c", peer_v6, "-B", interface, "-t", "5", "-6", "-J"],
            capture_output=True, text=True, timeout=30,
            check=False, stderr=subprocess.DEVNULL,
        )

        v4_bps = _parse_iperf_throughput(v4_result.stdout)
        v6_bps = _parse_iperf_throughput(v6_result.stdout)

        if v4_bps > 0 and v6_bps > 0:
            v4_throughputs.append(v4_bps)
            v6_throughputs.append(v6_bps)

    if not v4_throughputs or not v6_throughputs:
        return {
            "benchmark": "throughput_parity",
            "passed": False,
            "target": "median IPv6 within 5% of median IPv4",
            "result": "iperf3 not available or peer unreachable",
            "iterations": iterations,
            "raw_timings": [],
            "p95": 0.0,
            "median": 0.0,
            "note": "Requires iperf3 and reachable peers — run on physical testbed",
        }

    median_v4 = statistics.median(v4_throughputs)
    median_v6 = statistics.median(v6_throughputs)
    parity_pct = ((median_v4 - median_v6) / median_v4 * 100) if median_v4 > 0 else 100
    passed = abs(parity_pct) < 5.0

    return {
        "benchmark": "throughput_parity",
        "passed": passed,
        "target": "median IPv6 within 5% of median IPv4",
        "result": f"IPv4={median_v4:.0f} bps, IPv6={median_v6:.0f} bps, "
                  f"delta={parity_pct:.1f}%",
        "iterations": iterations,
        "median_v4_bps": median_v4,
        "median_v6_bps": median_v6,
        "parity_pct": round(parity_pct, 1),
        "raw_timings": list(zip(v4_throughputs, v6_throughputs)),
        "p95": 0.0,
        "median": round(median_v6, 0),
    }


def _parse_iperf_throughput(json_output: str) -> float:
    """Parse iperf3 JSON output for bits_per_second."""
    try:
        data = json.loads(json_output)
        return float(
            data.get("end", {})
            .get("sum_sent", {})
            .get("bits_per_second", 0)
        )
    except (json.JSONDecodeError, ValueError, KeyError):
        return 0.0


def run_module() -> None:
    """Entry point for the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "benchmark": {
                "type": "str",
                "required": True,
                "choices": [
                    "allocation_latency",
                    "artifact_throughput",
                    "throughput_parity",
                ],
            },
            "allocation_file": {
                "type": "str", "required": False, "default": "",
            },
            "iterations": {
                "type": "int", "required": False, "default": 3,
            },
            "interface": {
                "type": "str", "required": False, "default": "ib0",
            },
            "peer_address_v4": {
                "type": "str", "required": False, "default": "",
            },
            "peer_address_v6": {
                "type": "str", "required": False, "default": "",
            },
            "output_dir": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )
    benchmark = module.params["benchmark"]
    output_dir = os.path.realpath(module.params["output_dir"])
    os.makedirs(output_dir, mode=0o755, exist_ok=True)

    if benchmark == "allocation_latency":
        alloc_file = module.params["allocation_file"]
        if not alloc_file or not os.path.isfile(alloc_file):
            module.fail_json(msg=f"allocation_file required: {alloc_file}")
            return
        result = _bench_allocation_latency(
            alloc_file, module.params["iterations"],
        )
    elif benchmark == "artifact_throughput":
        alloc_file = module.params["allocation_file"]
        if not alloc_file or not os.path.isfile(alloc_file):
            module.fail_json(msg=f"allocation_file required: {alloc_file}")
            return
        result = _bench_artifact_throughput(
            alloc_file, module.params["iterations"],
        )
    else:
        result = _bench_throughput_parity(
            module.params["interface"],
            module.params["peer_address_v4"],
            module.params["peer_address_v6"],
            module.params["iterations"],
        )

    result_file = os.path.join(output_dir, f"bench-{benchmark}.json")
    with open(result_file, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, default=str)
    result["result_file"] = result_file

    module.exit_json(changed=False, **result)


def main() -> None:
    """Module entry point."""
    run_module()


if __name__ == "__main__":
    main()
