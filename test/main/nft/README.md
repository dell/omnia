# Non-Functional Tests (NFT) — Omnia Main

Non-Functional Tests validate **performance** and **idempotency** of the
`omnia.sh` setup and init operations. Unlike FVT (which verifies
correctness), NFT ensures that operations complete within acceptable
timeframes and produce consistent results across repeated executions.

---

## Test Cases

| TC ID | Test Name | Category | What It Validates |
|-------|-----------|----------|-------------------|
| NFT_MA_001 | `test_setup_venv_performance` | Performance | `omnia.sh --setup-venv --deps-only` completes within threshold |
| NFT_MA_002 | `test_init_performance` | Performance | `omnia.sh --init` completes within threshold |
| NFT_MA_003 | `test_setup_venv_idempotent` | Idempotency | Running `--setup-venv` twice produces no errors or state change |
| NFT_MA_004 | `test_init_idempotent` | Idempotency | Running `--init` twice leaves domain dirs unchanged |
| NFT_MA_005 | `test_check_deps_performance` | Performance | `omnia.sh --check-deps` completes within threshold |

---

## Performance Thresholds

| Operation | Threshold | Timeout | Rationale |
|-----------|-----------|---------|-----------|
| `--setup-venv --deps-only` | 300s (5 min) | 360s | pip + Galaxy install on first run |
| `--init` | 120s (2 min) | 180s | Domain log dir creation + input file copy |
| `--check-deps` | 10s | 30s | File scan only, no installs |

Thresholds are defined in `nft/test_performance.py` and can be adjusted
based on target hardware or network speed.

---

## Idempotency Checks

`test_setup_venv_idempotent` (NFT_MA_003) verifies:
1. First `--setup-venv --deps-only` run exits 0
2. Second run exits 0 (no error about existing dirs/files)
3. Venv and env file are still present after second run

`test_init_idempotent` (NFT_MA_004) verifies:
1. First `--init` run exits 0
2. Second run exits 0 (no error overwriting domain files)
3. Domain log directories and input directories are still present

---

## Prerequisites

NFT tests require a **fully deployed** environment. Run FVT first:

```bash
# Deploy and verify environment
bash run_validation.sh setup test
bash run_validation.sh init test

# Then run NFT
bash run_validation.sh nft test
```

---

## Running NFT

```bash
# Run all NFT tests
bash run_validation.sh nft test

# Run performance NFT only
bash run_validation.sh nft test --marker nft

# Run with verbose output
bash run_validation.sh nft test -v
```

---

## Test Execution Flow

```
nft/
├── test_performance.py    ← NFT_MA_001, NFT_MA_002, NFT_MA_005
│   ├── test_setup_venv_performance    (order=1)
│   ├── test_init_performance          (order=2)
│   └── test_check_deps_performance    (order=3)
│
└── test_idempotency.py    ← NFT_MA_003, NFT_MA_004
    ├── test_setup_venv_idempotent     (order=1)
    └── test_init_idempotent           (order=2)
```

Tests use `@pytest.mark.nft` and `@pytest.mark.order(n)` markers.

---

## Interpreting Results

| Result | Meaning |
|--------|---------|
| **PASSED** | Operation completed within threshold / idempotency verified |
| **FAILED (threshold)** | Operation succeeded but exceeded time threshold |
| **FAILED (rc)** | `omnia.sh` command failed (non-zero return code) |
| **FAILED (idempotency)** | Files or dirs missing / errors on second run |

---

## Adjusting Thresholds

Edit the constants in `nft/test_performance.py`:

```python
SETUP_VENV_THRESHOLD = 300   # 5 minutes
INIT_THRESHOLD = 120          # 2 minutes
CHECK_DEPS_THRESHOLD = 10    # 10 seconds
```

For air-gapped environments with Pulp, pip and Galaxy installs are fast
(local mirror). Adjust thresholds to reflect observed run times.
