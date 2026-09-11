# Orchestrator negative tests

This suite retains both groups of negative coverage:

- `test_input_contracts.py`: 12 deterministic invalid-input and runner-safety
  checks (`ORCH_FVT_NEGATIVE_V001` through `V012`).
- `test_negative.py`: the 10 environment-aware cases inherited from PR #5220
  (`ORCH_FVT_NEGATIVE_V013` through `V022`).

Run all 22 test functions with:

```bash
cd test/orchestrator
./run_validation.sh fvt_orchestrator negative verify --marker negative
```

The negative area is verification-only. It never executes an Ansible
lifecycle phase.
