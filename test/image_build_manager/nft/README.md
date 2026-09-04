# Non-Functional Tests (NFT) — Image Build Manager

Non-Functional Tests validate **performance** and repeated prepare execution
for the image_build_manager playbook. Unlike FVT (which verifies correctness),
NFT checks operation duration and confirms that required services are
available after prepare is run twice.

---

## Test Cases

| TC ID | Test Name | Category | What It Validates |
|-------|-----------|----------|-------------------|
| NFT_001 | `test_prepare_performance` | Performance | Prepare completes within threshold |
| NFT_002 | `test_build_performance` | Performance | Build completes within threshold |
| NFT_003 | `test_cleanup_performance` | Performance | Cleanup completes within threshold |
| NFT_004 | `test_prepare_idempotent` | Idempotency | Prepare succeeds twice and required services remain available |

---

## Performance Thresholds

| Operation | Threshold | Timeout | Rationale |
|-----------|-----------|---------|-----------|
| Prepare | 300s (5 min) | 360s | Container pull + systemd unit creation |
| Build | 3600s (60 min) | 3660s | Full image build for all configured architectures |
| Cleanup | 120s (2 min) | 180s | Container stop + artifact removal |

Thresholds are defined in `nft/test_performance.py` and can be adjusted
based on target hardware capabilities.

---

## Idempotency Checks

The idempotency test (`NFT_004`) verifies:

1. **First run** — Prepare completes successfully
2. **Second run** — Prepare completes successfully without errors
3. **Post-check** — MinIO and Registry are running and the expected S3 buckets
   are present after the second run

A failure indicates that repeated prepare execution returned an error or left
MinIO, Registry, or the expected S3 buckets unavailable. The test verifies
service availability; it does not compare container IDs or prove that the
containers were never recreated.

---

## Prerequisites

Run these commands from `test/image_build_manager/`. NFT requires a valid
target environment, input configuration, and credentials; the NFT suite runs
its own prepare, build, and cleanup operations. Running FVT precheck and
validate first is recommended:

```bash
# Validate prerequisites
./run_validation.sh fvt_image_build_manager precheck verify
./run_validation.sh fvt_image_build_manager validate verify

# Run NFT (includes cleanup)
./run_validation.sh nft_image_build_manager test
```

NFT_003 executes the cleanup tag. A full NFT run therefore removes local
MinIO/registry data and services, build output/logs, and
`image_build_credentials.yml` with its vault key. The default MinIO flow also
removes s3cmd configuration. External PowerScale S3 storage and
`/root/.s3cfg` are retained. Before a later credential-dependent run, rerun
`./setup_env.sh --set-domain-creds` on the execution OIM.

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

Tests use `@pytest.mark.nft` and `@pytest.mark.order(n)` markers. Within the
performance tests, the markers enforce prepare -> build -> cleanup. NFT_004 is
also marked `order=1`; its position relative to NFT_001 follows pytest's
collection order, and it independently executes prepare twice.

---

## Interpreting Results

| Result | Meaning |
|--------|---------|
| **PASSED** | Operation completed within threshold / repeated prepare and post-checks succeeded |
| **FAILED (threshold)** | Operation succeeded but exceeded time threshold |
| **FAILED (rc)** | Playbook execution failed (non-zero return code) |
| **FAILED (idempotency)** | Second prepare failed, or a required container or bucket was unavailable afterward |

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
