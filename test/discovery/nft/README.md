# Non-Functional Tests (NFT) -- Discovery

Non-Functional Tests validate **performance** and **idempotency** for the
discovery playbook. Unlike FVT (which verifies correctness), NFT checks
operation duration and confirms that repeated execution does not introduce
errors.

---

## Test Cases

NFT IDs use `DISC_NFT_<SEQ>`: `DISC` identifies Discovery, `NFT`
identifies the test level, and `SEQ` is a stable three-digit sequence.

| TC ID | Test Name | Category | What It Validates |
|-------|-----------|----------|-------------------|
| DISC_NFT_001 | `test_precheck_performance` | Performance | Precheck completes within threshold |
| DISC_NFT_002 | `test_execute_performance` | Performance | Execute completes within threshold |
| DISC_NFT_003 | `test_cleanup_performance` | Performance | Cleanup completes within threshold |
| DISC_NFT_004 | `test_precheck_idempotent` | Idempotency | Precheck succeeds twice without errors |
| DISC_NFT_005 | `test_cleanup_idempotent` | Idempotency | Cleanup succeeds twice and output stays clean |

---

## Performance Thresholds

| Operation | Threshold | Timeout | Rationale |
|-----------|-----------|---------|-----------|
| Precheck | 60s (1 min) | 120s | Environment validation and OME connectivity |
| Execute | 600s (10 min) | 660s | OME discovery and report generation |
| Cleanup | 120s (2 min) | 180s | Artifact and credential removal |

Thresholds are defined in `nft/test_performance.py` and can be adjusted
based on target hardware capabilities.

---

## Idempotency Checks

The idempotency tests verify:

### Precheck Idempotency (DISC_NFT_004)
1. **First run** -- Precheck completes successfully
2. **Second run** -- Precheck completes successfully without errors

### Cleanup Idempotency (DISC_NFT_005)
1. **First run** -- Cleanup completes successfully
2. **Second run** -- Cleanup completes successfully without errors
3. **Post-check** -- Output directory and credentials are removed

---

## Prerequisites

Run these commands from `test/discovery/`. NFT requires a valid target
environment and input configuration. Running FVT precheck and validate
first is recommended:

```bash
# Validate prerequisites
./run_validation.sh fvt_discovery precheck verify
./run_validation.sh fvt_discovery validate verify

# Run NFT
./run_validation.sh nft_discovery test
```

---

## Running NFT

```bash
# Run all NFT tests
./run_validation.sh nft_discovery test

# Run NFT with verbose output
./run_validation.sh nft_discovery test -v

# Run NFT with debug output
./run_validation.sh nft_discovery test --debug
```

---

## Test Execution Flow

```
nft/
+-- test_performance.py    <- DISC_NFT_001, DISC_NFT_002, DISC_NFT_003
|   +-- test_precheck_performance    (order=1)
|   +-- test_execute_performance     (order=2)
|   +-- test_cleanup_performance     (order=3)
|
+-- test_idempotency.py    <- DISC_NFT_004, DISC_NFT_005
    +-- test_precheck_idempotent     (order=1)
    +-- test_cleanup_idempotent      (order=2)
```

Tests use `@pytest.mark.nft` and `@pytest.mark.order(n)` markers. Within the
performance tests, the markers enforce precheck -> execute -> cleanup.

---

## Interpreting Results

| Result | Meaning |
|--------|---------|
| **PASSED** | Operation completed within threshold / repeated run succeeded |
| **FAILED (threshold)** | Operation succeeded but exceeded time threshold |
| **FAILED (rc)** | Playbook execution failed (non-zero return code) |
| **FAILED (idempotency)** | Second run failed or post-checks did not pass |

---

## Adjusting Thresholds

Edit the constants in `nft/test_performance.py`:

```python
PRECHECK_THRESHOLD = 60    # 1 minute
EXECUTE_THRESHOLD = 600    # 10 minutes
CLEANUP_THRESHOLD = 120    # 2 minutes
```

For faster hardware, reduce thresholds. For CI/CD pipelines with shared
resources, consider increasing them.
