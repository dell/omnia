# Non-Functional Tests (NFT) — Image Build Manager

Non-Functional Tests validate **performance** and **idempotency** of the
image_build_manager playbook operations. Unlike FVT (which verifies
correctness), NFT ensures that operations complete within acceptable
timeframes and produce consistent results across repeated executions.

---

## Test Cases

| TC ID | Test Name | Category | What It Validates |
|-------|-----------|----------|-------------------|
| NFT_001 | `test_prepare_performance` | Performance | Prepare completes within threshold |
| NFT_002 | `test_build_performance` | Performance | Build completes within threshold |
| NFT_003 | `test_cleanup_performance` | Performance | Cleanup completes within threshold |
| NFT_004 | `test_prepare_idempotent` | Idempotency | Running prepare twice does not recreate containers |

---

## Performance Thresholds

| Operation | Threshold | Timeout | Rationale |
|-----------|-----------|---------|-----------|
| Prepare | 300s (5 min) | 360s | Container pull + systemd unit creation |
| Build | 3600s (60 min) | 3660s | Full image build for all architectures |
| Cleanup | 120s (2 min) | 180s | Container stop + artifact removal |

Thresholds are defined in `nft/test_performance.py` and can be adjusted
based on target hardware capabilities.

---

## Idempotency Checks

The idempotency test (`NFT_004`) verifies:

1. **First run** — Prepare completes successfully, containers are running
2. **Second run** — Prepare completes successfully without errors
3. **Post-check** — MinIO and Registry containers remain running, S3 buckets
   are intact after the second run

A failure indicates that the playbook is not idempotent — it may recreate
containers, lose data, or produce errors on re-execution.

---

## Prerequisites

NFT tests require a **fully deployed** environment with `OMNIA_DATA_PATH` and
`OMNIA_PROJECT_NAME` set on the target host (via `omnia.sh --setup-venv`).
Run FVT first:

```bash
# Deploy the environment
./run_validation.sh fvt_image_build_manager prepare test
./run_validation.sh fvt_image_build_manager build test --marker x86_64

# Then run NFT
./run_validation.sh nft_image_build_manager test
```

---

## Running NFT

```bash
# Run all NFT tests
./run_validation.sh nft_image_build_manager test

# Run NFT with verbose output
./run_validation.sh nft_image_build_manager test -v

# Run NFT with debug output
./run_validation.sh nft_image_build_manager test --debug
```

---

## Test Execution Flow

```
nft/
├── test_performance.py    ← NFT_001, NFT_002, NFT_003
│   ├── test_prepare_performance    (order=1)
│   ├── test_build_performance      (order=2)
│   └── test_cleanup_performance    (order=3)
│
└── test_idempotency.py    ← NFT_004
    └── test_prepare_idempotent     (order=1)
```

Tests use `@pytest.mark.nft` and `@pytest.mark.order(n)` markers.
Execution order is controlled by the `order` marker — performance tests
run first (prepare -> build -> cleanup), then idempotency.

---

## Interpreting Results

| Result | Meaning |
|--------|---------|
| **PASSED** | Operation completed within threshold / idempotency verified |
| **FAILED (threshold)** | Operation succeeded but exceeded time threshold |
| **FAILED (rc)** | Playbook execution failed (non-zero return code) |
| **FAILED (idempotency)** | Containers or buckets not stable after second run |

---

## Adjusting Thresholds

Edit the constants in `nft/test_performance.py`:

```python
PREPARE_THRESHOLD = 300   # 5 minutes
BUILD_THRESHOLD = 3600    # 60 minutes
CLEANUP_THRESHOLD = 120   # 2 minutes
```

For faster hardware, reduce thresholds. For CI/CD pipelines with shared
resources, consider increasing them.
