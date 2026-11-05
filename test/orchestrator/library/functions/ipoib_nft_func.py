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

"""ER-ORCH-005 IPoIB non-functional benchmarks (TC-NFT-001/002).

Both benchmarks exercise the shipped product modules in-process against a
synthetic allocation export, so the measured cost is the product's own
validation and rendering path rather than a test reimplementation.
"""

import importlib.util
import time
from pathlib import Path
from typing import Any

from ..vars.ipoib_vars import (
    ALLOCATION_VALIDATOR_PATH,
    IPOIB_NFT_INTERFACES_PER_NODE,
    IPOIB_NFT_ITERATIONS,
    IPOIB_NFT_PREFIX,
    IPOIB_NFT_PREFIX_LENGTH,
    IPOIB_NFT_RENDER_NODES,
    IPOIB_NFT_RENDER_P95_S_PER_NODE,
    IPOIB_NFT_VALIDATION_P95_MS_PER_RECORD,
    IPOIB_NFT_VALIDATION_RECORDS,
    NM_RENDERER_PATH,
)

_ERRORS = (OSError, ImportError, RuntimeError, TypeError, ValueError, KeyError)
_RENDER_KEYS = frozenset({"nm_results", "cloud_init", "smd_component", "config_hash"})


def _result(success: bool, summary: str, fields, error: str = "") -> dict[str, Any]:
    return {"success": success, "details": summary, "fields": fields, "error": error}


def _product_module(parts: tuple[str, ...], name: str):
    """Load one shipped product module from the source tree by path."""
    path = Path(__file__).resolve().parents[4].joinpath(*parts)
    if not path.is_file():
        raise FileNotFoundError(f"ER-ORCH-005 product module not found: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _percentile(samples: list[float], pct: float) -> float:
    """Return the linearly interpolated *pct* percentile of *samples*."""
    if not samples:
        return 0.0
    ordered = sorted(samples)
    rank = (pct / 100.0) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (rank - lower) * (ordered[upper] - ordered[lower])


def _allocation_export(record_count: int) -> dict[str, Any]:
    """Return a schema-valid synthetic allocation export of *record_count* records."""
    records = []
    for index in range(record_count):
        node, iface = divmod(index, IPOIB_NFT_INTERFACES_PER_NODE)
        records.append({
            "allocation_id": f"alloc-{index:06d}",
            "node_id": f"x3000c0s{node}b0n0",
            "interface_id": f"ib{iface}",
            "hostname": f"node-{node:04d}",
            "address": f"{IPOIB_NFT_PREFIX}{node:04x}:{iface + 1}",
            "prefix_length": IPOIB_NFT_PREFIX_LENGTH,
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
        "snapshot_id": f"omnia-fvt-nft-{record_count}",
        "generated_at": "2026-01-01T00:00:00Z",
        "allocations": records,
    }


def check_ipoib_allocation_validation_latency(_host) -> dict[str, Any]:
    """TC-NFT-001: full preflight validation p95 stays under the per-record target."""
    summary = "IPoIB allocation validation latency"
    records = IPOIB_NFT_VALIDATION_RECORDS
    try:
        validator = _product_module(ALLOCATION_VALIDATOR_PATH, "omnia_nft_allocation_validator")
        data = _allocation_export(records)
        expected_nodes = -(-records // IPOIB_NFT_INTERFACES_PER_NODE)
        per_record_ms, problems, normalized = [], [], {}
        for _ in range(IPOIB_NFT_ITERATIONS):
            started = time.perf_counter()
            schema_errors = validator.validate_schema(data)
            semantic_errors = validator.validate_semantic(data)
            normalized, node_errors = validator.preflight_validate(data)
            per_record_ms.append((time.perf_counter() - started) * 1000 / records)
            if schema_errors or semantic_errors or node_errors:
                problems.append(
                    f"synthetic export rejected: schema={schema_errors[:2]} "
                    f"semantic={semantic_errors[:2]} nodes={list(node_errors)[:2]}"
                )
                break
        p95 = _percentile(per_record_ms, 95)
        fields = [
            ("Records", records),
            ("Iterations", len(per_record_ms)),
            ("p95 ms/record", f"{p95:.3f}"),
            ("Target ms/record", IPOIB_NFT_VALIDATION_P95_MS_PER_RECORD),
            ("Nodes normalized", f"{len(normalized)}/{expected_nodes}"),
        ]
        if not problems and len(normalized) != expected_nodes:
            problems.append(f"preflight normalized {len(normalized)} of {expected_nodes} nodes")
        if p95 >= IPOIB_NFT_VALIDATION_P95_MS_PER_RECORD:
            problems.append(
                f"p95 {p95:.3f} ms/record exceeds "
                f"{IPOIB_NFT_VALIDATION_P95_MS_PER_RECORD} ms"
            )
        return _result(not problems, summary, fields, "; ".join(problems))
    except _ERRORS as exc:
        return _result(False, summary, [("Records", records)], str(exc))


def check_ipoib_artifact_generation_throughput(_host) -> dict[str, Any]:
    """TC-NFT-002: per-node artifact rendering p95 stays under the target and is stable."""
    summary = "IPoIB artifact generation throughput"
    nodes = IPOIB_NFT_RENDER_NODES
    try:
        validator = _product_module(ALLOCATION_VALIDATOR_PATH, "omnia_nft_allocation_validator")
        renderer = _product_module(NM_RENDERER_PATH, "omnia_nft_nm_renderer")
        normalized, node_errors = validator.preflight_validate(
            _allocation_export(nodes * IPOIB_NFT_INTERFACES_PER_NODE)
        )
        if node_errors or len(normalized) != nodes:
            return _result(
                False, summary, [("Nodes", nodes)],
                f"preflight normalized {len(normalized)} of {nodes} nodes; "
                f"errors for {list(node_errors)[:3]}",
            )
        per_node_s, hashes, problems = [], {}, []
        for iteration in range(IPOIB_NFT_ITERATIONS):
            for node_id in sorted(normalized):
                started = time.perf_counter()
                rendered = renderer.render_node_full(node_id, normalized[node_id])
                per_node_s.append(time.perf_counter() - started)
                if iteration == 0:
                    missing = _RENDER_KEYS - set(rendered)
                    if missing:
                        problems.append(f"{node_id} render missing {sorted(missing)}")
                    hashes[node_id] = rendered.get("config_hash")
                elif rendered.get("config_hash") != hashes[node_id]:
                    problems.append(f"{node_id} config_hash changed between identical renders")
                elif renderer.is_reapplication_needed(hashes[node_id], rendered["config_hash"]):
                    problems.append(f"{node_id} unchanged input requests reapplication")
            if problems:
                break
        p95 = _percentile(per_node_s, 95)
        fields = [
            ("Nodes", nodes),
            ("Renders", len(per_node_s)),
            ("p95 s/node", f"{p95:.4f}"),
            ("Target s/node", IPOIB_NFT_RENDER_P95_S_PER_NODE),
            ("Idempotent config_hash", "yes" if not problems else "NO"),
        ]
        if p95 >= IPOIB_NFT_RENDER_P95_S_PER_NODE:
            problems.append(f"p95 {p95:.4f} s/node exceeds {IPOIB_NFT_RENDER_P95_S_PER_NODE} s")
        return _result(not problems, summary, fields, "; ".join(problems[:5]))
    except _ERRORS as exc:
        return _result(False, summary, [("Nodes", nodes)], str(exc))
